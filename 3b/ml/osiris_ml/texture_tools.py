"""Fotoğraflardan oyun dokusu üretimi: zemin bölgesi seçimi, renk eşitleme, dikişsiz (tileable) döşeme, yükseklik haritası."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter


def ground_region(im: Image.Image, has_crop: bool) -> Image.Image:
    """Yüzey fotoğraflarında gökyüzü/ufuk üstte olur: kırpılmamışsa alt %62'yi al."""
    if has_crop:
        return im
    w, h = im.size
    return im.crop((0, int(h * 0.38), w, h))


def best_square(im: Image.Image, frac: float = 0.8, tries: int = 9, seed: int = 0) -> Image.Image:
    """En dokulu ama aşırı karanlık/parlak olmayan kare pencereyi seçer (gölge, gökyüzü, gezgin parçası elenir)."""
    w, h = im.size
    s = int(min(w, h) * frac)
    if s < 16:
        return im
    rng = np.random.default_rng(seed)
    g = np.asarray(im.convert("L"), dtype=np.float32) / 255
    best, best_score = None, -1e9
    for _ in range(tries):
        x = int(rng.integers(0, w - s + 1)); y = int(rng.integers(0, h - s + 1))
        win = g[y:y + s, x:x + s]
        m = win.mean()
        edge = np.abs(np.diff(win, axis=1)).mean() + np.abs(np.diff(win, axis=0)).mean()
        score = win.std() - 2.0 * max(0, 0.12 - m) - 2.0 * max(0, m - 0.85) - 0.8 * max(0, edge - 0.12)
        if score > best_score:
            best, best_score = (x, y), score
    x, y = best
    return im.crop((x, y, x + s, y + s))


def lab_stats(im: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    from skimage.color import rgb2lab
    lab = rgb2lab(np.asarray(im.convert("RGB"), dtype=np.float32) / 255)
    return lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0)


def match_color(im: Image.Image, mean: np.ndarray, std: np.ndarray, strength: float = 0.8) -> Image.Image:
    """Farklı kamera/ışık koşullarındaki fotoğrafları sınıfın ortak tonuna yaklaştırır (Lab uzayında)."""
    from skimage.color import lab2rgb, rgb2lab
    lab = rgb2lab(np.asarray(im.convert("RGB"), dtype=np.float32) / 255)
    m, s = lab.reshape(-1, 3).mean(0), lab.reshape(-1, 3).std(0) + 1e-6
    tgt = (lab - m) * (1 + strength * (std / s - 1)) + (m + strength * (mean - m))
    rgb = np.clip(lab2rgb(tgt), 0, 1)
    return Image.fromarray((rgb * 255).astype(np.uint8))


def make_seamless(im: Image.Image) -> Image.Image:
    """Yarım kaydırma + kenar maskesi ile dikişsiz döşeme (döşendiğinde kenar çizgisi görünmez)."""
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w = a.shape[:2]
    b = np.roll(a, (h // 2, w // 2), axis=(0, 1))
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.minimum(np.minimum(xx, w - 1 - xx) / (w / 2), np.minimum(yy, h - 1 - yy) / (h / 2))
    m = np.clip(d / 0.45, 0, 1)
    m = (m * m * (3 - 2 * m))[..., None]
    return Image.fromarray(np.clip(a * m + b * (1 - m), 0, 255).astype(np.uint8))


def compose_tile(patches: list[Image.Image], size: int) -> Image.Image:
    """4+ yama varsa 2×2 yumuşak geçişli mozaik (çeşitlilik), yoksa tek yama; sonra dikişsiz yapılır."""
    if len(patches) >= 4:
        half = size // 2
        ov = max(4, size // 10)
        canvas = np.zeros((size + ov, size + ov, 3), np.float32)
        weight = np.zeros((size + ov, size + ov, 1), np.float32)
        ramp = np.ones(half + ov, np.float32)
        ramp[:ov] = np.linspace(0, 1, ov); ramp[-ov:] = np.linspace(1, 0, ov)
        wmask = (ramp[:, None] * ramp[None, :])[..., None] + 1e-3
        for k, p in enumerate(patches[:4]):
            arr = np.asarray(p.convert("RGB").resize((half + ov, half + ov), Image.LANCZOS), np.float32)
            y, x = (k // 2) * half, (k % 2) * half
            canvas[y:y + half + ov, x:x + half + ov] += arr * wmask
            weight[y:y + half + ov, x:x + half + ov] += wmask
        img = Image.fromarray(np.clip(canvas / weight, 0, 255).astype(np.uint8)).crop((ov // 2, ov // 2, ov // 2 + size, ov // 2 + size))
    else:
        img = patches[0].convert("RGB").resize((size, size), Image.LANCZOS)
    return make_seamless(img)


def height_map(tile: Image.Image) -> Image.Image:
    """Parlaklığın yüksek geçirgen hâli: çakıl/kaya üstleri yüksek, çatlak/gölgeler alçak."""
    L = np.asarray(tile.convert("L"), np.float32)
    blur = np.asarray(tile.convert("L").filter(ImageFilter.GaussianBlur(max(2, tile.size[0] // 40))), np.float32)
    hp = L - blur
    lo, hi = np.percentile(hp, 1), np.percentile(hp, 99)
    h = np.clip((hp - lo) / max(1e-3, hi - lo), 0, 1)
    return Image.fromarray((h * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.6))


def normalize_orbital(im: Image.Image, size: int) -> Image.Image:
    """HiRISE gri görüntüsünü makro albedoya çevirir: %2–%98 germe, ortalama 0.5 civarı."""
    g = np.asarray(im.convert("L").resize((size, size), Image.LANCZOS), np.float32)
    lo, hi = np.percentile(g, 2), np.percentile(g, 98)
    v = np.clip((g - lo) / max(1, hi - lo), 0, 1)
    v = 0.5 + (v - v.mean()) * 0.9
    return Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8))
