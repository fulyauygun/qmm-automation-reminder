# QMM Automation Reminder

Bosch QMM (Kalite) bolumu icin calisma talimatlarinin gecerlilik suresi
dolmadan once otomatik mail hatirlatmasi gonderen basit bir otomasyon.

## Nasil calisir

1. `data/QMM_Talimat_Index.xlsx` dosyasindaki **"Liste"** sayfasi tek veri
   kaynagidir. Her talimatin **"Degisiklik Olmamasi Durumunda Guncellenmesi
   Gereken Ilk Tarih"** sutunu (H) o talimatin son gecerlilik tarihidir.
2. `scripts/check_reminders.py` her gun otomatik calisir, bu tarihe kalan gun
   sayisini hesaplar. Kalan gun **30 / 15 / 7 / 1** oldugunda
   `config/recipients.json` icindeki herkese ozet bir hatirlatma maili gider.
3. Ayni talimat + ayni esik icin ikinci kez mail gitmemesi icin gonderilen
   hatirlatmalar `scripts/state/sent_reminders.json` dosyasina kaydedilir
   (GitHub Actions bu dosyayi her calismadan sonra otomatik commit'ler).
4. Zamanlama: `.github/workflows/qmm-reminders.yml` her gun saat 06:00 UTC'de
   (TR saatiyle ~08:00-09:00) otomatik calisir. `Actions` sekmesinden elle de
   tetiklenebilir (test icin farkli bir tarih veya dry-run secenegiyle).

## Talimat listesini guncel tutmak

Yeni bir talimat eklendiginde veya bir revizyon tarihi degistiginde:
`data/QMM_Talimat_Index.xlsx` dosyasini guncelleyip repoya push edin.
Baska bir islem gerekmez, script bir sonraki calismasinda guncel dosyayi
okur.

## Alici listesini yonetmek (admin)

`config/recipients.json` dosyasi hatirlatma alacak kisileri tutar:

```json
{
  "admins": [{ "name": "Caglar", "email": "caglar.ornek@bosch.com" }],
  "recipients": [
    { "name": "Caglar", "email": "caglar.ornek@bosch.com" },
    { "name": "Yeni Kisi", "email": "yeni.kisi@bosch.com" }
  ]
}
```

- Yeni birini eklemek icin `recipients` listesine `{ "name": ..., "email": ... }`
  ekleyip commit+push etmeniz yeterli.
- Bu repoya push yetkisi olan kisi (orn. Caglar abi ve eklediginiz kisiler)
  fiilen "admin" rolundedir; ayri bir giris/sifre sistemi yoktur (basit
  otomasyon secildigi icin web paneli kurulmadi).
- `admins` alani su an bilgi amaclidir, script tarafindan kullanilmiyor;
  ileride "sadece adminler ekleme yapabilsin" gibi bir kontrol gerekirse
  buradan genisletilebilir.

## Mail gonderimi icin kurulum gereken secret'lar

Repo `Settings > Secrets and variables > Actions` altina eklenmesi gerekenler:

| Secret            | Aciklama                                                       |
| ----------------- | ---------------------------------------------------------------- |
| `SMTP_HOST`       | SMTP sunucu adresi (orn. `smtp.gmail.com`)                      |
| `SMTP_PORT`       | Genelde `587`                                                    |
| `SMTP_USER`       | Gonderen mail hesabinin kullanici adi (giris icin)               |
| `SMTP_PASSWORD`   | Mail hesabinin (uygulama) sifresi                                |
| `MAIL_FROM`       | Gorunecek gonderen adresi (bos birakilirsa SMTP_USER)            |
| `MAIL_FROM_NAME`  | Gorunen gonderen ismi (bos birakilirsa "QMM Talimat Hatirlatma Sistemi") |
| `REPLY_TO`        | (Opsiyonel) Birisi maile "yanitla" derse gidecek adres           |

**Kurumsal (Bosch) SMTP izni alinamiyorsa oneri:** Kimseye ait olmayan,
sadece bu otomasyon icin acilmis notr bir hesap kullanin (orn.
`qmmhatirlatma@gmail.com`). Bosch IT'den herhangi bir onay/erisim
gerektirmez, sadece normal bir Gmail hesabi acmak kadar basittir:

1. Bu iş icin yeni bir Gmail hesabi acin (kimsenin kisisel adi olmasin).
2. O hesapta 2 Adimli Dogrulama'yi acip
   ["Uygulama Sifresi"](https://myaccount.google.com/apppasswords) olusturun.
3. Secret'lari şöyle ayarlayin:
   - `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`
   - `SMTP_USER` / `MAIL_FROM` = yeni acilan hesabin adresi
   - `SMTP_PASSWORD` = olusturulan uygulama sifresi
   - `MAIL_FROM_NAME` = orn. `QMM Talimat Hatirlatma Sistemi`
   - `REPLY_TO` = orn. Caglar'in gercek adresi (biri yanitlarsa ona gitsin diye)

Boylece mailler kisisel bir isimle degil, kurumsal gorunumlu bir sistem
adiyla gider ve yanitlar dogru kisiye yonlenir. Ileride Bosch kurumsal SMTP
erisimi saglanirsa sadece bu secret'lari degistirmeniz yeterli, kod
tarafinda degisiklik gerekmez.

## Lokal test

```bash
pip install -r requirements.txt

# Belirli bir tarihte kimlere ne gidecegini gormek icin (mail atmadan):
python scripts/check_reminders.py --date 2026-08-07 --dry-run

# Gercek gonderim icin once SMTP_HOST/SMTP_USER/SMTP_PASSWORD/MAIL_FROM
# ortam degiskenlerini set edip --dry-run olmadan calistirin.
```
