"""4. ADIM — Eğitilmiş modelle fotoğrafları sınıflandır.

Örnek:
  python scripts/04_predict.py --model models/dl_surface_resnet18.pt --input data/raw/yeni_fotograflar
  python scripts/04_predict.py --model models/ml_surface.joblib --input foto1.jpg foto2.jpg --out reports/tahmin.csv
Çıktı CSV: path, class, confidence, p_regolith … p_dust
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osiris_ml.config import REPORTS  # noqa: E402
from osiris_ml.datasets import IMG_EXT  # noqa: E402
from osiris_ml.predictor import Predictor  # noqa: E402


def gather(inputs: list[str]) -> list[Path]:
    out: list[Path] = []
    for s in inputs:
        p = Path(s)
        if p.is_dir():
            out += sorted(q for q in p.rglob("*") if q.suffix.lower() in IMG_EXT)
        elif p.suffix.lower() in IMG_EXT:
            out.append(p)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True)
    ap.add_argument("--input", nargs="+", required=True)
    ap.add_argument("--out", default=str(REPORTS / "predictions.csv"))
    ap.add_argument("--batch", type=int, default=32)
    args = ap.parse_args()
    from PIL import Image
    pred = Predictor(args.model)
    files = gather(args.input)
    if not files:
        sys.exit("Görüntü bulunamadı.")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "class", "confidence"] + [f"p_{k}" for k in pred.labels])
        for i in range(0, len(files), args.batch):
            chunk = files[i:i + args.batch]
            P = pred.predict_proba([Image.open(f).convert("RGB") for f in chunk])
            for f, p in zip(chunk, P):
                k = int(p.argmax())
                w.writerow([str(f), pred.labels[k], f"{p[k]:.4f}"] + [f"{v:.4f}" for v in p])
            print(f"{min(i + args.batch, len(files))}/{len(files)}", end="\r" if sys.stdout.isatty() else "\n")
    print(f"\n✓ {args.out}")


if __name__ == "__main__":
    main()
