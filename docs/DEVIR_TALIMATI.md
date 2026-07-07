# QMM Hatırlatma Otomasyonu — Devir ve İşletim Talimatı

Bu belge, aracı kuran kişi ayrıldıktan sonra QMM ekibinin sistemi
**kod bilgisi gerektirmeden** işletebilmesi için yazılmıştır.

## Sistem ne yapar?

Her sabah (varsayılan 08:00) kontrol listesi Excel'ini ağ paylaşımından
okur; geçerlilik süresinin dolmasına **30 / 15 / 7 / 1 gün** kala ve süre
dolduktan sonra **7 günde bir**, Teams kanalına hatırlatma kartı gönderir
(isteğe bağlı olarak e-posta da). Excel dosyası hiçbir dış sisteme
yüklenmez.

## Günlük kullanımda ekibin yapması gerekenler

| İstediğiniz şey | Yapılacak işlem |
|---|---|
| Bir talimat revize edildi | Excel'de satırın **Revizyon Tarihi** ve **güncellenme tarihi** alanlarını güncelleyin — hatırlatmalar otomatik olarak yeni tarihe göre yeniden kurulur |
| Yeni talimat eklendi | Excel'e yeni satır ekleyin, başka işlem gerekmez |
| Yeni biri kişisel bildirim alsın | Excel'deki **"Bildirim Alıcıları"** sayfasına ad + e-posta satırı ekleyin — ertesi sabahtan itibaren Teams kartlarında adıyla etiketlenir (@bahsetme) ve kişisel bildirim alır. Kişinin ilgili Teams ekibine üye olması gerekir |
| Birine artık gitmesin | Aynı sayfada o kişinin **Aktif** sütununa `Hayır` yazın |
| Teams kartlarını yeni biri sadece görsün | Kişiyi ilgili Teams kanalına ekleyin — başka işlem yok |
| E-posta da gitsin (kanal açıksa) | Aynı "Bildirim Alıcıları" sayfası e-posta kanalını da besler; ayrı liste tutulmaz |
| Hatırlatma günlerini değiştirmek | Kurulum klasöründeki `config.yaml` → `milestones_days` satırı (örn. `[30, 15, 7, 1]`) |
| Genel durumu görsel olarak görmek | Kurulum klasöründeki `rapor\index.html` dosyasını tarayıcıda açın — özet sayılar ve talimat tablosu her sabah otomatik yenilenir. Bu dosyayı şirket dışına/İnternet'e koymayın |

## Sistem çalışıyor mu? (aylık kontrol önerilir)

1. **Teams kanalına bakın:** yaklaşan tarih olduğu hâlde günlerce kart
   gelmiyorsa şüphelenin. Araç bozulduğunda kanala kırmızı
   **"🔴 QMM hatırlatma otomasyonu ÇALIŞAMADI"** kartı düşürmeye çalışır;
   bu kartı görürseniz aşağıdaki arıza tablosuna gidin.
2. **Log dosyasına bakın:** kurulum klasöründe `logs\qmm_reminder.log` —
   her çalıştırma tarih damgasıyla görünür. Son satırların tarihi bugünse
   sistem çalışıyordur.
3. **Elle deneme:** kurulum klasöründe komut istemi açıp şunu çalıştırın
   (hiçbir bildirim göndermez, sadece ne yapacağını gösterir):
   `py -3 -m qmm_reminder --config config.yaml --dry-run`

## Arıza tablosu

| Belirti | Muhtemel sebep | Çözüm |
|---|---|---|
| Kanala hiç kart düşmüyor, logda da yeni kayıt yok | Zamanlanmış görev çalışmıyor (PC kapalı, görev silinmiş, kullanıcı hesabı pasif) | Görev Zamanlayıcı'yı açın → "QMM Reminder" görevinin durumuna/geçmişine bakın; gerekirse README'deki `schtasks` komutuyla yeniden oluşturun |
| "ÇALIŞAMADI" kartında *Excel file not found* | Dosya taşınmış/yeniden adlandırılmış | `config.yaml` içindeki `excel.path` satırını yeni yola göre düzeltin |
| "ÇALIŞAMADI" kartında *header/column* hatası | Excel'de sütun başlığı değiştirilmiş | Başlığı eski hâline getirin ya da `config.yaml` → `excel.columns` bölümünü yeni başlığa göre güncelleyin |
| Kartlar Teams'e gelmiyor, logda webhook hatası var | Webhook URL'si geçersiz (akış silinmiş ya da sahibinin hesabı kapanmış) | Aşağıdaki "Webhook yenileme" adımlarını uygulayın |
| Aynı hatırlatma tekrar tekrar geliyor | `state` klasörü silinmiş | Normaldir, kendini toparlar: geçmiş gönderim hafızası silindiği için bir kez tekrar gönderir, sonra düzene girer |

### Webhook yenileme (5 dakika)

1. Teams'te ilgili kanal → **⋯ → Workflows → "Post to a channel when a
   webhook request is received"** şablonuyla yeni akış oluşturun ve URL'yi
   kopyalayın. **Önemli:** akışı kalıcı bir ekip üyesi (tercihen ortak
   ekip hesabı) oluşturmalı — akış, oluşturanın hesabına bağlıdır ve o
   hesap kapanırsa çalışmaz.
2. Otomasyonun çalıştığı PC'de, görevi çalıştıran kullanıcıyla oturum
   açıp komut istemine şunu yazın:
   `setx QMM_TEAMS_WEBHOOK_URL "yeni-url"`
3. Deneme: `py -3 -m qmm_reminder --config config.yaml --dry-run`

## Devir sırasında yapılması gerekenler (ayrılmadan önce)

- [ ] Kurulumu stajyerin kişisel PC'sinden **ekipçe kullanılan bir PC'ye
      veya IT'den istenecek küçük bir sunucuya/VM'e** taşıyın; görevi
      kişisel hesap yerine **ekip/servis hesabıyla** zamanlayın.
      (Kişisel hesap kapatıldığında görev de durur — en sık devir hatası
      budur.)
- [ ] Teams webhook akışının sahipliğini kalıcı bir ekip üyesine/ortak
      hesaba aldırın (yukarıdaki not).
- [ ] Kod ve bu belgelerin bir kopyasını şirket içi bir konumda tutun
      (ağ paylaşımında `_kurulum` klasörü ve/veya şirket Git deposu) —
      kişisel GitHub hesabına bağımlı kalmayın.
- [ ] `config.yaml` içindeki yolların ve ayarların güncel olduğunu
      birlikte kontrol edin; bu talimatı ekipten bir kişiyle birlikte
      baştan sona bir kez uygulayın (kuru çalıştırma dahil).
- [ ] Sistemin "sahibi" olarak bir ekip üyesi belirleyin (aylık kontrolü
      yapacak kişi).

## Sınırlar

- Araç Excel'e **hiçbir zaman yazmaz**; tek yönlü okur. Excel'i bozması
  mümkün değildir.
- Excel o an bir kullanıcıda açıksa okuma yine çalışır (salt-okunur).
- Gizli "Revizyon İçeriği" sütunu hiçbir bildirime yazılmaz.
