=======================================================================
 OSIRISZK - MARS PATHFINDER v3.2 (MASAÜSTÜ SÜRÜMÜ)
 INGenuity BENZERİ DRONE + GÜNEŞ ENERJİLİ MARS GEZGİNİ
=======================================================================

0) WEB SÜRÜMÜ / WEB VERSION

- Aynı oyun tarayıcıda da oynanır (kurulum gerekmez, Türkçe / English):
  deponun kökündeki index.html; yayın adresi için GITHUB-KILAVUZU.md'ye bakın.
- Oyun motoru (mars_core.py) iki sürümde de AYNI dosyadır.

1) ÇALIŞTIRMA (WINDOWS / IDLE)

- ZIP dosyasını tamamen klasöre çıkartın.
- `baslat.py` dosyasına sağ tıklayıp "Edit with IDLE" seçin.
- IDLE üst menüsü > Run > Run Module.
- Fn+F5 de çoğu laptopta işe yarar.
- Alternatif: `mars_oyunu.py` dosyasını doğrudan IDLE'da açıp çalıştırın.
- Alternatif: `BASLAT_WINDOWS.bat` dosyasına çift tıklayın.
- Üçüncü taraf paket kurulumu / internet bağlantısı gerekmez.
- Python 3.10 veya daha güncel sürüm önerilir; tkinter gerekir.

ÖNEMLİ: mars_oyunu.py, mars_core.py ve kamera.py AYNI klasörde olmalı.
Kod Python'dur; JavaScript satırlarını IDLE'a yapıştırmayın.

2) OYUNUN BAŞLANGICI

- Gezgin "ANA ÜS" konumunda ve hareket etmeye hazırdır.
- Ingenuity tarzı drone gezginin üstündeki iniş/kalkış alanındadır.
- "Başlat / Duraklat"a tıklayın.
- Drone denetimindeyken Space veya yukarı ok basın: drone gezginden kalkar.
- Tab tuşuyla drone ve gezgin kontrolleri arasında geçiş yapılır.
- Gezgin hareket ederse ve drone kenetliyse drone da gezginle taşınır.

3) KONTROLLER

W A S D ........... Seçili aracı harita düzleminde hareket ettirir
Space veya ↑ ..... Drone yükselir; kenetliyse gezginden kalkar
Shift veya ↓ ..... Drone alçalır
Tab ............... Drone / gezgin arasında geçiş yapar
E ................. Drone ile 75 birim yakınındaki kayayı tara (>=0,7 m)
R ................. Gezginle 66 birim yakınındaki kayayı incele
F ................. Drone'u gezginin üzerine kenetle
B ................. Kenetliyken drone bataryasını değiştir
T ................. Simüle edilen Dünya veri aktarımını aç / kapat
H ................. Yedek batarya deposu ısıtmasını aç / kapat
G ................. Gezgin güneş panellerini aç / kapat
C ................. Seçili aracın simülasyon kamerasından fotoğraf çek
V ................. Sanal kamera fotoğraflarını oyun içinde görüntüle
K ................. Kenetliyken drone bakım / onarım uygula
P ................. Oyunu duraklat / sürdür

Önemli: Gelişmiş kontrollerin butonları sağ panel ve alt çubukta da vardır.

4) DRONE-GEZGİN GÖREV SİSTEMİ

ADIM 1: Drone, hareketli gezgin üzerinden kalkar.
ADIM 2: Haritadaki üç kaya hedefini (E) ile tarar; her tarama için
        görüntü ve sensör verisinden bir paket üretilir.
ADIM 3: Gezgin kameralarıyla en az iki kaya yakınında (R) araştırma yapar.
ADIM 4: Drone, gezginin 35 birim yakınına gelir; 0,9 m veya altına
        yavaşça inip F'ye basarak gezgine kenetlenir.
ADIM 5: Kenetlenince drone hafızasındaki paketler gezgine aktarılır.
        Gerekirse B ile pil değiştir; eski pil raflarda şarj edilir.
ADIM 6: T ile Dünya veri bağlantısını aç; gezgindeki paketlerin aktarımı
        veri boyutlarına göre zamanla ilerler.
ADIM 7: Drone gezgine kenetlenmiş, tüm en az beş paket gönderilmiş ve
        gezgin başlangıç üssüne dönmüşse görev tamamlanır.

5) FİZİK / ENERJİ / SİSTEMLER

- Havada kalma: ağırlık = kütle * Mars yerçekimi.
- Güç tahmini: ideal rotor diski momentum teorisi + basitleştirilmiş verim.
- Drone yumuşatılmış hız/irtifa kontrolü ve kayaya çarpma hasarı kullanır.
- Gezgin yasal harita sınırları ve kayalık engeller dışına çıkamaz.
- Yalıtımlı batarya deposunda sıcaklık ve ısıtıcı enerji tüketimi izlenir.
- Oyunlaştırılmış toz fırtınalarında drone dışarıda risk alır, gezgin
  platformuna kenetliyken korunur; güneş panelinin üretimi azalır.
- Güneş paneli sahte oyun-gün döngüsü üzerinden güç üretir (W).
- Gezgin ana batarya ve yedek pil rafı enerji miktarları (Wh) ayrıdır.
- Gezgin değerleri mimari çizimlere göredir (../modeller/modeller.json):
  ana batarya 1200 Wh, güneş paneli 120 W, drone/yedek pil şarj gücü 100 W.
- Depodaki bitik bataryalar ana gezgin pilinden şarj edilerek doldurulur.
- Drone verisi gezgine kenetlendikten sonra simüle Dünya'ya gönderilebilir.
- Tüm fotoğraflar / kamera konumları / veriler oyun tarafından üretilir.

6) KAMERA DOSYALARI / KAYIT / CSV

- E, R veya C ile başarılı görüntü alımında `kamera_kayitlari` klasöründe
  gerçek PNG dosyası oluşturulur. Bunlar Mars yüzeyi temsili görselleridir.
- V tuşu / "GÖRÜNTÜ KAYITLARINI GÖR" butonu arşivi açar.
- "Kaydet" ile oyunun mevcut durumu JSON'a yazılır.
- "Yükle" ile v3 JSON kayıtları veya önceki oyundaki v1 kayıtları açılır.
- "CSV" ile uçuş + gezgin telemetrisi dışa aktarılır.
- PNG dosyaları JSON'a gömülmez. Tam arşiv için kamera klasörünü koruyun.
- Kayıt yolları ve JSON dosyaları, 4 MB boyut ve sayısal aralık kontrolleriyle
  doğrulanır; bilinmeyen program kodu çalıştırılmaz.

7) DOSYALAR

baslat.py ............... IDLE için başlatıcı
mars_oyunu.py ........... Arayüz / kontroller / harita / kayıt / galeri
mars_core.py ............ Drone fiziği + gezgin + enerji + iletişim + görev
kamera.py ............... Yerel PNG yazıcısı / sanal kamera
BASLAT_WINDOWS.bat ...... Windows kolay başlatıcı
test_eski_uyumluluk.py .. Önceki oyunun 11 testi
test_rover_drone.py ...... 29 gezgin/drone testi
test_modeller.py ......... 3 test: oyun motoru ↔ mimari çizimler (../modeller/modeller.json)
arayuz_onizleme.png ..... Oyunun ekran örneği
kamera_galeri_onizleme.png - Görsel arşiv ekran örneği

8) TEST ETME

Bilgisayarınızda CMD üzerinden:
  python -m unittest -v test_eski_uyumluluk.py test_rover_drone.py test_modeller.py

Veya test dosyasını Python IDLE ile açıp Run > Run Module.

9) BİLİMSEL DÜRÜSTLÜK

Bu OYUN, gerçek Ingenuity uçuş kodu veya Mars gezgini uçuş/işletim yazılımı
DEĞİLDİR. Ingenuity referansları: yaklaşık 1,8 kg kütle ve 1,2 m rotor çapı.
Mars yerçekimi yaklaşık 3,71 m/s². Geri kalan rover kütleleri, güç değerleri,
batarya kapasiteleri, sıcaklık, Mars gün döngüsü, mesaj büyüklükleri ve harita
ölçekleri bilerek temsilî/simülasyon amaçlı seçilmiştir. Dünya'ya GERÇEK ağ
bağlantısı yapılmaz, gerçek NASA fotoğrafı kullanılmaz.
=======================================================================
