"""Klasik makine öğrenmesi için elle tasarlanmış doku/renk öznitelikleri.

Renk   : RGB ort/std, Lab ort/std, HSV histogramları (Mars tonlarını ayırır: koyu bazaltik kum, parlak toz, açık tonlu kaya)
Doku   : LBP (yerel ikili örüntü, 2 ölçek), GLCM (kontrast, homojenlik, enerji, korelasyon, farklılık)
Yapı   : Sobel gradyan istatistikleri, Canny kenar yoğunluğu, FFT radyal enerji bantları (dalgacık/çakıl sıklığı)
Toplam 88 boyut. Gri (HiRISE) görüntülerde renk öznitelikleri doğal olarak sabit kalır.
"""
from __future__ import annotations

import numpy as np

FEATURE_SIZE = 128
FEATURE_VERSION = 1


def _hist(x: np.ndarray, bins: int, rng: tuple[float, float]) -> np.ndarray:
    h, _ = np.histogram(x, bins=bins, range=rng)
    return h.astype(np.float32) / max(1, h.sum())


def extract(img) -> np.ndarray:
    """PIL görüntüsü -> öznitelik vektörü (float32)."""
    from PIL import Image
    from skimage.color import rgb2lab, rgb2hsv
    from skimage.feature import local_binary_pattern, graycomatrix, graycoprops, canny
    from skimage.filters import sobel

    im = img.convert("RGB").resize((FEATURE_SIZE, FEATURE_SIZE), Image.BILINEAR)
    rgb = np.asarray(im, dtype=np.float32) / 255.0
    gray = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    lab = rgb2lab(rgb)
    hsv = rgb2hsv(rgb)
    f: list[np.ndarray] = [
        rgb.reshape(-1, 3).mean(0), rgb.reshape(-1, 3).std(0),
        lab.reshape(-1, 3).mean(0) / 100.0, lab.reshape(-1, 3).std(0) / 50.0,
        _hist(hsv[..., 0], 12, (0, 1)), _hist(hsv[..., 1], 8, (0, 1)), _hist(hsv[..., 2], 8, (0, 1)),
    ]
    g8 = (gray * 255).astype(np.uint8)
    f.append(_hist(local_binary_pattern(g8, 8, 1, "uniform"), 10, (0, 10)))
    f.append(_hist(local_binary_pattern(g8, 16, 2, "uniform"), 18, (0, 18)))
    q = (gray * 31).astype(np.uint8)
    glcm = graycomatrix(q, distances=[1, 3], angles=[0, np.pi / 4, np.pi / 2, 3 * np.pi / 4], levels=32, symmetric=True, normed=True)
    for prop in ("contrast", "homogeneity", "energy", "correlation", "dissimilarity"):
        v = graycoprops(glcm, prop)                    # (mesafe, açı)
        f.append(np.nan_to_num(v.mean(axis=1)).astype(np.float32) / (100.0 if prop == "contrast" else 1.0))
    mag = sobel(gray)
    f.append(np.array([mag.mean(), mag.std(), np.percentile(mag, 90)], dtype=np.float32))
    f.append(np.array([canny(gray, sigma=1.5).mean()], dtype=np.float32))
    spec = np.abs(np.fft.fftshift(np.fft.fft2(gray - gray.mean())))
    yy, xx = np.indices(spec.shape)
    r = np.hypot(yy - spec.shape[0] / 2, xx - spec.shape[1] / 2)
    edges = np.linspace(1, FEATURE_SIZE / 2, 7)
    bands = np.array([spec[(r >= a) & (r < b)].sum() for a, b in zip(edges[:-1], edges[1:])], dtype=np.float32)
    f.append(bands / max(1e-6, bands.sum()))
    out = np.concatenate([np.asarray(x, dtype=np.float32).ravel() for x in f])
    return np.nan_to_num(out)
