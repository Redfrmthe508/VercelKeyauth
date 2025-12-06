# 🔐 KeyAuth System

A simple yet powerful key authentication system with HWID (Hardware ID) binding. FastAPI REST API designed for Vercel deployment + Discord Bot for easy key management.

## 📋 Overview

KeyAuth System is a lightweight solution for managing license keys with hardware ID binding. The API runs serverless on Vercel for zero-cost hosting, while the Discord bot (optional) runs on your local machine or server for convenient key management.

## ✨ Features

- **🔑 Key Generation**: Generate unique license keys via Discord bot
- **🖥️ HWID Binding**: Automatically bind keys to hardware IDs on first use
- **🤖 Discord Bot**: Optional bot for easy key management
- **🌐 REST API**: Simple HTTP API for key verification
- **☁️ Vercel Deployment**: Free serverless hosting for the API
- **💾 MongoDB Storage**: Reliable cloud database (MongoDB Atlas)
- **⚡ Fast**: Built with FastAPI for high performance

## 🗂️ Project Structure

```
keyauth-system/
├── server.py            # Main FastAPI server (deploy to Vercel)
├── app.py               # Example client implementation
├── bot.py               # Discord bot (run locally/on server - OPTIONAL)
├── vercel.json          # Vercel configuration
├── requirements.txt     # Python dependencies for Vercel
└── README.md            # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.7+
- MongoDB Atlas account (free tier)
- Vercel account (free tier)
- Discord Bot Token (only if using bot features - OPTIONAL)

### Part 1: Setting Up MongoDB Atlas

1. Create a free account at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Create a new cluster (free M0 tier)
3. Create a database user (Database Access)
4. Whitelist all IPs: `0.0.0.0/0` (Network Access) - required for Vercel
5. Get your connection string (looks like `mongodb+srv://username:password@cluster.mongodb.net/`)
6. Create a database and collection for your keys

### Part 2: Deploying API to Vercel

#### Method 1: Deploy via Vercel CLI (Recommended)

1. Install Vercel CLI:
```bash
npm i -g vercel
```

2. Update `server.py` with your MongoDB details:
```python
MONGO_URL = "your-mongodb-connection-string"
DB_NAME = "your-database-name"
COLLECTION_NAME = "your-collection-name"
```

3. Create `vercel.json`:
```json
{
  "builds": [
    {
      "src": "server.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "server.py"
    }
  ]
}
```

4. Create `requirements.txt`:
```txt
fastapi
pymongo
```

5. Deploy:
```bash
vercel login
vercel
```

6. Your API is now live at: `https://your-project.vercel.app`

#### Method 2: Deploy via GitHub

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com) and import your repository
3. Vercel auto-detects Python and deploys
4. Add environment variables in Vercel dashboard (recommended over hardcoding)

### Part 3: Using the Discord Bot (OPTIONAL)

**Note**: The Discord bot is completely optional. You can manage keys directly in MongoDB if you prefer.

The Discord bot **CANNOT** run on Vercel (it needs a persistent connection). You must run it on:
- Your local computer
- A VPS (DigitalOcean, AWS, etc.)
- Heroku / Railway / PythonAnywhere
- Any server with Python

**To run the bot:**

1. Update `bot.py` with your MongoDB details:
```python
url = "your-mongodb-connection-string"
db = client["your-database-name"]
keys = db["your-collection-name"]
```

2. Add your Discord bot token at the bottom:
```python
bot.run("YOUR_DISCORD_BOT_TOKEN")
```

3. Install dependencies:
```bash
pip install discord.py pymongo
```

4. Run the bot:
```bash
python bot.py
```

**Keep the bot running** - if you close it, the bot goes offline.

## 📚 API Documentation

### Base URL
After deploying to Vercel: `https://your-project.vercel.app`

### Endpoint: Check Key

**GET** `/check_key/{key}/{hwid}`

Verify a license key and bind it to a hardware ID.

**Parameters:**
- `key`: The license key to verify (e.g., `Keyauth-AbCdEfGh`)
- `hwid`: The hardware ID of the user's machine

**Response:**
```json
{
  "status": "valid"
}
```
or
```json
{
  "status": "invalid"
}
```

**Example Request:**
```bash
curl https://your-project.vercel.app/check_key/Keyauth-AbCdEfGh/user-hwid-123
```

**How it works:**
1. First time a key is used with an HWID: Binds the key to that HWID and returns `valid`
2. Same key used with same HWID: Returns `valid`
3. Same key used with different HWID: Returns `invalid` (key is locked to first HWID)
4. Invalid key: Returns `invalid`

## 🤖 Discord Bot Commands (OPTIONAL)

If you choose to run the Discord bot, these commands are available:

| Command | Description | Usage |
|---------|-------------|-------|
| `!create` | Generate a new license key | `!create` |
| `!check <key>` | Check if a key exists and view its HWID | `!check Keyauth-AbCdEfGh` |
| `!delete <key>` | Delete an unused key (only works if HWID is empty) | `!delete Keyauth-AbCdEfGh` |
| `!list_keys` | List all keys in the database | `!list_keys` |

## 💻 Client Integration (app.py)

The `app.py` file shows how to integrate the key check into your application:

```python
import requests
import hwid

key = input("Enter your key: ")
user_hwid = hwid.get_hwid()

def check_key(key, hwid):
    # Replace with your Vercel URL
    url = f"https://your-project.vercel.app/check_key/{key}/{hwid}"
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data.get("status") == "valid"
    return False

if check_key(key, user_hwid):
    print("✓ Key is valid! Access granted.")
    # Your application code here
else:
    print("✗ Invalid key. Access denied.")
    exit()
```

**Update the URL** in `app.py` to your Vercel deployment URL.

## 🔧 Configuration Files

### `vercel.json`
```json
{
  "builds": [
    {
      "src": "server.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "server.py"
    }
  ]
}
```

### `requirements.txt` (for Vercel)
```txt
fastapi
pymongo
```

### `.vercelignore` (optional)
```
bot.py
app.py
__pycache__/
*.pyc
.env
venv/
```

## 🔒 Security Best Practices

### For Production Use:

1. **Use Environment Variables** (instead of hardcoding):
   - In Vercel dashboard: Settings → Environment Variables
   - Add: `MONGO_URL`, `DB_NAME`, `COLLECTION_NAME`
   - Update `server.py` to use `os.getenv()`

2. **MongoDB Atlas Security**:
   - Whitelist `0.0.0.0/0` (required for Vercel serverless)
   - Use strong database password
   - Enable MongoDB authentication

3. **API Security** (optional enhancements):
   - Add rate limiting
   - Implement API key authentication
   - Add request logging

4. **Key Generation**:
   - Current: 8 characters (increase for more security)
   - Consider adding more entropy or special characters

## 📊 Database Schema

Keys are stored in MongoDB with this structure:

**Unused key:**
```json
{
  "key": "Keyauth-AbCdEfGh",
  "hwid": ""
}
```

**Used key (after first activation):**
```json
{
  "key": "Keyauth-AbCdEfGh",
  "hwid": "ABC123-XYZ789-USER-HWID"
}
```

## 🚨 Troubleshooting

### Vercel API Issues:

**"Failed to connect to MongoDB"**
- Check MongoDB Atlas whitelist includes `0.0.0.0/0`
- Verify connection string is correct
- Ensure database user has read/write permissions

**"API returns 404"**
- Check `vercel.json` routes match your endpoint
- Verify `server.py` is the correct filename
- Check Vercel deployment logs

**Cold starts (slow first request)**
- Normal for serverless - first request wakes up the function
- Subsequent requests are fast

### Discord Bot Issues:

**Bot won't start**
- Verify Discord token is correct
- Check MongoDB connection string
- Ensure all dependencies installed: `pip install discord.py pymongo`

**Bot goes offline**
- Bot needs to run continuously
- Consider using a VPS or always-on server
- Free options: Railway, PythonAnywhere, Heroku

**Commands not working**
- Ensure bot has proper Discord permissions
- Check bot is in your Discord server
- Verify command prefix is `!`

## 💡 Use Cases

- Desktop application licensing
- Game authentication systems
- Discord server premium access
- Software beta access control
- SaaS product key management
- Digital product licensing

## 🔮 Future Improvements

- [ ] Key expiration dates
- [ ] Usage limits per key
- [ ] Multiple HWID support per key
- [ ] Web dashboard for key management
- [ ] Analytics and usage tracking
- [ ] Webhook notifications
- [ ] API rate limiting
- [ ] Key groups/tiers
- [ ] One of these will be done every 10 ⭐ this project gets

## 📝 Important Notes

- **Discord bot is OPTIONAL** - you can manage keys manually in MongoDB
- **Discord bot CANNOT run on Vercel** - needs separate hosting
- **API runs on Vercel** - free serverless hosting
- **MongoDB Atlas free tier** is sufficient for most use cases
- **First API request may be slow** - cold start (serverless limitation)

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## ⭐ Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Discord.py](https://discordpy.readthedocs.io/) - Discord bot library  
- [PyMongo](https://pymongo.readthedocs.io/) - MongoDB driver
- [Vercel](https://vercel.com/) - Serverless hosting platform
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) - Cloud database

