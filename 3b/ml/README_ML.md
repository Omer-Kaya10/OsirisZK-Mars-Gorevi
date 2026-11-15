# OSIRISZK — Mars Zemin Sınıflandırma Altyapısı (ML + Derin Öğrenme)

Bu klasör, Mars fotoğraflarından **zemin/kaya sınıflandırma** modelleri eğitip sonucu **oyuna** aktaran boru hattıdır.
Model, fotoğraftaki zemini oyunun 5 sınıfından birine atar; oyun o sınıfın **dokusunu** ve **fizik değerlerini**
(kayma, batma, sürtünme) kullanır.

> **Hızlı başlangıç:** Tam hattı kurmadan önce gerçek veriyle kısa bir deneme için `baslangic/` klasörüne bakın
> (HiRISE v1'den 300 görüntü, AI4Mars'tan 120 görüntü+etiket; MobileNetV3 sınıflandırıcı ve küçük U-Net). Ayrıntı: `baslangic/README.md`.

```
 veri setleri (zip/klasör)
        │  01_prepare_dataset.py   → biçim tanıma, etiket eşleme, bölme  → data/processed/index.csv
        ▼
 ┌──────────────┬─────────────────┐
 │ 02_train_ml  │ 03_train_dl     │   klasik ML (RF/SVM/HGB)   |   CNN (ResNet18/MobileNet/EfficientNet/MarsNet)
 └──────┬───────┴────────┬────────┘
        ▼                ▼            models/*.joblib, *.pt, *.onnx   ·   reports/*.json, *_confusion.png
 04_predict.py   (yeni fotoğrafları sınıflandır → CSV)
        ▼
 05_build_game_assets.py  → ../assets/terrain/textures/{low,medium,high}/*.jpg  + macro_hirise.png
                             + material_map.png  + manifest.json   ──►  OYUN açılışta okur
```

## 1. Kurulum (Windows)

`KURULUM_WINDOWS.bat` dosyasına çift tıklayın: sanal ortam kurar, paketleri yükler ve **duman testini** çalıştırır
(sentetik veriyle tüm adımları dener). Elle kurulum:

```bat
cd ml
py -3 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dl.txt      :: NVIDIA ekran kartı varsa CUDA sürümünü pytorch.org'dan kurun
python tests\run_smoke_test.py
```

Python 3.9 veya üstü gerekir. Oyunun kendisi bu paketlere **ihtiyaç duymaz**; yalnızca model eğitimi için.

## 2. Veri setleri

| Veri seti | Görüş | Bu altyapıda kullanımı | Kaynak |
|---|---|---|---|
| HiRISE etiketli set v3.2 (JPL) | Yörünge (yukarıdan, gri) | Uzak arazi: kum tepesi, krater, fırlatma, toz | zenodo.org/records/4002935 |
| Curiosity (MSL) etiketli set v1 (JPL, 24 sınıf) | Yüzey | Sınıfların çoğu gezgin parçası/kalibrasyon hedefi; yalnız `ground` ve `drill holes` zemine katılır | zenodo.org/record/1049137 |
| Curiosity (MSL) bilim/mühendislik seti v2 (JPL, 19 sınıf) | Yüzey | `Nearby surface`, `Sand`, `Layers`, `Float`, `Light-toned veins`… zemine katılır | zenodo.org/record/4033453 |
| AI4Mars (JPL, piksel etiketli) | Yüzey (Curiosity NAVCAM) | **Zemin sınıflandırma için en uygun set**: toprak / ana kaya / kum / büyük kaya | Kaggle / Hugging Face kopyaları (ör. `hassanjbara/AI4MARS`) |
| Kendi fotoğraflarınız | Yüzey | `kum/ regolit/ kaya/ cakil/ toz/` alt klasörleri | — |

> **Önemli:** Curiosity v1 setinin 24 sınıfının çoğu gezgin donanımıdır (APXS, MAHLI, tekerlek, kalibrasyon hedefleri…).
> Zemin sınıflandırma için tek başına zayıftır; v2 ve özellikle AI4Mars ile birlikte kullanın.

Zip'leri olduğu gibi verebilirsiniz; iç içe klasörler ve birden fazla set aynı anda desteklenir.

## 3. Oyun sınıfları ve etiket eşleme

Tek doğruluk kaynağı: **`../assets/terrain/terrain_classes.json`** (oyun da aynı dosyayı okur). Sıra değiştirilmemeli.

| id | anahtar | ad | HiRISE | MSL v1 | MSL v2 | AI4Mars |
|---|---|---|---|---|---|---|
| 0 | regolith | Regolit (toprak) | other | ground | Nearby surface, Wheel tracks | soil |
| 1 | sand | Kum | dark dune | — | Sand | sand |
| 2 | bedrock | Ana kaya | — | drill holes | Layers, Light-toned veins, Close-up rock, Drill hole, DRT spot | bedrock |
| 3 | gravel | Çakıllı / bloklu | crater, impact ejecta | — | Float | big rock |
| 4 | dust | Toz (sürüklenme) | bright dune, slope streak | — | — | — |

`null` olanlar (gökyüzü, güneş, gezgin parçaları, kutup buzu "spider/swiss cheese") eğitime girmez.
Tabloda olmayan bir etiket görülürse `01_prepare_dataset.py` uyarır → `dataset_mappings`'e ekleyin.

**Dikkat edilecek dengesizlikler:** Yüzey verisinde `dust` neredeyse yoktur (yalnız yörüngede var); yörünge verisinde
`bedrock` yoktur. Bu yüzden iki model ayrı eğitilir (`--domain surface` / `--domain orbital`). Oyun, yörünge haritasında
olmayan ana kayayı eğimden üretmeye devam eder.

## 4. Adım adım

```bat
:: 1) Hazırla (zip'ler data\raw altına açılır)
python scripts\01_prepare_dataset.py C:\indir\hirise-map-proj-v3_2.zip C:\indir\msl-images.zip C:\indir\msl-labeled-data-set.zip C:\indir\ai4mars.zip

:: 2) Klasik ML (öznitelik: renk + LBP + GLCM + gradyan + FFT, 88 boyut)
python scripts\02_train_ml.py --domain surface
python scripts\02_train_ml.py --domain orbital

:: 3) Derin öğrenme (transfer öğrenme; internet yoksa --arch marsnet --no-pretrained)
python scripts\03_train_dl.py --domain surface --arch resnet18 --epochs 20
python scripts\03_train_dl.py --domain orbital --arch mobilenet_v3_small --img 160

:: 4) Yeni fotoğrafları sınıflandır
python scripts\04_predict.py --model models\dl_surface_resnet18.pt --input C:\yeni_fotograflar

:: 5) Oyun varlıklarını üret (dokular + HiRISE makro + malzeme haritası + manifest.json)
python scripts\05_build_game_assets.py --model models\dl_surface_resnet18.pt --images data\raw\msl-images ^
       --hirise-image C:\indir\ESP_XXXXXX_XXXX_RED.browse.jpg --hirise-mpp 0.25 --orbital-model models\ml_orbital.joblib
:: Model olmadan, doğrudan etiketlerden doku üretmek için:
python scripts\05_build_game_assets.py --from-labels
```

Ardından oyunu `baslat.py` ile açın; sağ paneldeki **ZEMİN / TERRAMEKANİK** bölümünde `doku: fotoğraf (ML)` yazar.
Prosedürel dokulara dönmek için `assets/terrain/manifest.json` içinde `"quality": {}` bırakın.

### Önemli parametreler
| Betik | Parametre | Açıklama |
|---|---|---|
| 01 | `--val-frac/--test-frac` | Hazır bölmesi olmayan veride oran (HiRISE/MSL kendi bölmelerini kullanır) |
| 01 | `--ai4mars-patches/--ai4mars-patch-size` | Görüntü başına saf etiketli yama sayısı/boyutu (saflık ≥ %85) |
| 02 | `--models rf svm hgb` · `--max-per-class` | Model seçimi doğrulama macro-F1'e göre |
| 03 | `--arch` · `--img` · `--epochs` · `--balanced-sampler` | Sınıf ağırlıklı kayıp varsayılan; erken durdurma `--patience` |
| 05 | `--per-class` · `--min-conf` | Sınıf başına aday fotoğraf ve en düşük model güveni |
| 05 | `--hirise-mpp` · `--hirise-center` | Görüntünün m/piksel çözünürlüğü (oyun alanı 212 m) ve kırpma merkezi |

## 5. Oyunla sözleşme (değiştirirken uyulacak biçim)

`assets/terrain/manifest.json`:
```json
{ "source": "photos|mixed|procedural",
  "quality": { "low":    {"size":256,  "textures":{"sand":"textures/low/sand.jpg", ...},    "heights":{"sand":"textures/low/sand_h.png", ...}},
               "medium": {"size":512,  ...}, "high": {"size":1024, ...} },
  "macro":       {"image":"macro_hirise.png"},                                         // gri, 0.5 = nötr albedo
  "materialMap": {"image":"material_map.png", "dust":"material_map_dust.png", "size":256} }  // R kum, G kaya, B çakıl; toz ayrı gri
```
* Dokular **opak RGB** olmalı; yükseklik ayrı gri PNG (tarayıcı alfa kanalını önçarpımlı sakladığı için).
* Bir sınıfın dokusu yoksa oyun o sınıf için Mars renklerine göre prosedürel doku üretir.
* Harita yönü: görüntünün üstü = kuzey (oyunda −Z), sol = batı (−X); kapsam 212 m × 212 m.
* Fizik değerleri sınıfa bağlıdır (`terrain_classes.json > physics`): Bekker n, kc, kφ, kohezyon c, iç sürtünme φ, kayma modülü K.

## 6. Oyundaki fizik (terramekanik) kısaca

* Batma: Bekker basınç-batma bağıntısı (rijit teker çözümü, Wong 2012).
* Çekiş: Mohr-Coulomb `Hmax = A·c + W·tanφ`, kaymaya bağlı Janosi-Hanamoto eğrisi.
* Yuvarlanma direnci: zemin sıkıştırma direnci; eğimde Mars yerçekimi 3.71 m/s².
* Sonuç: regolitte ~%10 kayma, kumda %50+, tozda daha fazla; kumlu/tozlu yokuşta saplanma; frenleme mesafesi düşük
  yerçekimi nedeniyle uzun.

Parametre kaynakları JSON'daki `sources` alanlarında: Golombek vd. 2008 / Delage vd. 2017 (Mars yüzey malzemeleri),
Sullivan, Anderson vd. 2011 (MER teker hendekleri, JGR 116 E02006), M90 Mars simulantı (arXiv:2606.06790),
Wong / Shibly vd. 2005 (kuru kum Bekker değerleri), Moore vd. 1987 (Viking).

## 7. Diğer konuşmada yapılacaklar için notlar

Hazır olanlar: veri yükleyiciler (5 biçim), etiket eşleme, sızıntısız bölme (artırılmış HiRISE türevleri aynı kümede),
klasik ML (3 model + seçim), CNN eğitimi (4 mimari, ONNX), tahmin, doku/makro/malzeme haritası üretimi, duman testi.

Geliştirme fikirleri:
1. **AI4Mars ile segmentasyon:** Şu an yama sınıflandırma yapılıyor; DeepLabv3/U-Net ile piksel düzeyinde segmentasyon
   eğitilip oyun dokuları daha temiz bölgelerden kesilebilir.
2. **Sol (Mars günü) bazlı bölme:** Curiosity verisinde aynı bölgeden gelen fotoğraflar sızıntı yaratabilir; MSL setleri
   zaten sol'e göre bölünmüş, kendi verinizde de tarih/konuma göre bölün.
3. **Hiperparametre taraması:** `--img 224`, `--epochs 40`, `efficientnet_b0`; sınıf dengesizliği için `--balanced-sampler`.
4. **Model → fizik doğrulaması:** Sınıf başına güven düşükse (`--min-conf`) doku üretmeyin; oyun prosedürele döner.
5. **Tarayıcıda canlı çıkarım:** `models/dl_surface.onnx` ileride onnxruntime-web ile oyunda (ör. tarama tuşunda) çalıştırılabilir;
   şimdilik sonuçlar çevrimdışı olarak dokulara ve haritaya gömülüyor, oyun internetsiz kalıyor.

## 8. Test

```bat
python tests\run_smoke_test.py          :: sentetik veriyle uçtan uca (gerçek klasörlere dokunmaz)
python tests\run_smoke_test.py --keep   :: üretilen oyun varlıklarını incelemek için geçici klasörü silmez
```
`tests/make_synthetic_datasets.py` her biçimden küçük sahte veri üretir (gerçek Mars fotoğrafı değildir).
