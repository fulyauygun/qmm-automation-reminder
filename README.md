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

| Secret          | Aciklama                                              |
| --------------- | ------------------------------------------------------ |
| `SMTP_HOST`     | SMTP sunucu adresi (orn. `smtp.gmail.com`)             |
| `SMTP_PORT`     | Genelde `587`                                          |
| `SMTP_USER`     | Gonderen mail adresi / kullanici adi                   |
| `SMTP_PASSWORD` | Mail hesabinin (uygulama) sifresi                       |
| `MAIL_FROM`     | Gorunecek gonderen adresi (bos birakilirsa SMTP_USER)  |

**Oneri:** Kurumsal SMTP bilgisi yoksa, baslangicta bir Gmail hesabi icin
["Uygulama Sifresi" (App Password)](https://myaccount.google.com/apppasswords)
olusturup `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587` ile kullanabilirsiniz.
Ileride Bosch kurumsal SMTP bilgisi temin edilirse sadece bu secret'lari
degistirmeniz yeterli, kod tarafinda degisiklik gerekmez.

## Lokal test

```bash
pip install -r requirements.txt

# Belirli bir tarihte kimlere ne gidecegini gormek icin (mail atmadan):
python scripts/check_reminders.py --date 2026-08-07 --dry-run

# Gercek gonderim icin once SMTP_HOST/SMTP_USER/SMTP_PASSWORD/MAIL_FROM
# ortam degiskenlerini set edip --dry-run olmadan calistirin.
```
