"""1. ADIM — Veri setlerini hazırla.

Zip'leri data/raw/ altına açar, biçimleri otomatik tanır (HiRISE v3, MSL v1/v2, AI4Mars, sınıf klasörleri),
etiketleri oyunun 5 zemin sınıfına eşler ve tek bir dizin yazar: data/processed/index.csv

Örnek:
  python scripts/01_prepare_dataset.py C:\\indirilenler\\hirise-map-proj-v3_2.zip C:\\indirilenler\\msl-images.zip
  python scripts/01_prepare_dataset.py data/raw/benim_fotograflarim --ai4mars-patches 8
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osiris_ml.config import PROCESSED, RAW, UNMAPPED, ensure_dirs, load_classes  # noqa: E402
from osiris_ml.datasets import scan, write_index  # noqa: E402


def safe_extract(zp: Path, dest: Path) -> None:
    """Zip içindeki '../' yollarına karşı korumalı açma."""
    with zipfile.ZipFile(zp) as z:
        root = dest.resolve()
        for m in z.infolist():
            target = (dest / m.filename).resolve()
            if not str(target).startswith(str(root)):
                raise RuntimeError(f"Güvensiz yol zip içinde: {m.filename}")
        z.extractall(dest)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="zip dosyaları veya klasörler")
    ap.add_argument("--out", default=str(PROCESSED / "index.csv"))
    ap.add_argument("--val-frac", type=float, default=0.15, help="Hazır bölmesi olmayan veride doğrulama oranı")
    ap.add_argument("--test-frac", type=float, default=0.15)
    ap.add_argument("--ai4mars-patches", type=int, default=6, help="AI4Mars görüntüsü başına kesilecek yama sayısı")
    ap.add_argument("--ai4mars-patch-size", type=int, default=128)
    ap.add_argument("--ai4mars-max-images", type=int, default=None, help="Hızlı deneme için görüntü sınırı")
    args = ap.parse_args()

    ensure_dirs()
    cfg = load_classes()
    roots: list[Path] = []
    for inp in args.inputs:
        p = Path(inp)
        if p.suffix.lower() == ".zip":
            dest = RAW / p.stem
            if not dest.exists():
                print(f"[aç] {p.name} -> {dest}")
                safe_extract(p, dest)
            else:
                print(f"[var] {dest} zaten açılmış, atlanıyor")
            roots.append(dest)
        elif p.is_dir():
            roots.append(p)
        else:
            sys.exit(f"Bulunamadı: {p}")

    all_recs = []
    for root in roots:
        formats, recs = scan(root, cfg, args.val_frac, args.test_frac,
                             {"patch": args.ai4mars_patch_size, "per_image": args.ai4mars_patches, "max_images": args.ai4mars_max_images})
        print(f"[tara] {root}: biçim={','.join(formats)} kayıt={len(recs)}")
        all_recs += recs

    out = Path(args.out)
    write_index(all_recs, out)

    # ── Rapor
    table = collections.Counter((r.source, r.domain, r.game_class or "-", r.split) for r in all_recs)
    unmapped = collections.Counter((r.source, r.orig_label) for r in all_recs if r.game_class == UNMAPPED)
    excluded = collections.Counter((r.source, r.orig_label) for r in all_recs if r.game_class is None)
    keys = [c["key"] for c in cfg["classes"]]
    summary = {"index": str(out), "records": len(all_recs), "by_domain": {}}
    print("\nOyun sınıfı başına örnek (train/val/test):")
    for dom in ("surface", "orbital"):
        per = {k: [sum(table[(s, dom, k, sp)] for s in {r.source for r in all_recs}) for sp in ("train", "val", "test")] for k in keys}
        if sum(sum(v) for v in per.values()) == 0:
            continue
        summary["by_domain"][dom] = per
        print(f"  [{dom}]")
        for k, (tr, va, te) in per.items():
            warn = "  ⚠ az örnek" if 0 < tr < 30 else ("  ⚠ hiç örnek yok" if tr == 0 else "")
            print(f"    {k:9s} {tr:6d} {va:6d} {te:6d}{warn}")
    if excluded:
        print("\nBilinçli olarak dışarıda bırakılan etiketler (gezgin parçası, gökyüzü, kutup buzu…):")
        for (s, l), n in excluded.most_common(12):
            print(f"    {s:10s} {l:28s} {n}")
    if unmapped:
        print("\n⚠ Eşleme tablosunda olmayan etiketler — terrain_classes.json > dataset_mappings'e ekleyin:")
        for (s, l), n in unmapped.most_common():
            print(f"    {s:10s} {l:28s} {n}")
        summary["unmapped"] = {f"{s}:{l}": n for (s, l), n in unmapped.items()}
    with open(out.with_name("index_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)
    print(f"\n✓ Dizin yazıldı: {out}")


if __name__ == "__main__":
    main()
