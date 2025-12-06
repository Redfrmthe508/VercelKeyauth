from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.server_api import ServerApi

MONGO_URL = "URL_TO_YOUR_MONGODB_DATABASE"

try:
    client = MongoClient(MONGO_URL, server_api=ServerApi("1"), serverSelectionTimeoutMS=5000)
    client.server_info()  
except ServerSelectionTimeoutError:
    raise RuntimeError("Failed to connect to MongoDB. Check your connection string!")

db = client["NAME_OF_YOUR_DATABASE"]
keys_collection = db["NAME_OF_YOUR_COLLECTION"]

app = FastAPI(
    title="KeyAuth API",
    description="API for checking and binding keys to HWIDs",
    version="1.0.0",
)

def key_auth(key, hwid):
    key_data = keys_collection.find_one({"key": key})

    if not key_data:
        return False
    stored_hwid = key_data.get("hwid", "")

    if stored_hwid == "":
        keys_collection.update_one({"key": key}, {"$set": {"hwid": hwid}})
        return True

    if stored_hwid == hwid:
        return True

    return False


@app.get("/check_key/{key}/{hwid}")
def check_key(key, hwid):
    idk = key_auth(key, hwid) 
    if idk is True:
        return {"status": "valid"}
    else:
        return {"status": "invalid"}