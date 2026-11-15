"""Gerçek veri gelmeden boru hattını sınamak için 5 biçimde küçük SENTETİK veri setleri üretir.
Görüntüler gerçek Mars fotoğrafı değildir; sınıflar ayırt edilebilsin diye farklı renk/doku desenleri taşır.
Kullanım: python tests/make_synthetic_datasets.py <hedef_klasör> [--n 24]
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

import numpy as np
from PIL import Image


def noise(rng, h, w, scale):
    small = rng.random((max(2, h // scale), max(2, w // scale)))
    return np.asarray(Image.fromarray((small * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC), np.float32) / 255


def surface(kind: str, rng, size=256) -> np.ndarray:
    h = w = size
    yy, xx = np.mgrid[0:h, 0:w] / size
    n = noise(rng, h, w, 16) * .6 + noise(rng, h, w, 4) * .4
    base = {"regolith": (.56, .30, .19), "sand": (.36, .26, .21), "bedrock": (.66, .47, .34), "gravel": (.48, .29, .20), "dust": (.74, .47, .30)}[kind]
    t = .85 + .3 * (n - .5)
    if kind == "sand":
        t = t + .14 * np.sin(2 * np.pi * (xx * 3 + yy * 11) + n * 6)
    if kind == "bedrock":
        t = t * (.92 + .1 * np.sin(2 * np.pi * yy * 9 + n * 4)) - .25 * (np.abs(np.sin(xx * 23 + n * 9)) < .05)
    if kind == "dust":
        t = .95 + .08 * (n - .5)
    img = np.stack([np.clip(base[c] * t + rng.normal(0, .02, (h, w)), 0, 1) for c in range(3)], -1)
    if kind in ("gravel", "regolith"):
        for _ in range(140 if kind == "gravel" else 25):
            cy, cx, r = rng.integers(0, h), rng.integers(0, w), rng.integers(2, 9 if kind == "gravel" else 4)
            m = (yy * size - cy) ** 2 + (xx * size - cx) ** 2 < r * r
            img[m] = np.array([.25, .21, .2]) * rng.uniform(.8, 1.4)
    return (np.clip(img, 0, 1) * 255).astype(np.uint8)


def orbital(kind: str, rng, size=227) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size] / size
    n = noise(rng, size, size, 12)
    g = .45 + .15 * (n - .5)
    if kind in ("dark dune", "bright dune"):
        g = (.25 if kind == "dark dune" else .7) + .1 * np.sin(2 * np.pi * (xx * 5 + yy * 2) + n * 3)
    elif kind == "crater":
        d = np.hypot(xx - .5, yy - .5); g = g - .25 * (d < .3) + .2 * (np.abs(d - .3) < .03)
    elif kind == "slope streak":
        g = g - .2 * (np.abs((xx - .5) + .3 * (yy - .5)) < .04)
    elif kind == "impact ejecta":
        g = g + .25 * (rng.random((size, size)) > .93)
    elif kind in ("spider", "swiss cheese"):
        g = g - .2 * (noise(rng, size, size, 6) > .7)
    return (np.clip(g, 0, 1) * 255).astype(np.uint8)


def save(arr, p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(arr).save(p, quality=92)


def make(root: Path, n: int, seed: int = 0) -> dict:
    rng = np.random.default_rng(seed)
    root.mkdir(parents=True, exist_ok=True)
    # HiRISE v3.2 benzeri
    hr = root / "hirise-map-proj-v3_2"
    names = ["other", "crater", "dark dune", "slope streak", "bright dune", "impact ejecta", "swiss cheese", "spider"]
    (hr / "map-proj-v3_2").mkdir(parents=True, exist_ok=True)
    (hr / "landmarks_map-proj-v3_2_classmap.csv").write_text("\n".join(f"{i},{nm}" for i, nm in enumerate(names)))
    lines = []
    for i, nm in enumerate(names):
        for k in range(n):
            fn = f"ESP_{i:02d}{k:04d}_RED-0001.jpg"
            save(orbital(nm, rng), hr / "map-proj-v3_2" / fn)
            sp = "test" if k % 6 == 0 else "val" if k % 6 == 1 else "train"
            lines.append(f"{fn} {i} {sp}")
            if sp == "train" and k % 3 == 0:
                fa = fn.replace(".jpg", "-r90.jpg"); save(np.rot90(orbital(nm, rng)).copy(), hr / "map-proj-v3_2" / fa); lines.append(f"{fa} {i} train")
    (hr / "labels-map-proj-v3_2_train_val_test.txt").write_text("\n".join(lines))
    # MSL v1 benzeri (yalnız 'ground' zemin sınıfıdır)
    m1 = root / "msl-images"
    m1.mkdir(parents=True, exist_ok=True)
    syn = ["apxs", "ground", "horizon", "wheel", "drill holes"]
    (m1 / "msl_synset_words-indexed.txt").write_text("\n".join(f"{i} {nm}" for i, nm in enumerate(syn)))
    sets = {"train": [], "val": [], "test": []}
    for i, nm in enumerate(syn):
        kind = {"ground": "regolith", "drill holes": "bedrock"}.get(nm, "dust")
        for k in range(n):
            fn = f"calibrated/{i:02d}{k:04d}ML_DRCL.JPG"
            arr = surface(kind, rng) if nm in ("ground", "drill holes") else (np.full((256, 256, 3), (120, 120, 130), np.uint8))
            save(arr, m1 / fn)
            sets["test" if k % 6 == 0 else "val" if k % 6 == 1 else "train"].append(f"{fn} {i}")
    for sp, ls in sets.items():
        (m1 / f"{sp}-calibrated-shuffled.txt").write_text("\n".join(ls))
    # MSL v2 benzeri
    m2 = root / "msl-labeled-data-set-v2.1"
    m2.mkdir(parents=True, exist_ok=True)
    v2 = ["Nearby surface", "Sand", "Layers", "Float", "Sun", "Wheel tracks"]
    (m2 / "class_map.csv").write_text("\n".join(f"{nm},{i}" for i, nm in enumerate(v2)))
    sets = {"train": [], "val": [], "test": []}
    for i, nm in enumerate(v2):
        kind = {"Nearby surface": "regolith", "Sand": "sand", "Layers": "bedrock", "Float": "gravel", "Wheel tracks": "regolith"}.get(nm)
        for k in range(n):
            fn = f"{i:02d}{k:04d}MR_XXXX.jpg"
            save(surface(kind, rng) if kind else np.full((256, 256, 3), 250, np.uint8), m2 / "images" / fn)
            sets["test" if k % 6 == 0 else "val" if k % 6 == 1 else "train"].append(f"{fn} {i}")
    for sp, ls in sets.items():
        (m2 / f"{sp}-set-v2.1.txt").write_text("\n".join(ls))
    # AI4Mars benzeri: 4 çeyrek = 4 sınıf (0 toprak, 1 kaya, 2 kum, 3 büyük kaya)
    a4 = root / "ai4mars-dataset-merged-0.1" / "msl"
    kinds = ["regolith", "bedrock", "sand", "gravel"]
    for k in range(max(6, n // 2)):
        S = 512
        img = np.zeros((S, S, 3), np.uint8); mask = np.full((S // 2, S // 2), 255, np.uint8)
        order = rng.permutation(4)
        for q, c in enumerate(order):
            y, x = (q // 2) * S // 2, (q % 2) * S // 2
            img[y:y + S // 2, x:x + S // 2] = surface(kinds[c], rng, S // 2)
            mask[y // 2:(y + S // 2) // 2, x // 2:(x + S // 2) // 2] = c
        name = f"NLA_{k:09d}EDR_F0000000AUT_04096M1"
        save(img, a4 / "images" / "edr" / f"{name}.JPG")
        sub = a4 / "labels" / ("test/masked-gold-min3-100agree" if k % 5 == 0 else "train")
        sub.mkdir(parents=True, exist_ok=True)
        Image.fromarray(mask).save(sub / (f"{name}_merged.png" if k % 5 == 0 else f"{name}.png"))
    # Kendi fotoğraflarınız (klasör biçimi)
    fo = root / "benim_fotograflarim"
    for tr, kind in {"kum": "sand", "regolit": "regolith", "kaya": "bedrock", "cakil": "gravel", "toz": "dust"}.items():
        for k in range(n):
            save(surface(kind, rng), fo / tr / f"{tr}_{k:03d}.jpg")
    # Sahte HiRISE şeridi (uzak arazi): 1200×1200 px
    big = np.concatenate([np.concatenate([orbital(names[(i * 3 + j) % 6], rng, 240) for j in range(5)], 1) for i in range(5)], 0)
    save(big, root / "ESP_000000_0000_RED.browse.jpg")
    # İki seti zip'le (zip açma yolunu da sınamak için)
    zips = []
    for d in (hr, m1):
        zp = root / f"{d.name}.zip"
        with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
            for p in d.rglob("*"):
                z.write(p, p.relative_to(root))
        zips.append(zp)
    return {"zips": zips, "dirs": [m2, a4.parent, fo], "hirise_image": root / "ESP_000000_0000_RED.browse.jpg"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--n", type=int, default=24)
    a = ap.parse_args()
    print(make(Path(a.out), a.n))
