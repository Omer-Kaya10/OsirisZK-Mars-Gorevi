"""Yol ayarları ve ortak sınıf tanımları (oyunla aynı terrain_classes.json)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[1]
GAME_ROOT = ML_ROOT.parent
CLASSES_JSON = GAME_ROOT / "assets" / "terrain" / "terrain_classes.json"
import os
# OSIRIS_ML_WORKDIR ortam değişkeni verilirse veri/model/rapor oraya yazılır (testler bunu kullanır)
_WORK = Path(os.environ["OSIRIS_ML_WORKDIR"]) if os.environ.get("OSIRIS_ML_WORKDIR") else ML_ROOT
DATA = _WORK / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
MODELS = _WORK / "models"
REPORTS = _WORK / "reports"

# Veri seti türü -> görüş alanı. Yörünge (HiRISE) ve yüzey (gezgin) görüntüleri farklı alanlardır;
# modeller ayrı eğitilir: yüzey modeli yakın zemin dokularını, yörünge modeli uzak malzeme haritasını üretir.
DOMAIN_OF_SOURCE = {"hirise_v3": "orbital", "msl_v1": "surface", "msl_v2": "surface", "ai4mars": "surface", "folder": "surface"}


def load_classes(path: Path = CLASSES_JSON) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = json.load(fh)
    keys = [c["key"] for c in cfg["classes"]]
    if keys != ["regolith", "sand", "bedrock", "gravel", "dust"]:
        raise ValueError(f"terrain_classes.json sınıf sırası beklenenden farklı: {keys}")
    return cfg


def class_keys(cfg: dict | None = None) -> list[str]:
    cfg = cfg or load_classes()
    return [c["key"] for c in cfg["classes"]]


def norm_label(label: str) -> str:
    """'Wheel_tracks', 'wheel-tracks', ' Wheel  Tracks ' -> 'wheel tracks'"""
    return re.sub(r"\s+", " ", re.sub(r"[_\-]+", " ", str(label).strip().lower()))


UNMAPPED = "__unmapped__"


def map_label(source: str, label: str, cfg: dict) -> str | None:
    """Veri seti etiketini oyun sınıfına çevirir. None = bilinçli olarak dışarıda; UNMAPPED = tabloda yok."""
    table = {norm_label(k): v for k, v in cfg["dataset_mappings"].get(source, {}).items() if not k.startswith("_")}
    key = norm_label(label)
    if key in table:
        return table[key]
    return UNMAPPED


def ensure_dirs() -> None:
    for d in (RAW, PROCESSED, MODELS, REPORTS):
        d.mkdir(parents=True, exist_ok=True)
