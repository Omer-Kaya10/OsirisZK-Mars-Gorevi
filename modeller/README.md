# Araç modelleri / Vehicle models

| Dosya | İçerik |
|---|---|
| `gezgin-drone-destek-sistemi.png` | Gezgin + drone: iniş platformu, kenetleme, batarya değişim sistemi |
| `gezgin-mimari.jpg` | Mars gezgini (rover): ön, yan, üst görünüş ve teknik özellikler |
| `drone-mimari.jpg` | Mars drone (Ingenuity esaslı): yan, ön, üst görünüş ve teknik özellikler |
| `modeller.json` | Çizimlerdeki değerler; oyun motoru bunları kullanır (`oyun/test_modeller.py` denetler) |
| `index.html` | Çizimleri ve değerleri gösteren sayfa (TR/EN): sitede `/modeller/` |

Bir çizim değişirse: önce `modeller.json`, sonra `oyun/mars_core.py` güncellenir; testler uyumu denetler.
`modeller.json` → `oyunda_kullanim` bölümü hangi değerin oyunda kullanıldığını, hangisinin henüz
kullanılmadığını gösterir.

When a drawing changes, update `modeller.json` first, then `oyun/mars_core.py`; the tests check that
they match.
