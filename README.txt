OSIRISZK — MARS PATHFINDER 3D / SÜRÜM 2.0
=======================================

Node.js, npm, pip veya internet bağlantısı GEREKMEZ.
Python 3 ve WebGL2 destekleyen bir tarayıcı (Chrome / Edge) yeterlidir.

NASIL ÇALIŞTIRILIR? (WINDOWS + PYTHON IDLE)
1. ZIP dosyasına sağ tıklayın -> Tümünü Ayıkla.
2. Çıkan klasöre girin.
3. baslat.py dosyasını Python IDLE'da açın.
4. Üst menüden Run > Run Module (F5) seçin.
5. Tarayıcıda simülasyon otomatik açılır.
6. Kapatmak için IDLE Shell penceresinde Ctrl+C kullanın veya IDLE'ı kapatın.

ÖNEMLİ: index.html dosyasına çift tıklayıp doğrudan açmayın.
JavaScript modülleri yerel dosya güvenlik kısıtlamasına takılabilir.
Her zaman baslat.py üzerinden açın.

KONTROLLER
----------
TAB       Drone / gezgin aracı değiştir
WASD      Drone yatay hareket / Gezgin sürüş
SPACE     Drone yükselme
SHIFT     Drone alçalma
Q / E     Drone dönüş
F         Gezginin üzerine kenetlenme
G         Drone ile yakın kaya taraması
R         Gezgin ile yakın kaya araştırması
B         Platformda batarya değişimi
T         Toplanan verileri Dünya'ya aktarma (simülasyon)
M         Otonom keşif görevini başlat / durdur
P         Simülasyonu duraklat / devam et
1-4       Kamera modları
H         Kontrol kılavuzu
FARE      Sahne döndürme; tekerlekle yakınlaştırma

ÖZELLİKLER
----------
- Gerçek zamanlı 3B Mars yüzeyi, yükselti, kraterler, kaya formasyonları
- 6 tekerlekli gezgin: gövde, tekerler, güneş panelleri, mast, kol, iniş platformu
- Ingenuity tarzı 3B helikopter: çift karşıt dönüşlü rotor, iniş ayakları, kamera
- 4 takip kamera modu; fareyle bağımsız yörünge kontrolü
- Yükselme/alçalma, hız, enerji ve sinyal simülasyonu
- 3 kaya noktasına otonom keşif, tarama ve üsse dönüş
- Manuel tarama, kenetlenme, batarya değişimi, veri aktarımı
- Dinamik minimap, bilimsel telemetri, görev günlükleri
- Gün batımı / gündüz ışık geçişi
- Görev raporunu JSON biçiminde kaydetme
- Duraklatma ve sürdürme

BİLİMSEL SINIRLAR
-----------------
Mars yerçekimi 3.71 m/s², Ingenuity kütlesi yaklaşık 1.8 kg,
rotor çapı yaklaşık 1.2 m referans olarak kullanılmıştır.
3B rover, batarya değişimi ve bilimsel operasyonlar orijinal konsept tasarımdır.
Aerodinamik/çarpışma/iletişim/enerji denklemleri basitleştirilmiş ve
oyun amaçlıdır. Gerçek NASA uçuş analizi veya mühendislik doğrulaması değildir.

HATA DURUMUNDA
-------------
- Tarayıcıda WebGL2 ve donanım hızlandırmasının açık olduğuna bakın.
- index.html, app.js, engine.js, scene.js, ingenuity.js ve style.css aynı
  klasörde kalmalı; ZIP'in içinden doğrudan çalıştırmayın.
- Bir kez daha baslat.py başlatın (otomatik farklı uygun port seçer).
- F12 -> Console sekmesindeki hata mesajlarını kontrol edin.

KURULUM YAPMADAN ÖZGÜRCE GELİŞTİREBİLİRSİNİZ.
