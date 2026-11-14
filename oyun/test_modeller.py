"""Oyun motorundaki değerler mimari çizimlerle (modeller/modeller.json) aynı mı?

Çalıştırma: python -m unittest -v test_modeller.py
Bir çizim değişirse önce modeller.json, sonra mars_core.py güncellenir; bu test ikisinin
ayrışmasını yakalar.
"""
import json
import unittest
from pathlib import Path

from mars_core import Config, RoverConfig

MODEL_DOSYASI = Path(__file__).resolve().parent.parent / "modeller" / "modeller.json"


class ModelUyumuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not MODEL_DOSYASI.is_file():
            raise unittest.SkipTest("modeller/modeller.json bulunamadı (yalnızca oyun klasörü kopyalanmış).")
        cls.m = json.loads(MODEL_DOSYASI.read_text(encoding="utf-8"))

    def test_drone_kutle_ve_rotor(self):
        c = Config()
        self.assertEqual(c.mass, self.m["drone"]["kutle_kg"])
        self.assertEqual(c.rotor_diameter, self.m["drone"]["rotor_capi_m"])

    def test_gezgin_enerji_sistemi(self):
        r = RoverConfig()
        g = self.m["gezgin"]
        self.assertEqual(r.battery_capacity_wh, g["batarya_Wh"])
        self.assertEqual(r.solar_peak_w, g["gunes_paneli_W"])
        self.assertEqual(r.charger_w, g["drone_sarj_gucu_W"])
        low, high = g["batarya_araligi_kWh"]
        self.assertTrue(low * 1000 <= r.battery_capacity_wh <= high * 1000)
        self.assertLessEqual(r.initial_energy_wh, r.battery_capacity_wh)

    def test_platform_droneu_tasir(self):
        # Rotorlar (Ø1,20 m) platformdan taşar; en azından gövde 0,60 m platforma sığmalı. (İniş ayaklarının
        # açıklığı çizimde yok: takım ölçüp eklemeli.)
        g, d = self.m["gezgin"], self.m["drone"]
        self.assertLess(d["govde_m"]["boy"], g["inis_platformu_m"]["boy"])
        self.assertLess(d["govde_m"]["en"], g["inis_platformu_m"]["en"])


if __name__ == "__main__":
    unittest.main()
