import subprocess, sys, os
paketler = ["requests", "colorama", "cfonts"]
for p in paketler:
    try:
        __import__(p.replace("-", "_"))
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", p], capture_output=True)

from cfonts import render
from colorama import Fore, Style, init
import os
import sys
import json
import requests

init(autoreset=True)

WHITE = Fore.LIGHTWHITE_EX + Style.BRIGHT
CYAN = Fore.LIGHTCYAN_EX + Style.BRIGHT
RED = Fore.LIGHTRED_EX + Style.BRIGHT
GREEN = Fore.LIGHTGREEN_EX + Style.BRIGHT
YELLOW = Fore.LIGHTYELLOW_EX + Style.BRIGHT
MAGENTA = Fore.LIGHTMAGENTA_EX + Style.BRIGHT
RESET = Style.RESET_ALL

def temizle():
    os.system('cls' if os.name == 'nt' else 'clear')

temizle()
output = render('CC CHK', colors=['white', 'blue'], align='center')
print("\x1b[1;39m—" * 60)
print(output)
print("\x1b[1;39m—" * 60)
print("😛 kramyer  |  😸 Raiii Kramyer")
print("\x1b[1;39m—" * 60)
print()

api = "https://uncoder.eu.org/cc-checker/api.php"

head = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 15) AppleWebKit/537.36 Chrome/137.0.0.0 Mobile Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Origin": "https://uncoder.eu.org",
    "Referer": "https://uncoder.eu.org/cc-checker/",
    "X-Requested-With": "XMLHttpRequest"
}

def query(cc):
    try:
        r = requests.post(api, data={"data": cc}, headers=head, timeout=15)
        return r.json()
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    while True:
        cc = input(CYAN + "Enter CC (card|month|year|cvv) : " + RESET).strip()
        if not cc:
            print(RED + "CC cannot be empty." + RESET)
            continue

        print(YELLOW + "\nQuerying......" + RESET)
        result = query(cc)

        print()
        print(CYAN + "=" * 55 + RESET)
        print(WHITE + f"  RESULT : {cc}" + RESET)
        print(CYAN + "=" * 55 + RESET)

        status = result.get("status", "unknown")
        if status == "live":
            print(f"  Status    : {GREEN}LIVE{RESET}")
        elif status == "dead":
            print(f"  Status    : {RED}DEAD{RESET}")
        else:
            print(f"  Status    : {YELLOW}{status.upper()}{RESET}")

        if result.get("message"):
            print(f"  Message    : {result.get('message')}")
        if result.get("card"):
            print(f"  Card     : {result.get('card')}")
        if result.get("network"):
            print(f"  Network  : {result.get('network')}")
        if result.get("color"):
            print(f"  Color     : {result.get('color')}")
        if result.get("msg"):
            import re
            temiz_msg = re.sub(r'<[^>]+>', '', result.get('msg'))
            print(f"  Detail    : {temiz_msg.strip()}")
        print()

        cont = input(YELLOW + "Input another CC? (y/n) : " + RESET).strip().lower()
        if cont != 'y':
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(RED + "\nGoodbye...!" + RESET)
