# OSIRISZK — Mars Pathfinder: Gezgin + Drone

**Türkçe** · [English below](#english)

Ingenuity benzeri bir drone ile güneş enerjili bir Mars gezgininin birlikte çalıştığı keşif oyunu.
Drone kayaları havadan tarar, gezgin yakından inceler; drone gezginin üstündeki platforma kenetlenir,
pili değişir, toplanan veriler Dünya'ya aktarılır ve gezgin üsse döner.

| | |
|---|---|
| 🌐 **Tarayıcıda oyna** | https://omer-kaya10.github.io/OsirisZK-Mars-Gorevi/ (GitHub Pages açılınca) · https://osiris-mars-explorer.netlify.app/gezgin/ |
| 🖥 **Masaüstünde oyna** | `oyun/baslat.py` (Python 3.10+, IDLE'da Run > Run Module) |
| 🚀 **Araç modelleri** | `modeller/` — mimari çizimler ve `modeller.json` |
| 📄 **Karşılaştırma** | `belgeler/` — Ingenuity ve yeni nesil sistem karşılaştırması |
| 🧭 **GitHub'a yükleme ve yayına alma** | [`GITHUB-KILAVUZU.md`](GITHUB-KILAVUZU.md) |

### Tek oyun motoru, iki ekran
Fizik, enerji, görev ve kayıt kuralları **tek bir dosyada**: `oyun/mars_core.py`.

- Masaüstü sürümü (`oyun/mars_oyunu.py`) bu dosyayı tkinter ile çizer.
- Web sürümü (`index.html` + `web/`) **aynı Python dosyasını** tarayıcıda [Pyodide](https://pyodide.org)
  (WebAssembly ile çalışan Python) ile çalıştırır. Kural değişirse iki sürüm birlikte değişir.
- Web sürümünde **Türkçe / English** dil seçici vardır. Oyun içi mesajların çevirisi `web/ceviri.py`
  içindedir; çevirisi eksik mesajı `web/test_web.py` yakalar.

### Klasörler
```
index.html            web oyununun sayfası
web/                  web arayüzü (oyun.js, dil.js, stil.css) ve Python köprüsü (kopru.py, ceviri.py)
oyun/                 masaüstü oyunu ve ORTAK oyun motoru (mars_core.py, kamera.py) + testler
3b/                   3B web oyunu (WebGL 2): gerçekçi fizik, canlı MEDA verisi, ML + DL; testler 3b/testler/
modeller/             gezgin ve drone mimari çizimleri, modeller.json, modeller sayfası
belgeler/             Ingenuity karşılaştırma belgeleri, ekran görüntüleri
.github/workflows/    her yüklemede testleri otomatik çalıştırır
netlify.toml          Netlify yayın ayarı (derleme gerekmez)
```

### Araç modelleri oyunda nasıl kullanılıyor?
`modeller/modeller.json` mimari çizimlerdeki (v1.0) değerleri tutar. Oyunda kullanılanlar:
drone kütlesi 1,8 kg ve rotor çapı 1,20 m; gezgin bataryası 1,2 kWh, güneş paneli 120 W, drone şarj gücü
100 W; ekrandaki gezgin ve drone çizimleri üst görünüşe göre (1,60 × 1,20 m gövde, arkada güneş paneli,
önde 0,60 × 0,60 m iniş platformu, 6 teker; Ø1,20 m eş eksenli iki rotor). `oyun/test_modeller.py`
oyun motoru ile çizimlerin aynı kaldığını denetler. Henüz kullanılmayan değerler (hız, değişim süresi,
çalışma sıcaklığı...) `modeller.json` → `oyunda_kullanim` bölümünde listelidir.

### Testler
```bash
cd oyun && python -m unittest -v test_eski_uyumluluk test_rover_drone test_modeller
python -m unittest discover -s web -p "test_*.py"      # depo kökünden
node --test 3b/testler/sistemler.test.mjs                                # 3B oyun (Node 20+)
```

### 3B sürüm (`3b/`) — v3.0
Aynı görevin gerçek zamanlı 3B sürümü; adresin sonuna `/3b/` ekleyerek açılır. Python oyununa dokunmaz, yanında durur.
- **Fizik (`3b/sistemler.js`):** momentum teorisiyle rotor gücü (Ingenuity'nin ≈350 W uçuş gücüne kalibre),
  ρ = p/(R·T), güneş yüksekliği ve toz opaklığıyla panel gücü, sıcaklığa bağlı Li-ion kapasitesi, enerji Wh.
- **Ölçüler:** `modeller/modeller.json` — 3B oyun da aynı dosyayı okur (tek kaynak).
- **Canlı veri (`3b/veri.js`):** Perseverance MEDA hava akışı. Akış gecikmeli olabilir; ekranda sol ve tarih yazar.
  Ulaşılamazsa yayımlanmış MEDA aralığı kullanılır, veri uydurulmaz. (Canlı veri yalnızca Netlify yayınında çalışır.)
- **Makine öğrenmesi (`3b/yz.js`):** drone uçarken güç tüketimini öğrenir (çevrimiçi RLS) ve her hedeften önce
  "dönüşe pil yeter mi" kararını verir.
- **Derin öğrenme:** 8-16-16-3 sinir ağı taranan kayayı sınıflandırır. Eğitim spektrumları **temsilîdir**, ölçülmüş değildir.
- TR/EN, dokunmatik kumanda, kaydet/yükle, CSV telemetri, kamera arşivi, zaman hızlandırma.

### v3.1 → v3.2 değişiklikleri
- Web sürümü (Pyodide) ve Türkçe/English dil seçici; tablet için dokunmatik kumanda.
- `mars_core.py` artık tkinter içe aktarmıyor (kullanmıyordu); böylece tarayıcıda da çalışıyor.
- Gezgin değerleri mimari çizimlere göre: batarya 900 → 1200 Wh, güneş paneli 440 → 120 W,
  yedek pil şarj gücü 210 → 100 W, başlangıç enerjisi 700 → 900 Wh.
- Gezgin ve drone ekran çizimleri üst görünüşe göre yeniden yapıldı (masaüstü + web).
- Yeni testler: `oyun/test_modeller.py`, `web/test_web.py` (baştan sona görev + çeviri kapsamı).

### Bilimsel dürüstlük
Bu bir **oyundur**; gerçek Ingenuity ya da gezgin uçuş yazılımı değildir. Ingenuity referansları:
yaklaşık 1,8 kg kütle, 1,2 m rotor çapı; Mars yerçekimi 3,71 m/s². Diğer değerler takımın tasarım
hedefleri ya da oyun dengesi varsayımlarıdır. Kamera görüntüleri oyun tarafından üretilir.

---

<a id="english"></a>
## English

An exploration game where an Ingenuity-like drone and a solar-powered Mars rover work together.
The drone scans rocks from the air, the rover surveys them up close, the drone docks on the rover's
platform and swaps batteries, data is uplinked to Earth and the rover returns to base.

- **Play in the browser:** https://omer-kaya10.github.io/OsirisZK-Mars-Gorevi/ (once GitHub Pages is on) or https://osiris-mars-explorer.netlify.app/gezgin/ (no installation).
  Use the **TR / EN** switch in the top-right corner (or add `?dil=en` to the address).
- **3D version:** add `/3b/` to the address — real-time WebGL game with momentum-theory rotor power, live Perseverance MEDA weather (Netlify only), an online ML energy model and a small neural-network rock classifier (trained on representative, not measured, spectra).
- **Play on the desktop:** `oyun/baslat.py` (Python 3.10+). The desktop version is in Turkish.
- **One game engine:** all rules live in `oyun/mars_core.py`; the web version runs the very same
  Python file in the browser with Pyodide.
- **Vehicle models:** `modeller/` holds the architecture drawings and `modeller.json`; the engine uses
  the drone mass and rotor diameter, the rover battery, solar and charging power, and draws both
  vehicles from the top views. `oyun/test_modeller.py` keeps engine and drawings in sync.
- **Publishing on GitHub and going live:** see [`GITHUB-KILAVUZU.md`](GITHUB-KILAVUZU.md#english).

Controls: WASD move · Space/↑ climb · Shift/↓ descend · Tab switch drone/rover · E drone scan ·
R rover survey · F dock · B swap battery · T Earth uplink · H heater · G solar panel · C camera ·
V image archive · K repair · P pause.

This is a **game**, not real flight software. Ingenuity references: about 1.8 kg, 1.2 m rotor;
Mars gravity 3.71 m/s². Other values are the team's design targets or game-balance assumptions.
