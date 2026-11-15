"""2. ADIM — Klasik makine öğrenmesi (scikit-learn).

Renk + doku öznitelikleri (osiris_ml/features.py) çıkarılır, önbelleğe alınır; Random Forest, RBF-SVM ve
Histogram Gradient Boosting eğitilir. Doğrulama kümesindeki macro-F1'e göre en iyisi seçilir, test kümesinde raporlanır.

Örnek:
  python scripts/02_train_ml.py --domain surface
  python scripts/02_train_ml.py --domain orbital --models rf svm
Çıktı: models/ml_<alan>.joblib · reports/ml_<alan>.json · reports/ml_<alan>_confusion.png
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osiris_ml.config import MODELS, PROCESSED, REPORTS, class_keys, ensure_dirs, load_classes  # noqa: E402
from osiris_ml.datasets import open_image, read_index  # noqa: E402
from osiris_ml.evaluation import metrics, save_confusion_png, save_report  # noqa: E402
from osiris_ml.features import FEATURE_VERSION, extract  # noqa: E402


def _feat(row: dict) -> np.ndarray:
    return extract(open_image(row))


def featurize(rows: list[dict], cache: Path, jobs: int) -> np.ndarray:
    """Öznitelikleri paralel çıkarır; (yol, kırpma, sürüm) anahtarıyla önbellekte tutar."""
    from joblib import Parallel, delayed
    keys = [hashlib.md5(f"{r['path']}|{r['crop']}|{FEATURE_VERSION}".encode()).hexdigest() for r in rows]
    store: dict[str, np.ndarray] = {}
    if cache.exists():
        z = np.load(cache, allow_pickle=False)
        store = dict(zip(z["keys"].tolist(), z["X"]))
    todo = [i for i, k in enumerate(keys) if k not in store]
    if todo:
        print(f"[öznitelik] {len(todo)} görüntü işleniyor ({jobs} iş parçacığı)…")
        t = time.time()
        out = Parallel(n_jobs=jobs, batch_size=16)(delayed(_feat)(rows[i]) for i in todo)
        for i, v in zip(todo, out):
            store[keys[i]] = v
        np.savez_compressed(cache, keys=np.array(list(store.keys())), X=np.stack(list(store.values())))
        print(f"[öznitelik] {time.time() - t:.1f} sn")
    return np.stack([store[k] for k in keys])


def build_models(names: list[str], seed: int):
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.svm import SVC
    zoo = {
        "rf": RandomForestClassifier(n_estimators=400, min_samples_leaf=2, class_weight="balanced_subsample", n_jobs=-1, random_state=seed),
        # Olasılık çıktısı için kalibrasyon (sklearn 1.9+ SVC(probability=True) kullanımdan kalkıyor)
        "svm": make_pipeline(StandardScaler(), CalibratedClassifierCV(SVC(C=8.0, gamma="scale", class_weight="balanced", random_state=seed), cv=3, ensemble=False)),
        "hgb": HistGradientBoostingClassifier(max_iter=300, learning_rate=0.08, class_weight="balanced", random_state=seed),
    }
    return {n: zoo[n] for n in names}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--index", default=str(PROCESSED / "index.csv"))
    ap.add_argument("--domain", default="surface", choices=["surface", "orbital", "all"])
    ap.add_argument("--models", nargs="+", default=["rf", "svm", "hgb"], choices=["rf", "svm", "hgb"])
    ap.add_argument("--max-per-class", type=int, default=4000, help="Eğitim kümesinde sınıf başına üst sınır (dengesizlik/hız)")
    ap.add_argument("--jobs", type=int, default=-1)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    ensure_dirs()
    import joblib

    labels = class_keys(load_classes())
    rows = read_index(Path(args.index), args.domain)
    if not rows:
        sys.exit("Bu alan için etiketli kayıt yok. Önce 01_prepare_dataset.py çalıştırın.")
    rng = np.random.default_rng(args.seed)
    split = {s: [r for r in rows if r["split"] == s] for s in ("train", "val", "test")}
    # Sınıf başına üst sınır (yalnız eğitim)
    by_c: dict[str, list[dict]] = {}
    for r in split["train"]:
        by_c.setdefault(r["game_class"], []).append(r)
    split["train"] = [r for c, lst in by_c.items() for r in (rng.permutation(lst).tolist()[: args.max_per_class])]
    if not split["val"]:
        split["val"] = split["train"][::5]
    print({k: len(v) for k, v in split.items()})

    cache = PROCESSED / f"features_{args.domain}.npz"
    X = {s: featurize(v, cache, args.jobs) if v else np.zeros((0, 1)) for s, v in split.items()}
    y = {s: np.array([labels.index(r["game_class"]) for r in v]) for s, v in split.items()}

    best, best_name, best_f1, results = None, None, -1.0, {}
    for name, model in build_models(args.models, args.seed).items():
        t = time.time()
        model.fit(X["train"], y["train"])
        m = metrics(y["val"], model.predict(X["val"]), labels)
        results[name] = {"val": m, "fit_seconds": round(time.time() - t, 1)}
        print(f"[{name}] doğrulama acc={m['accuracy']:.3f} macro-F1={m['macro_f1']:.3f} ({results[name]['fit_seconds']} sn)")
        if m["macro_f1"] > best_f1:
            best, best_name, best_f1 = model, name, m["macro_f1"]

    test_m = metrics(y["test"], best.predict(X["test"]), labels) if len(y["test"]) else None
    if test_m:
        print(f"[en iyi: {best_name}] test acc={test_m['accuracy']:.3f} macro-F1={test_m['macro_f1']:.3f}")
    out = MODELS / f"ml_{args.domain}.joblib"
    joblib.dump({"model": best, "name": best_name, "labels": labels, "feature_version": FEATURE_VERSION, "domain": args.domain,
                 "val_macro_f1": best_f1, "test": test_m}, out)
    save_report({"domain": args.domain, "best": best_name, "counts": {k: len(v) for k, v in split.items()}, "models": results, "test": test_m},
                REPORTS / f"ml_{args.domain}.json")
    if test_m:
        save_confusion_png(test_m, REPORTS / f"ml_{args.domain}_confusion.png", f"Klasik ML ({best_name}) · {args.domain}")
    print(f"✓ Model: {out}")


if __name__ == "__main__":
    main()
