#!/data/data/com.termux/files/usr/bin/bash
# QShell — Termux driver for https://github.com/saekacutie/404script
#
# Paste a lab fallback link. The script reads the project id, opens
# Termux-X11 + Chromium with CDP on 127.0.0.1:9222, clears the two
# Cloud Shell dialogs, and types one line into the terminal. That line
# decodes to the deploy. Cloud Shell posts the result to ntfy. Termux
# polls the same topic, which both sides derive as sha256(project)[:16].
#
# No root. No gcloud in Termux. US regions only. Cloud Run and
# Compute Engine only. A raw "ssh -i key user@host" link is printed
# and the browser flow is skipped.
#
# Repo facts this script follows (not the guessed protocol folders):
#   proxies/{haproxy,envoy,caddy,h2o,traefik,openresty,ssh,ovpn-relay}
#   Dockerfiles COPY common/, so the build context is the repo root.
#   Client id/password are the literal "saeka" inside common/config-*.json.
#   "saeka" is not a UUID, so generated mode rewrites that inbound and the
#   selected engine's route before the image build.
#   Reality x25519 runs inside Cloud Shell. Termux has no xray binary.
set -u

HOME="${HOME:-/tmp}"
WORKDIR="$HOME/.qshell"
mkdir -p "$WORKDIR"
LOCAL=0
FDROID_API="https://f-droid.org/packages/com.termux.api/"

usage() {
  cat << 'EOF'
Usage: bash qshell.sh [--local]

  (default)  Open the fallback link in Chromium over Termux-X11 and
             type the deploy into Cloud Shell.
  --local    Skip X11. Print the one-liner so you can paste it yourself.
EOF
}

say() { printf '\n  %s\n' "$*"; }
warn() { printf '\n  ! %s\n' "$*" >&2; }
die() { warn "$*"; exit 1; }

case "${1:-}" in
  --local) LOCAL=1 ;;
  --help|-h) usage; exit 0 ;;
  "") ;;
  *) die "Unknown argument: $1 (try --help)" ;;
esac

notify() {
  local title="$1" body="$2"
  if command -v termux-notification >/dev/null 2>&1; then
    termux-notification --title "$title" --content "$body" >/dev/null 2>&1 || true
  fi
}

preflight() {
  local missing=()
  command -v python3 >/dev/null 2>&1 || missing+=("python")
  command -v curl >/dev/null 2>&1 || missing+=("curl")
  command -v openssl >/dev/null 2>&1 || missing+=("openssl")
  command -v sha256sum >/dev/null 2>&1 || missing+=("coreutils")
  if [ "$LOCAL" -eq 0 ]; then
    if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then
      missing+=("chromium")
    fi
    command -v termux-x11 >/dev/null 2>&1 || missing+=("termux-x11-nightly")
  fi
  command -v termux-notification >/dev/null 2>&1 || missing+=("termux-api")
  command -v qrencode >/dev/null 2>&1 || missing+=("qrencode")

  if [ "${#missing[@]}" -gt 0 ]; then
    local list
    list=$(printf '%s, ' "${missing[@]}")
    list=${list%, }
    echo ""
    echo "  Missing: $list"
    notify "QShell missing packages" "$list"
    if ! command -v pkg >/dev/null 2>&1; then
      warn "pkg is not available, so the missing packages were not installed."
      if printf '%s\n' "${missing[@]}" | grep -qx 'termux-api'; then
        echo "  Termux:API app: $FDROID_API"
      fi
      [ "${QSHELL_FORCE:-}" = 1 ] || exit 1
    else
      if printf '%s\n' "${missing[@]}" | grep -qx 'termux-x11-nightly'; then
        pkg install -y x11-repo || true
      fi
      # shellcheck disable=SC2068
      pkg install -y ${missing[@]} ca-certificates || warn "pkg install reported an error"
    fi
  fi

  if ! command -v termux-notification >/dev/null 2>&1; then
    echo ""
    echo "  Termux:API is not installed. Notifications will be skipped."
    echo "  Install the app from F-Droid:"
    echo "  $FDROID_API"
  fi

  if ! python3 -c 'import websocket' >/dev/null 2>&1; then
    say "Installing websocket-client"
    pip install --user websocket-client || pip install websocket-client || die "could not install websocket-client"
  fi
  if ! python3 -c 'import websocket' >/dev/null 2>&1; then
    die "python module websocket is still missing"
  fi
}

gen_svc() { printf 'q%s' "$(openssl rand -hex 3)"; }
gen_uuid() { cat /proc/sys/kernel/random/uuid; }
gen_path() { printf '/%s' "$(openssl rand -hex 6)"; }
gen_grpc() { printf 'grpc-%s' "$(openssl rand -hex 3)"; }
gen_pass() { openssl rand -base64 18 | tr -d '/+=' | cut -c1-20; }
gen_sid() { openssl rand -hex 4; }

ask() {
  local label="$1" def="$2" reply
  read -r -p "  $label [$def]: " reply
  printf '%s' "${reply:-$def}"
}

parse_link() {
  python3 - "$1" << 'PY'
import re, sys
raw = sys.argv[1].strip()
if not raw:
    print("EMPTY\t\t")
    raise SystemExit
if re.match(r"(?i)^ssh\b", raw) or re.search(r"(?i)(?:^|\s)ssh\s+-i\b", raw):
    print("SSH\t\t" + raw.replace("\t", " "))
    raise SystemExit
m = re.search(r"(?:project|projectId|cloudshell_project)=([A-Za-z][A-Za-z0-9-]{4,62})", raw, re.I)
proj = m.group(1).lower() if m else ""
if not proj:
    m = re.search(r"\b(qwiklabs-gcp-\d{2}-[a-z0-9-]+)\b", raw, re.I)
    proj = m.group(1).lower() if m else ""
if "://" not in raw and " " not in raw and re.fullmatch(r"[A-Za-z][A-Za-z0-9-]{4,62}", raw):
    print(f"PROJECT\t{raw.lower()}\t")
    raise SystemExit
url = raw if "://" in raw else ""
print(f"URL\t{proj}\t{url}")
PY
}

stock_path() {
  case "$1" in
    vless-ws|vless-ws-tls) printf '%s' /vless-saeka ;;
    vless-hu) printf '%s' /vless-saeka-hu ;;
    vless-xh) printf '%s' /vless-saeka-xh ;;
    vless-grpc) printf '%s' vless-saeka-grpc ;;
    vless-h2) printf '%s' /vless-saeka-h2 ;;
    vmess-ws) printf '%s' /vmess-saeka ;;
    trojan-ws) printf '%s' /saeka-tojirp ;;
    ss-ws) printf '%s' /ss-saeka ;;
    *) printf '%s' /vless-saeka ;;
  esac
}

menu() {
  local def reply
  echo ""
  echo "  -------- menu --------"
  def=$(gen_svc)
  while true; do
    reply=$(ask "Service name (lowercase, digits, dashes)" "$def")
    SVC=$(printf '%s' "$reply" | tr '[:upper:]' '[:lower:]' | tr -cd 'a-z0-9-')
    if [[ "$SVC" =~ ^[a-z]([a-z0-9-]{0,47}[a-z0-9])?$ ]]; then
      break
    fi
    echo "  Name must start with a letter and use only a-z, 0-9, and dashes."
  done

  echo ""
  echo "  Target"
  echo "    1) Cloud Run     HTTP/WS/gRPC/H2 style inbounds"
  echo "    2) Compute Engine  Reality, OpenVPN, SSH SOCKS"
  reply=$(ask "Choice" "1")
  if [ "$reply" = "2" ]; then TARGET=vm; else TARGET=cloudrun; fi

  ENGINE=haproxy
  PROTO=vless-ws-tls
  ADS=noads
  CPU=1
  MEM=512Mi
  MAXI=1
  MTYPE=e2-micro
  OVPN_HOST=""
  OVPN_PORT=1194
  OVPN_PROTO=udp
  SSH_USER=""
  SSH_PASS=""
  VPORT=443
  CRED_MODE=gen
  UUID=""
  PASSWORD=""
  WSPATH=""
  GRPC_NAME=""
  SID=""
  SNI="www.microsoft.com"
  CF_ZONE=""
  CF_TOKEN=""

  if [ "$TARGET" = "cloudrun" ]; then
    echo ""
    echo "  Engine  (proxies/<name>/Dockerfile, context = repo root)"
    echo "    1) haproxy     2) envoy      3) caddy       4) h2o"
    echo "    5) traefik     6) openresty  (no gRPC, no H2)"
    echo "    7) ssh         8) ovpn-relay (needs an OpenVPN VM already)"
    reply=$(ask "Choice" "1")
    case "$reply" in
      2) ENGINE=envoy ;;
      3) ENGINE=caddy ;;
      4) ENGINE=h2o ;;
      5) ENGINE=traefik ;;
      6) ENGINE=openresty ;;
      7) ENGINE=ssh ;;
      8) ENGINE=ovpn-relay ;;
      *) ENGINE=haproxy ;;
    esac

    if [ "$ENGINE" = "ssh" ]; then
      PROTO=ssh-gw
      SSH_USER=$(ask "SSH username" "tunnel")
      SSH_USER=$(printf '%s' "$SSH_USER" | tr -cd 'A-Za-z0-9_-')
      [ -n "$SSH_USER" ] || SSH_USER=tunnel
      SSH_PASS=$(ask "SSH password" "$(gen_pass)")
    elif [ "$ENGINE" = "ovpn-relay" ]; then
      PROTO=ovpn-relay
      OVPN_HOST=$(ask "Upstream OpenVPN IP" "")
      OVPN_PORT=$(ask "Upstream OpenVPN port" "1194")
    else
      echo ""
      echo "  Protocol  (the image serves all of them; this picks the client link"
      echo "  and, in generated mode, which inbound gets the new secret)"
      echo "    1) VLESS + WS + TLS     2) VLESS + WS (no TLS)"
      echo "    3) VLESS + HTTPUpgrade  4) VLESS + XHTTP"
      echo "    5) VLESS + gRPC         6) VLESS + H2"
      echo "    7) VMess + WS           8) Trojan + WS"
      echo "    9) Shadowsocks + WS"
      reply=$(ask "Choice" "1")
      case "$reply" in
        2) PROTO=vless-ws ;;
        3) PROTO=vless-hu ;;
        4) PROTO=vless-xh ;;
        5) PROTO=vless-grpc ;;
        6) PROTO=vless-h2 ;;
        7) PROTO=vmess-ws ;;
        8) PROTO=trojan-ws ;;
        9) PROTO=ss-ws ;;
        *) PROTO=vless-ws-tls ;;
      esac
      if [ "$ENGINE" = "openresty" ] && { [ "$PROTO" = "vless-grpc" ] || [ "$PROTO" = "vless-h2" ]; }; then
        warn "OpenResty cannot serve gRPC or H2. Falling back to VLESS + WS + TLS."
        PROTO=vless-ws-tls
      fi
      if [ "$PROTO" = "vless-ws" ]; then
        warn "security=none will not connect through a run.app hostname."
      fi
      echo ""
      echo "  Ads mode   1) noads   2) ads"
      reply=$(ask "Choice" "1")
      if [ "$reply" = "2" ]; then ADS=ads; else ADS=noads; fi
    fi

    echo ""
    echo "  Sizing"
    echo "    1) Lab      1 CPU / 512Mi / 1 instance"
    echo "    2) Browse   1 CPU / 2Gi   / 2 instances"
    echo "    3) Stream   2 CPU / 4Gi   / 4 instances"
    echo "    4) Custom"
    reply=$(ask "Choice" "1")
    case "$reply" in
      2) CPU=1; MEM=2Gi; MAXI=2 ;;
      3) CPU=2; MEM=4Gi; MAXI=4 ;;
      4)
        CPU=$(ask "CPU (1/2/4)" "1")
        MEM=$(ask "Memory (512Mi/1Gi/2Gi/4Gi)" "1Gi")
        MAXI=$(ask "Max instances" "1")
        ;;
      *) CPU=1; MEM=512Mi; MAXI=1 ;;
    esac
  else
    echo ""
    echo "  VM protocol"
    echo "    1) VLESS + Reality"
    echo "    2) OpenVPN"
    echo "    3) SSH SOCKS"
    reply=$(ask "Choice" "1")
    case "$reply" in
      2) PROTO=openvpn; VPORT=1194 ;;
      3) PROTO=ssh-socks; VPORT=22 ;;
      *) PROTO=reality; VPORT=443 ;;
    esac
    echo ""
    echo "  Machine"
    echo "    1) e2-micro   2) e2-small   3) e2-medium   4) custom"
    reply=$(ask "Choice" "1")
    case "$reply" in
      2) MTYPE=e2-small ;;
      3) MTYPE=e2-medium ;;
      4) MTYPE=$(ask "Machine type" "e2-micro") ;;
      *) MTYPE=e2-micro ;;
    esac
  fi

  echo ""
  echo "  Region (US only)"
  echo "    1) us-central1   2) us-east1   3) us-west1"
  echo "    4) us-west2      5) us-west3"
  reply=$(ask "Choice" "1")
  case "$reply" in
    2) REGION=us-east1 ;;
    3) REGION=us-west1 ;;
    4) REGION=us-west2 ;;
    5) REGION=us-west3 ;;
    *) REGION=us-central1 ;;
  esac
  ZONE="${REGION}-a"

  if [ "$TARGET" = "cloudrun" ] && [ "$ENGINE" != "ssh" ] && [ "$ENGINE" != "ovpn-relay" ]; then
    echo ""
    echo "  Secrets"
    echo "    1) Generate and patch the image before build"
    echo "    2) Keep the repo's baked saeka values"
    reply=$(ask "Choice" "1")
    if [ "$reply" = "2" ]; then
      CRED_MODE=stock
      UUID=saeka
      PASSWORD=saeka
      WSPATH=$(stock_path "$PROTO")
      GRPC_NAME=$WSPATH
      warn "VLESS/VMess id \"saeka\" is not a UUID. Xray may refuse the config."
    else
      CRED_MODE=gen
      if [ "$PROTO" = "trojan-ws" ] || [ "$PROTO" = "ss-ws" ]; then
        PASSWORD=$(ask "Password" "$(gen_pass)")
        UUID=$(ask "UUID (unused for this protocol)" "$(gen_uuid)")
      else
        UUID=$(ask "UUID" "$(gen_uuid)")
        PASSWORD=$(ask "Password (unused for VLESS/VMess)" "$(gen_pass)")
      fi
      if [ "$PROTO" = "vless-grpc" ]; then
        GRPC_NAME=$(ask "gRPC service name" "$(gen_grpc)")
        WSPATH=$GRPC_NAME
      else
        WSPATH=$(ask "Path" "$(gen_path)")
        case "$WSPATH" in
          /*) ;;
          *) WSPATH="/$WSPATH" ;;
        esac
        GRPC_NAME=$WSPATH
      fi
    fi
    SID=$(ask "Short id (VM only, stored anyway)" "$(gen_sid)")
    SNI=$(ask "SNI" "www.microsoft.com")
  elif [ "$TARGET" = "vm" ]; then
    CRED_MODE=gen
    UUID=$(ask "UUID" "$(gen_uuid)")
    PASSWORD=$(ask "Password" "$(gen_pass)")
    SID=$(ask "Reality short id" "$(gen_sid)")
    SNI=$(ask "Reality SNI" "www.microsoft.com")
    if [ "$PROTO" = "reality" ]; then
      VPORT=$(ask "Reality port" "443")
      echo "  The x25519 keypair is generated inside Cloud Shell, not here."
    elif [ "$PROTO" = "openvpn" ]; then
      VPORT=$(ask "OpenVPN port" "1194")
      OVPN_PROTO=$(ask "OpenVPN proto (udp/tcp)" "udp")
      case "$OVPN_PROTO" in
        tcp|udp) ;;
        *) OVPN_PROTO=udp ;;
      esac
    else
      VPORT=22
    fi
    CF_ZONE=$(ask "Cloudflare zone (blank skips DNS)" "")
    if [ -n "$CF_ZONE" ]; then
      CF_TOKEN=$(ask "Cloudflare API token" "")
    fi
  fi

  TOPIC=$(printf '%s' "$PROJECT" | sha256sum | awk '{print substr($1,1,16)}')
  NOTIFY=$(ask "Notify URL" "https://ntfy.sh/$TOPIC")
  echo ""
  echo "  service=$SVC target=$TARGET engine=$ENGINE proto=$PROTO region=$REGION"
  echo "  topic=$TOPIC"
}

write_cloud() {
  local out="$WORKDIR/cloud.sh"
  {
    echo '#!/bin/bash'
    echo 'set -uo pipefail'
    printf 'export PROJECT=%q\n' "$PROJECT"
    printf 'export SVC=%q\n' "$SVC"
    printf 'export REGION=%q\n' "$REGION"
    printf 'export ZONE=%q\n' "$ZONE"
    printf 'export TARGET=%q\n' "$TARGET"
    printf 'export ENGINE=%q\n' "$ENGINE"
    printf 'export PROTO=%q\n' "$PROTO"
    printf 'export UUID=%q\n' "$UUID"
    printf 'export PASSWORD=%q\n' "$PASSWORD"
    printf 'export WSPATH=%q\n' "$WSPATH"
    printf 'export GRPC_NAME=%q\n' "$GRPC_NAME"
    printf 'export SID=%q\n' "$SID"
    printf 'export SNI=%q\n' "$SNI"
    printf 'export ADS=%q\n' "$ADS"
    printf 'export CPU=%q\n' "$CPU"
    printf 'export MEM=%q\n' "$MEM"
    printf 'export MAXI=%q\n' "$MAXI"
    printf 'export MTYPE=%q\n' "$MTYPE"
    printf 'export VPORT=%q\n' "$VPORT"
    printf 'export OVPN_PROTO=%q\n' "$OVPN_PROTO"
    printf 'export OVPN_HOST=%q\n' "$OVPN_HOST"
    printf 'export OVPN_PORT=%q\n' "$OVPN_PORT"
    printf 'export SSH_USER=%q\n' "$SSH_USER"
    printf 'export SSH_PASS=%q\n' "$SSH_PASS"
    printf 'export CF_ZONE=%q\n' "$CF_ZONE"
    printf 'export CF_TOKEN=%q\n' "$CF_TOKEN"
    printf 'export CRED_MODE=%q\n' "$CRED_MODE"
    printf 'export NOTIFY=%q\n' "$NOTIFY"
    cat << 'EOS'
export RESULT_URL="" RESULT_IP="" RESULT_PBK="" RESULT_PORT="" RESULT_SHARE=""
export RESULT_KEY="" RESULT_OVPN="" RESULT_PRIV=""

post() {
  export POST_STATUS="$1"
  export POST_DETAIL="${2:-}"
  python3 - << 'PY' || true
import hashlib, json, os, urllib.request
status = os.environ.get("POST_STATUS", "ok")
detail = os.environ.get("POST_DETAIL", "")
project = os.environ.get("PROJECT", "")
topic = hashlib.sha256(project.encode()).hexdigest()[:16]
url = os.environ.get("NOTIFY") or f"https://ntfy.sh/{topic}"
ovpn = os.environ.get("RESULT_OVPN", "")
parts = []
if len(ovpn) > 3000:
    parts = [ovpn[i:i+2800] for i in range(0, len(ovpn), 2800)]
    ovpn_field = ""
else:
    ovpn_field = ovpn
body = {
    "status": status,
    "detail": detail,
    "svc": os.environ.get("SVC", ""),
    "region": os.environ.get("REGION", ""),
    "zone": os.environ.get("ZONE", ""),
    "target": os.environ.get("TARGET", ""),
    "protocol": os.environ.get("PROTO", ""),
    "engine": os.environ.get("ENGINE", ""),
    "url": os.environ.get("RESULT_URL", ""),
    "ip": os.environ.get("RESULT_IP", ""),
    "uuid": os.environ.get("UUID", ""),
    "path": os.environ.get("WSPATH", ""),
    "password": os.environ.get("PASSWORD", ""),
    "sni": os.environ.get("SNI", ""),
    "pbk": os.environ.get("RESULT_PBK", ""),
    "sid": os.environ.get("SID", ""),
    "port": os.environ.get("RESULT_PORT", "") or os.environ.get("VPORT", ""),
    "method": "aes-256-gcm",
    "share": os.environ.get("RESULT_SHARE", ""),
    "ssh_key": os.environ.get("RESULT_KEY", ""),
    "ssh_user": os.environ.get("SSH_USER", ""),
    "ovpn": ovpn_field,
    "ovpn_parts": len(parts),
    "topic": topic,
}
def send(obj, title):
    data = json.dumps(obj).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json", "Title": title})
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            resp.read()
        print("NTFY_OK", url)
    except Exception as exc:
        print("NTFY_FAIL", exc)
send(body, f"QShell {status}")
for i, part in enumerate(parts, 1):
    send({"status": "part", "svc": body["svc"], "index": i, "total": len(parts), "data": part}, f"QShell ovpn {i}")
PY
}

on_err() {
  echo "FAILED at line $1" >&2
  post fail "cloud script failed at line $1"
  exit 1
}
trap 'on_err $LINENO' ERR
set -e

build_share() {
  RESULT_SHARE=$(python3 - << 'PY'
import base64, json, os
from urllib.parse import quote
proto = os.environ.get("PROTO", "")
svc = os.environ.get("SVC", "svc")
uuid = os.environ.get("UUID", "")
password = os.environ.get("PASSWORD", "")
path = os.environ.get("WSPATH", "")
sni = os.environ.get("SNI") or "www.microsoft.com"
pbk = os.environ.get("RESULT_PBK", "")
sid = os.environ.get("SID", "")
port = os.environ.get("RESULT_PORT") or os.environ.get("VPORT") or "443"
method = "aes-256-gcm"
host = os.environ.get("RESULT_URL") or os.environ.get("RESULT_IP") or ""
host = host.replace("https://", "").replace("http://", "").strip("/")
name = quote(svc)
def q(v):
    return quote(v or "", safe="")
if proto == "vmess-ws":
    obj = {"v":"2","ps":svc,"add":host,"port":"443","id":uuid,"aid":"0","scy":"auto","net":"ws","type":"none","host":host,"path":path,"tls":"tls","sni":host}
    print("vmess://" + base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode())
elif proto == "trojan-ws":
    print(f"trojan://{q(password)}@{host}:443?type=ws&path={q(path)}&security=tls&sni={host}#{name}")
elif proto == "ss-ws":
    user = base64.b64encode(f"{method}:{password}".encode()).decode()
    print(f"ss://{user}@{host}:443#{name}")
elif proto == "vless-grpc":
    print(f"vless://{uuid}@{host}:443?encryption=none&security=tls&type=grpc&serviceName={q(path)}&mode=gun&sni={host}#{name}")
elif proto == "reality":
    print(f"vless://{uuid}@{host}:{port}?encryption=none&security=reality&sni={q(sni)}&fp=chrome&pbk={q(pbk)}&sid={q(sid)}&type=tcp&flow=xtls-rprx-vision#{name}")
elif proto == "openvpn":
    print(f"ovpn://{host}:{port}")
elif proto == "ssh-socks":
    print(f"ssh -i {svc}_tunnel_key -D 1080 -N tunnel@{host}")
elif proto == "ssh-gw":
    print(f"wss://{host}/saeka-ssh")
elif proto == "ovpn-relay":
    print(f"wss://{host}/saeka-ovpn")
else:
    typ = {"vless-hu":"httpupgrade","vless-xh":"xhttp","vless-h2":"http"}.get(proto, "ws")
    sec = "none" if proto == "vless-ws" else "tls"
    print(f"vless://{uuid}@{host}:443?encryption=none&security={sec}&type={typ}&path={q(path)}&host={host}&sni={host}#{name}")
PY
)
  export RESULT_SHARE
}

patch_configs() {
  [ "$CRED_MODE" = "gen" ] || return 0
  case "$ENGINE" in
    ssh|ovpn-relay) return 0 ;;
  esac
  python3 - << 'PY'
import json, os, re
from pathlib import Path
engine = os.environ["ENGINE"]
proto = os.environ["PROTO"]
new_path = os.environ.get("WSPATH") or ""
new_uuid = os.environ.get("UUID") or ""
new_pass = os.environ.get("PASSWORD") or ""
tags = {
    "vless-ws": "vless-ws",
    "vless-ws-tls": "vless-ws",
    "vless-hu": "vless-hu",
    "vless-xh": "vless-xh",
    "vless-grpc": "vless-grpc",
    "vless-h2": "vless-h2",
    "vmess-ws": "vmess-ws",
    "trojan-ws": "trojan-ws",
    "ss-ws": "ss-ws",
}
tag = tags.get(proto)
if not tag:
    raise SystemExit(0)
net_key = {
    "ws": "wsSettings",
    "httpupgrade": "httpupgradeSettings",
    "xhttp": "xhttpSettings",
    "http": "httpSettings",
}
old = None
kind = "grpc" if proto == "vless-grpc" else "path"
for name in ("common/config-noads.json", "common/config-ads.json"):
    path = Path(name)
    data = json.loads(path.read_text())
    for ib in data.get("inbounds", []):
        if ib.get("tag") != tag:
            continue
        ss = ib.setdefault("streamSettings", {})
        if kind == "grpc":
            block = ss.setdefault("grpcSettings", {})
            old = block.get("serviceName")
            if new_path:
                block["serviceName"] = new_path
        else:
            key = net_key.get(ss.get("network", ""))
            if key:
                block = ss.setdefault(key, {})
                old = block.get("path")
                if new_path:
                    block["path"] = new_path
        clients = (ib.get("settings") or {}).get("clients") or []
        if clients:
            if new_uuid and "id" in clients[0]:
                clients[0]["id"] = new_uuid
            if new_pass and "password" in clients[0]:
                clients[0]["password"] = new_pass
    path.write_text(json.dumps(data, indent=2) + "\n")
if old and new_path and old != new_path:
    root = Path("proxies") / engine
    rx = re.compile(re.escape(old) + r"(?![A-Za-z0-9_-])")
    for file in root.rglob("*"):
        if not file.is_file():
            continue
        text = file.read_text(errors="ignore")
        if old not in text:
            continue
        file.write_text(rx.sub(new_path, text))
print(f"patched {tag}: {old} -> {new_path}")
PY
}

deploy_run() {
  cd "$HOME"
  if [ ! -d "$HOME/404script/.git" ]; then
    git clone --depth 1 https://github.com/saekacutie/404script 404script
  fi
  cd "$HOME/404script"
  git checkout -- common proxies >/dev/null 2>&1 || true
  gcloud config set project "$PROJECT"
  gcloud services enable run.googleapis.com cloudbuild.googleapis.com --project="$PROJECT"
  patch_configs
  local img="gcr.io/${PROJECT}/${SVC}"
  cat > /tmp/qshell-cb.yaml << YAML
steps:
- name: gcr.io/cloud-builders/docker
  args: ["build", "-f", "proxies/${ENGINE}/Dockerfile", "-t", "${img}", "."]
images:
- ${img}
YAML
  gcloud builds submit . --config /tmp/qshell-cb.yaml --project="$PROJECT" --quiet
  local env_vars
  case "$ENGINE" in
    ssh) env_vars="^@^SSH_USERS=${SSH_USER}:${SSH_PASS}" ;;
    ovpn-relay) env_vars="^@^OVPN_UPSTREAM_HOST=${OVPN_HOST}@OVPN_UPSTREAM_PORT=${OVPN_PORT}" ;;
    *) env_vars="ADS_MODE=${ADS}" ;;
  esac
  gcloud run deploy "$SVC" \
    --image "$img" \
    --platform managed \
    --region "$REGION" \
    --port 8080 \
    --cpu "$CPU" \
    --memory "$MEM" \
    --max-instances "$MAXI" \
    --timeout 3600 \
    --allow-unauthenticated \
    --set-env-vars "$env_vars" \
    --project="$PROJECT" \
    --quiet
  RESULT_URL=$(gcloud run services describe "$SVC" --region "$REGION" --project="$PROJECT" --format='value(status.url)')
  export RESULT_URL
  RESULT_PORT=443
  export RESULT_PORT
  echo "DEPLOYED: $RESULT_URL"
}

reality_keys() {
  mkdir -p "$HOME/.qshell"
  if [ ! -x "$HOME/.qshell/xray" ]; then
    command -v unzip >/dev/null 2>&1 || (sudo apt-get update && sudo apt-get install -y unzip)
    curl -fsSL -o /tmp/qshell-xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -p /tmp/qshell-xray.zip xray > "$HOME/.qshell/xray"
    chmod +x "$HOME/.qshell/xray"
  fi
  local out priv pub
  out=$("$HOME/.qshell/xray" x25519)
  priv=$(printf '%s\n' "$out" | awk -F: 'BEGIN{IGNORECASE=1} /private/ {sub(/^[[:space:]]+/, "", $2); print $2; exit}')
  pub=$(printf '%s\n' "$out" | awk -F: 'BEGIN{IGNORECASE=1} /public/ {sub(/^[[:space:]]+/, "", $2); print $2; exit}')
  if [ -z "$pub" ]; then
    pub=$(printf '%s\n' "$out" | awk -F: 'BEGIN{IGNORECASE=1} /^password/ {sub(/^[[:space:]]+/, "", $2); print $2; exit}')
  fi
  [ -n "$priv" ] && [ -n "$pub" ] || { echo "$out" >&2; echo "xray x25519 parse failed" >&2; return 1; }
  RESULT_PRIV=$priv
  RESULT_PBK=$pub
  export RESULT_PRIV RESULT_PBK
  echo "REALITY public key: $RESULT_PBK"
}

wait_ssh() {
  local i mode
  SSH_MODE=plain
  for mode in plain iap; do
    SSH_MODE=$mode
    for i in $(seq 1 18); do
      if ssh_vm --command "true" >/dev/null 2>&1; then
        echo "  SSH up ($mode)"
        return 0
      fi
      echo "  waiting for SSH via $mode ($i)"
      sleep 8
    done
  done
  echo "SSH did not come up" >&2
  return 1
}

ssh_vm() {
  if [ "${SSH_MODE:-plain}" = "iap" ]; then
    gcloud compute ssh "$VM" --zone "$ZONE" --project="$PROJECT" --quiet --tunnel-through-iap "$@"
  else
    gcloud compute ssh "$VM" --zone "$ZONE" --project="$PROJECT" --quiet "$@"
  fi
}

run_remote() {
  local b64
  b64=$(base64 -w0 /tmp/qremote.sh 2>/dev/null || base64 /tmp/qremote.sh | tr -d '\n')
  ssh_vm --command "echo $b64 | base64 -d | sudo bash" | tee /tmp/qremote.out
}

cf_dns() {
  [ -n "$CF_ZONE" ] && [ -n "$CF_TOKEN" ] && [ -n "$RESULT_IP" ] || return 0
  python3 - << 'PY' || true
import json, os, urllib.request
zone_name = os.environ["CF_ZONE"].strip().rstrip(".")
token = os.environ["CF_TOKEN"]
ip = os.environ["RESULT_IP"]
sub = os.environ["SVC"]
root = ".".join(zone_name.split(".")[-2:])
fqdn = f"{sub}.{root}"
def req(method, path, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    r = urllib.request.Request(
        "https://api.cloudflare.com/client/v4" + path,
        data=data, method=method,
        headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(r, timeout=25) as resp:
        return json.loads(resp.read().decode())
zones = req("GET", "/zones?name=" + root)
zid = zones["result"][0]["id"]
recs = req("GET", f"/zones/{zid}/dns_records?type=A&name={fqdn}")
payload = {"type": "A", "name": fqdn, "content": ip, "ttl": 120, "proxied": False}
if recs.get("result"):
    req("PUT", f"/zones/{zid}/dns_records/{recs['result'][0]['id']}", payload)
else:
    req("POST", f"/zones/{zid}/dns_records", payload)
print("CF_FQDN", fqdn)
PY
}

deploy_vm() {
  gcloud config set project "$PROJECT"
  gcloud services enable compute.googleapis.com --project="$PROJECT"
  VM="${SVC}-vm"
  TAG="${SVC}-vm"
  export VM TAG
  if [ "$PROTO" = "reality" ]; then
    reality_keys
  fi
  if [ "$PROTO" = "ssh-socks" ]; then
    mkdir -p "$HOME/.qshell"
    if [ ! -f "$HOME/.qshell/${SVC}_key" ]; then
      ssh-keygen -t ed25519 -N "" -f "$HOME/.qshell/${SVC}_key" -q
    fi
    RESULT_KEY=$(cat "$HOME/.qshell/${SVC}_key")
    export RESULT_KEY
    SSH_PUB=$(cat "$HOME/.qshell/${SVC}_key.pub")
    export SSH_PUB
  fi
  if ! gcloud compute instances describe "$VM" --zone "$ZONE" --project="$PROJECT" >/dev/null 2>&1; then
    gcloud compute instances create "$VM" \
      --zone "$ZONE" \
      --machine-type "$MTYPE" \
      --image-family debian-12 \
      --image-project debian-cloud \
      --boot-disk-size 20GB \
      --tags "$TAG" \
      --project="$PROJECT" \
      --quiet
  fi
  local allow
  case "$PROTO" in
    openvpn) allow="${OVPN_PROTO}:${VPORT}" ;;
    ssh-socks) allow="tcp:22" ;;
    *) allow="tcp:${VPORT}" ;;
  esac
  if ! gcloud compute firewall-rules describe "${SVC}-allow" --project="$PROJECT" >/dev/null 2>&1; then
    gcloud compute firewall-rules create "${SVC}-allow" \
      --allow "$allow" \
      --target-tags "$TAG" \
      --project="$PROJECT" \
      --quiet
  fi
  RESULT_IP=$(gcloud compute instances describe "$VM" --zone "$ZONE" --project="$PROJECT" --format='value(networkInterfaces[0].accessConfigs[0].natIP)')
  export RESULT_IP
  echo "DEPLOYED: $RESULT_IP"
  wait_ssh
  if [ "$PROTO" = "reality" ]; then
    cat > /tmp/qremote.sh << REMOTE
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends unzip curl ca-certificates
curl -fsSL -o /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
rm -rf /tmp/xraybin
unzip -o /tmp/xray.zip -d /tmp/xraybin
install -m 755 /tmp/xraybin/xray /usr/local/bin/xray
mkdir -p /usr/local/etc/xray
cat > /usr/local/etc/xray/config.json << JSON
{
  "inbounds": [{
    "listen": "0.0.0.0",
    "port": ${VPORT},
    "protocol": "vless",
    "settings": {"clients": [{"id": "${UUID}", "flow": "xtls-rprx-vision"}], "decryption": "none"},
    "streamSettings": {
      "network": "tcp",
      "security": "reality",
      "realitySettings": {
        "show": false,
        "dest": "${SNI}:443",
        "xver": 0,
        "serverNames": ["${SNI}"],
        "privateKey": "${RESULT_PRIV}",
        "shortIds": ["${SID}"]
      }
    }
  }],
  "outbounds": [{"protocol": "freedom"}]
}
JSON
cat > /etc/systemd/system/xray.service << 'UNIT'
[Unit]
Description=xray
After=network.target
[Service]
ExecStart=/usr/local/bin/xray run -config /usr/local/etc/xray/config.json
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now xray
systemctl is-active xray
REMOTE
    run_remote
  elif [ "$PROTO" = "openvpn" ]; then
    cat > /tmp/qremote.sh << REMOTE
#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends openvpn easy-rsa iptables curl ca-certificates
if command -v make-cadir >/dev/null 2>&1; then
  rm -rf /root/easyrsa
  make-cadir /root/easyrsa
else
  rm -rf /root/easyrsa
  cp -a /usr/share/easy-rsa /root/easyrsa
fi
cd /root/easyrsa
export EASYRSA_BATCH=1
./easyrsa init-pki
./easyrsa build-ca nopass
./easyrsa gen-req server nopass
./easyrsa sign-req server server
./easyrsa gen-req client1 nopass
./easyrsa sign-req client client1
./easyrsa gen-dh
openvpn --genkey secret /root/easyrsa/tc.key
install -d -m 755 /etc/openvpn/server
install -m 644 pki/ca.crt pki/issued/server.crt pki/issued/client1.crt /etc/openvpn/server/
install -m 600 pki/private/server.key pki/private/client1.key pki/dh.pem tc.key /etc/openvpn/server/
cat > /etc/openvpn/server/server.conf << CONF
port ${VPORT}
proto ${OVPN_PROTO}
dev tun
ca /etc/openvpn/server/ca.crt
cert /etc/openvpn/server/server.crt
key /etc/openvpn/server/server.key
dh /etc/openvpn/server/dh.pem
tls-crypt /etc/openvpn/server/tc.key
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 1.1.1.1"
keepalive 10 120
cipher AES-256-GCM
auth SHA256
persist-key
persist-tun
explicit-exit-notify 1
CONF
echo 'net.ipv4.ip_forward=1' > /etc/sysctl.d/99-qshell.conf
sysctl -w net.ipv4.ip_forward=1 >/dev/null
IFACE=\$(ip -4 route show default | awk '{print \$5; exit}')
iptables -t nat -C POSTROUTING -s 10.8.0.0/24 -o "\$IFACE" -j MASQUERADE 2>/dev/null || \
  iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o "\$IFACE" -j MASQUERADE
systemctl enable --now openvpn-server@server
IP=\$(curl -fsS --max-time 10 ifconfig.me || true)
[ -n "\$IP" ] || IP="${RESULT_IP}"
{
  echo client
  echo dev tun
  echo proto ${OVPN_PROTO}
  echo "remote \$IP ${VPORT}"
  echo nobind
  echo persist-key
  echo persist-tun
  echo remote-cert-tls server
  echo cipher AES-256-GCM
  echo auth SHA256
  echo '<ca>'
  cat /etc/openvpn/server/ca.crt
  echo '</ca>'
  echo '<cert>'
  sed -n '/-----BEGIN/,/-----END/p' /etc/openvpn/server/client1.crt
  echo '</cert>'
  echo '<key>'
  cat /etc/openvpn/server/client1.key
  echo '</key>'
  echo '<tls-crypt>'
  cat /etc/openvpn/server/tc.key
  echo '</tls-crypt>'
} > /root/client1.ovpn
chmod 600 /root/client1.ovpn
echo OVPN_BEGIN
base64 -w0 /root/client1.ovpn || base64 /root/client1.ovpn | tr -d '\n'
echo
echo OVPN_END
REMOTE
    run_remote
    RESULT_OVPN=$(sed -n '/OVPN_BEGIN/,/OVPN_END/p' /tmp/qremote.out | sed '1d;$d' | tr -d '\n')
    export RESULT_OVPN
  else
    cat > /tmp/qremote.sh << REMOTE
#!/bin/bash
set -euo pipefail
id tunnel >/dev/null 2>&1 || useradd -m -s /usr/sbin/nologin tunnel
mkdir -p /home/tunnel/.ssh
cat > /home/tunnel/.ssh/authorized_keys << 'PUB'
${SSH_PUB}
PUB
chmod 700 /home/tunnel/.ssh
chmod 600 /home/tunnel/.ssh/authorized_keys
chown -R tunnel:tunnel /home/tunnel/.ssh
grep -q 'Match User tunnel' /etc/ssh/sshd_config || cat >> /etc/ssh/sshd_config << 'CFG'
Match User tunnel
  AllowTcpForwarding yes
  X11Forwarding no
  PermitTunnel no
  GatewayPorts no
  AllowAgentForwarding no
  PermitTTY no
  ForceCommand /usr/sbin/nologin
CFG
systemctl restart ssh || systemctl restart sshd
echo SSH_READY
REMOTE
    run_remote
  fi
  RESULT_PORT=$VPORT
  export RESULT_PORT
  cf_dns
}

if [ "$TARGET" = "vm" ]; then
  deploy_vm
else
  deploy_run
fi
build_share
echo "SHARE: $RESULT_SHARE"
post ok "deployed"
echo QSHELL_DONE
EOS
  } > "$out"
  chmod 700 "$out"
}

write_oneline() {
  local b64
  b64=$(base64 "$WORKDIR/cloud.sh" | tr -d '\n')
  printf '%s\n' "echo ${b64} | base64 -d > \"\$HOME/qshell-run.sh\" && bash \"\$HOME/qshell-run.sh\"" > "$WORKDIR/oneline.txt"
}

launch_browser() {
  local url="$1" bin
  mkdir -p "$WORKDIR/chrome"
  export DISPLAY="${DISPLAY:-:1}"
  if [ ! -f "$WORKDIR/x11.pid" ] || ! kill -0 "$(cat "$WORKDIR/x11.pid")" >/dev/null 2>&1; then
    termux-x11 "$DISPLAY" >"$WORKDIR/x11.log" 2>&1 &
    echo $! > "$WORKDIR/x11.pid"
    sleep 1
  fi
  command -v am >/dev/null 2>&1 && am start --user 0 -n com.termux.x11/.MainActivity >/dev/null 2>&1 || true
  if command -v chromium >/dev/null 2>&1; then bin=chromium
  else bin=chromium-browser
  fi
  if ! curl -sf --max-time 1 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
    "$bin" \
      --no-sandbox \
      --disable-dev-shm-usage \
      --disable-gpu \
      --no-first-run \
      --no-default-browser-check \
      --remote-debugging-address=127.0.0.1 \
      --remote-debugging-port=9222 \
      --user-data-dir="$WORKDIR/chrome" \
      --window-size=1200,800 \
      "$url" >"$WORKDIR/chromium.log" 2>&1 &
    echo $! > "$WORKDIR/chromium.pid"
  fi
  local i
  for i in $(seq 1 40); do
    if curl -sf --max-time 1 http://127.0.0.1:9222/json/version >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  warn "Chromium CDP did not open on 127.0.0.1:9222"
  return 1
}

write_cdp() {
  cat > "$WORKDIR/cdp.py" << 'PY'
import json, sys, time, urllib.request
import websocket

HOME_WAIT = 90

def targets():
    with urllib.request.urlopen("http://127.0.0.1:9222/json/list", timeout=5) as resp:
        return json.load(resp)

class CDP:
    def __init__(self, url):
        self.ws = websocket.create_connection(url, timeout=20, suppress_origin=True)
        self.n = 0
    def call(self, method, params=None, timeout=25):
        self.n += 1
        mid = self.n
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            self.ws.settimeout(max(0.2, end - time.time()))
            try:
                raw = self.ws.recv()
            except websocket.WebSocketTimeoutException:
                continue
            data = json.loads(raw)
            if data.get("id") == mid:
                if "error" in data:
                    raise RuntimeError(str(data["error"]))
                return data.get("result") or {}
        raise TimeoutError(method)
    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

def eval_js(cdp, expression):
    result = cdp.call("Runtime.evaluate", {
        "expression": expression,
        "returnByValue": True,
        "awaitPromise": True,
    })
    if result.get("exceptionDetails"):
        return None
    return (result.get("result") or {}).get("value")

POPUP_JS = r"""
(bankSource) => {
  const bank = new RegExp(bankSource, "i");
  const reject = /cancel|deny|close|dismiss|not now|no thanks|learn more|delete|remove|reject|decline|\blater\b|\bback\b/i;
  const nodes = [...document.querySelectorAll("button, [role='button'], a, input[type='submit']")];
  const vw = window.innerWidth || 1;
  const vh = window.innerHeight || 1;
  const cands = [];
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) continue;
    if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) continue;
    const text = (el.innerText || el.value || "").trim().replace(/\s+/g, " ").slice(0, 80);
    const aria = el.getAttribute("aria-label") || "";
    const title = el.getAttribute("title") || "";
    const tip = el.getAttribute("data-tooltip") || el.getAttribute("mattooltip") || el.getAttribute("data-mat-icon-name") || "";
    const cls = typeof el.className === "string" ? el.className : "";
    if (reject.test(text) || reject.test(aria)) continue;
    let score = 0;
    const parts = [];
    if (bank.test(text)) { score += 6; parts.push("text+6"); }
    if (bank.test(aria) || bank.test(title) || bank.test(tip)) { score += 2; parts.push("aria/title/tooltip+2"); }
    const iconBlob = [
      el.querySelector("svg") ? el.querySelector("svg").innerHTML : "",
      el.querySelector("mat-icon") ? el.querySelector("mat-icon").textContent : "",
      el.getAttribute("data-mat-icon-name") || "",
    ].join(" ").toLowerCase();
    if (/check|done|arrow_forward|navigate_next|play_arrow|task_alt|verified|send/.test(iconBlob)) {
      score += 4; parts.push("svg+4");
    }
    if (/mat-mdc-button|mat-button|mdc-button|mat-raised-button|mat-flat-button|mat-primary|mdc-button--raised/.test(cls)) {
      score += 2; parts.push("material+2");
    }
    const cx = r.left + r.width / 2;
    const cy = r.top + r.height / 2;
    if (cx > vw * 0.55 && cy > vh * 0.55) { score += 3; parts.push("bottom-right+3"); }
    if (score > 0) cands.push({ score, parts, text, aria, x: Math.round(cx), y: Math.round(cy) });
  }
  cands.sort((a, b) => b.score - a.score);
  return cands.slice(0, 6);
}
"""

CLICK_JS = r"""
(text) => {
  const nodes = [...document.querySelectorAll("button, [role='button'], a, input[type='submit']")];
  const want = (text || "").trim();
  for (const el of nodes) {
    const t = (el.innerText || el.value || "").trim().replace(/\s+/g, " ");
    if (want && t === want) { el.click(); return true; }
  }
  return false;
}
"""

CHECK_JS = r"""
() => {
  const hint = /agree|accept|terms|conditions|understand|consent|acknowledge|read.and.understood|privacy|policy|\btos\b/i;
  const modal = document.querySelector("[role='dialog'], mat-dialog-container, .mat-mdc-dialog-container, .mdc-dialog, .cdk-dialog-container");
  const roots = [modal, document.scrollingElement, document.body].filter(Boolean);
  for (const node of roots) {
    if (node.scrollHeight > node.clientHeight + 8) node.scrollTop = node.scrollHeight;
  }
  document.querySelectorAll("[role='dialog'] *, mat-dialog-container *").forEach((node) => {
    if (node.scrollHeight > node.clientHeight + 20) node.scrollTop = node.scrollHeight;
  });
  const boxes = [...document.querySelectorAll("input[type='checkbox'], [role='checkbox'], [aria-checked]")];
  const seen = new Set();
  for (const el of boxes) {
    if (seen.has(el)) continue;
    seen.add(el);
    let how = "input[type=checkbox]";
    if (el.getAttribute("role") === "checkbox") how = "[role=checkbox]";
    else if (el.hasAttribute("aria-checked") && el.tagName !== "INPUT") how = "[aria-checked]";
    const id = el.id;
    let label = "";
    if (id) {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab) label += " " + lab.innerText;
    }
    const wrap = el.closest("label");
    if (wrap) label += " " + wrap.innerText;
    label += " " + (el.getAttribute("aria-label") || "");
    const by = el.getAttribute("aria-labelledby");
    if (by) by.split(/\s+/).forEach((i) => { const n = document.getElementById(i); if (n) label += " " + n.innerText; });
    if (el.parentElement) label += " " + el.parentElement.innerText;
    label = label.replace(/\s+/g, " ").trim().slice(0, 160);
    if (!hint.test(label)) continue;
    const checked = el.checked === true || el.getAttribute("aria-checked") === "true";
    if (!checked) el.click();
    return { ticked: !checked, already: checked, label, how };
  }
  return { ticked: false, label: "", how: "" };
}
"""

SIGNIN_JS = r"""
() => {
  const u = location.href || "";
  if (u.includes("accounts.google.com")) return true;
  if (document.querySelector("input[type='email'], input[type='password']")) return true;
  return false;
}
"""

TERM_JS = r"""
() => {
  const el = document.querySelector("textarea.xterm-helper-textarea, .xterm-screen, .xterm, [aria-label*='Terminal'], [aria-label*='Cloud Shell']");
  if (!el) return false;
  el.focus();
  if (typeof el.click === "function") el.click();
  return true;
}
"""

BANK = "accept|agree|continue|confirm|\\bok\\b|\\byes\\b|create|start|proceed|understand|got it|allow|enable|\\bnext\\b|i agree|begin"

def connect_first(prefer_url):
    items = targets()
    pages = [t for t in items if t.get("type") == "page" and t.get("webSocketDebuggerUrl")]
    if not pages:
        raise SystemExit("no debuggable page")
    chosen = pages[0]
    for t in pages:
        if prefer_url and prefer_url.split("?")[0] in (t.get("url") or ""):
            chosen = t
            break
    return CDP(chosen["webSocketDebuggerUrl"])

def dump(prefix, cands):
    if not cands:
        print(f"[{prefix}] no scored candidates", flush=True)
        return
    for c in cands:
        parts = "+".join(c.get("parts") or []) or "-"
        label = c.get("text") or c.get("aria") or "(blank)"
        print(f"[{prefix}] score={c.get('score')} {label} [{parts}]", flush=True)

def click_best(cdp, prefix, min_score):
    cands = eval_js(cdp, f"({POPUP_JS})({json.dumps(BANK)})") or []
    dump(prefix, cands)
    if not cands or cands[0].get("score", 0) < min_score:
        print(f"[{prefix}] nothing at or above {min_score}", flush=True)
        return False
    best = cands[0]
    clicked = eval_js(cdp, f"({CLICK_JS})({json.dumps(best.get('text') or '')})")
    if not clicked:
        x, y = best.get("x") or 0, best.get("y") or 0
        cdp.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1})
        cdp.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1})
        clicked = True
        print(f"[{prefix}] mouse fallback at {x},{y}", flush=True)
    print(f"[{prefix}] click {best.get('text')!r} total={best.get('score')} ok={clicked}", flush=True)
    return bool(clicked)

def pause(msg):
    print(msg, flush=True)
    try:
        with open("/dev/tty", "r") as tty:
            tty.readline()
    except Exception:
        input()

def prepare(url):
    cdp = connect_first(url)
    cdp.call("Page.enable")
    cdp.call("Runtime.enable")
    if url:
        try:
            cdp.call("Page.navigate", {"url": url}, timeout=20)
        except Exception as exc:
            print("navigate warning:", exc, flush=True)
    time.sleep(2)
    if eval_js(cdp, f"({SIGNIN_JS})()"):
        pause("  Sign in inside the Termux-X11 window, then press Enter here.")
    deadline = time.time() + 45
    clicked = False
    while time.time() < deadline and not clicked:
        clicked = click_best(cdp, "popup1", 6)
        if not clicked:
            time.sleep(2)
    time.sleep(3)
    deadline = time.time() + 25
    while time.time() < deadline:
        box = eval_js(cdp, f"({CHECK_JS})()") or {}
        if box.get("label"):
            print(f"[popup2] checkbox via {box.get('how')} label={box.get('label')!r} ticked={box.get('ticked')} already={box.get('already')}", flush=True)
            click_best(cdp, "popup2", 6)
            break
        time.sleep(2)
    else:
        print("[popup2] no terms checkbox found — continuing", flush=True)
    cdp.close()
    focus_terminal()

def every_socket():
    out = []
    for t in targets():
        ws = t.get("webSocketDebuggerUrl")
        if not ws:
            continue
        if t.get("type") not in ("page", "iframe", "other"):
            continue
        out.append(t)
    return out

def focus_terminal():
    deadline = time.time() + HOME_WAIT
    while time.time() < deadline:
        for t in every_socket():
            blob = f"{t.get('url','')} {t.get('title','')}"
            cdp = None
            try:
                cdp = CDP(t["webSocketDebuggerUrl"])
                cdp.call("Runtime.enable")
                found = eval_js(cdp, f"({TERM_JS})()")
            except Exception:
                found = False
            finally:
                if cdp:
                    cdp.close()
            if found:
                print("TERMINAL_READY", blob[:120], flush=True)
                return
        time.sleep(2)
    print("TERMINAL_MISSING", flush=True)
    raise SystemExit(2)

def key_combo(cdp, key, code, vk, modifiers=0):
    base = {
        "key": key, "code": code,
        "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
        "modifiers": modifiers,
    }
    cdp.call("Input.dispatchKeyEvent", {**base, "type": "keyDown"})
    cdp.call("Input.dispatchKeyEvent", {**base, "type": "keyUp"})

def type_line(path):
    line = open(path, encoding="utf-8").read().strip("\n")
    deadline = time.time() + 30
    target = None
    while time.time() < deadline and target is None:
        for t in every_socket():
            cdp = None
            try:
                cdp = CDP(t["webSocketDebuggerUrl"])
                cdp.call("Runtime.enable")
                if eval_js(cdp, f"({TERM_JS})()"):
                    target = t
                    cdp.close()
                    break
            except Exception:
                pass
            finally:
                if cdp and target is None:
                    cdp.close()
        if target is None:
            time.sleep(1)
    if target is None:
        raise SystemExit("terminal target disappeared before insert")
    cdp = CDP(target["webSocketDebuggerUrl"])
    cdp.call("Runtime.enable")
    eval_js(cdp, f"({TERM_JS})()")
    # Break a partial line, then type the whole command at once.
    key_combo(cdp, "c", "KeyC", 67, modifiers=2)
    time.sleep(0.2)
    cdp.call("Input.insertText", {"text": line})
    time.sleep(0.2)
    key_combo(cdp, "Enter", "Enter", 13, modifiers=0)
    cdp.close()
    print("INSERTED", len(line), flush=True)

def main():
    cmd = sys.argv[1]
    if cmd == "prepare":
        prepare(sys.argv[2] if len(sys.argv) > 2 else "")
    elif cmd == "type":
        type_line(sys.argv[2])
    else:
        raise SystemExit("usage: cdp.py prepare URL | type FILE")

if __name__ == "__main__":
    main()
PY
}

show_banner() {
  python3 - "$WORKDIR/result.json" << 'PY'
import json, sys
data = json.load(open(sys.argv[1]))
rows = [
    ("service", data.get("svc") or ""),
    ("region", data.get("region") or ""),
    ("target", data.get("target") or ""),
    ("protocol", data.get("protocol") or ""),
    ("engine", data.get("engine") or ""),
    ("url", data.get("url") or ""),
    ("ip", data.get("ip") or ""),
    ("uuid", data.get("uuid") or ""),
    ("path", data.get("path") or ""),
    ("password", data.get("password") or ""),
    ("sni", data.get("sni") or ""),
    ("public key", data.get("pbk") or ""),
    ("short id", data.get("sid") or ""),
]
print("")
print("  ================================================")
print("  QShell")
for k, v in rows:
    if v:
        print(f"  {k:<12} {v}")
share = data.get("share") or ""
if share:
    print("  ------------------------------------------------")
    print("  " + share)
print("  ================================================")
print("")
PY
}

save_artifacts() {
  local reply dest dir
  read -r -p "  Save QR and .txt into ~/storage/downloads? [y/N]: " reply
  case "$reply" in
    y|Y) ;;
    *) return 0 ;;
  esac
  dir="$HOME/storage/downloads"
  if [ ! -d "$dir" ]; then
    warn "~/storage/downloads is missing. Writing to $WORKDIR instead."
    echo "  If you want shared storage: termux-setup-storage"
    dir="$WORKDIR"
  fi
  dest="$dir/${SVC}"
  python3 - "$WORKDIR/result.json" "$dest" << 'PY'
import json, sys, pathlib, base64
data = json.load(open(sys.argv[1]))
stem = pathlib.Path(sys.argv[2])
share = data.get("share") or ""
text = share + "\n"
if data.get("ssh_key"):
    text += "\n# tunnel private key\n" + data["ssh_key"] + "\n"
stem.with_suffix(".txt").write_text(text)
ovpn = data.get("ovpn") or ""
if ovpn:
    try:
        stem.with_suffix(".ovpn").write_bytes(base64.b64decode(ovpn))
    except Exception:
        stem.with_suffix(".ovpn").write_text(ovpn)
print(stem.with_suffix(".txt"))
PY
  if command -v qrencode >/dev/null 2>&1; then
    local share
    share=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("share",""))' "$WORKDIR/result.json")
    if [ -n "$share" ]; then
      qrencode -t ANSIUTF8 "$share" || true
      qrencode -o "${dest}.png" "$share" || true
      echo "  QR: ${dest}.png"
    fi
  fi
}

poll_ntfy() {
  local since="$1"
  python3 - "$NOTIFY" "$PROJECT" "$since" "$WORKDIR/result.json" << 'PY'
import hashlib, json, sys, time, urllib.request
notify, project, since, dest = sys.argv[1:]
topic = hashlib.sha256(project.encode()).hexdigest()[:16]
url = notify or f"https://ntfy.sh/{topic}"
poll = url.rstrip("/") + f"/json?poll=1&since={since}"
deadline = time.time() + 15 * 60
parts = {}
meta = None
print(f"  polling {url}", flush=True)
while time.time() < deadline:
    try:
        with urllib.request.urlopen(poll, timeout=25) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        print("  poll error:", exc, flush=True)
        time.sleep(5)
        continue
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        message = event.get("message") or ""
        try:
            body = json.loads(message)
        except json.JSONDecodeError:
            continue
        if not isinstance(body, dict):
            continue
        if body.get("status") == "part":
            parts[int(body.get("index") or 0)] = body.get("data") or ""
            continue
        if body.get("svc") or body.get("status") in ("ok", "fail"):
            meta = body
    if meta and meta.get("status") in ("ok", "fail"):
        need = int(meta.get("ovpn_parts") or 0)
        if need and len(parts) < need and time.time() + 20 < deadline:
            time.sleep(2)
            if len(parts) < need:
                continue
        if need:
            meta["ovpn"] = "".join(parts[i] for i in range(1, need + 1))
        json.dump(meta, open(dest, "w"))
        print(meta.get("status"), flush=True)
        raise SystemExit(0 if meta.get("status") == "ok" else 1)
    time.sleep(5)
print("timed out waiting for ntfy", flush=True)
raise SystemExit(1)
PY
}

main() {
  umask 077
  preflight
  echo ""
  echo "  QShell"
  echo "  Paste the fallback link. A raw ssh -i command is printed, not opened."
  local raw kind project url rest
  read -r -p "  Fallback link: " raw
  rest=$(parse_link "$raw")
  kind=${rest%%$'\t'*}
  rest=${rest#*$'\t'}
  project=${rest%%$'\t'*}
  url=${rest#*$'\t'}

  if [ "$kind" = "SSH" ]; then
    echo ""
    echo "  SSH command (browser flow skipped):"
    echo "  $url"
    notify "QShell SSH" "$url"
    exit 0
  fi
  if [ "$kind" = "EMPTY" ]; then
    die "No link pasted."
  fi
  PROJECT=$project
  if [ -z "$PROJECT" ]; then
    read -r -p "  Project id: " PROJECT
  fi
  PROJECT=$(printf '%s' "$PROJECT" | tr -cd 'a-z0-9-')
  [ -n "$PROJECT" ] || die "No project id."
  if [ -z "$url" ]; then
    url="https://shell.cloud.google.com/?project=${PROJECT}&show=terminal"
  fi
  echo "  project: $PROJECT"

  if [ "$LOCAL" -eq 0 ]; then
    say "Starting Termux-X11 and Chromium"
    if ! launch_browser "$url"; then
      warn "Browser failed. Continuing in local mode."
      LOCAL=1
    else
      write_cdp
      say "Driving the page. Score lines below are the dialog clicks."
      if ! python3 "$WORKDIR/cdp.py" prepare "$url"; then
        warn "Terminal was not detected."
        read -r -p "  Continue and only print the command? [Y/n]: " reply
        case "${reply:-Y}" in
          n|N) exit 1 ;;
        esac
        LOCAL=1
      fi
    fi
  fi

  menu
  write_cloud
  write_oneline
  echo ""
  echo "  One line (also saved at $WORKDIR/oneline.txt):"
  echo ""
  cat "$WORKDIR/oneline.txt"
  echo ""

  local since
  since=$(date +%s)
  if [ "$LOCAL" -eq 0 ]; then
    say "Typing the line into Cloud Shell"
    if ! python3 "$WORKDIR/cdp.py" type "$WORKDIR/oneline.txt"; then
      warn "Insert failed. Paste the line above into the terminal yourself."
    fi
  else
    say "Local mode: paste the line into Cloud Shell, then this script will wait."
  fi
  if command -v termux-clipboard-set >/dev/null 2>&1; then
    termux-clipboard-set < "$WORKDIR/oneline.txt" || true
  fi

  say "Waiting for the deploy to call back. First Cloud Build is often about two minutes."
  if ! poll_ntfy "$since"; then
    die "No successful callback. The line is still in $WORKDIR/oneline.txt"
  fi
  show_banner
  local share result_url
  share=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("share",""))' "$WORKDIR/result.json")
  result_url=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("url",""))' "$WORKDIR/result.json")
  if [ -n "$result_url" ]; then
    notify "QShell $PROTO" "$result_url"
    if command -v termux-open-url >/dev/null 2>&1; then
      termux-open-url "$result_url" >/dev/null 2>&1 || true
    fi
  else
    notify "QShell $PROTO" "${share:-deployed}"
  fi
  save_artifacts
}

main "$@"
