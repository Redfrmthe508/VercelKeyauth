"""
KeyAuth Client — advanced example client for the KeyAuth API (v2)

Features:
  • Robust API calls with retry + timeout
  • Clear status reporting (valid / banned / expired / mismatch)
  • HWID via the bundled hwid.py module
  • Usable as a library (KeyAuthClient) or standalone script

Setup:
  1. Deploy server.py to Vercel and copy your URL
  2. Set API_URL below (or set the KEYAUTH_API_URL env var)
  3. Run:  python app.py
"""

import os
import sys
import time
import requests

import hwid

API_URL = os.environ.get("KEYAUTH_API_URL", "https://your-project-name.vercel.app")


class KeyAuthError(Exception):
    pass


class KeyAuthClient:
    def __init__(self, api_url: str, timeout: int = 10, retries: int = 3):
        self.api_url = api_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries

    def _get(self, path: str) -> dict:
        url = self.api_url + path
        last_err = None
        for attempt in range(1, self.retries + 1):
            try:
                r = requests.get(url, timeout=self.timeout)
                if r.status_code == 200:
                    return r.json()
                if r.status_code == 404:
                    raise KeyAuthError(f"Endpoint not found: {path} (wrong API_URL?)")
                last_err = f"HTTP {r.status_code}"
            except (requests.Timeout, requests.ConnectionError) as e:
                last_err = str(e)
            time.sleep(1.5 * attempt)  # linear backoff
        raise KeyAuthError(f"API unreachable after {self.retries} attempts: {last_err}")

    def check(self, key: str, user_hwid: str) -> dict:
        """Return {'status': ..., 'reason': ...} from the API."""
        from urllib.parse import quote
        return self._get(f"/check_key/{quote(key)}/{quote(user_hwid)}")

    def is_valid(self, key: str, user_hwid: str) -> bool:
        return self.check(key, user_hwid).get("status") == "valid"


def _print_banner():
    print("=" * 46)
    print("        🔐  KeyAuth — License Check")
    print("=" * 46)


def main():
    _print_banner()
    if "your-project-name" in API_URL:
        print("⚠️  Set API_URL in app.py (or KEYAUTH_API_URL env var) first!")
        sys.exit(1)

    key = input("Enter your key: ").strip()
    if not key:
        print("✗ No key entered.")
        sys.exit(1)

    user_hwid = hwid.get_hwid()
    print(f"HWID: {user_hwid[:24]}…")

    client = KeyAuthClient(API_URL)
    try:
        result = client.check(key, user_hwid)
    except KeyAuthError as e:
        print(f"✗ Connection error: {e}")
        time.sleep(2)
        sys.exit(2)

    if result.get("status") == "valid":
        print("✓ Key is valid! Access granted.")
        # ------------------------------------------------------------
        # Your application code starts here
        # ------------------------------------------------------------
    else:
        reason = result.get("reason", "unknown")
        reasons = {
            "key_not_found": "Key does not exist.",
            "key_banned": f"Key is banned — {result.get('detail', 'no reason given')}",
            "key_expired": "Key has expired. Contact support.",
            "hwid_mismatch": "Key is bound to another machine.",
        }
        print(f"✗ Invalid key: {reasons.get(reason, reason)}")
        time.sleep(2)
        sys.exit(1)


if __name__ == "__main__":
    main()
