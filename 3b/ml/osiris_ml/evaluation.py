"""Ortak değerlendirme: metrikler, karışıklık matrisi görseli, rapor dosyaları."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np


def metrics(y_true, y_pred, labels: list[str]) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
    idx = list(range(len(labels)))
    present = sorted(set(np.asarray(y_true).tolist()) | set(np.asarray(y_pred).tolist()))
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=present, average="macro", zero_division=0)),
        "per_class": classification_report(y_true, y_pred, labels=idx, target_names=labels, output_dict=True, zero_division=0),
        "confusion": confusion_matrix(y_true, y_pred, labels=idx).tolist(),
        "labels": labels,
    }


def save_confusion_png(m: dict, path: Path, title: str) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    cm = np.array(m["confusion"], dtype=float)
    norm = cm / np.maximum(1, cm.sum(1, keepdims=True))
    fig, ax = plt.subplots(figsize=(5.2, 4.4), dpi=120)
    ax.imshow(norm, cmap="Oranges", vmin=0, vmax=1)
    ax.set_xticks(range(len(m["labels"])), m["labels"], rotation=35, ha="right")
    ax.set_yticks(range(len(m["labels"])), m["labels"])
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(j, i, int(cm[i, j]), ha="center", va="center", fontsize=8, color="black" if norm[i, j] < .6 else "white")
    ax.set_xlabel("Tahmin"); ax.set_ylabel("Gerçek")
    ax.set_title(f"{title}\nacc {m['accuracy']:.3f} · macro-F1 {m['macro_f1']:.3f}", fontsize=9)
    fig.tight_layout(); fig.savefig(path); plt.close(fig)


def save_report(obj: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=2)
