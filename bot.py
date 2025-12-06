import discord 
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from discord.ext import commands
url = "URL_TO_YOUR_MONGODB_DATABASE"
client = MongoClient(url, server_api=ServerApi('1'))
db = client["NAME_OF_YOUR_DATABASE"]
keys = db["NAME_OF_YOUR_COLLECTION"]


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)


def gen_key(): 
    import random 
    import string 
    length = 8 
    characters = string.ascii_letters 
    for i in range(length):
        key = ''.join(random.choice(characters) for i in range(length)) 
        return "Keyauth-" + key
@bot.command()
async def create(ctx): 
    key = gen_key()
    keys.insert_one({
        "key" : key,
        "hwid" : "" 
    })
    await ctx.send(f"Generated Key: {key}") 
@bot.command()
async def check(ctx, key_input): 
    result = keys.find_one({"key": key_input})
    
    if result: 
        await ctx.send(f"Key `{key_input}` is valid. with hwid {result['hwid']}")
    else: 
        await ctx.send(f"Key `{key_input}` is invalid.")
@bot.command()
async def delete(ctx, key_input): 
    result = keys.find_one({"key": key_input, "hwid": ""})
    if result: 
        keys.delete_one({"key": key_input, "hwid": ""})
        await ctx.send(f"Key `{key_input}` has been deleted.")
    else: 
        await ctx.send(f"Key `{key_input}` not found or already used.") 
@bot.command()
async def list_keys(ctx): 
    result = keys.find({"key": {"$exists": True}})
    lines = []
    for document in result:
        lines.append(f"Key: {document.get('key', '')}, HWID: {document.get('hwid', '')}")
    if lines:
        await ctx.send("Keys in Database:\n" + "\n".join(lines))
    else:
        await ctx.send("No keys found.")


bot.run("YOUR_DISCORD_BOT_TOKEN") 
