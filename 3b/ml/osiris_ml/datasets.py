"""Veri seti biçimlerini otomatik tanıyıp tek bir dizin (index) tablosuna çeviren yükleyiciler.

Desteklenen biçimler (klasör ya da zip içinde, iç içe olabilir):
  hirise_v3 : JPL "Mars orbital image (HiRISE) labeled data set" v3/v3.2
              labels-map-proj*.txt  (dosya sınıf [set]) + *classmap*.csv + map-proj*/ görüntüleri
  msl_v1    : JPL "Mars surface image (Curiosity rover) labeled data set" v1 (24 sınıf)
              train/val/test-calibrated-shuffled.txt + msl_synset_words-indexed.txt + calibrated/
  msl_v2    : JPL "MSL Curiosity Rover Images with Science and Engineering Classes" v2 (19 sınıf)
              train/val/test-set*.txt + class_map.csv + images/
  ai4mars   : JPL AI4Mars (Curiosity NAVCAM, piksel etiketleri 0 toprak, 1 ana kaya, 2 kum, 3 büyük kaya, 255 boş)
              msl/images/edr/*.JPG + msl/labels/train/*.png (+ test/...) -> saf etiketli yamalar (patch) kesilir
  folder    : sınıf_adı/ alt klasörleri (ör. kum/, regolit/, kaya/) — kendi fotoğraflarınız için

Her kayıt: path, source, domain, split, orig_label, game_class, group, crop (x,y,w,h veya boş).
"""
from __future__ import annotations

import csv
import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable

from .config import DOMAIN_OF_SOURCE, UNMAPPED, map_label, norm_label

IMG_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
AUG_SUFFIX = re.compile(r"(-r90|-r180|-r270|-fh|-fv|-brt)(?=\.[a-z]+$)", re.I)


@dataclass
class Record:
    path: str
    source: str
    split: str
    orig_label: str
    game_class: str | None
    group: str
    crop: str = ""          # "x,y,w,h" (piksel) — AI4Mars yamaları için
    domain: str = field(default="")

    def __post_init__(self):
        if not self.domain:
            self.domain = DOMAIN_OF_SOURCE.get(self.source, "surface")

    def row(self) -> dict:
        return asdict(self)


def stable_split(key: str, val_frac: float, test_frac: float) -> str:
    """Grup anahtarına göre deterministik bölme (aynı görüntünün türevleri aynı kümeye düşer)."""
    h = int(hashlib.md5(key.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    if h < test_frac:
        return "test"
    if h < test_frac + val_frac:
        return "val"
    return "train"


def _norm_split(s: str) -> str:
    s = s.strip().lower()
    return {"training": "train", "validation": "val", "valid": "val", "testing": "test"}.get(s, s)


def _find(root: Path, pattern: str) -> list[Path]:
    return sorted(p for p in root.rglob(pattern) if p.is_file())


def _read_id_name_map(path: Path) -> dict[int, str]:
    """'0,other' / 'other,0' / '0 apxs cal target' / başlıklı CSV — hepsini okur."""
    out: dict[int, str] = {}
    text = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in text:
        line = line.strip()
        if not line:
            continue
        parts = [p.strip() for p in (line.split(",") if "," in line else line.split(None, 1))]
        if len(parts) < 2:
            continue
        if parts[0].lstrip("-").isdigit():
            out[int(parts[0])] = parts[1]
        elif parts[-1].lstrip("-").isdigit():
            out[int(parts[-1])] = ",".join(parts[:-1])
    return out


def _resolve(img_dirs: list[Path], name: str) -> Path | None:
    for d in img_dirs:
        p = d / name
        if p.exists():
            return p
        p = d / Path(name).name
        if p.exists():
            return p
    return None


# ───────────────────────── HiRISE v3 ─────────────────────────
def load_hirise(root: Path, cfg: dict, val_frac: float, test_frac: float) -> list[Record]:
    recs: list[Record] = []
    for cm in _find(root, "*classmap*.csv"):
        base = cm.parent
        names = _read_id_name_map(cm)
        tvt = _find(base, "labels-map-proj*train_val_test*.txt")
        plain = [p for p in _find(base, "labels-map-proj*.txt") if "train_val_test" not in p.name]
        label_file = (tvt or plain or [None])[0]
        if not label_file or not names:
            continue
        img_dirs = [d for d in base.rglob("map-proj*") if d.is_dir()] + [base]
        for line in label_file.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if len(parts) < 2:
                continue
            fname, cid = parts[0], int(parts[1])
            p = _resolve(img_dirs, fname)
            if p is None:
                continue
            label = names.get(cid, str(cid))
            group = AUG_SUFFIX.sub("", Path(fname).name)
            split = _norm_split(parts[2]) if len(parts) > 2 else stable_split("hirise/" + group, val_frac, test_frac)
            recs.append(Record(str(p), "hirise_v3", split, label, map_label("hirise_v3", label, cfg), group))
    return recs


# ───────────────────────── MSL v1 / v2 ─────────────────────────
def _load_msl(root: Path, cfg: dict, source: str, map_glob: str, split_globs: dict[str, str], img_dir_names: tuple[str, ...]) -> list[Record]:
    recs: list[Record] = []
    for mp in _find(root, map_glob):
        base = mp.parent
        names = _read_id_name_map(mp)
        img_dirs = [d for n in img_dir_names for d in base.rglob(n) if d.is_dir()] + [base]
        for split, pat in split_globs.items():
            for lf in _find(base, pat):
                for line in lf.read_text(encoding="utf-8", errors="replace").splitlines():
                    parts = line.split()
                    if len(parts) < 2 or not parts[-1].lstrip("-").isdigit():
                        continue
                    fname, cid = " ".join(parts[:-1]), int(parts[-1])
                    p = _resolve(img_dirs, fname)
                    if p is None:
                        continue
                    label = names.get(cid, str(cid))
                    group = AUG_SUFFIX.sub("", Path(fname).name)
                    recs.append(Record(str(p), source, split, label, map_label(source, label, cfg), group))
    return recs


def load_msl_v1(root: Path, cfg: dict, *_):
    return _load_msl(root, cfg, "msl_v1", "msl_synset_words-indexed.txt",
                     {"train": "train-calibrated-shuffled.txt", "val": "val-calibrated-shuffled.txt", "test": "test-calibrated-shuffled.txt"},
                     ("calibrated",))


def load_msl_v2(root: Path, cfg: dict, *_):
    return _load_msl(root, cfg, "msl_v2", "class_map.csv",
                     {"train": "train-set*.txt", "val": "val-set*.txt", "test": "test-set*.txt"}, ("images",))


# ───────────────────────── AI4Mars ─────────────────────────
AI4MARS_NAMES = {0: "soil", 1: "bedrock", 2: "sand", 3: "big rock"}


def load_ai4mars(root: Path, cfg: dict, val_frac: float, test_frac: float, patch: int = 128, per_image: int = 6,
                 purity: float = 0.85, max_images: int | None = None) -> list[Record]:
    """Etiket maskesinden saf (tek sınıflı) kare yamalar seçer. Yamalar kayıtta 'crop' olarak tutulur, diske yazılmaz."""
    import numpy as np
    from PIL import Image

    recs: list[Record] = []
    for edr in [d for d in root.rglob("edr") if d.is_dir() and d.parent.name == "images"]:
        mission = edr.parent.parent                      # .../msl
        labels_root = mission / "labels"
        if not labels_root.exists():
            continue
        images = {p.stem: p for p in edr.iterdir() if p.suffix.lower() in IMG_EXT}
        label_files = [(p, "test" if "test" in p.parts else "train") for p in labels_root.rglob("*.png")]
        if max_images:
            label_files = label_files[:max_images]
        rnd = np.random.default_rng(1234)
        for lp, split in label_files:
            stem = lp.stem.replace("_merged", "")
            ip = images.get(stem)
            if ip is None:
                continue
            m = np.array(Image.open(lp))
            if m.ndim == 3:
                m = m[..., 0]
            H, W = m.shape
            with Image.open(ip) as im:
                iw, ih = im.size
            sx, sy = iw / W, ih / H
            ps = max(16, int(round(patch / sx)))          # yama boyu maske pikselinde
            if H < ps or W < ps:
                continue
            group = stem
            if split == "train":
                split = stable_split("ai4mars/" + group, val_frac, 0.0)
            found = 0
            for _ in range(per_image * 12):
                if found >= per_image:
                    break
                y = int(rnd.integers(0, H - ps + 1)); x = int(rnd.integers(0, W - ps + 1))
                win = m[y:y + ps, x:x + ps]
                valid = win[win != 255]
                if valid.size < 0.8 * win.size:
                    continue
                vals, counts = np.unique(valid, return_counts=True)
                k = int(vals[np.argmax(counts)])
                if k not in AI4MARS_NAMES or counts.max() / valid.size < purity:
                    continue
                label = AI4MARS_NAMES[k]
                crop = f"{int(x * sx)},{int(y * sy)},{int(ps * sx)},{int(ps * sy)}"
                recs.append(Record(str(ip), "ai4mars", split, label, map_label("ai4mars", label, cfg), group, crop))
                found += 1
    return recs


# ───────────────────────── Klasör ─────────────────────────
def load_folder(root: Path, cfg: dict, val_frac: float, test_frac: float) -> list[Record]:
    recs: list[Record] = []
    table = {norm_label(k) for k, v in cfg["dataset_mappings"]["folder"].items() if not k.startswith("_")}
    for d in sorted(p for p in root.rglob("*") if p.is_dir()):
        if norm_label(d.name) not in table:
            continue
        for p in sorted(d.rglob("*")):
            if p.suffix.lower() in IMG_EXT and p.is_file():
                group = p.stem
                recs.append(Record(str(p), "folder", stable_split("folder/" + str(p.relative_to(root)), val_frac, test_frac),
                                   d.name, map_label("folder", d.name, cfg), group))
    return recs


LOADERS = {"hirise_v3": load_hirise, "msl_v1": load_msl_v1, "msl_v2": load_msl_v2, "ai4mars": load_ai4mars, "folder": load_folder}


def detect_formats(root: Path) -> list[str]:
    found = []
    if _find(root, "*classmap*.csv") and _find(root, "labels-map-proj*.txt"):
        found.append("hirise_v3")
    if _find(root, "msl_synset_words-indexed.txt"):
        found.append("msl_v1")
    if _find(root, "class_map.csv") and _find(root, "train-set*.txt"):
        found.append("msl_v2")
    if any(d.parent.name == "images" for d in root.rglob("edr") if d.is_dir()):
        found.append("ai4mars")
    if not found:
        found.append("folder")
    return found


def scan(root: Path, cfg: dict, val_frac: float = 0.15, test_frac: float = 0.15, ai4mars_kwargs: dict | None = None) -> tuple[list[str], list[Record]]:
    formats = detect_formats(root)
    recs: list[Record] = []
    for f in formats:
        if f == "ai4mars":
            recs += load_ai4mars(root, cfg, val_frac, test_frac, **(ai4mars_kwargs or {}))
        else:
            recs += LOADERS[f](root, cfg, val_frac, test_frac)
    return formats, recs


INDEX_FIELDS = ["path", "source", "domain", "split", "orig_label", "game_class", "group", "crop"]


def write_index(recs: Iterable[Record], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=INDEX_FIELDS)
        w.writeheader()
        for r in recs:
            row = r.row()
            row["game_class"] = row["game_class"] if row["game_class"] is not None else ""
            w.writerow({k: row[k] for k in INDEX_FIELDS})


def read_index(path: Path, domain: str | None = None, usable_only: bool = True) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if domain and domain != "all":
        rows = [r for r in rows if r["domain"] == domain]
    if usable_only:
        rows = [r for r in rows if r["game_class"] and r["game_class"] != UNMAPPED]
    return rows


def open_image(row: dict, size: int | None = None):
    """Kaydı RGB PIL görüntüsü olarak açar (crop uygulanır)."""
    from PIL import Image
    im = Image.open(row["path"]).convert("RGB")
    if row.get("crop"):
        x, y, w, h = map(int, row["crop"].split(","))
        im = im.crop((x, y, x + w, y + h))
    if size:
        im = im.resize((size, size), Image.BILINEAR)
    return im
