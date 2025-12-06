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

## 🚀 Quick Start Guide

### Step 1: Fork/Clone This Repository

1. Click the **Fork** button on GitHub (top right)
2. This creates your own copy of the project

### Step 2: Set Up MongoDB Atlas (Free)

1. Go to [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas) and create a free account
2. Create a new cluster (select **FREE M0** tier)
3. Click **"Database Access"** → Create a database user:
   - Username: `keyauth_user` (or your choice)
   - Password: Generate a secure password (save this!)
4. Click **"Network Access"** → Add IP Address:
   - Click **"Allow Access from Anywhere"**
   - This adds `0.0.0.0/0` (required for Vercel)
5. Click **"Database"** → Connect → "Connect your application"
   - Copy your connection string (looks like: `mongodb+srv://keyauth_user:PASSWORD@cluster0.xxxxx.mongodb.net/`)
6. In MongoDB Atlas, create your database:
   - Click **"Browse Collections"** → "Add My Own Data"
   - Database name: `keyauth_db` (or your choice)
   - Collection name: `keys` (or your choice)

### Step 3: Update Configuration in Your Code

**In `server.py`, replace these lines:**

```python
MONGO_URL = "URL_TO_YOUR_MONGODB_DATABASE"
db = client["NAME_OF_YOUR_DATABASE"]
keys_collection = db["NAME_OF_YOUR_COLLECTION"]
```

**With your actual values:**

```python
MONGO_URL = "mongodb+srv://keyauth_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/"
db = client["keyauth_db"]  # Your database name
keys_collection = db["keys"]  # Your collection name
```

**In `app.py`, replace this line:**

```python
url = f"http://VercelURL/{key}/{hwid}"
```

**With your Vercel URL (you'll get this in Step 4):**

```python
url = f"https://your-project-name.vercel.app/check_key/{key}/{hwid}"
```

### Step 4: Deploy to Vercel (via GitHub)

1. Go to [vercel.com](https://vercel.com) and sign up (use GitHub login)
2. Click **"Add New..."** → **"Project"**
3. Click **"Import"** next to your forked repository
4. Vercel will auto-detect the settings:
   - Framework Preset: **Other**
   - Build Command: (leave empty)
   - Output Directory: (leave empty)
5. Click **"Deploy"**
6. Wait 1-2 minutes for deployment
7. You'll get a URL like: `https://your-project-name.vercel.app`
8. **Copy this URL** and update it in `app.py` (see Step 3)

### Step 5: Test Your API

Visit in your browser:
```
https://your-project-name.vercel.app/check_key/test-key/test-hwid
```

You should see:
```json
{"status": "invalid"}
```

This is normal - the key doesn't exist yet!

### Step 6: (Optional) Set Up Discord Bot

**The Discord bot is optional!** You can manually add keys to MongoDB if you prefer.

**To use the Discord bot:**

1. **Update `bot.py`** with your MongoDB info:
```python
url = "mongodb+srv://keyauth_user:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/"
db = client["keyauth_db"]  # Your database name
keys = db["keys"]  # Your collection name
```

2. **Create a Discord Bot**:
   - Go to [discord.com/developers/applications](https://discord.com/developers/applications)
   - Click "New Application" → name it
   - Go to "Bot" tab → Click "Add Bot"
   - Click "Reset Token" → Copy the token (save it!)
   - Enable "Message Content Intent" under "Privileged Gateway Intents"

3. **Invite bot to your server**:
   - Go to "OAuth2" → "URL Generator"
   - Check: `bot` and `applications.commands`
   - Bot Permissions: Check `Administrator` (or specific permissions)
   - Copy the generated URL and open it in browser
   - Select your Discord server

4. **Update bot token in `bot.py`**:
```python
bot.run("YOUR_DISCORD_BOT_TOKEN")
```

5. **Run the bot** (on your computer or server):
```bash
pip install discord.py pymongo
python bot.py
```

**Note**: The bot must stay running. If you close it, it goes offline.

## 📚 API Documentation

### Base URL
Your Vercel deployment: `https://your-project-name.vercel.app`

### Endpoint: Check Key

**GET** `/check_key/{key}/{hwid}`

**Parameters:**
- `key`: License key (e.g., `Keyauth-AbCdEfGh`)
- `hwid`: Hardware ID of user's machine

**Response:**
```json
{"status": "valid"}
```
or
```json
{"status": "invalid"}
```

**How it works:**
1. **First use**: Key binds to HWID → returns `valid`
2. **Same HWID**: Returns `valid`
3. **Different HWID**: Returns `invalid` (locked to first HWID)
4. **Invalid key**: Returns `invalid`

**Example:**
```bash
curl https://your-project-name.vercel.app/check_key/Keyauth-AbCdEfGh/user-hwid-123
```

## 🤖 Discord Bot Commands (Optional)

| Command | Description | Usage |
|---------|-------------|-------|
| `!create` | Generate a new license key | `!create` |
| `!check <key>` | Check if a key exists and view its HWID | `!check Keyauth-AbCdEfGh` |
| `!delete <key>` | Delete an unused key (HWID must be empty) | `!delete Keyauth-AbCdEfGh` |
| `!list_keys` | List all keys in database | `!list_keys` |

## 💻 Using the Client (app.py)

After deploying, update `app.py` with your Vercel URL:

```python
import requests
import hwid

key = input("Enter your key: ")
user_hwid = hwid.get_hwid()

def check_key(key, hwid):
    # 👇 REPLACE THIS WITH YOUR VERCEL URL
    url = f"https://your-project-name.vercel.app/check_key/{key}/{hwid}"
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

**To use in your application:**
```bash
pip install requests
python app.py
```

## 🔧 Required Files (Already Included)

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

### `requirements.txt`
```txt
fastapi
pymongo
```

These files are already in the repository - **no changes needed!**

## 📊 Database Schema

**New key (unused):**
```json
{
  "key": "Keyauth-AbCdEfGh",
  "hwid": ""
}
```

**After first use:**
```json
{
  "key": "Keyauth-AbCdEfGh",
  "hwid": "ABC123-XYZ789-USER-HWID"
}
```

## 🚨 Troubleshooting

### MongoDB Connection Failed

**Error in Vercel logs**: `Failed to connect to MongoDB`

**Solutions:**
- ✅ Check MongoDB Atlas Network Access allows `0.0.0.0/0`
- ✅ Verify connection string is correct (no typos)
- ✅ Ensure database user has read/write permissions
- ✅ Check your MongoDB password doesn't contain special characters that need URL encoding

### API Returns 404

**Solutions:**
- ✅ Verify `vercel.json` exists in repository root
- ✅ Check `server.py` filename is correct
- ✅ Re-deploy from Vercel dashboard

### Discord Bot Won't Start

**Solutions:**
- ✅ Install dependencies: `pip install discord.py pymongo`
- ✅ Check Discord token is correct
- ✅ Verify MongoDB connection string in `bot.py`
- ✅ Enable "Message Content Intent" in Discord Developer Portal

### API is Slow on First Request

This is **normal** for serverless (called "cold start"). Vercel puts your function to sleep after inactivity. First request wakes it up (~2-5 seconds), then it's fast.

## 🔒 Security Tips

### For Production:

1. **Don't commit secrets to GitHub:**
   - Use Vercel Environment Variables
   - Go to Vercel Dashboard → Settings → Environment Variables
   - Add: `MONGO_URL`, `DB_NAME`, `COLLECTION_NAME`

2. **Stronger keys:**
   - Current: 8 characters
   - Increase in `bot.py` → `gen_key()` function
   - Change `length = 8` to `length = 16` or more

3. **MongoDB Security:**
   - Use strong database password
   - While `0.0.0.0/0` is required for Vercel, this is safe with authentication

4. **Rate Limiting:**
   - Consider adding rate limits to prevent API abuse

## 💡 Common Use Cases

- Desktop application licensing
- Game key authentication
- Discord premium role management
- Software beta access control
- SaaS product licensing
- Digital product keys

## ⚠️ Important Notes

- **Discord bot is OPTIONAL** - manage keys manually in MongoDB if you prefer
- **Discord bot CANNOT run on Vercel** - run it locally or on a server
- **API runs on Vercel** - free, serverless, automatic scaling
- **Update `app.py` URL** after deployment with your Vercel URL
- **First request may be slow** - serverless cold start (normal)

## 📝 Quick Checklist

Before using:
- [ ] MongoDB Atlas cluster created
- [ ] Database and collection created in MongoDB
- [ ] Network access set to `0.0.0.0/0`
- [ ] Updated `server.py` with MongoDB connection string
- [ ] Deployed to Vercel via GitHub
- [ ] Updated `app.py` with your Vercel URL
- [ ] (Optional) Discord bot configured and running

## 🤝 Contributing

Issues and pull requests are welcome!

## 📝 License

MIT License - free to use and modify

## ⭐ Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Discord.py](https://discordpy.readthedocs.io/) - Discord bot library  
- [PyMongo](https://pymongo.readthedocs.io/) - MongoDB driver
- [Vercel](https://vercel.com/) - Serverless hosting
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) - Cloud database

---

**⭐ Found this useful? Give it a star on GitHub!**

**Need help?** Open an issue on GitHub with your error message and I'll help troubleshoot.
