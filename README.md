# 🔐 KeyAuth System v2.0

A complete, advanced key authentication system with **HWID binding, key expiry, bans, plans, usage tracking** — plus a built-in **web admin dashboard** and a modern **Discord bot** with slash commands.

FastAPI REST API designed for Vercel (free serverless) · MongoDB Atlas storage · zero-cost hosting.

---

## ✨ What's new in v2.0

| Feature | v1 | v2 |
|---|---|---|
| Key generation | Discord bot only | **Web dashboard + bot + bulk generate (up to 100)** |
| HWID binding | ✅ | ✅ + **HWID reset** |
| Key expiry | ❌ | ✅ **per-key expiry (days)** |
| Bans | ❌ | ✅ **ban/unban with reason** |
| Plans | ❌ | ✅ trial / premium / lifetime / custom |
| Usage stats | ❌ | ✅ uses counter, last used, `/stats` |
| Admin UI | ❌ | ✅ **built-in dark dashboard at `/admin`** |
| Discord bot | `!commands` | ✅ **slash commands, embeds, pagination, modals** |
| Security | fixed 8-char keys | ✅ **crypto-random 16-char keys (no ambiguous chars), token auth, activity log** |
| Client | plain requests | ✅ **KeyAuthClient class, retries, timeout, clear error reasons** |

---

## 🗂️ Project Structure

```
keyauth-system/
├── server.py              # FastAPI + admin dashboard (deploy to Vercel)
├── app.py                 # Example client (KeyAuthClient class)
├── hwid.py                # Cross-platform HWID fingerprinting (no deps)
├── bot.py                 # Discord bot — slash commands (run locally/server)
├── vercel.json            # Vercel configuration
├── requirements.txt       # API dependencies (Vercel)
├── requirements-bot.txt   # Bot dependencies
└── README.md
```

---

## 🚀 Quick Start

### 1 · MongoDB Atlas (free)

1. Create a free **M0 cluster** at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. **Database Access** → create user (save the password)
3. **Network Access** → **Allow Access from Anywhere** (`0.0.0.0/0` — required for Vercel)
4. Copy the connection string:
   `mongodb+srv://user:PASSWORD@cluster0.xxxxx.mongodb.net/`

### 2 · Deploy the API to Vercel

1. Fork this repo → sign in at [vercel.com](https://vercel.com) with GitHub
2. **Add New… → Project** → Import your fork (settings are auto-detected)
3. **Before first deploy**, add Environment Variables (Settings → Environment Variables):

   | Name | Value |
   |---|---|
   | `MONGO_URL` | your connection string |
   | `DB_NAME` | `keyauth_db` |
   | `COLLECTION_NAME` | `keys` |
   | `ADMIN_TOKEN` | **a long random secret** — unlocks the dashboard |

4. Deploy → copy your URL, e.g. `https://your-app.vercel.app`

### 3 · Open the dashboard

Visit **`https://your-app.vercel.app/admin`**

- On first action you'll be asked for the **Admin Token** (stored in your browser's localStorage).
- From there you can: generate keys in bulk, set expiry/plan/note, reset HWIDs, ban/unban, delete, live-search, filter and watch the live counters.

### 4 · Run the client

```bash
pip install -r requirements.txt
```

Set your API URL in `app.py` (or `KEYAUTH_API_URL` env var), then:

```bash
python app.py
```

### 5 · (Optional) Discord bot

1. **Update config** — use env vars (`MONGO_URL`, `DB_NAME`, `COLLECTION_NAME`, `DISCORD_TOKEN`, `ADMIN_ROLE`) or edit the CONFIG section in `bot.py`
2. Create the bot at [discord.com/developers/applications](https://discord.com/developers/applications) → **New Application** → Bot → **Reset Token**
3. Enable **Message Content Intent** is *not* required (slash commands only) — but enable it if you also want prefix commands
4. OAuth2 → URL Generator → check `bot` + `applications.commands` → invite to your server
5. Run it:

```bash
pip install -r requirements-bot.txt
python bot.py
```

---

## 📚 API Reference

### `GET /check_key/{key}/{hwid}`

The single endpoint your app calls.

| Response | Meaning |
|---|---|
| `{"status":"valid","reason":"ok"}` | valid, HWID matches |
| `{"status":"valid","reason":"hwid_bound"}` | first use — key bound to this HWID |
| `{"status":"invalid","reason":"key_not_found"}` | key doesn't exist |
| `{"status":"invalid","reason":"hwid_mismatch"}` | key locked to another machine |
| `{"status":"invalid","reason":"key_banned"}` | banned (includes `detail`) |
| `{"status":"invalid","reason":"key_expired"}` | past its expiry date |

```bash
curl https://your-app.vercel.app/check_key/KEY-ABCD1234EFGH5678/user-hwid
```

### `GET /status` · `GET /stats`

Health check and key statistics (total / used / unused / banned).

### Admin endpoints (require `Authorization: Bearer <ADMIN_TOKEN>`)

| Endpoint | Body | Description |
|---|---|---|
| `GET /admin` | — | Dashboard UI |
| `GET /admin/data` | — | All keys + status |
| `POST /admin/generate` | `{amount, days, plan, note, prefix}` | Create up to 100 keys |
| `POST /admin/reset` | `{key}` | Reset HWID binding |
| `POST /admin/ban` | `{key, reason}` | Ban a key |
| `POST /admin/unban` | `{key}` | Unban |
| `POST /admin/delete` | `{key}` | Delete |
| `POST /admin/extend` | `{key, days}` | Extend expiry |

### Discord slash commands

| Command | Admin | Description |
|---|---|---|
| `/create [amount] [days] [plan] [note]` | ✅ | Generate up to 25 keys at once |
| `/check <key>` | — | Full key details in an embed |
| `/delete <key>` | ✅ | Delete a key |
| `/reset <key>` | ✅ | Reset HWID |
| `/ban <key> [reason]` / `/unban <key>` | ✅ | Ban management |
| `/list [page]` | ✅ | Paginated key browser (◀ ▶ buttons) |
| `/stats` | — | Database statistics |
| `/modal` | ✅ | Generate a key via dialog |

---

## 💻 Using the client library

```python
from app import KeyAuthClient
import hwid

client = KeyAuthClient("https://your-app.vercel.app")
result = client.check("KEY-ABCD1234EFGH5678", hwid.get_hwid())

if result["status"] == "valid":
    print("Access granted")        # your app here
else:
    print("Denied:", result["reason"])
```

Or simply run `python app.py` for an interactive check.

---

## 🗄️ Database schema

```json
{
  "key": "KEY-ABCD1234EFGH5678",
  "hwid": "A3F9…",
  "banned": false,
  "ban_reason": "",
  "note": "customer@email.com",
  "plan": "premium",
  "expires": "2026-10-05T18:00:00+00:00",
  "uses": 12,
  "created_at": "2026-09-05T18:00:00+00:00",
  "last_used": "2026-09-05T19:32:11+00:00"
}
```

---

## 🔒 Security tips

1. **Always set `ADMIN_TOKEN`** in Vercel env vars — the dashboard is public at `/admin`, the token is what protects your keys.
2. Keys are generated with `secrets` (CSPRNG) using an alphabet without ambiguous characters (`0/O`, `1/I`).
3. All admin actions are recorded in a `logs` collection with timestamps.
4. Consider Vercel's built-in DDoS protection; for heavy abuse add rate limiting at the edge.

---

## 🚨 Troubleshooting

| Problem | Fix |
|---|---|
| `Failed to connect to MongoDB` | Check `MONGO_URL`, user permissions, and that Network Access allows `0.0.0.0/0` |
| Dashboard asks for token repeatedly | Token wrong or missing — set `ADMIN_TOKEN` env var in Vercel |
| 404 on `/check_key/...` | `vercel.json` missing or wrong API URL in `app.py` |
| Slash commands don't appear | Wait up to a minute after `bot.py` starts (global sync) |
| First request slow | Normal serverless cold start (~2–5 s) |

---

## 📝 License

MIT — free to use and modify.

**⭐ Found this useful? Give it a star on GitHub!**
