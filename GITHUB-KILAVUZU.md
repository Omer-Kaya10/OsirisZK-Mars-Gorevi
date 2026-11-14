# GitHub'a yükleme ve oyunu yayına alma kılavuzu

**Türkçe** · [English summary](#english)

Bu kılavuz `OsirisZK-Mars-Gorevi.zip` dosyasını takımın deposuna ilk kez yüklemek ve oyunu internette
herkesin açabileceği bir adrese koymak içindir.

**Depo:** <https://github.com/Omer-Kaya10/OsirisZK-Mars-Gorevi> (takım kaptanının hesabında, şu an boş).
Yüklemeyi deponun sahibi (takım kaptanı) öğretmenin gözetiminde yapar.

> ⏱ Süre: yaklaşık 15 dakika · 🔐 Depoya hiçbir şifre, anahtar ya da kişisel bilgi konmaz.

---

## 0. Öğretmen erişimi (önerilen, bir kez)
Hesaplar öğretmenin kontrolünde olacağı için kaptan, depoya öğretmeni ekler:
1. Depoda **Settings → Collaborators → Add people**.
2. Öğretmenin GitHub kullanıcı adını yazın (`AnubisZk`) → **Add**. Öğretmen gelen daveti kabul eder.
3. Böylece öğretmen de dosya yükleyebilir, değişiklikleri onaylayabilir ve gerekirse yapay zekâ
   ajanına depoda çalışma izni verebilir.

## 1. Zip'i açın
1. `OsirisZK-Mars-Gorevi.zip` dosyasına sağ tıklayın → **Tümünü ayıkla**.
2. Açılan `OsirisZK-Mars-Gorevi` klasörünün içinde şunları görmelisiniz:
   `index.html`, `README.md`, `GITHUB-KILAVUZU.md`, `netlify.toml`, `.gitignore`, `.github`,
   `oyun`, `web`, `modeller`, `belgeler`.
3. Mac kullanıyorsanız `.github` ve `.gitignore` gizli görünür. Görmek için Finder'da
   **Cmd + Shift + .** tuşlarına basın.

> ⚠ GitHub zip dosyasını **açmaz**. Zip'in kendisini değil, **klasörün içindekileri** yükleyeceğiz.

## 2. Depo hazır
Depo zaten açılmış ve boş: <https://github.com/Omer-Kaya10/OsirisZK-Mars-Gorevi>.
(README, .gitignore ya da lisans eklemeyin; bunlar zip'te var.) Yeni bir takım kendi deposunu açacaksa:
<https://github.com/new> → ad girin → **Public** → kutuları işaretlemeden **Create repository**.

## 3. Dosyaları yükleyin

### Yol A — Tarayıcıdan (en kolay)
1. Yeni deponun sayfasında **"uploading an existing file"** bağlantısına tıklayın.
2. Bilgisayarınızda `OsirisZK-Mars-Gorevi` klasörünü açın, içindeki **her şeyi seçin**
   (Ctrl + A / Cmd + A) ve tarayıcıdaki kutuya **sürükleyip bırakın**. Klasörler alt klasörleriyle gelir.
3. Listede `.github/workflows/testler.yml` ve `netlify.toml` dosyalarının da olduğunu kontrol edin.
4. **Commit changes** kutusuna şunu yazın: `İlk sürüm: OsirisZk Mars Pathfinder v3.2 (masaüstü + web, TR/EN)`
5. **Commit changes**'e basın.

> `.github` klasörü sürüklenmediyse: depoda **Add file → Create new file** deyin, ad olarak
> `.github/workflows/testler.yml` yazın ve zip'teki aynı dosyanın içeriğini yapıştırın.

### Yol B — GitHub Desktop
1. GitHub Desktop → **File → Clone repository** → `OsirisZK-Mars-Gorevi`.
2. Zip'teki klasörün içindekileri, klonlanan klasöre kopyalayın.
3. Özet: `İlk sürüm: OsirisZk Mars Pathfinder v3.2` → **Commit to main** → **Push origin**.

### Yol C — Komut satırı
```bash
cd OsirisZK-Mars-Gorevi
git init -b main
git add .
git commit -m "İlk sürüm: OsirisZk Mars Pathfinder v3.2 (masaüstü + web, TR/EN)"
git remote add origin https://github.com/Omer-Kaya10/OsirisZK-Mars-Gorevi.git
git push -u origin main
```

## 4. Testlerin yeşil olduğunu görün
Depoda **Actions** sekmesine gidin. "Testler" iş akışı birkaç dakika içinde ✅ olmalı.
Bu iş akışı her yüklemede masaüstü testlerini, araç modeli uyumunu ve web köprüsünü (İngilizce çeviriler
dahil) denetler. ❌ görürseniz kırmızı satıra tıklayıp hata mesajını okuyun.

## 5. Oyunu yayına alın

### Seçenek 1 — GitHub Pages (en kolay; deponun kendi ayarı)
1. Depoda **Settings → Pages**.
2. **Source: Deploy from a branch**, **Branch: `main`**, klasör **`/ (root)`** → **Save**.
3. Birkaç dakika sonra adres: **https://omer-kaya10.github.io/OsirisZK-Mars-Gorevi/**
4. Bundan sonra `main` dalına yapılan her yükleme siteyi kendiliğinden günceller.

### Seçenek 2 — Netlify (öğretmenin Netlify hesabında)
1. <https://app.netlify.com> → **Add new project → Import an existing project → GitHub**.
2. Depo listede yoksa **Configure the Netlify app on GitHub** deyin. Depo kaptanın hesabında olduğu için
   bu izni **depo sahibi** verir (kendi GitHub hesabıyla Netlify uygulamasına bu depoyu seçerek).
3. Ayarlar `netlify.toml`'dan otomatik gelir: **Build command boş**, **Publish directory `.`** → **Deploy**.
4. **Project configuration → Change project name** → ör. `osiriszk-mars-gorevi`.

İki seçenekte de derleme yoktur: oyun dosyaları olduğu gibi yayımlanır. Oyun motoru (Python), ilk açılışta
tarayıcıya yaklaşık 15 MB olarak `cdn.jsdelivr.net` adresinden yüklenir; okul ağı bu adresi engelliyorsa
masaüstü sürümünü kullanın.

Oyun bu sırada OsirisZk sitesinde de açık: <https://osiris-mars-explorer.netlify.app/gezgin/>.
Takımın adresi yayına girince oradaki kopya bu depoya yönlendirilecek; böylece tek kaynak kalır.

### Yayını kontrol edin
- Sayfa açılınca "Oyun motoru yükleniyor" yazısı kaybolmalı.
- **Başlat**'a basın, **Space** ile kalkın, **WASD** ile uçun.
- Sağ üstteki **TR / EN** düğmesiyle dili değiştirin; `?dil=en` ile İngilizce bağlantı paylaşabilirsiniz.
- `…/modeller/` sayfasında araç çizimleri ve değerleri görünmeli.
- `…/3b/` adresinde 3B oyun açılmalı; **OTONOM KEŞİF**'e basınca drone üç kayayı tarayıp gezgine dönmeli.

## 6. Öğrencilerle çalışma kuralları
- **Ana dal (`main`) korunsun:** Settings → Branches → **Add branch ruleset** → `main` için
  "Require a pull request before merging" ve "Block force pushes" açın. Böylece kimsenin çalışması
  üzerine yazılamaz ya da silinemez.
- Her öğrenci ya da takım kendi dalında çalışır (`ogrenci/drone-fizigi` gibi), bitince **Pull request** açar,
  öğretmen inceleyip birleştirir.
- Bir değeri değiştirmek isteyen önce `modeller/modeller.json`'u, sonra `oyun/mars_core.py`'yi günceller;
  `test_modeller.py` ikisinin uyumunu denetler.
- Yeni bir oyun mesajı eklenirse `web/ceviri.py`'ye İngilizcesi de eklenir (yoksa test kırmızı olur).
- Depoya **şifre, API anahtarı, ad soyad, okul numarası, fotoğraf** konmaz.
- Lisans: Depoyu başkalarının nasıl kullanabileceğine öğretmen karar verir; karar verilince GitHub'da
  **Add file → Create new file → `LICENSE`** ile şablon seçilebilir.

## 7. Sorun giderme
| Belirti | Çözüm |
|---|---|
| Sayfa "404 / Page not found" | Pages için klasör `/ (root)`, Netlify için Publish directory `.` mı? `index.html` deponun **kökünde** mi (bir klasörün içinde değil)? |
| "Oyun motoru yüklenemedi" | İnternet bağlantısı ya da okul ağı `cdn.jsdelivr.net`'i engelliyor olabilir; masaüstü sürümünü kullanın. |
| Actions'ta test ❌ | Hata satırını okuyun; çoğunlukla `modeller.json` ile `mars_core.py` farklı değerdedir. |
| Masaüstü sürümü açılmıyor | Python 3.10+ ve tkinter gerekir (Windows Python kurulumunda vardır). `oyun/README.txt`'ye bakın. |
| Yüklemede bazı dosyalar eksik | Tarayıcıdan yüklemede en çok 100 dosya bir kerede yüklenir; eksikleri ikinci kez sürükleyin. |

---

<a id="english"></a>
## English summary

Repository: <https://github.com/Omer-Kaya10/OsirisZK-Mars-Gorevi> (owned by the team captain, currently empty).

0. **Teacher access (recommended):** *Settings → Collaborators → Add people* → `AnubisZk`.
1. **Unzip** `OsirisZK-Mars-Gorevi.zip`. GitHub does not unpack zip files, so upload the *contents* of the
   folder (including the hidden `.github` folder and `.gitignore`).
2. **Upload:** on the empty repository page click *uploading an existing file*, drag everything from the
   folder and commit with `Initial release: OsirisZk Mars Pathfinder v3.2 (desktop + web, TR/EN)`.
   Alternatives: GitHub Desktop, or `git init -b main && git add . && git commit -m "…" &&
   git remote add origin https://github.com/Omer-Kaya10/OsirisZK-Mars-Gorevi.git && git push -u origin main`.
3. **Check the tests:** the *Actions* tab should show the "Testler" workflow passing ✅.
4. **Go live:** *Settings → Pages → Deploy from a branch → `main` / root* →
   `https://omer-kaya10.github.io/OsirisZK-Mars-Gorevi/`. Netlify also works (no build, publish `.`), but the
   repository owner must grant the Netlify GitHub app access to this repository.
5. **Verify:** the loading message disappears, *Start* + Space takes off, the **TR / EN** switch changes the
   language (`?dil=en` links straight to English), and `/modeller/` shows the vehicle drawings.
6. **Working with students:** protect `main` (require pull requests, block force pushes), one branch per
   student/team, no passwords, keys or personal data in the repository. When a new game message is added,
   add its English translation to `web/ceviri.py` (the tests enforce this).
