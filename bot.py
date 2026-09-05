"""
KeyAuth Discord Bot — advanced key management (v2)

Commands:
  /create [amount] [days] [plan] [note]  Generate key(s)      (admin only)
  /check <key>                           Key details + status
  /delete <key>                          Delete a key         (admin only)
  /reset <key>                           Reset HWID           (admin only)
  /ban <key> [reason]                    Ban a key            (admin only)
  /unban <key>                           Unban a key          (admin only)
  /list [page]                           Paginated key list
  /stats                                 Database statistics

Setup:
  1. pip install -r requirements-bot.txt
  2. Fill in the CONFIG section below (or use env vars)
  3. python bot.py
"""

import os
import secrets
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.server_api import ServerApi

# ------------------------------------------------------------- CONFIG ------
MONGO_URL = os.environ.get("MONGO_URL", "URL_TO_YOUR_MONGODB_DATABASE")
DB_NAME = os.environ.get("DB_NAME", "keyauth_db")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "keys")
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN")
ADMIN_ROLE = os.environ.get("ADMIN_ROLE", "Admin")  # role name allowed to manage keys

client = MongoClient(MONGO_URL, server_api=ServerApi("1"), serverSelectionTimeoutMS=8000)
client.server_info()  # fail fast with a clear error
db = client[DB_NAME]
keys = db[COLLECTION_NAME]
keys.create_index([("key", ASCENDING)], unique=True)

# ------------------------------------------------------------- BOT ----------
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

PAGE_SIZE = 10
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars


# ------------------------------------------------------------- helpers ------
def is_admin(interaction: discord.Interaction) -> bool:
    if interaction.user.guild_permissions.administrator:
        return True
    role = discord.utils.get(interaction.user.roles, name=ADMIN_ROLE)
    return role is not None


def gen_key(prefix: str = "KEY", length: int = 16) -> str:
    body = "".join(secrets.choice(ALPHABET) for _ in range(length))
    return f"{prefix}-{body}"


def _now():
    return datetime.now(timezone.utc)


def key_embed(key_doc: dict, color: discord.Color = None) -> discord.Embed:
    key = key_doc.get("key", "?")
    banned = bool(key_doc.get("banned"))
    hwid = key_doc.get("hwid", "")
    expires = key_doc.get("expires")
    expired = False
    if expires:
        try:
            expired = datetime.fromisoformat(expires) < _now()
        except Exception:
            pass

    if banned:
        color = color or discord.Color.red()
        status = "🚫 Banned" + (f" — {key_doc.get('ban_reason', '')}" if key_doc.get("ban_reason") else "")
    elif expired:
        color = color or discord.Color.gold()
        status = "⌛ Expired"
    elif hwid:
        color = color or discord.Color.green()
        status = "✅ Active"
    else:
        color = color or discord.Color.blurple()
        status = "🆕 Unused"

    e = discord.Embed(title=f"🔑 {key}", color=color)
    e.add_field(name="Status", value=status, inline=True)
    e.add_field(name="Plan", value=key_doc.get("plan", "default"), inline=True)
    e.add_field(name="Uses", value=str(key_doc.get("uses", 0)), inline=True)
    e.add_field(name="HWID", value=(hwid[:16] + "…") if hwid else "—", inline=True)
    e.add_field(name="Expires", value=expires[:10] if expires else "Never", inline=True)
    e.add_field(name="Created", value=str(key_doc.get("created_at", "—"))[:10], inline=True)
    if key_doc.get("note"):
        e.add_field(name="Note", value=key_doc["note"][:200], inline=False)
    return e


def admin_denied(interaction: discord.Interaction) -> discord.Embed:
    return discord.Embed(
        title="⛔ Access denied",
        description="You need the **Administrator** permission "
                    f"or the **{ADMIN_ROLE}** role to use this command.",
        color=discord.Color.red(),
    )


class KeyModal(discord.ui.Modal):
    """Quick single-key generation via dialog."""

    def __init__(self):
        super().__init__(title="Generate a new key")
        self.days = discord.ui.TextInput(label="Valid for (days, 0 = forever)", default="30", max_length=4)
        self.note = discord.TextInput(label="Note (optional)", required=False, max_length=200)
        self.add_item(self.days)
        self.add_item(self.note)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            days = max(0, int(str(self.days.value)))
        except ValueError:
            days = 30
        expires = _iso_expiry(days)
        key = gen_key()
        keys.insert_one({
            "key": key, "hwid": "", "banned": False, "note": str(self.note.value),
            "plan": "default", "expires": expires, "uses": 0,
            "created_at": _now(), "last_used": None,
        })
        await interaction.response.send_message(
            embed=discord.Embed(
                title="✅ Key generated",
                description=f"```{key}```Expires: {expires[:10] if expires else 'never'}",
                color=discord.Color.green(),
            ),
            ephemeral=True,
        )


def _iso_expiry(days: int):
    """ISO expiry string N days from now, or None for 'never'."""
    return (_now() + timedelta(days=days)).isoformat() if days > 0 else None


# ------------------------------------------------------------- events -------
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ Logged in as {bot.user} — slash commands synced.")
    except Exception as e:
        print(f"⚠️ Slash command sync failed: {e}")


# ------------------------------------------------------------- commands -----
@bot.tree.command(name="create", description="Generate one or more license keys")
@app_commands.describe(amount="How many keys (1-25)", days="Validity in days (0 = forever)",
                       plan="Plan name", note="Optional note")
async def create(interaction: discord.Interaction, amount: int = 1, days: int = 30,
                 plan: str = "default", note: str = ""):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    amount = max(1, min(amount, 25))
    days = max(0, days)
    plan = plan.strip()[:32] or "default"
    expires = (_now() + timedelta(days=days)).isoformat() if days > 0 else None

    created = []
    for _ in range(amount):
        key = gen_key()
        keys.insert_one({
            "key": key, "hwid": "", "banned": False, "note": note[:200],
            "plan": plan, "expires": expires, "uses": 0,
            "created_at": _now(), "last_used": None,
        })
        created.append(key)

    e = discord.Embed(
        title=f"✅ Generated {len(created)} key(s)",
        description="\n".join(f"```{k}```" for k in created),
        color=discord.Color.green(),
    )
    e.add_field(name="Plan", value=plan, inline=True)
    e.add_field(name="Expires", value=(expires or "Never")[:10], inline=True)
    if note:
        e.add_field(name="Note", value=note[:200], inline=False)
    await interaction.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(name="check", description="Check a key's status and details")
@app_commands.describe(key="The license key to check")
async def check(interaction: discord.Interaction, key: str):
    doc = keys.find_one({"key": key})
    if not doc:
        return await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not found", description=f"Key `{key}` does not exist.",
                                color=discord.Color.red()),
            ephemeral=True)
    await interaction.response.send_message(embed=key_embed(doc), ephemeral=True)


@bot.tree.command(name="delete", description="Delete a key (admin only)")
@app_commands.describe(key="The key to delete")
async def delete(interaction: discord.Interaction, key: str):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    r = keys.delete_one({"key": key})
    if r.deleted_count:
        await interaction.response.send_message(
            embed=discord.Embed(title="🗑️ Deleted", description=f"`{key}` has been deleted.",
                                color=discord.Color.green()),
            ephemeral=True)
    else:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not found", description=f"`{key}` does not exist.",
                                color=discord.Color.red()),
            ephemeral=True)


@bot.tree.command(name="reset", description="Reset a key's HWID binding (admin only)")
@app_commands.describe(key="The key whose HWID should be reset")
async def reset(interaction: discord.Interaction, key: str):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    r = keys.update_one({"key": key}, {"$set": {"hwid": "", "uses": 0}})
    if r.matched_count:
        await interaction.response.send_message(
            embed=discord.Embed(title="↺ HWID reset",
                                description=f"`{key}` can now bind to a new machine.",
                                color=discord.Color.green()),
            ephemeral=True)
    else:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not found", description=f"`{key}` does not exist.",
                                color=discord.Color.red()),
            ephemeral=True)


@bot.tree.command(name="ban", description="Ban a key (admin only)")
@app_commands.describe(key="The key to ban", reason="Why is it banned?")
async def ban(interaction: discord.Interaction, key: str, reason: str = "no reason given"):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    r = keys.update_one({"key": key}, {"$set": {"banned": True, "ban_reason": reason[:200]}})
    if r.matched_count:
        await interaction.response.send_message(
            embed=discord.Embed(title="🚫 Banned", description=f"`{key}` — {reason}",
                                color=discord.Color.red()),
            ephemeral=True)
    else:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not found", description=f"`{key}` does not exist.",
                                color=discord.Color.red()),
            ephemeral=True)


@bot.tree.command(name="unban", description="Unban a key (admin only)")
@app_commands.describe(key="The key to unban")
async def unban(interaction: discord.Interaction, key: str):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    r = keys.update_one({"key": key}, {"$set": {"banned": False}, "$unset": {"ban_reason": ""}})
    if r.matched_count:
        await interaction.response.send_message(
            embed=discord.Embed(title="✅ Unbanned", description=f"`{key}` is active again.",
                                color=discord.Color.green()),
            ephemeral=True)
    else:
        await interaction.response.send_message(
            embed=discord.Embed(title="❌ Not found", description=f"`{key}` does not exist.",
                                color=discord.Color.red()),
            ephemeral=True)


class ListPaginator(discord.ui.View):
    def __init__(self, author_id: int, docs, total: int):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.docs = docs
        self.total = total
        self.page = 0
        self.max_page = max(0, (len(docs) - 1) // PAGE_SIZE)

    def embed(self) -> discord.Embed:
        chunk = self.docs[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        lines = []
        for d in chunk:
            status = "🚫" if d.get("banned") else ("✅" if d.get("hwid") else "🆕")
            lines.append(f"{status} `{d.get('key', '?')}` — {d.get('plan', 'default')}")
        e = discord.Embed(
            title=f"🗝️ Keys ({self.total} total)",
            description="\n".join(lines) or "No keys.",
            color=discord.Color.blurple(),
        )
        e.set_footer(text=f"Page {self.page + 1} / {self.max_page + 1}")
        return e

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, _):
        self.page = max(0, self.page - 1)
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, _):
        self.page = min(self.max_page, self.page + 1)
        await interaction.response.edit_message(embed=self.embed(), view=self)


@bot.tree.command(name="list", description="List keys with pagination")
@app_commands.describe(page="Starting page")
async def list_keys(interaction: discord.Interaction, page: int = 1):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    docs = list(keys.find().sort("created_at", DESCENDING).limit(500))
    view = ListPaginator(interaction.user.id, docs, len(docs))
    view.page = max(0, min(page - 1, view.max_page))
    await interaction.response.send_message(embed=view.embed(), view=view, ephemeral=True)


@bot.tree.command(name="stats", description="Database statistics")
async def stats(interaction: discord.Interaction):
    total = keys.count_documents({})
    used = keys.count_documents({"hwid": {"$ne": ""}})
    banned = keys.count_documents({"banned": True})
    e = discord.Embed(title="📊 KeyAuth Statistics", color=discord.Color.blurple())
    e.add_field(name="Total", value=str(total), inline=True)
    e.add_field(name="Active", value=str(used), inline=True)
    e.add_field(name="Unused", value=str(total - used - banned), inline=True)
    e.add_field(name="Banned", value=str(banned), inline=True)
    e.add_field(name="Available", value=str(total - banned), inline=True)
    await interaction.response.send_message(embed=e, ephemeral=True)


@bot.tree.command(name="modal", description="Open a dialog to generate a key (admin only)")
async def modal(interaction: discord.Interaction):
    if not is_admin(interaction):
        return await interaction.response.send_message(embed=admin_denied(interaction), ephemeral=True)
    await interaction.response.send_modal(KeyModal())


if __name__ == "__main__":
    if DISCORD_TOKEN == "YOUR_DISCORD_BOT_TOKEN":
        raise SystemExit("Set DISCORD_TOKEN (env var or in bot.py CONFIG section).")
    bot.run(DISCORD_TOKEN)
