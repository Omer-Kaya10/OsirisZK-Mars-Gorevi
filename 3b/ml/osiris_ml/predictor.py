"""Eğitilmiş modeli (klasik .joblib ya da derin .pt) tek arayüzle yükleyip görüntü sınıflandırma."""
from __future__ import annotations

from pathlib import Path

import numpy as np


class Predictor:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if self.path.suffix == ".joblib":
            import joblib
            d = joblib.load(self.path)
            self.kind, self.model, self.labels, self.domain = "ml", d["model"], d["labels"], d.get("domain", "surface")
        elif self.path.suffix == ".pt":
            import importlib.util
            import torch
            spec = importlib.util.spec_from_file_location("train_dl", Path(__file__).resolve().parents[1] / "scripts" / "03_train_dl.py")
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            ck = torch.load(self.path, map_location="cpu", weights_only=False)
            meta = ck["meta"]
            self.model = mod.build_model(meta["arch"], len(meta["labels"]), pretrained=False)
            self.model.load_state_dict(ck["state_dict"]); self.model.eval()
            self.kind, self.labels, self.domain, self.meta = "dl", meta["labels"], meta.get("domain", "surface"), meta
            self.tf = mod.transforms(meta["img"], False, False)
        else:
            raise ValueError("Model uzantısı .joblib veya .pt olmalı")

    def predict_proba(self, images: list) -> np.ndarray:
        """PIL görüntü listesi -> (N, sınıf) olasılıklar."""
        if not images:
            return np.zeros((0, len(self.labels)))
        if self.kind == "ml":
            from .features import extract
            X = np.stack([extract(im) for im in images])
            p = self.model.predict_proba(X)
            full = np.zeros((len(images), len(self.labels)))
            classes = getattr(self.model, "classes_", None)
            if classes is None and hasattr(self.model, "steps"):
                classes = self.model.steps[-1][1].classes_
            classes = list(range(p.shape[1])) if classes is None else classes
            for j, c in enumerate(classes):
                full[:, int(c)] = p[:, j]
            return full
        import torch
        with torch.no_grad():
            x = torch.stack([self.tf(im.convert("RGB")) for im in images])
            return self.model(x).softmax(1).numpy()
