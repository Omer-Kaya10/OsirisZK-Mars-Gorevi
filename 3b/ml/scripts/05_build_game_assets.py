"""5. ADIM — Model/etiket sonuçlarından oyun varlıklarını üret (dokular + makro albedo + malzeme haritası).

Yakın zemin (yüzey, Curiosity/AI4Mars/kendi fotoğraflarınız):
  Her zemin sınıfı için en güvenilir fotoğraflar seçilir, zemin bölgesi kesilir, renkleri eşitlenir, 2×2 mozaik +
  dikişsiz döşeme yapılır ve 3 kalitede yazılır: assets/terrain/textures/{low,medium,high}/<sınıf>.jpg (+ _h.png yükseklik)
Uzak arazi (yörünge, HiRISE):
  --hirise-image verilirse oyun haritası (212 m) kadarlık bölge makro albedo olur; --orbital-model verilirse
  kayan pencereyle sınıflandırılıp malzeme haritası üretilir (oyun kum/kaya/çakıl/toz dağılımını buradan alır).
Son olarak assets/terrain/manifest.json yazılır; oyun açılışta bunu okur.

Örnekler:
  # Etiketlerle (model gerekmez):
  python scripts/05_build_game_assets.py --from-labels
  # Yüzey modeli tahminleriyle + HiRISE görüntüsüyle:
  python scripts/05_build_game_assets.py --model models/dl_surface_resnet18.pt --images data/raw/msl-images ^
         --hirise-image data/raw/ESP_012345_1950_RED.browse.jpg --hirise-mpp 0.25 --orbital-model models/ml_orbital.joblib
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osiris_ml.config import GAME_ROOT, PROCESSED, class_keys, load_classes  # noqa: E402
from osiris_ml.datasets import IMG_EXT, open_image, read_index  # noqa: E402
from osiris_ml import texture_tools as tt  # noqa: E402

SIZES = {"low": 256, "medium": 512, "high": 1024}
MAP_SPAN_M = 212.0


def candidates_from_labels(index: Path, labels: list[str], per_class: int, seed: int) -> dict[str, list[dict]]:
    rows = read_index(index, "surface")
    rng = np.random.default_rng(seed)
    out: dict[str, list[dict]] = {k: [] for k in labels}
    for k in labels:
        lst = [r for r in rows if r["game_class"] == k and r["split"] in ("train", "val")]
        if lst:
            idx = rng.permutation(len(lst))[: per_class * 3]
            out[k] = [{**lst[i], "confidence": 1.0} for i in idx]
    return out


def candidates_from_model(model: str, images: list[str], labels: list[str], per_class: int, min_conf: float) -> dict[str, list[dict]]:
    from PIL import Image
    from osiris_ml.predictor import Predictor
    pred = Predictor(model)
    files: list[Path] = []
    for s in images:
        p = Path(s)
        files += sorted(q for q in p.rglob("*") if q.suffix.lower() in IMG_EXT) if p.is_dir() else [p]
    scored: dict[str, list[dict]] = {k: [] for k in labels}
    for i in range(0, len(files), 32):
        chunk = files[i:i + 32]
        P = pred.predict_proba([tt.ground_region(Image.open(f).convert("RGB"), False) for f in chunk])
        for f, p in zip(chunk, P):
            k = int(p.argmax())
            if p[k] >= min_conf:
                scored[labels[k]].append({"path": str(f), "crop": "", "confidence": float(p[k])})
        print(f"[sınıflandırma] {min(i + 32, len(files))}/{len(files)}", end="\r" if sys.stdout.isatty() else "\n")
    print()
    return {k: sorted(v, key=lambda r: -r["confidence"])[: per_class * 3] for k, v in scored.items()}


def build_textures(cands: dict[str, list[dict]], labels: list[str], per_class: int, out_root: Path, seed: int) -> tuple[dict, dict, dict]:
    tex, hts, prov = {q: {} for q in SIZES}, {q: {} for q in SIZES}, {}
    for k in labels:
        rows = cands.get(k, [])
        patches = []
        for j, r in enumerate(rows):
            try:
                im = open_image(r)
            except Exception as e:
                print(f"  ⚠ {r['path']}: {e}"); continue
            p = tt.best_square(tt.ground_region(im, bool(r.get("crop"))), seed=seed + j)
            if min(p.size) >= 48:
                patches.append((p, r))
            if len(patches) >= per_class:
                break
        if not patches:
            print(f"[{k}] fotoğraf yok → oyun prosedürel dokuyu kullanacak")
            continue
        stats = [tt.lab_stats(p) for p, _ in patches]
        mean = np.median([s[0] for s in stats], axis=0); std = np.median([s[1] for s in stats], axis=0)
        # En dokulu 4 yama mozaiğe girer
        ranked = sorted(patches, key=lambda pr: -np.asarray(pr[0].convert("L"), np.float32).std())
        chosen = [tt.match_color(p, mean, std) for p, _ in ranked[:4]]
        prov[k] = {"images": [Path(r["path"]).name for _, r in ranked[:4]], "candidates": len(patches),
                   "mean_confidence": float(np.mean([r.get("confidence", 1.0) for _, r in patches]))}
        for q, size in SIZES.items():
            d = out_root / "textures" / q
            d.mkdir(parents=True, exist_ok=True)
            tile = tt.compose_tile(chosen, size)
            tile.save(d / f"{k}.jpg", quality=92)
            tt.height_map(tile).save(d / f"{k}_h.png")
            tex[q][k] = f"textures/{q}/{k}.jpg"; hts[q][k] = f"textures/{q}/{k}_h.png"
        print(f"[{k}] {len(patches)} yama → doku yazıldı ({', '.join(prov[k]['images'][:2])}…)")
    return tex, hts, prov


def orbital_assets(args, labels: list[str], out_root: Path) -> tuple[dict | None, dict | None]:
    if not args.hirise_image:
        return None, None
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    im = Image.open(args.hirise_image).convert("L")
    span_px = int(round(MAP_SPAN_M / args.hirise_mpp))
    w, h = im.size
    if span_px > min(w, h):
        print(f"⚠ Görüntü {MAP_SPAN_M} m'yi kapsamıyor ({w}×{h}px, {args.hirise_mpp} m/px); tamamı kullanılacak.")
        span_px = min(w, h)
    cx, cy = (args.hirise_center or [w // 2, h // 2])
    x0, y0 = int(np.clip(cx - span_px // 2, 0, w - span_px)), int(np.clip(cy - span_px // 2, 0, h - span_px))
    crop = im.crop((x0, y0, x0 + span_px, y0 + span_px))
    tt.normalize_orbital(crop, 1024).save(out_root / "macro_hirise.png")
    macro = {"image": "macro_hirise.png", "source": Path(args.hirise_image).name, "meters_per_pixel": args.hirise_mpp, "crop_px": [x0, y0, span_px]}
    print(f"[makro] {Path(args.hirise_image).name} → macro_hirise.png ({span_px}px = {MAP_SPAN_M:.0f} m)")
    if not (args.orbital_model or args.heuristic_map):
        return macro, None
    G = 32                                                       # 32×32 pencere ızgarası
    win = span_px // G
    W = np.zeros((G, G, 5), np.float32)
    if args.orbital_model:
        from osiris_ml.predictor import Predictor
        pred = Predictor(args.orbital_model)
        tiles = [crop.crop((i * win, j * win, (i + 1) * win, (j + 1) * win)).convert("RGB") for j in range(G) for i in range(G)]
        P = np.concatenate([pred.predict_proba(tiles[k:k + 64]) for k in range(0, len(tiles), 64)])
        W = P.reshape(G, G, -1)
    else:                                                       # sezgisel: koyu-düz=kum, parlak-düz=toz, dokulu=çakıl/kaya
        g = np.asarray(crop, np.float32) / 255
        for j in range(G):
            for i in range(G):
                t = g[j * win:(j + 1) * win, i * win:(i + 1) * win]
                m, s = t.mean(), t.std()
                W[j, i] = [0.4, max(0, .35 - m) * 3 * (s < .08), max(0, s - .12) * 4 * (m > .45), max(0, s - .1) * 3, max(0, m - .62) * 3 * (s < .08)]
    W = W / np.maximum(1e-6, W.sum(-1, keepdims=True))
    from PIL import ImageFilter
    def chan(c):
        return Image.fromarray((W[..., c] * 255).astype(np.uint8)).resize((256, 256), Image.BILINEAR).filter(ImageFilter.GaussianBlur(2.5))
    rgb = Image.merge("RGB", [chan(labels.index("sand")), chan(labels.index("bedrock")), chan(labels.index("gravel"))])
    rgb.save(out_root / "material_map.png"); chan(labels.index("dust")).save(out_root / "material_map_dust.png")
    print("[malzeme haritası] material_map.png (R kum, G kaya, B çakıl) + material_map_dust.png")
    return macro, {"image": "material_map.png", "dust": "material_map_dust.png", "size": 256, "method": "model" if args.orbital_model else "heuristic"}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--from-labels", action="store_true", help="Model yerine index.csv'deki gerçek etiketleri kullan")
    ap.add_argument("--index", default=str(PROCESSED / "index.csv"))
    ap.add_argument("--model", help="Yüzey sınıflandırıcı (.pt / .joblib)")
    ap.add_argument("--images", nargs="*", default=[], help="Modelle sınıflandırılacak fotoğraf klasörleri")
    ap.add_argument("--per-class", type=int, default=12)
    ap.add_argument("--min-conf", type=float, default=0.6)
    ap.add_argument("--hirise-image", help="HiRISE görüntüsü (uzak arazi albedosu)")
    ap.add_argument("--hirise-mpp", type=float, default=0.25, help="Görüntünün metre/piksel çözünürlüğü (HiRISE tam çözünürlük ≈0.25)")
    ap.add_argument("--hirise-center", type=int, nargs=2, help="Kırpma merkezi (piksel x y)")
    ap.add_argument("--orbital-model", help="Yörünge sınıflandırıcı → malzeme haritası")
    ap.add_argument("--heuristic-map", action="store_true", help="Model yoksa parlaklık/dokuya göre kaba malzeme haritası")
    ap.add_argument("--game-root", default=str(GAME_ROOT))
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    cfg = load_classes(Path(args.game_root) / "assets" / "terrain" / "terrain_classes.json")
    labels = class_keys(cfg)
    out_root = Path(args.game_root) / "assets" / "terrain"
    out_root.mkdir(parents=True, exist_ok=True)
    if args.model:
        cands = candidates_from_model(args.model, args.images, labels, args.per_class, args.min_conf)
        mode = f"model:{Path(args.model).name}"
    elif args.from_labels:
        cands = candidates_from_labels(Path(args.index), labels, args.per_class, args.seed)
        mode = "labels"
    else:
        cands, mode = {}, "none"
    tex, hts, prov = build_textures(cands, labels, args.per_class, out_root, args.seed) if cands else ({q: {} for q in SIZES}, {q: {} for q in SIZES}, {})
    macro, matmap = orbital_assets(args, labels, out_root)
    n = len(prov)
    manifest = {
        "version": 1, "source": "photos" if n == 5 else ("mixed" if n else "procedural"),
        "generated": dt.datetime.now().isoformat(timespec="seconds"), "selection": mode,
        "quality": {q: {"size": s, "textures": tex[q], "heights": hts[q]} for q, s in SIZES.items()},
        "macro": macro, "materialMap": matmap, "provenance": prov,
        "note": "05_build_game_assets.py tarafından üretildi. Sınıfların fizik değerleri terrain_classes.json'dadır.",
    }
    with open(out_root / "manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
    print(f"✓ {out_root / 'manifest.json'} · fotoğraf dokulu sınıf: {n}/5 · makro: {'var' if macro else 'yok'} · malzeme haritası: {'var' if matmap else 'yok'}")


if __name__ == "__main__":
    main()
