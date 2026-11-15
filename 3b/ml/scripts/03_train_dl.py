"""3. ADIM — Derin öğrenme (PyTorch, evrişimli sinir ağı).

Mimariler: resnet18 · mobilenet_v3_small · efficientnet_b0 (ImageNet ön eğitimli, transfer öğrenme) · marsnet (küçük, internetsiz)
Sınıf ağırlıklı kayıp + etiket yumuşatma, AdamW + kosinüs öğrenme oranı, erken durdurma (doğrulama macro-F1), CUDA'da karma hassasiyet.
Yörünge (HiRISE) verisinde 90° döndürme/dikey çevirme artırımı açılır; yüzey verisinde ufuk yönü korunur.

Örnek:
  python scripts/03_train_dl.py --domain surface --arch resnet18 --epochs 20
  python scripts/03_train_dl.py --domain orbital --arch mobilenet_v3_small --img 160
  python scripts/03_train_dl.py --domain surface --arch marsnet --no-pretrained     (internet yoksa)
Çıktı: models/dl_<alan>_<mimari>.pt · models/dl_<alan>.onnx · reports/dl_<alan>_<mimari>.json (+ karışıklık matrisi)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osiris_ml.config import MODELS, PROCESSED, REPORTS, class_keys, ensure_dirs, load_classes  # noqa: E402
from osiris_ml.datasets import open_image, read_index  # noqa: E402
from osiris_ml.evaluation import metrics, save_confusion_png, save_report  # noqa: E402

import torch  # noqa: E402
import torch.nn as nn  # noqa: E402
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler  # noqa: E402

MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


class MarsNet(nn.Module):
    """İnternetsiz eğitim için küçük CNN (~0.4 M parametre)."""
    def __init__(self, n: int):
        super().__init__()
        def blk(i, o):
            return nn.Sequential(nn.Conv2d(i, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                                 nn.Conv2d(o, o, 3, padding=1, bias=False), nn.BatchNorm2d(o), nn.ReLU(inplace=True), nn.MaxPool2d(2))
        self.f = nn.Sequential(blk(3, 32), blk(32, 64), blk(64, 128), blk(128, 160))
        self.head = nn.Sequential(nn.AdaptiveAvgPool2d(1), nn.Flatten(), nn.Dropout(0.3), nn.Linear(160, n))

    def forward(self, x):
        return self.head(self.f(x))


def build_model(arch: str, n: int, pretrained: bool) -> nn.Module:
    if arch == "marsnet":
        return MarsNet(n)
    import torchvision.models as tvm
    weights = None
    if pretrained:
        try:
            weights = {"resnet18": tvm.ResNet18_Weights.DEFAULT, "mobilenet_v3_small": tvm.MobileNet_V3_Small_Weights.DEFAULT,
                       "efficientnet_b0": tvm.EfficientNet_B0_Weights.DEFAULT}[arch]
        except Exception:  # eski torchvision
            weights = None
    try:
        m = getattr(tvm, arch)(weights=weights)
    except Exception as e:  # ağırlık indirilemedi (internet yok)
        print(f"⚠ Ön eğitimli ağırlık alınamadı ({e}); rastgele başlatılıyor.")
        m = getattr(tvm, arch)(weights=None)
    if arch == "resnet18":
        m.fc = nn.Linear(m.fc.in_features, n)
    elif arch == "mobilenet_v3_small":
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n)
    elif arch == "efficientnet_b0":
        m.classifier[-1] = nn.Linear(m.classifier[-1].in_features, n)
    return m


class TerrainDataset(Dataset):
    def __init__(self, rows, labels, tf):
        self.rows, self.labels, self.tf = rows, labels, tf

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        return self.tf(open_image(r)), self.labels.index(r["game_class"])


def transforms(img: int, train: bool, orbital: bool):
    import torchvision.transforms as T
    if not train:
        return T.Compose([T.Resize((img, img)), T.ToTensor(), T.Normalize(MEAN, STD)])
    aug = [T.RandomResizedCrop(img, scale=(0.55, 1.0), ratio=(0.8, 1.25)), T.RandomHorizontalFlip()]
    if orbital:  # yukarıdan çekimde yön yok
        aug += [T.RandomVerticalFlip(), T.RandomChoice([T.RandomRotation((a, a)) for a in (0, 90, 180, 270)])]
    aug += [T.ColorJitter(brightness=0.25, contrast=0.25, saturation=0.1), T.ToTensor(), T.Normalize(MEAN, STD)]  # ton (hue) değişmez: Mars renkleri ayırt edicidir
    return T.Compose(aug)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    ys, ps, probs = [], [], []
    for x, y in loader:
        out = model(x.to(device)).float().softmax(1).cpu()
        ys.append(y); ps.append(out.argmax(1)); probs.append(out)
    if not ys:
        return np.array([]), np.array([]), np.zeros((0, 1))
    return torch.cat(ys).numpy(), torch.cat(ps).numpy(), torch.cat(probs).numpy()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default=str(PROCESSED / "index.csv"))
    ap.add_argument("--domain", default="surface", choices=["surface", "orbital", "all"])
    ap.add_argument("--arch", default="resnet18", choices=["resnet18", "mobilenet_v3_small", "efficientnet_b0", "marsnet"])
    ap.add_argument("--no-pretrained", action="store_true")
    ap.add_argument("--img", type=int, default=192)
    ap.add_argument("--epochs", type=int, default=20)
    ap.add_argument("--batch", type=int, default=48)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--balanced-sampler", action="store_true", help="Ağırlıklı kayıp yerine dengeli örnekleyici")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-onnx", action="store_true")
    args = ap.parse_args()
    ensure_dirs()
    torch.manual_seed(args.seed); np.random.seed(args.seed)
    labels = class_keys(load_classes())
    rows = read_index(Path(args.index), args.domain)
    if not rows:
        sys.exit("Bu alan için etiketli kayıt yok. Önce 01_prepare_dataset.py çalıştırın.")
    split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    if not split["val"]:
        split["val"] = split["train"][::5]
    print({k: len(v) for k, v in split.items()})
    orbital = args.domain == "orbital"
    device = torch.device("cuda" if torch.cuda.is_available() else "mps" if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available() else "cpu")
    print(f"[aygıt] {device}")

    counts = np.bincount([labels.index(r["game_class"]) for r in split["train"]], minlength=len(labels)).astype(float)
    cw = np.where(counts > 0, 1.0 / np.sqrt(np.maximum(counts, 1)), 0.0)
    cw = cw / cw[counts > 0].mean()
    ds_tr = TerrainDataset(split["train"], labels, transforms(args.img, True, orbital))
    sampler = None
    if args.balanced_sampler:
        sw = [1.0 / counts[labels.index(r["game_class"])] for r in split["train"]]
        sampler = WeightedRandomSampler(sw, num_samples=len(sw), replacement=True)
    pin = device.type == "cuda"
    dl_tr = DataLoader(ds_tr, batch_size=args.batch, shuffle=sampler is None, sampler=sampler, num_workers=args.workers, pin_memory=pin, drop_last=len(ds_tr) > args.batch)
    mk = lambda s: DataLoader(TerrainDataset(split[s], labels, transforms(args.img, False, orbital)), batch_size=args.batch, num_workers=args.workers, pin_memory=pin)
    dl_va, dl_te = mk("val"), mk("test")

    model = build_model(args.arch, len(labels), not args.no_pretrained).to(device)
    crit = nn.CrossEntropyLoss(weight=None if args.balanced_sampler else torch.tensor(cw, dtype=torch.float32, device=device), label_smoothing=0.05)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr * 3, total_steps=max(1, args.epochs * len(dl_tr)), pct_start=0.15)
    scaler = torch.amp.GradScaler("cuda", enabled=device.type == "cuda")
    best_f1, best_state, wait, history = -1.0, None, 0, []
    tag = f"dl_{args.domain}_{args.arch}"
    for ep in range(1, args.epochs + 1):
        model.train(); t = time.time(); tot = n = 0
        for x, y in dl_tr:
            x, y = x.to(device, non_blocking=True), y.to(device, non_blocking=True)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.float16, enabled=device.type == "cuda"):
                loss = crit(model(x), y)
            scaler.scale(loss).backward(); scaler.step(opt); scaler.update(); sched.step()
            tot += loss.item() * len(y); n += len(y)
        yv, pv, _ = evaluate(model, dl_va, device)
        mv = metrics(yv, pv, labels)
        history.append({"epoch": ep, "loss": tot / max(1, n), "val_acc": mv["accuracy"], "val_macro_f1": mv["macro_f1"]})
        print(f"[{ep:02d}/{args.epochs}] kayıp {tot / max(1, n):.4f} · doğrulama acc {mv['accuracy']:.3f} macro-F1 {mv['macro_f1']:.3f} · {time.time() - t:.0f} sn")
        if mv["macro_f1"] > best_f1:
            best_f1, wait = mv["macro_f1"], 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            wait += 1
            if wait >= args.patience:
                print("[erken durdurma]"); break
    model.load_state_dict(best_state)
    yt, pt, _ = evaluate(model, dl_te, device)
    test_m = metrics(yt, pt, labels) if len(yt) else None
    if test_m:
        print(f"[test] acc {test_m['accuracy']:.3f} · macro-F1 {test_m['macro_f1']:.3f}")
    meta = {"arch": args.arch, "labels": labels, "img": args.img, "mean": MEAN, "std": STD, "domain": args.domain, "val_macro_f1": best_f1, "test": test_m}
    torch.save({"state_dict": best_state, "meta": meta}, MODELS / f"{tag}.pt")
    if not args.no_onnx:
        try:
            model.eval().cpu()
            onnx_path = MODELS / f"dl_{args.domain}.onnx"
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                kw = {"dynamo": False} if "dynamo" in torch.onnx.export.__code__.co_varnames else {}
                torch.onnx.export(model, torch.zeros(1, 3, args.img, args.img), str(onnx_path), input_names=["image"], output_names=["logits"],
                                  dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, **kw)
            with open(onnx_path.with_suffix(".json"), "w", encoding="utf-8") as fh:
                json.dump(meta, fh, ensure_ascii=False, indent=2)
            print(f"✓ ONNX: {onnx_path}")
        except Exception as e:
            print(f"⚠ ONNX dışa aktarılamadı: {e}")
    save_report({"meta": meta, "history": history, "counts": {k: len(v) for k, v in split.items()}, "test": test_m}, REPORTS / f"{tag}.json")
    if test_m:
        save_confusion_png(test_m, REPORTS / f"{tag}_confusion.png", f"Derin öğrenme ({args.arch}) · {args.domain}")
    print(f"✓ Model: {MODELS / (tag + '.pt')}")


if __name__ == "__main__":
    main()
