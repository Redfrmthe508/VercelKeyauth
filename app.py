import requests 
import json 
import hwid
key = input("Enter your key: ")
user_hwid = hwid.get_hwid() 

def check_key(key, hwid):
    url = f"http://VercelURL/{key}/{hwid}"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "valid":
            return True 
        else:
            return False
    return False