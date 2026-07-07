# Kurulum Günü — Adım Adım Yapılacaklar

Şirket PC'sinde ilk kurulum için sıralı liste. Tahmini süre: 1–2 saat
(IT bekleme süreleri hariç). Her adımı bitirmeden sonrakine geçmeyin.

## Yanınızda olması gerekenler

- [ ] Bu projenin ZIP'i (aşağıda Adım 1'de adresi var; şirket ağından
      GitHub'a erişilemiyorsa önceden indirip şirket politikasına uygun
      bir yolla getirin)
- [ ] Gerçek kontrol listesi Excel'inin ağ paylaşımındaki tam yolu
      (örn. `\\sunucu\QMM\...xlsx`)
- [ ] Bildirim alacak kişilerin ad + şirket e-posta adresleri
- [ ] Teams'te hatırlatmaların gideceği kanalın adı (test için ayrıca
      geçici bir "QMM Test" kanalı açma yetkisi)

---

## Adım 1 — Kodu PC'ye alın

Tarayıcıdan ZIP indirin:

```
https://github.com/irmkoci/qmm-automation-reminder/archive/refs/heads/claude/confident-meitner-w3p1fk.zip
```

ZIP'i açın ve klasörü şuraya taşıyın (klasör adındaki ek uzantıları
temizleyin):

```
C:\QMM\qmm-automation-reminder\
```

Doğrulama: bu klasörün içinde `qmm_reminder\`, `tests\`, `docs\`,
`config.example.yaml`, `requirements.txt`, `run_qmm_reminder.bat`
görünmeli.

## Adım 2 — Python

Komut istemi açın (Başlat → `cmd`):

```bat
py --version
```

- `Python 3.10`+ görünüyorsa → Adım 3'e geçin.
- Görünmüyorsa → **Software Center**'dan Python kurun; orada da yoksa IT
  talebi açın (metin örneği `docs`'taki Python kurulum notlarında).

## Adım 3 — Paketler

```bat
cd C:\QMM\qmm-automation-reminder
py -3 -m pip install -r requirements.txt
```

Proxy/bağlantı hatası alırsanız IT'den dahili PyPI adresini isteyin:
`py -3 -m pip install -r requirements.txt -i <dahili-adres>`

## Adım 4 — Kurulum sağlaması (TEST_PLANI T1)

```bat
py -3 -m pytest tests\
```

**Beklenen: `31 passed`.** Değilse ilerlemeyin; hata çıktısını kaydedin.

## Adım 5 — Test Excel'i

Gerçek Excel'in bir **kopyasını** alın:

```
C:\QMM\test\Kontrol Listesi (TEST).xlsx
```

## Adım 6 — config.yaml

```bat
copy config.example.yaml config.yaml
notepad config.yaml
```

Düzenlenecek yerler:

1. `excel.path` → önce TEST kopyasının yolu (Adım 5).
   Dikkat: ters bölüler çift yazılır: `"C:\\QMM\\test\\Kontrol Listesi (TEST).xlsx"`
2. `excel.columns` → başlıklar gerçek dosyayla birebir aynı mı kontrol edin.
3. `notifications.teams.mentions` → gerçek kişilerin ad + e-postaları.
4. `notifications.email.enabled` → `false` kalsın (mail kanalı sonra).

## Adım 7 — Teams webhook (önce TEST kanalı)

1. Teams'te geçici **"QMM Test"** kanalı açın.
2. Kanal adının yanındaki **⋯ → Workflows →** "Post to a channel when a
   webhook request is received" şablonunu seçin → oluşturun → **URL'yi
   kopyalayın**.
3. Komut isteminde:
   ```bat
   setx QMM_TEAMS_WEBHOOK_URL "kopyaladığınız-url"
   ```
4. **ÖNEMLİ:** `setx` yeni pencerelerde geçerli olur — komut istemini
   **kapatıp yeniden açın.**

## Adım 8 — İlk kuru çalıştırma (T2)

```bat
cd C:\QMM\qmm-automation-reminder
py -3 -m qmm_reminder --config config.yaml --dry-run
```

**Beklenen:** `Read N document(s)` → N, Excel'inizdeki talimat sayısı.
`WARNING` satırı varsa hangi satırın sorunlu olduğunu söyler.

## Adım 9 — Kabul testleri

`docs\TEST_PLANI.md`'yi açın ve **T3'ten T13'e** sırayla uygulayın
(tarih simülasyonu için `--today` kullanılır; senaryolar arasında
`state` klasörü silinir — hepsi planda yazılı).

## Adım 10 — Canlıya geçiş (testler tamamsa)

1. `config.yaml` → `excel.path`'i **gerçek** dosyanın ağ yoluna çevirin.
2. Gerçek kanal için yeni webhook oluşturun (tercihen kalıcı bir ekip
   üyesinin hesabıyla), `setx` ile güncelleyin, pencereyi yenileyin.
3. `state` klasörünü **bir kez** silin (test geçmişi temizlensin).
4. Son bir `--dry-run` ile gerçek dosyada ne gönderileceğini görün —
   listede sürpriz yoksa devam.
5. Zamanlanmış görevi kurun:
   ```bat
   schtasks /Create /TN "QMM Reminder" /SC DAILY /ST 08:00 ^
     /TR "C:\QMM\qmm-automation-reminder\run_qmm_reminder.bat"
   ```
6. Görev Zamanlayıcı'yı açın → "QMM Reminder" → Özellikler → Ayarlar →
   **"Zamanlanan başlangıç kaçırılırsa görevi en kısa sürede çalıştır"**
   kutusunu işaretleyin.
7. İlk deneme için görevi sağ tıklayıp **Çalıştır** deyin → log'a kayıt
   düştüyse kurulum tamamdır.

## Ertesi sabah (T15)

- [ ] `logs\qmm_reminder.log` → bu sabahki çalıştırma var mı?
- [ ] Kanala beklenen kartlar düştü mü?
- [ ] `rapor\index.html` yenilenmiş mi?

Üçü de evetse: sistem canlıda. 🎉 Aylık işletim için
`DEVIR_TALIMATI.md`'ye geçin.

## Takılırsanız

Hata mesajını / log satırını olduğu gibi kopyalayın — sütun başlığı,
proxy, webhook sorunlarının hepsinin bilinen çözümü var
(`DEVIR_TALIMATI.md` → arıza tablosu).
