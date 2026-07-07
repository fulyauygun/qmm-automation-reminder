# QMM Hatırlatma Otomasyonu — Kabul Test Planı

Kurulum yapılan PC'de, sistemi devreye almadan önce sırayla uygulanır.
Her testin **Beklenen** sonucu birebir gerçekleşmeden bir sonrakine
geçmeyin.

## Test ortamı kuralları (önce bunu okuyun)

1. **Gerçek Excel ile değil, KOPYASIYLA test edin.** Gerçek dosyanın bir
   kopyasını `C:\QMM\test\` gibi bir klasöre alın; `config.yaml` →
   `excel.path` önce bu kopyayı göstersin.
2. **Gerçek kanala değil, TEST kanalına gönderin.** Teams'te "QMM Test"
   adında geçici bir kanal açın, webhook'unu oluşturun ve
   `QMM_TEAMS_WEBHOOK_URL` değişkenine önce bu test webhook'unu koyun.
3. **Senaryolar arası hafızayı sıfırlayın.** Mükerrer engelleme geçmişi
   `state\` klasöründe tutulur; T5–T9 senaryoları arasında temiz
   başlangıç için `state` klasörünü silin (test ortamında serbest,
   canlıda asla).
4. **Zaman makinesi:** `--today 2026-08-01` gibi bir parametre, o günü
   simüle eder — gün beklemeden tüm tarih senaryoları test edilir.
5. Tüm testler bitince: `excel.path` gerçek dosyaya, webhook gerçek
   kanala çevrilir, `state` klasörü bir kez daha silinir ve T14 (zamanlama)
   canlıda tekrarlanır.

---

## Faz 1 — Kurulum doğrulama

### T1. Birim testleri
```bat
py -3 -m pip install -r requirements-dev.txt
py -3 -m pytest tests\
```
**Beklenen:** `31 passed` (tamamı yeşil). Kırmızı varsa kurulum/Python
sürümünü kontrol edin (3.10+).

### T2. Gerçek veri okuma (kuru çalıştırma)
```bat
py -3 -m qmm_reminder --config config.yaml --dry-run
```
**Beklenen:** Log'da `Read N document(s)` satırındaki **N, Excel'deki
dolu satır sayısına eşit**. `WARNING` satırı yoksa tüm satırlar
okunabiliyor demektir; varsa hangi satırın neden atlandığını söyler —
düzeltin ve tekrarlayın.

### T3. Tarih matematiği kontrolü
Excel'den 1 talimat seçin, son geçerlilik tarihini not edin (örn.
15.09.2026). Elle hesaplayın: T-30 = 16.08.2026.
```bat
py -3 -m qmm_reminder --config config.yaml --dry-run --today 2026-08-16
```
**Beklenen:** O talimat için `would send T-30` satırı. Bir gün öncesiyle
(`--today 2026-08-15`) çalıştırınca o talimat için hiçbir şey çıkmamalı.

---

## Faz 2 — Bildirim teslimatı (test kanalına)

### T4. Gerçek Teams kartı
T3'teki tarihle bu kez `--dry-run` OLMADAN çalıştırın:
```bat
py -3 -m qmm_reminder --config config.yaml --today 2026-08-16
```
**Beklenen:** Test kanalına sarı başlıklı kart düşer; Doküman / Bölüm /
Revizyon No / tarihler Excel'dekiyle birebir aynı; karttaki gün sayısı
doğru. Config'de `mentions` tanımlıysa kartın altında "Bilgi: @Ad ..."
satırı görünür ve o kişiye **kişisel bildirim** gider (kişiye teyit
ettirin — Teams ekibine üye olması şarttır).

### T5. Mükerrer engelleme
T4'teki komutu **aynen bir kez daha** çalıştırın.
**Beklenen:** Kanala **hiçbir yeni kart düşmez**; log `0 notification(s)
due` der. (Kritik: bu çalışmazsa her gün aynı hatırlatma tekrar gider.)

### T6. Telafi (catch-up) davranışı
`state` klasörünü silin. Seçtiğiniz talimatın T-5 gününü simüle edin
(örn. son geçerlilik 15.09 ise `--today 2026-09-10`).
**Beklenen:** Kanala **tek** kart düşer (T-7), T-30/T-15 için ayrıca
kart **gelmez** — kaçan günler sessizce "aşıldı" olarak işaretlenir.
Ardından `--today 2026-09-14` ile çalıştırın → T-1 kartı gelir.

### T7. Süresi geçmiş (overdue) döngüsü
`state` klasörünü silin. Son geçerliliği geçmiş bir gün simüle edin
(örn. `--today 2026-09-20`).
**Beklenen:** Kırmızı "GEÇERLİLİK SÜRESİ DOLDU" kartı gelir. Ertesi günü
simüle edin (`--today 2026-09-21`) → kart **gelmez** (7 günlük aralık).
`--today 2026-09-27` → kart **tekrar gelir**.

### T8. Revizyon sonrası sıfırlanma
Test Excel'inde o talimatın revizyon/geçerlilik tarihini ileri bir
tarihe güncelleyin (revize edilmiş gibi).
**Beklenen:** Overdue kartları kesilir; yeni tarihe göre T-30 günü
simüle edilince hatırlatma döngüsü **yeniden** başlar.

### T9. Yeni satır otomatik takip
Test Excel'ine yepyeni bir talimat satırı ekleyin (son geçerliliği ~6
gün sonra olacak şekilde) ve bugünle çalıştırın.
**Beklenen:** Sadece yeni satır için kart gelir — hiçbir "tanıtma"
işlemi yapılmadan.

---

## Faz 3 — Dayanıklılık

### T10. Arıza bildirimi
Test Excel'inin adını geçici olarak değiştirin ve çalıştırın.
**Beklenen:** Kanala kırmızı **"🔴 QMM hatırlatma otomasyonu
ÇALIŞAMADI"** kartı düşer, log'a hata yazılır, komut çıkış kodu 2 olur.
Dosya adını geri alın → sistem kendiliğinden normale döner.

### T11. Excel açıkken çalışma
Test Excel'ini Excel programında **açık bırakın**, dry-run çalıştırın.
**Beklenen:** Okuma normal çalışır (araç salt-okunur açar); hata yok.

### T12. Durum sayfası (dashboard)
`rapor\index.html` dosyasını tarayıcıda açın.
**Beklenen:** Özet kutular tabloyla tutarlı; bölüm grafiği doğru; arama
kutusu ve durum filtreleri çalışıyor; "Süresi doldu" filtresi yalnızca
gecikmişleri gösteriyor. Gizli "Revizyon İçeriği" hiçbir yerde görünmüyor.

### T13. Log ve kayıt kontrolü
`logs\qmm_reminder.log` dosyasını açın.
**Beklenen:** Yapılan her test çalıştırması tarih damgası, okunan satır
sayısı ve gönderim sonuçlarıyla görünüyor.

---

## Faz 4 — Zamanlama (canlıya geçiş)

### T14. Görev Zamanlayıcı
`config.yaml`'ı gerçek dosya + gerçek kanala çevirin, `state` klasörünü
silin, README'deki `schtasks` komutuyla görevi oluşturun. İlk denemede
saati 5 dakika sonrasına verin.
**Beklenen:** Görev kendiliğinden çalışır (log'a yeni kayıt düşer);
"Son Çalıştırma Sonucu 0x0" görünür. Sonra saati 08:00'e alın ve görev
özelliklerinde **"Zamanlanan başlangıç kaçırılırsa görevi en kısa sürede
çalıştır"** kutusunu işaretleyin (PC geç açılırsa telafi için).

### T15. Ertesi sabah kontrolü (canlı)
İlk gerçek sabahtan sonra: log'da o sabahki çalıştırma var mı, kanala
beklenen kartlar düştü mü, dashboard yenilendi mi?
**Beklenen:** Üçü de evet. Bu noktadan sonra sistem devrededir; aylık
kontrol rutini için `DEVIR_TALIMATI.md`'ye geçin.

---

## Hızlı sonuç tablosu

| # | Test | Sonuç (✓/✗) | Not |
|---|---|---|---|
| T1 | Birim testleri | | |
| T2 | Gerçek veri okuma | | |
| T3 | Tarih matematiği | | |
| T4 | Teams kartı + mention | | |
| T5 | Mükerrer engelleme | | |
| T6 | Telafi davranışı | | |
| T7 | Overdue döngüsü | | |
| T8 | Revizyon sıfırlanması | | |
| T9 | Yeni satır takibi | | |
| T10 | Arıza bildirimi | | |
| T11 | Excel açıkken okuma | | |
| T12 | Dashboard | | |
| T13 | Log kontrolü | | |
| T14 | Zamanlama | | |
| T15 | Canlı sabah kontrolü | | |
