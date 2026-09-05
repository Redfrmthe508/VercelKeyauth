"""
KeyAuth System — Advanced API + Admin Dashboard
FastAPI serverless API for Vercel with a built-in, self-contained admin UI.

Endpoints:
  GET  /check_key/{key}/{hwid}   -> {"status": "valid"|"invalid", ...}
  GET  /status                   -> service health
  GET  /stats                    -> key statistics (JSON)
  GET  /admin                    -> Admin Dashboard (HTML UI)
  GET  /admin/data               -> dashboard data (stats + lists)
  POST /admin/generate           -> create key(s)  {amount, days, note, prefix}
  POST /admin/reset              -> reset HWID     {key}
  POST /admin/ban                -> ban key        {key, reason}
  POST /admin/unban              -> unban key      {key}
  POST /admin/delete             -> delete key     {key}
  POST /admin/extend             -> extend expiry  {key, days}
"""

import os
import time
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ServerSelectionTimeoutError
from pymongo.server_api import ServerApi

# ------------------------------------------------------------------ config --
MONGO_URL = os.environ.get("MONGO_URL", "URL_TO_YOUR_MONGODB_DATABASE")
DB_NAME = os.environ.get("DB_NAME", "keyauth_db")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "keys")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "change-me")  # change in production!
BAN_ENFORCEMENT = os.environ.get("BAN_ENFORCEMENT", "1") == "1"

try:
    client = MongoClient(MONGO_URL, server_api=ServerApi("1"), serverSelectionTimeoutMS=5000)
    client.server_info()
except ServerSelectionTimeoutError:
    raise RuntimeError("Failed to connect to MongoDB. Check your connection string!")

db = client[DB_NAME]
keys_collection = db[COLLECTION_NAME]
logs_collection = db["logs"]

keys_collection.create_index([("key", ASCENDING)], unique=True)
keys_collection.create_index([("hwid", ASCENDING)])
keys_collection.create_index([("banned", ASCENDING)])
logs_collection.create_index([("ts", DESCENDING)])


# ----------------------------------------------------------------- helpers --
def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat() if dt else None


def _parse_iso(s):
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def _gen_key(prefix="KEY", length=16):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars
    body = "".join(secrets.choice(alphabet) for _ in range(length))
    return f"{prefix}-{body}"


def _log(action, key="", detail=""):
    try:
        logs_collection.insert_one(
            {"action": action, "key": key, "detail": detail, "ts": _now()}
        )
    except Exception:
        pass


def _key_doc(key):
    return keys_collection.find_one({"key": key})


def _public_view(doc):
    """Shape a key document for the dashboard."""
    if not doc:
        return None
    expires = doc.get("expires")
    expired = bool(expires and _parse_iso(expires) and _parse_iso(expires) < _now())
    return {
        "key": doc.get("key", ""),
        "hwid": doc.get("hwid", ""),
        "banned": bool(doc.get("banned", False)),
        "ban_reason": doc.get("ban_reason", ""),
        "note": doc.get("note", ""),
        "plan": doc.get("plan", "default"),
        "expires": expires,
        "expired": expired,
        "created_at": _iso(doc.get("created_at")),
        "last_used": _iso(doc.get("last_used")),
        "uses": int(doc.get("uses", 0)),
    }


def _is_expired(doc):
    expires = doc.get("expires")
    if not expires:
        return False
    dt = _parse_iso(expires) if isinstance(expires, str) else expires
    return bool(dt and dt < _now())


def _authorize(request: Request) -> bool:
    auth = request.headers.get("Authorization", "")
    token = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
    if not token:
        token = request.query_params.get("token", "")
    return secrets.compare_digest(token, ADMIN_TOKEN)


async def _json_body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


# ------------------------------------------------------------------- flask? --
# (no) — FastAPI app below.

app = FastAPI(
    title="KeyAuth API",
    description="Advanced key authentication with HWID binding, expiry, bans and an admin dashboard.",
    version="2.0.0",
)

_START_TIME = time.time()


# -------------------------------------------------------------------- auth --
@app.get("/check_key/{key}/{hwid}")
def check_key(key: str, hwid: str):
    doc = _key_doc(key)

    if not doc:
        return {"status": "invalid", "reason": "key_not_found"}

    if doc.get("banned"):
        return {"status": "invalid", "reason": "key_banned", "detail": doc.get("ban_reason", "")}

    if _is_expired(doc):
        return {"status": "invalid", "reason": "key_expired"}

    stored = doc.get("hwid", "")
    if stored == "":
        keys_collection.update_one(
            {"key": key},
            {"$set": {"hwid": hwid, "last_used": _now()}, "$inc": {"uses": 1}},
        )
        _log("bind", key, f"bound to {hwid[:12]}…")
        return {"status": "valid", "reason": "hwid_bound"}

    if stored == hwid:
        keys_collection.update_one({"key": key}, {"$set": {"last_used": _now()}, "$inc": {"uses": 1}})
        return {"status": "valid", "reason": "ok"}

    return {"status": "invalid", "reason": "hwid_mismatch"}


# ------------------------------------------------------------------ health --
@app.get("/status")
def status():
    return {
        "status": "online",
        "service": "KeyAuth API",
        "version": "2.0.0",
        "uptime_seconds": round(time.time() - _START_TIME, 1),
        "time": _iso(_now()),
    }


@app.get("/stats")
def stats():
    total = keys_collection.count_documents({})
    used = keys_collection.count_documents({"hwid": {"$ne": ""}})
    banned = keys_collection.count_documents({"banned": True})
    unused = total - used
    return {
        "total": total,
        "used": used,
        "unused": unused,
        "banned": banned,
        "available": total - banned,
    }


# ---------------------------------------------------------------- dashboard --
ADMIN_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>KeyAuth — Admin Dashboard</title>
<style>
  :root{
    --bg:#0b0f17; --panel:#111827; --panel2:#0e1523; --line:#1f2a3d;
    --text:#e5edf8; --muted:#8b9cb5; --accent:#38bdf8; --accent2:#818cf8;
    --good:#34d399; --warn:#fbbf24; --bad:#f87171; --radius:14px;
  }
  *{margin:0;padding:0;box-sizing:border-box}
  body{background:
      radial-gradient(1000px 500px at 80% -10%, rgba(56,189,248,.12), transparent 60%),
      radial-gradient(800px 400px at -10% 110%, rgba(129,140,248,.10), transparent 60%),
      var(--bg);
    color:var(--text);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;min-height:100vh}
  .wrap{max-width:1150px;margin:0 auto;padding:28px 20px 60px}
  header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:26px;flex-wrap:wrap}
  .brand{display:flex;align-items:center;gap:12px}
  .logo{width:44px;height:44px;border-radius:12px;display:grid;place-items:center;font-size:22px;
    background:linear-gradient(135deg,var(--accent),var(--accent2));box-shadow:0 8px 24px rgba(56,189,248,.35)}
  h1{font-size:22px;font-weight:700;letter-spacing:.3px}
  .sub{color:var(--muted);font-size:13px;margin-top:2px}
  .dot{display:inline-block;width:8px;height:8px;border-radius:50%;background:var(--good);
    margin-right:6px;box-shadow:0 0 8px var(--good);animation:pulse 2s infinite}
  @keyframes pulse{50%{opacity:.4}}
  .card{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);
    border-radius:var(--radius);padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.35)}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin-bottom:22px}
  .stat{padding:18px}
  .stat .label{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:1.2px}
  .stat .value{font-size:30px;font-weight:800;margin-top:6px}
  .stat .value.total{color:var(--accent)} .stat .value.good{color:var(--good)}
  .stat .value.warn{color:var(--warn)} .stat .value.bad{color:var(--bad)}
  .row{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
  input,select,button{font:inherit;border-radius:10px;outline:none}
  input,select{background:#0b1220;border:1px solid var(--line);color:var(--text);padding:10px 12px}
  input:focus,select:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(56,189,248,.15)}
  button{cursor:pointer;border:none;padding:10px 16px;font-weight:600;transition:.15s}
  .btn-primary{background:linear-gradient(135deg,var(--accent),var(--accent2));color:#06121f}
  .btn-primary:hover{filter:brightness(1.12);transform:translateY(-1px)}
  .btn-ghost{background:#16213a;color:var(--text);border:1px solid var(--line)}
  .btn-ghost:hover{background:#1d2b4d}
  .btn-danger{background:rgba(248,113,113,.12);color:var(--bad);border:1px solid rgba(248,113,113,.35)}
  .btn-danger:hover{background:rgba(248,113,113,.22)}
  .btn-warn{background:rgba(251,191,36,.12);color:var(--warn);border:1px solid rgba(251,191,36,.35)}
  .btn-warn:hover{background:rgba(251,191,36,.2)}
  .btn-good{background:rgba(52,211,153,.12);color:var(--good);border:1px solid rgba(52,211,153,.35)}
  .btn-good:hover{background:rgba(52,211,153,.2)}
  table{width:100%;border-collapse:collapse;font-size:14px}
  th{color:var(--muted);text-align:left;font-size:11px;text-transform:uppercase;letter-spacing:1px;
    padding:10px 12px;border-bottom:1px solid var(--line)}
  td{padding:11px 12px;border-bottom:1px solid rgba(31,42,61,.55);vertical-align:middle}
  tr:hover td{background:rgba(56,189,248,.04)}
  .badge{display:inline-block;padding:3px 10px;border-radius:999px;font-size:11px;font-weight:700}
  .b-good{background:rgba(52,211,153,.15);color:var(--good)}
  .b-bad{background:rgba(248,113,113,.15);color:var(--bad)}
  .b-warn{background:rgba(251,191,36,.15);color:var(--warn)}
  .b-muted{background:rgba(139,156,181,.15);color:var(--muted)}
  .mono{font-family:'Cascadia Code',Consolas,monospace;font-size:13px}
  .muted{color:var(--muted)}
  .actions{display:flex;gap:6px;flex-wrap:wrap}
  .actions button{padding:5px 10px;font-size:12px;border-radius:8px}
  #toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(80px);
    background:var(--panel);border:1px solid var(--line);padding:12px 20px;border-radius:12px;
    font-size:14px;opacity:0;transition:.3s;box-shadow:0 12px 30px rgba(0,0,0,.5);z-index:99}
  #toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
  #toast.ok{border-color:var(--good)} #toast.err{border-color:var(--bad)}
  .empty{padding:34px;text-align:center;color:var(--muted)}
  .fade{animation:fade .25s ease}
  @keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1}}
  footer{text-align:center;color:var(--muted);font-size:12px;margin-top:34px}
  .search{flex:1;min-width:220px}
  h2{font-size:16px;margin-bottom:14px;display:flex;align-items:center;gap:8px}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="brand">
      <div class="logo">🔐</div>
      <div>
        <h1>KeyAuth Admin</h1>
        <div class="sub"><span class="dot"></span>API online — license &amp; HWID control center</div>
      </div>
    </div>
    <button class="btn-ghost" onclick="loadAll()">⟳ Refresh</button>
  </header>

  <div class="grid">
    <div class="card stat"><div class="label">Total keys</div><div class="value total" id="s-total">—</div></div>
    <div class="card stat"><div class="label">Bound (used)</div><div class="value good" id="s-used">—</div></div>
    <div class="card stat"><div class="label">Unused</div><div class="value warn" id="s-unused">—</div></div>
    <div class="card stat"><div class="label">Banned</div><div class="value bad" id="s-banned">—</div></div>
  </div>

  <div class="card" style="margin-bottom:22px">
    <h2>⚡ Generate keys</h2>
    <div class="row">
      <input id="g-amount" type="number" min="1" max="100" value="1" title="Amount" style="width:90px"/>
      <input id="g-days" type="number" min="0" value="30" title="Days (0 = never)" style="width:90px"/>
      <input id="g-prefix" value="KEY" title="Prefix" style="width:110px"/>
      <input id="g-note" placeholder="Note (optional)" style="flex:1;min-width:180px"/>
      <select id="g-plan" title="Plan">
        <option value="default">default</option>
        <option value="trial">trial</option>
        <option value="premium">premium</option>
        <option value="lifetime">lifetime</option>
      </select>
      <button class="btn-primary" onclick="generate()">Generate</button>
    </div>
    <div id="g-result" class="mono muted fade"></div>
  </div>

  <div class="card">
    <h2>🗝️ Keys</h2>
    <div class="row">
      <input class="search" id="search" placeholder="Search key, HWID or note…" oninput="renderKeys()"/>
      <select id="filter" onchange="renderKeys()">
        <option value="all">All</option>
        <option value="unused">Unused</option>
        <option value="used">Used</option>
        <option value="banned">Banned</option>
        <option value="expired">Expired</option>
      </select>
    </div>
    <div style="overflow-x:auto">
      <table>
        <thead><tr>
          <th>Key</th><th>Status</th><th>HWID</th><th>Expires</th><th>Uses</th><th>Note</th><th>Actions</th>
        </tr></thead>
        <tbody id="tbody"></tbody>
      </table>
    </div>
    <div id="empty" class="empty" style="display:none">No keys yet — generate your first one above ✨</div>
  </div>

  <footer>KeyAuth v2.0 — advanced license &amp; HWID system</footer>
</div>
<div id="toast"></div>

<script>
let KEYS = [];
const $ = id => document.getElementById(id);

function toast(msg, ok=true){
  const t = $('toast');
  t.textContent = msg;
  t.className = 'show ' + (ok ? 'ok' : 'err');
  setTimeout(()=> t.className = '', 2600);
}

async function api(path, body){
  const token = localStorage.getItem('ka_token') || '';
  const res = await fetch(path, {
    method: body ? 'POST' : 'GET',
    headers: {'Content-Type':'application/json', 'Authorization':'Bearer ' + token},
    body: body ? JSON.stringify(body) : undefined
  });
  const data = await res.json().catch(()=>({}));
  if (res.status === 401){
    const tk = prompt('Admin token:' );
    if (tk){ localStorage.setItem('ka_token', tk); return api(path, body); }
    throw new Error('unauthorized');
  }
  if (!res.ok) throw new Error(data.detail || data.error || res.statusText);
  return data;
}

async function loadAll(){
  try{
    const [stats, data] = await Promise.all([api('/stats'), api('/admin/data')]);
    $('s-total').textContent = stats.total;
    $('s-used').textContent = stats.used;
    $('s-unused').textContent = stats.unused;
    $('s-banned').textContent = stats.banned;
    KEYS = data.keys || [];
    renderKeys();
  }catch(e){ toast('Load failed: ' + e.message, false); }
}

function statusBadge(k){
  if (k.banned) return '<span class="badge b-bad">BANNED</span>';
  if (k.expired) return '<span class="badge b-warn">EXPIRED</span>';
  if (k.hwid) return '<span class="badge b-good">ACTIVE</span>';
  return '<span class="badge b-muted">UNUSED</span>';
}

function renderKeys(){
  const q = ($('search').value || '').toLowerCase();
  const f = $('filter').value;
  const rows = KEYS.filter(k=>{
    if (f==='unused' && k.hwid) return false;
    if (f==='used' && !k.hwid) return false;
    if (f==='banned' && !k.banned) return false;
    if (f==='expired' && !k.expired) return false;
    if (!q) return true;
    return (k.key+' '+(k.hwid||'')+' '+(k.note||'')).toLowerCase().includes(q);
  });
  $('empty').style.display = rows.length ? 'none' : 'block';
  $('tbody').innerHTML = rows.map(k=>`
    <tr class="fade">
      <td class="mono">${esc(k.key)}</td>
      <td>${statusBadge(k)}</td>
      <td class="mono muted">${k.hwid ? esc(k.hwid.slice(0,18))+'…' : '—'}</td>
      <td class="muted">${k.expires ? new Date(k.expires).toLocaleDateString() : '∞'}</td>
      <td>${k.uses}</td>
      <td class="muted">${esc(k.note || '')}</td>
      <td><div class="actions">
        <button class="btn-ghost" title="Copy" onclick="copyKey('${esc(k.key)}')">⧉</button>
        ${k.hwid ? `<button class="btn-warn" title="Reset HWID" onclick="resetHwid('${esc(k.key)}')">↺</button>` : ''}
        ${k.banned
          ? `<button class="btn-good" onclick="unban('${esc(k.key)}')">Unban</button>`
          : `<button class="btn-danger" onclick="ban('${esc(k.key)}')">Ban</button>`}
        <button class="btn-danger" title="Delete" onclick="del('${esc(k.key)}')">✕</button>
      </div></td>
    </tr>`).join('');
}

function esc(s){ return String(s).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function copyKey(k){ navigator.clipboard.writeText(k).then(()=>toast('Copied ' + k)); }

async function generate(){
  const body = {
    amount: parseInt($('g-amount').value)||1,
    days: parseInt($('g-days').value)||0,
    prefix: $('g-prefix').value || 'KEY',
    note: $('g-note').value,
    plan: $('g-plan').value
  };
  try{
    const r = await api('/admin/generate', body);
    $('g-result').innerHTML = (r.keys||[]).map(k=>`<div>✅ <code>${esc(k)}</code></div>`).join('');
    toast(`Generated ${r.keys.length} key(s)`);
    loadAll();
  }catch(e){ toast(e.message, false); }
}

async function resetHwid(k){ try{ await api('/admin/reset',{key:k}); toast('HWID reset'); loadAll(); }catch(e){ toast(e.message,false);} }
async function ban(k){ const reason = prompt('Ban reason:', 'abuse') || 'abuse';
  try{ await api('/admin/ban',{key:k, reason}); toast('Banned ' + k); loadAll(); }catch(e){ toast(e.message,false);} }
async function unban(k){ try{ await api('/admin/unban',{key:k}); toast('Unbanned ' + k); loadAll(); }catch(e){ toast(e.message,false);} }
async function del(k){ if(!confirm('Delete ' + k + '? This cannot be undone.')) return;
  try{ await api('/admin/delete',{key:k}); toast('Deleted ' + k); loadAll(); }catch(e){ toast(e.message,false);} }

loadAll();
</script>
</body>
</html>"""


@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return ADMIN_HTML


@app.get("/admin/data")
def admin_data(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    docs = keys_collection.find().sort("created_at", DESCENDING).limit(1000)
    return {"keys": [_public_view(d) for d in docs if d]}


@app.post("/admin/generate")
async def admin_generate(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    amount = max(1, min(int(body.get("amount", 1) or 1), 100))
    days = int(body.get("days", 0) or 0)
    prefix = (body.get("prefix") or "KEY").strip()[:16] or "KEY"
    note = (body.get("note") or "").strip()[:200]
    plan = (body.get("plan") or "default").strip()[:32]

    keys, expires = [], None
    if days > 0:
        expires = _iso(_now() + timedelta(days=days))
    for _ in range(amount):
        key = _gen_key(prefix)
        keys_collection.insert_one(
            {"key": key, "hwid": "", "banned": False, "note": note,
             "plan": plan, "expires": expires, "uses": 0,
             "created_at": _now(), "last_used": None}
        )
        keys.append(key)
    _log("generate", ",".join(keys[:5]), f"{amount} key(s), {days}d")
    return {"keys": keys, "expires": expires, "plan": plan}


@app.post("/admin/reset")
async def admin_reset(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    key = (body.get("key") or "").strip()
    r = keys_collection.update_one({"key": key}, {"$set": {"hwid": "", "uses": 0}})
    if r.matched_count == 0:
        return JSONResponse(status_code=404, content={"error": "key not found"})
    _log("reset_hwid", key)
    return {"ok": True, "message": f"HWID reset for {key}"}


@app.post("/admin/ban")
async def admin_ban(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    key = (body.get("key") or "").strip()
    reason = (body.get("reason") or "no reason given").strip()[:200]
    r = keys_collection.update_one({"key": key}, {"$set": {"banned": True, "ban_reason": reason}})
    if r.matched_count == 0:
        return JSONResponse(status_code=404, content={"error": "key not found"})
    _log("ban", key, reason)
    return {"ok": True, "message": f"Banned {key}"}


@app.post("/admin/unban")
async def admin_unban(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    key = (body.get("key") or "").strip()
    r = keys_collection.update_one(
        {"key": key}, {"$set": {"banned": False}, "$unset": {"ban_reason": ""}}
    )
    if r.matched_count == 0:
        return JSONResponse(status_code=404, content={"error": "key not found"})
    _log("unban", key)
    return {"ok": True, "message": f"Unbanned {key}"}


@app.post("/admin/delete")
async def admin_delete(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    key = (body.get("key") or "").strip()
    r = keys_collection.delete_one({"key": key})
    if r.deleted_count == 0:
        return JSONResponse(status_code=404, content={"error": "key not found"})
    _log("delete", key)
    return {"ok": True, "message": f"Deleted {key}"}


@app.post("/admin/extend")
async def admin_extend(request: Request):
    if not _authorize(request):
        return JSONResponse(status_code=401, content={"detail": "unauthorized"})
    body = await _json_body(request)
    key = (body.get("key") or "").strip()
    days = int(body.get("days", 0) or 0)
    doc = _key_doc(key)
    if not doc:
        return JSONResponse(status_code=404, content={"error": "key not found"})
    base = _parse_iso(doc.get("expires")) if doc.get("expires") else None
    if not base or base < _now():
        base = _now()
    new_exp = _iso(base + timedelta(days=days))
    keys_collection.update_one({"key": key}, {"$set": {"expires": new_exp}})
    _log("extend", key, f"+{days}d")
    return {"ok": True, "expires": new_exp}


# ------------------------------------------------------------- root (docs) --
@app.get("/")
def root():
    return {
        "service": "KeyAuth API",
        "version": "2.0.0",
        "docs": "/docs",
        "dashboard": "/admin",
        "check": "/check_key/{key}/{hwid}",
        "health": "/status",
        "stats": "/stats",
    }
