# Operasyon Rehberi — Rakip Analizi

## Genel bakış — nerede ne çalışıyor

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Docker (docker.service, host: /home/khan/docker/changedetection/)       │
│  ├─ changedetection   → :5000  (UI + API)                                │
│  └─ playwright        → :3000  (JS render için sockpuppetbrowser)        │
│                                                                          │
│  Telegram bildirimi:   CD Apprise → tgram://…/-1003936786052 (kanal)    │
│  Datastore:            /home/khan/docker/changedetection/data/           │
└─────────────────────────────────────────────────────────────────────────┘
                                    ↑ API
                                    │
┌─────────────────────────────────────────────────────────────────────────┐
│ systemd --user (kullanıcı `khan`)                                        │
│  ├─ rakip-main.service         → main.py (30dk / 2sa döngü)              │
│  ├─ rakip-dashboard.service    → streamlit :8501                         │
│  └─ rakip-backup-cd.timer      → günlük 04:30 CD datastore yedeği        │
│                                                                          │
│  Repo (symlink):    /home/khan/rakip-analizi                             │
│  Gerçek konum:      /home/khan/Masaüstü/Rakip Analizi v2/repo            │
│  DB:                /home/khan/rakip-analizi/data/rakip_analizi.db       │
│  Log:               /home/khan/rakip-analizi/logs/                       │
│  Yedek:             /home/khan/rakip-analizi/backups/cd/*.tar.zst        │
└─────────────────────────────────────────────────────────────────────────┘
```

## URL'ler (yerel makinede)
- **Streamlit dashboard**: http://localhost:8501
- **changedetection UI**: http://localhost:5000
- **Portainer** (Docker yönetimi): http://localhost:9000

## Günlük komutlar

### Durum
```fish
systemctl --user status rakip-main rakip-dashboard rakip-backup-cd.timer
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Log takibi
```fish
journalctl --user -u rakip-main -f          # main.py canlı
journalctl --user -u rakip-dashboard -f     # streamlit canlı
tail -f ~/rakip-analizi/logs/main.service.log
tail -f ~/rakip-analizi/logs/$(date +%Y-%m-%d).log   # main.py'nin uygulama log'u
```

### Restart
```fish
systemctl --user restart rakip-main         # .env değişikliği sonrası şart
systemctl --user restart rakip-dashboard    # dashboard.py değişikliği sonrası
docker compose -f /home/khan/docker/changedetection/docker-compose.yml restart
```

### Manuel yedek al
```fish
systemctl --user start rakip-backup-cd.service
ls -la ~/rakip-analizi/backups/cd/
```

### Yedekten geri yükleme (CD datastore)
```fish
docker compose -f /home/khan/docker/changedetection/docker-compose.yml stop changedetection
sudo rm -rf /home/khan/docker/changedetection/data
sudo mkdir -p /home/khan/docker/changedetection/data
sudo tar --zstd -xf ~/rakip-analizi/backups/cd/cd-datastore-YYYYMMDD-HHMMSS.tar.zst \
    -C /home/khan/docker/changedetection/data
docker compose -f /home/khan/docker/changedetection/docker-compose.yml start changedetection
```

## `.env` bayrakları

| Anahtar | Anlam | Şu anki değer |
|---|---|---|
| `CD_BASE_URL` | changedetection URL | `http://localhost:5000` |
| `CD_API_KEY` | CD API key | `9f27a45aed03c826410dc5be255db03b` |
| `LLM_API_URL` | LLM endpoint (llm.gen.tr) | `https://llm.gen.tr/v1/chat/completions` |
| `LLM_API_KEY` | LLM auth token | `sk-llm-…5zTW` |
| `LLM_MODEL` | Model adı | `gemini-2.5-flash` |
| `DISABLE_LLM` | 1 → LLM parse tamamen kapalı | **1** |
| `DISABLE_DB_PUSH` | 1 → GitHub push atlanır (PAT yoksa) | **1** |

## LLM'i tekrar açma
1. llm.gen.tr panelinde `gemini-2.5-flash` modeline erişim var mı doğrula (şu an 400 "Unknown model" dönüyor).
2. Sorun düzelince: `.env` → `DISABLE_LLM=0`
3. `systemctl --user restart rakip-main`
4. `tail -f ~/rakip-analizi/logs/main.service.log` ile LLM çağrılarını izle.

## GitHub push'u tekrar açma (isteğe bağlı)
1. GitHub'da bir **PAT** oluştur (`repo` scope yeterli).
2. `~/.git-credentials` dosyasına yaz:
   ```
   https://TurkmenKhan:<PAT>@github.com
   ```
   `chmod 600 ~/.git-credentials`
3. `.env` → `DISABLE_DB_PUSH=0`
4. `systemctl --user restart rakip-main`
5. Log'da "push_db: DB başarıyla GitHub'a push edildi." görülmeli.

## Reboot'ta otomatik başlaması için (bir kereye mahsus)
Kullanıcı servisleri normalde login'de başlar. Reboot'ta login yapılmasa bile başlaması için **linger**:

```fish
sudo loginctl enable-linger khan
```

Şu an `Linger=no` — reboot sonrası ilk login'e kadar servisler duracak. Yukarıdaki komutla bunu kalıcı yaparız.

## Sorun giderme kılavuzu

### Dashboard 8501'de yanıt vermiyor
```fish
systemctl --user status rakip-dashboard --no-pager -n 30
tail -50 ~/rakip-analizi/logs/dashboard.log
```

### CD Telegram bildirim atmıyor
1. CD UI → Settings → Notifications, tgram URL orada mı?
2. Log: `docker logs changedetection --tail 100 | grep -i notif`
3. Bir watch'a manuel "recheck" yaptır, bildirim gelir mi?

### main.py'de "0 değişim" hep aynı
Normal — CD tarafında watch değişmemişse main.py yeni bir şey yapmaz. Test için CD UI'de bir watch'ı "Force recheck" edip 30dk beklet.

### `python-dotenv could not parse …`
`.env` dosyasında bozuk satır. Tırnak/`=` işaretine dikkat, yorumları ayrı satıra al.

### Servis "activating (auto-restart)" döngüsünde
- ExecStart path'i yanlış olabilir (Türkçe karakter/boşluk).
- Tüm systemd unit'leri `/home/khan/rakip-analizi/...` symlink path'i kullanır — sakın Türkçe orijinal path'e dönme.

## Rutin sağlık kontrolü (haftada bir)
```fish
# Servisler
systemctl --user status rakip-main rakip-dashboard --no-pager

# CD watch sayısı
curl -s http://localhost:5000/api/v1/watch -H "x-api-key: 9f27a45aed03c826410dc5be255db03b" | jq 'length'

# DB büyüklüğü
du -h ~/rakip-analizi/data/rakip_analizi.db

# Yedek sayısı
ls ~/rakip-analizi/backups/cd/ | wc -l

# Disk
df -h ~
```
