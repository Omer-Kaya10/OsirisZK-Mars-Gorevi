"""Uçtan uca duman testi: sentetik veri → hazırla → klasik ML → derin öğrenme → tahmin → oyun varlıkları.
Gerçek klasörlere dokunmaz: her şey geçici bir çalışma klasörüne ve oyunun geçici bir kopyasına yazılır.
Kullanım: python tests/run_smoke_test.py [--keep] [--no-dl]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ML = Path(__file__).resolve().parents[1]
GAME = ML.parent
sys.path.insert(0, str(ML / "tests"))
from make_synthetic_datasets import make  # noqa: E402


def run(args, env):
    print("\n$ python " + " ".join(str(a) for a in args))
    r = subprocess.run([sys.executable, *map(str, args)], cwd=ML, env=env)
    if r.returncode:
        sys.exit(f"✗ Başarısız: {args[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-dl", action="store_true")
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp(prefix="osiris_ml_test_"))
    env = {**os.environ, "OSIRIS_ML_WORKDIR": str(tmp / "work"), "PYTHONIOENCODING": "utf-8"}
    data = make(tmp / "synthetic", n=18)
    game_copy = tmp / "game"
    (game_copy / "assets" / "terrain").mkdir(parents=True)
    shutil.copy(GAME / "assets" / "terrain" / "terrain_classes.json", game_copy / "assets" / "terrain")
    run(["scripts/01_prepare_dataset.py", *data["zips"], *data["dirs"], "--ai4mars-patches", "4"], env)
    run(["scripts/02_train_ml.py", "--domain", "surface", "--models", "rf", "svm"], env)
    run(["scripts/02_train_ml.py", "--domain", "orbital", "--models", "rf"], env)
    if not a.no_dl:
        run(["scripts/03_train_dl.py", "--domain", "surface", "--arch", "marsnet", "--no-pretrained", "--epochs", "10", "--img", "96", "--batch", "32", "--workers", "0"], env)
        run(["scripts/03_train_dl.py", "--domain", "orbital", "--arch", "resnet18", "--no-pretrained", "--epochs", "1", "--img", "96", "--batch", "32", "--workers", "0", "--no-onnx"], env)
        run(["scripts/04_predict.py", "--model", tmp / "work" / "models" / "dl_surface_marsnet.pt", "--input", data["dirs"][2], "--out", tmp / "work" / "reports" / "pred_dl.csv"], env)
    model = tmp / "work" / "models" / "ml_surface.joblib"   # doku seçimi için en kararlı model
    run(["scripts/04_predict.py", "--model", model, "--input", data["dirs"][2], "--out", tmp / "work" / "reports" / "pred.csv"], env)
    run(["scripts/05_build_game_assets.py", "--model", model, "--images", data["dirs"][2], "--min-conf", "0.3",
         "--hirise-image", data["hirise_image"], "--hirise-mpp", "0.25", "--orbital-model", tmp / "work" / "models" / "ml_orbital.joblib",
         "--game-root", game_copy], env)
    man = json.loads((game_copy / "assets" / "terrain" / "manifest.json").read_text(encoding="utf-8"))
    print("\nmanifest:", json.dumps({k: man[k] for k in ("source", "selection", "macro", "materialMap")}, ensure_ascii=False))
    assert man["macro"] and man["materialMap"], "makro/malzeme haritası üretilmedi"
    assert man["source"] == "photos", f"5 sınıfın hepsinde fotoğraf dokusu bekleniyordu: {man['source']}"
    for q in ("low", "medium", "high"):
        for k, rel in man["quality"][q]["textures"].items():
            assert (game_copy / "assets" / "terrain" / rel).exists(), rel
    print(f"\n✓ Duman testi geçti. Çalışma klasörü: {tmp}")
    if not a.keep:
        shutil.rmtree(tmp, ignore_errors=True)
    else:
        print(f"(--keep) Oyun varlıkları: {game_copy / 'assets' / 'terrain'}")


if __name__ == "__main__":
    main()
