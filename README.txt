OSIRISZK — MARS PATHFINDER 3D / SÜRÜM 2.3
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

HELİKOPTER (UD-07)
W / S  veya  ↑ / ↓   Burnun baktığı yöne ileri / geri
A / D                Yana kayma
← / →  veya  Q / E   Kendi ekseni etrafında sola / sağa dönüş
SPACE / SHIFT        Yükselme / alçalma (platformdayken SPACE kalkış yaptırır)

GEZGİN (RV-01)
W / S  veya  ↑ / ↓   Gaz / geri vites
A / D  veya  ← / →   Direksiyon (araç dururken basılı tutunca yerinde döner)
SHIFT                Turbo
SPACE                Fren

XBOX KUMANDASI (Xbox One / Series; USB, Bluetooth veya kablosuz adaptör)
Kumandayı bağlayın, sayfa açıkken herhangi bir düğmeye bir kez basın
(tarayıcılar güvenlik gereği kumandayı ancak bir düğmeye basılınca tanır).
Bağlanınca görüntünün üstünde "🎮 KUMANDA" rozeti çıkar. Çubuk ve tetikler analogdur:
az basarsanız araç da yavaş hareket eder.
  Helikopter:  Sol çubuk ileri-geri / yana kayma · Sağ çubuk ←→ kendi ekseninde dönüş
               RT yüksel (platformdayken kalkış) · LT alçal
  Gezgin:      RT gaz · LT fren / geri · Sol çubuk direksiyon · RB turbo · B el freni
               Sağ çubuk kamerayı çevirir
  Düğmeler:    A kalkış / kenetlen · X tarama · Y araç değiştir · LB batarya
               Yön ↑ otonom görev · Yön ↓ veri gönder · Yön ←→ kamera modu
               R3 (sağ çubuğa bas) yakınlaştır · ☰ duraklat · ⧉ kılavuz
  Kalkış, kenetlenme, numune ve batarya değişiminde kumanda titrer (destekleyen tarayıcıda).

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
SÜRÜM 2.3 YENİLİKLERİ
- Xbox kumandası desteği (analog çubuk/tetik, titreşim, tüm görev düğmeleri).
- Platformdayken SPACE / RT ile kalkış.

SÜRÜM 2.2 YENİLİKLERİ
- Drone ok tuşlarıyla kendi ekseni etrafında döner; W/↑ her zaman burnun baktığı
  yöne uçar (2.0'daki model/hareket yönü ters dönme hatası giderildi).
- Drone ileri giderken burnunu indirir, yana kayarken yatar; otonom uçuşta rotaya döner.
- Helikopterin üstüne Ingenuity'deki gibi sabit güneş paneli eklendi.
- Gezgin: ~5 m/s seyir, SHIFT ile ~8 m/s turbo; ivme, fren ve eğim (yokuş/iniş) etkisi.
- 4 köşe tekerden direksiyon (ön ve arka zıt döner), dururken yerinde dönüş.
- Gövde arazi eğimine uyar, her teker ayrı süspansiyonla zemine basar,
  gövde ivmede/virajda yaylanır; tekerler doğru yönde ve iç/dış farklı hızda döner.
- Teker izleri, tekerlerden ve rotor akımından kalkan toz.
- HUD'da yön göstergesi (HDG), haritada araçların yön çizgisi.

- Gerçek zamanlı 3B Mars yüzeyi, yükselti, kraterler, kaya formasyonları
- 6 tekerlekli gezgin: gövde, tekerler, güneş panelleri, mast, kol, iniş platformu
- Ingenuity tarzı 3B helikopter: çift karşıt dönüşlü rotor, iniş ayakları, kamera,
  direk üstünde güneş paneli (gündüz bataryayı yavaşça şarj eder)
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
- Kumanda tepki vermiyorsa: sayfa açıkken bir düğmesine basın; Chrome/Edge kullanın;
  Steam açıksa Steam'in kumandayı ele geçirmediğinden emin olun.
- Tarayıcıda WebGL2 ve donanım hızlandırmasının açık olduğuna bakın.
- index.html, app.js, engine.js, scene.js, ingenuity.js, gamepad.js ve style.css aynı
  klasörde kalmalı; ZIP'in içinden doğrudan çalıştırmayın.
- Bir kez daha baslat.py başlatın (otomatik farklı uygun port seçer).
- F12 -> Console sekmesindeki hata mesajlarını kontrol edin.

KURULUM YAPMADAN ÖZGÜRCE GELİŞTİREBİLİRSİNİZ.
