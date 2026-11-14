"""Web köprüsü (kopru.py) ve İngilizce çeviri testleri.

Çalıştırma (depo kökünden):  python -m unittest discover -s web -p "test_*.py"
tkinter gerekmez: web sürümü masaüstü arayüzünü kullanmaz.
"""
import json
import math
import re
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(KOK / "oyun"), str(KOK / "web")]

import kopru                                   # noqa: E402
from ceviri import cevir, cevrildi_mi, KAYALAR  # noqa: E402
from mars_core import BASE_X, BASE_Y           # noqa: E402


def yeni_oyun():
    kopru.KAMERA_KLASORU = Path(tempfile.mkdtemp()) / "kamera_kayitlari"
    return kopru.Oyun()


def git(oyun, hedef_x, hedef_y, arac, tirmanma=0.0, adim=4000):
    """Seçili aracı hedefe doğru sürer (basit otomatik pilot)."""
    s = oyun.s
    for _ in range(adim):
        v = s.drone if arac == "drone" else s.rover
        dx, dy = hedef_x - v.x, hedef_y - v.y
        if math.hypot(dx, dy) < 8:
            return True
        n = max(1e-9, math.hypot(dx, dy))
        oyun.ilerle(0.02, dx / n, dy / n, tirmanma)
    return False


class KopruTest(unittest.TestCase):
    def test_durum_json_gecerli_ve_iki_dilde(self):
        o = yeni_oyun()
        tr, en = json.loads(o.durum("tr")), json.loads(o.durum("en"))
        self.assertEqual(tr["drone"]["kenetli"], True)
        self.assertEqual({k["ad"] for k in en["kayalar"]}, set(KAYALAR.values()) - {"Terrain panorama"})
        self.assertNotEqual(tr["mesaj"], en["mesaj"])

    def test_duraklatilmisken_zaman_akmaz(self):
        o = yeni_oyun()
        o.ilerle(0.1, 1, 0, 1)
        self.assertEqual(o.s.elapsed, 0)
        o.eylem("duraklat")
        o.ilerle(0.1, 0, 0, 0)
        self.assertGreater(o.s.elapsed, 0)

    def test_kayit_ve_yukleme(self):
        o = yeni_oyun()
        o.eylem("duraklat")
        for _ in range(30):
            o.ilerle(0.05, 0, 0, 1)
        metin = o.kaydet()
        o2 = yeni_oyun()
        o2.yukle(metin)
        self.assertAlmostEqual(o2.s.drone.altitude, o.s.drone.altitude)
        with self.assertRaises(ValueError):
            o2.yukle('{"version": 3, "seed": NaN}')
        self.assertIn("time_s", o.csv().splitlines()[0])

    def test_bastan_sona_gorev_ve_her_mesaj_cevriliyor(self):
        o = yeni_oyun()
        mesajlar = set()
        def eylem(ad):
            mesajlar.add(o.eylem(ad))
        eylem("tara"); eylem("duraklat"); eylem("tara")          # kenetliyken tarama
        eylem("kenetle")                                           # zaten kenetli
        for _ in range(60):
            o.ilerle(0.02, 0, 0, 1)                                # kalkış
        for kaya in o.s.mission.rocks:                             # 3 kayayı drone ile tara
            self.assertTrue(git(o, kaya.x, kaya.y, "drone", 0.05))
            eylem("tara")
        eylem("kamera")
        eylem("degistir")                                          # gezgine geç
        yol = [(o.s.rover.x, o.s.rover.y)]
        for kaya in o.s.mission.rocks[:2]:
            # kayaların yanına git; gidilen yol dönüşte tersten izlenir (engellere çarpmamak için)
            git(o, kaya.x - 40, kaya.y, "rover")
            yol.append((o.s.rover.x, o.s.rover.y))
            eylem("arastir")
        eylem("degistir")                                          # drone'a geç, gezginin üstüne in
        git(o, o.s.rover.x, o.s.rover.y, "drone", 0.0)
        for _ in range(2000):
            o.ilerle(0.02, 0, 0, -0.4)
            if o.s.drone.altitude < 0.8 and abs(o.s.drone.vertical_speed) < 1.5:
                break
        eylem("kenetle")
        eylem("pil"); eylem("isi"); eylem("isi"); eylem("gunes"); eylem("gunes"); eylem("onar")
        eylem("aktarim")
        for _ in range(4000):
            o.ilerle(0.02, 0, 0, 0)
            if all(p.delivered for p in o.s.packets):
                break
        eylem("degistir")
        for x, y in reversed(yol):
            git(o, x, y, "rover")
        o.ilerle(0.02, 0, 0, 0)
        mesajlar.update(o.s.events)
        mesajlar.add(o.s.mission.message)
        mesajlar.discard("")
        eksik = sorted(m for m in mesajlar if not cevrildi_mi(m))
        self.assertEqual(eksik, [], "Çevirisi olmayan mesajlar")
        self.assertTrue(o.s.mission.finished, o.s.mission_progress())


class CeviriTest(unittest.TestCase):
    def test_kalipli_mesajlar(self):
        self.assertEqual(cevir("Delta Tortusu başarıyla tarandı! (1/3)", "en"), "Delta Deposit scanned successfully! (1/3)")
        self.assertEqual(cevir("Batarya değişti: 12.0 Wh → 40.0 Wh. Eski pil depoda.", "en"),
                         "Battery swapped: 12.0 Wh → 40.0 Wh. Old pack stored.")
        self.assertEqual(cevir("Görev duraklatıldı.", "tr"), "Görev duraklatıldı.")

    def test_cekirdekteki_sabit_mesajlarin_hepsi_cevrilmis(self):
        # mars_core.py ve kopru.py'deki sabit (f-string olmayan) oyuncu mesajları
        kaynak = (KOK / "oyun" / "mars_core.py").read_text(encoding="utf-8") + (KOK / "web" / "kopru.py").read_text(encoding="utf-8")
        sabitler = set(re.findall(r'(?:return|notify\(|result = |self\.mesaj = |message = )\s*"([^"{}]+)"', kaynak))
        sabitler |= set(re.findall(r'else\s+"([^"{}]+\.)"', kaynak))
        sabitler = {m for m in sabitler if not m.rstrip().endswith(":")}   # "Kontrol: " + ... gibi parçalar
        eksik = sorted(m for m in sabitler if not cevrildi_mi(m))
        self.assertEqual(eksik, [])


if __name__ == "__main__":
    unittest.main()
