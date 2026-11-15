# Mars AI — mini veri seti ve eğitim başlangıç projesi

Bu pakette **gerçek görüntüler bulunmaz**: oturum ortamından haricî veri sunucularına erişilemediği için `prepare.py` görüntüleri bilgisayarınızda indirir. Gerekli görüntülerin resmî kaynakları dosyanın altında verilmiştir.

## Windows PowerShell kurulum

Python 3.10 veya 3.11 kurulu olsun. İndirilen ZIP'i açın, proje klasöründe terminal açın:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python prepare.py --dataset both --hirise-count 300 --ai4mars-count 120
python train_hirise.py --epochs 5
python train_ai4mars.py --epochs 5
```

Linux/macOS: `python3 -m venv .venv`, `source .venv/bin/activate`, sonrasındaki komutlar aynı.

**Sadece HiRISE** ile hızlı başlamak isterseniz: `python prepare.py --dataset hirise --hirise-count 300`. Orijinal 2017 HiRISE v1 arşivi (47.3 MB) indirilir; 300 etiketli örnek kopyalanır. Veri seti dengesiz olduğu için alt küme sınıflar arasında olabildiğince dengeli seçilir. Bu sürüm, HiRISE v3.2 değildir.

**AI4Mars**: Hugging Face'deki topluluk aynasından `streaming=True` ile 120 gerçek görüntü+etiket çifti alınır; tam 6.47 GB veri seti indirilmez. Hugging Face erişimi ve internete bağlantı gerekir. Maskeler: 0=soil, 1=bedrock, 2=sand, 3=big rock, 255=ignore. Görüntüler 256×256 olarak yeniden boyutlandırılır.

Her ikisinde de yaklaşık %80 eğitim, %10 doğrulama, %10 test ayrımı bulunur. Bu kod **başlangıç denemesidir**; özellikle HiRISE görsellerinin kaynak görüntüye veya artırılmış orijinal örneğe göre gruplandırılmış ayrılması bilimsel değerlendirmede gereklidir. HiRISE v1'de hazır bağımsız test ayrımı yoktur. Test dosyaları eğitimde kullanılmaz. AI4Mars'ın uzman etiketli asıl test kümesi, bu küçük demonstrasyon paketine dahil değildir.

**GPU:** NVIDIA/CUDA destekli PyTorch kuruluysa kullanılır, aksi hâlde CPU'da çalışır. En iyi sonuçları değil, çalışır eğitim hattını hedefler.

**Kaynaklar:**
- NASA AI4Mars: https://data.nasa.gov/dataset/ai4mars-a-dataset-for-terrain-aware-autonomous-driving-on-mars
- AI4Mars topluluk aynası: https://huggingface.co/datasets/hassanjbara/AI4MARS
- NASA/JPL HiRISE v1: https://zenodo.org/records/1048301 (DOI:10.5281/zenodo.1048301)
- Daha yeni HiRISE v3.2: https://zenodo.org/records/4002935

Yayınlarda her veri setinin orijinal çalışmasını ve kullanılan sürümü kaynak gösterin.

## OsirisZK düzeltmeleri (15 Kasım 2026)

- **HiRISE ayrımı kaynak görüntüye göre:** v1 arşivinde her görüntünün çevrilmiş/döndürülmüş kopyaları (`-fh`, `-fv`, `-brt`, `-r90`, `-r180`, `-r270`) var. Önceden aynı kaynağın kopyaları eğitim ve teste ayrı düşebiliyordu; bu, test doğruluğunu olduğundan yüksek gösterir. Artık bir kaynağın tüm kopyaları aynı kümede (`manifest.csv` içinde `source` sütunu).
- **Test kümesi gerçekten kullanılıyor:** iki eğitim betiği en iyi doğrulama epokunu geri yükler ve test kümesinde **bir kez** ölçer (HiRISE: doğruluk ve karışıklık tablosu; AI4Mars: mIoU ve sınıf başına IoU).
- **Rapor dosyaları:** `hirise_rapor.json` ve `ai4mars_rapor.json` (veri seti, model, küme boyutları, en iyi epok, test sonuçları, epok geçmişi). Sunumda yalnız bu dosyalardaki test sayılarını kullanın.
- Betikler sentetik veriyle uçtan uca denendi; gerçek veriyle sonuç, öğrencilerin kendi bilgisayarında çalıştırınca ortaya çıkar.
- AI4Mars'ta hâlâ dikkat: alt küme, aynanın `train` bölümünden sırayla alınır; ardışık görüntüler aynı sol'den olabilir. Bilimsel karşılaştırma için uzman etiketli resmî test kümesi gerekir.
