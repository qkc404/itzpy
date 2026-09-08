#!/bin/bash
# ==============================================================================
# 4N1 FAST DEPLOYER (UNIFIED SINGLE-SCRIPT EDITION)
# ENGINEERED BY SAEKA TOJIRP | OPTIMIZED FOR SMOOTH DEPLOYMENT
# ==============================================================================
# ENHANCED: Strict error handling
set -euo pipefail

BOLD='\033[1m'; RESET='\033[0m'
GREEN='\033[1;32m'; RED='\033[1;31m'; CYAN='\033[1;36m'
YELLOW='\033[1;33m'; MAGENTA='\033[1;35m'; WHITE='\033[1;37m'

# ENHANCED: Real asynchronous spinner that tracks background PIDs
spinner() {
    local pid=$1
    local msg=$2
    local s="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    local i=0
    while kill -0 "$pid" 2>/dev/null; do
        echo -ne "\r  ${CYAN}${s:$((i % ${#s})):1} ${msg}...${RESET}"
        i=$((i + 1))
        sleep 0.1
    done
    wait "$pid"
    if [ $? -eq 0 ]; then
        echo -ne "\r  ${GREEN}✓ DONE: ${msg}${RESET}                       \n"
    else
        echo -ne "\r  ${RED}✗ FAILED: ${msg}${RESET}                     \n"
        return 1
    fi
}

clear
echo ""
echo -e "  ${BOLD}${WHITE}4N1 FAST DEPLOYER (QWIKLABS OPTIMIZED)${RESET}"
echo -e "  ${MAGENTA}MADE BY SAEKA TOJIRP${RESET}"
echo -e "  ${GREEN}fb.com/saekacutiee${RESET}"
echo ""

PROJECT_ID=$(gcloud config get-value project 2>/dev/null | tr -d '[:space:]')
if [ -z "$PROJECT_ID" ]; then
    echo -e "  ${RED}ERROR: No active GCP project detected. Please run 'gcloud init'.${RESET}"
    exit 1
fi
echo -e "  ${CYAN}PROJECT: ${GREEN}${PROJECT_ID}${RESET}"
echo ""

# Run API enable in background and track it with the spinner
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com --project="$PROJECT_ID" --quiet >/dev/null 2>&1 &
spinner $! "ENABLING REQUIRED GCP SERVICES" || true

# ==============================================================================
# 1. INTEGRATED REGION SELECTION (QWIKLABS OPTIMIZED)
# ==============================================================================
echo -e "  ${CYAN}SELECT DEPLOYMENT REGION:${RESET}"
echo -e "  ${YELLOW} 1) 🇺🇸 us-central1 (Iowa)        2) 🇺🇸 us-east1 (S. Carolina)   3) 🇺🇸 us-east4 (N. Virginia)${RESET}"
echo -e "  ${YELLOW} 4) 🇺🇸 us-west1 (Oregon)         5) 🇺🇸 us-south1 (Dallas)       6) 🇨🇦 northamerica-northeast1 (Montreal)${RESET}"
echo -e "  ${YELLOW} 7) 🇧🇪 europe-west1 (Belgium)    8) 🇬🇧 europe-west2 (London)    9) 🇩🇪 europe-west3 (Frankfurt)${RESET}"
echo -e "  ${YELLOW}10) 🇳🇱 europe-west4 (Netherlands)11) 🇫🇷 europe-west9 (Paris)   12) 🇹🇼 asia-east1 (Taiwan)${RESET}"
echo -e "  ${YELLOW}13) 🇭🇰 asia-east2 (Hong Kong)   14) 🇸🇬 asia-southeast1 (SG)    15) 🇯🇵 asia-northeast1 (Tokyo)${RESET}"
echo -e "  ${YELLOW}16) 🇰🇷 asia-northeast3 (Seoul)  17) 🇦🇺 australia-southeast1 (Sydney)${RESET}"
echo ""

echo -ne "  ${CYAN}CHOICE [1-17]: ${RESET}"
read -r REGION_CHOICE || true

case "$REGION_CHOICE" in
    2)  REGION="us-east1";;
    3)  REGION="us-east4";;
    4)  REGION="us-west1";;
    5)  REGION="us-south1";;
    6)  REGION="northamerica-northeast1";;
    7)  REGION="europe-west1";;
    8)  REGION="europe-west2";;
    9)  REGION="europe-west3";;
    10) REGION="europe-west4";;
    11) REGION="europe-west9";;
    12) REGION="asia-east1";;
    13) REGION="asia-east2";;
    14) REGION="asia-southeast1";;
    15) REGION="asia-northeast1";;
    16) REGION="asia-northeast3";;
    17) REGION="australia-southeast1";;
    *)  REGION="us-central1";;
esac
echo -e "  ${GREEN}REGION SET TO: ${REGION}${RESET}\n"

# ==============================================================================
# 2. TOKEN & CONFIGURATION PROMPTS
# ==============================================================================
curl -sL "https://pastebin.com/raw/7rAmCXDp" | tr -d '\r\n[:space:]' > ~/.gh_token || true
if [ ! -s ~/.gh_token ] || ! grep -q "^gh[pousr]_" ~/.gh_token 2>/dev/null; then
    echo -e "  ${YELLOW}REMOTE TOKEN UNAVAILABLE.${RESET}"
    echo -ne "  ${MAGENTA}PLEASE PASTE GITHUB TOKEN MANUALLY (Hidden): ${RESET}"
    read -r -s MANUAL_TOKEN || true
    echo "$MANUAL_TOKEN" | tr -d '\r\n[:space:]' > ~/.gh_token
    echo -e "\n\n  ${GREEN}TOKEN SAVED SECURELY.${RESET}\n"
fi

echo -ne "  ${CYAN}SERVICE NAME [prvtspyyy]: ${RESET}"
read -r INPUT_NAME || true
SERVICE_NAME=${INPUT_NAME:-prvtspyyy}

echo ""
echo -e "  ${CYAN}SELECT MODE:${RESET}"
echo -e "  ${YELLOW}1) BROWSING (1 vCPU / 2Gi)  2) STREAMING (2 vCPU / 4Gi)${RESET}"
echo -e "  ${YELLOW}3) GAMING   (4 vCPU / 8Gi)  4) ULTRA     (8 vCPU / 16Gi)${RESET}"
echo ""
echo -ne "  ${CYAN}CHOICE: ${RESET}"
read -r MODE_CHOICE || true

case "$MODE_CHOICE" in
    1) CPU="1"; RAM="2Gi"; MODE="BROWSING"; MAX_INSTANCES="4";;
    2) CPU="2"; RAM="4Gi"; MODE="STREAMING"; MAX_INSTANCES="4";;
    3) CPU="4"; RAM="8Gi"; MODE="GAMING"; MAX_INSTANCES="4";;
    *) CPU="8"; RAM="16Gi"; MODE="ULTRA"; MAX_INSTANCES="4";;
esac

# ==============================================================================
# 3. DYNAMIC WORKSPACE & ASSET GENERATION
# ==============================================================================
WORKSPACE="/tmp/${SERVICE_NAME}_deploy"

# ENHANCED: Moved trap up here so cleanup happens even if workspace prep/build fails
cleanup_routine() {
    echo -e "\n\n  ${YELLOW}⚠️ INITIATING PIPELINE CLEANUP...${RESET}"
    rm -rf "$WORKSPACE"
    rm -f "$HOME/.gh_token"
    echo -e "  ${GREEN}DEPLOYER PIPELINE DISENGAGED CLEANLY.${RESET}\n"
    exit 0
}
trap cleanup_routine INT TERM EXIT

rm -rf "$WORKSPACE" && mkdir -p "$WORKSPACE" && cd "$WORKSPACE"
echo -ne "  ${CYAN}GENERATING SERVER ASSETS...${RESET}\n"

# Generate Dockerfile
cat <<'EOF' > Dockerfile
FROM openresty/openresty:alpine
RUN apk add --no-cache ca-certificates wget unzip netcat-openbsd
RUN wget -qO /tmp/xray.zip https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip && \
    unzip -p /tmp/xray.zip xray > /usr/local/bin/xray && \
    chmod +x /usr/local/bin/xray && rm -rf /tmp/xray.zip
COPY config.json /etc/xray.json
COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY index.html /usr/local/openresty/nginx/html/index.html
EXPOSE 8080
CMD /usr/local/bin/xray run -c /etc/xray.json & exec /usr/local/openresty/bin/openresty -g "daemon off;"
EOF

# Fetch config.json with robust fallback
curl -sL "https://raw.githubusercontent.com/qkc404/saeka-gcp-panel/main/config.json" > config.json || true
if [ ! -s config.json ]; then
cat <<'EOF' > config.json
{
  "log": {"loglevel": "none"},
  "dns": {
    "servers": ["8.8.8.8", "1.1.1.1"],
    "queryStrategy": "UseIPv4",
    "hosts": {
      "pagead2.googlesyndication.com": "127.0.0.1",
      "googlesyndication.com": "127.0.0.1",
      "googleadservices.com": "127.0.0.1",
      "youtube-nocookie.com": "127.0.0.1"
    }
  },
  "inbounds": [
    {
      "port": 10000, "listen": "127.0.0.1", "protocol": "trojan", "tag": "trojan-ws",
      "settings": {"clients": [{"password": "saeka"}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/saeka-tojirp"}, "sockopt": {"tcpFastOpen": true, "tcpNoDelay": true, "tcpKeepAliveInterval": 15}},
      "sniffing": {"enabled": true, "destOverride": ["http", "tls"]}
    },
    {
      "port": 10003, "listen": "127.0.0.1", "protocol": "vmess", "tag": "vmess-ws",
      "settings": {"clients": [{"id": "saeka", "alterId": 0}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/vmess-saeka"}, "sockopt": {"tcpFastOpen": true, "tcpNoDelay": true, "tcpKeepAliveInterval": 15}},
      "sniffing": {"enabled": true, "destOverride": ["http", "tls"]}
    },
    {
      "port": 10006, "listen": "127.0.0.1", "protocol": "vless", "tag": "vless-ws",
      "settings": {"clients": [{"id": "saeka"}], "decryption": "none"},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/vless-saeka"}, "sockopt": {"tcpFastOpen": true, "tcpNoDelay": true, "tcpKeepAliveInterval": 15}},
      "sniffing": {"enabled": true, "destOverride": ["http", "tls"]}
    },
    {
      "port": 10009, "listen": "127.0.0.1", "protocol": "shadowsocks", "tag": "ss-ws",
      "settings": {"clients": [{"password": "saeka", "method": "aes-256-gcm"}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/ss-saeka"}, "sockopt": {"tcpFastOpen": true, "tcpNoDelay": true, "tcpKeepAliveInterval": 15}}
    }
  ],
  "outbounds": [{"protocol": "freedom", "tag": "direct"}, {"protocol": "blackhole", "tag": "block"}],
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [{"type": "field", "inboundTag": ["trojan-ws", "vmess-ws", "vless-ws", "ss-ws"], "outboundTag": "direct"}]
  }
}
EOF
fi

# Generate nginx.conf
cat <<'EOF' > nginx.conf
worker_processes auto;
worker_rlimit_nofile 65535;
events { worker_connections 16384; multi_accept on; use epoll; }
http {
    include mime.types; default_type application/octet-stream;
    sendfile on; tcp_nopush on; tcp_nodelay on;
    keepalive_timeout 65; keepalive_requests 10000;
    server_tokens off; resolver 8.8.8.8 1.1.1.1 valid=300s;
    
    map $http_upgrade $connection_upgrade {
        default upgrade; '' close;
    }

    server {
        listen 8080 default_server backlog=4096;
        server_name _;
        location = /health { return 200 "OK"; add_header Content-Type text/plain; access_log off; }
        location = / { root /usr/local/openresty/nginx/html; index index.html; access_log off; }

        location /saeka-tojirp {
            proxy_pass http://127.0.0.1:10000;
            proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host; proxy_socket_keepalive on;
        }
        location /vmess-saeka {
            proxy_pass http://127.0.0.1:10003;
            proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host; proxy_socket_keepalive on;
        }
        location /vless-saeka {
            proxy_pass http://127.0.0.1:10006;
            proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host; proxy_socket_keepalive on;
        }
        location /ss-saeka {
            proxy_pass http://127.0.0.1:10009;
            proxy_http_version 1.1; proxy_set_header Upgrade $http_upgrade; proxy_set_header Connection $connection_upgrade;
            proxy_set_header Host $host; proxy_socket_keepalive on;
        }
    }
}
EOF

# Generate index.html
cat <<'EOF' > index.html
<!DOCTYPE html><html><head><title>LAB EXPIRATION</title></head>
<body style="background:#000; color:#0f0; font-family:monospace; text-align:center; padding-top:100px;">
    <h1>QWIKLABS INSTANCE ACTIVE</h1>
    <h2 id="timer">HOST DURATION: 05:00:00</h2>
    <script>
        let s=18000;
        setInterval(()=>{ s--; let h=Math.floor(s/3600),m=Math.floor((s%3600)/60),sec=s%60;
        document.getElementById('timer').innerText=`HOST DURATION: 0${h}:${m<10?'0'+m:m}:${sec<10?'0'+sec:sec}`;},1000);
    </script>
</body></html>
EOF

# ==============================================================================
# 4. DEPLOYMENT TO GOOGLE CLOUD
# ==============================================================================
gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" --project="$PROJECT_ID" --quiet > build.log 2>&1 &
if ! spinner $! "BUILDING CONTAINER IMAGE"; then
    echo -e "\n  ${RED}BUILD FAILED. Displaying build.log:${RESET}"
    cat build.log
    exit 1
fi

gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform managed --region "$REGION" \
  --cpu "$CPU" --memory "$RAM" --port 8080 \
  --concurrency 1000 --cpu-boost --no-cpu-throttling \
  --timeout 3600 --min-instances 1 --max-instances "$MAX_INSTANCES" \
  --allow-unauthenticated --project="$PROJECT_ID" --quiet > deploy.log 2>&1 &

if ! spinner $! "DEPLOYING TO CLOUD RUN IN ${REGION}"; then
    echo -e "\n  ${RED}DEPLOYMENT FAILED. Displaying deploy.log:${RESET}"
    cat deploy.log
    exit 1
fi

SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region "$REGION" --project="$PROJECT_ID" --format='value(status.url)' 2>/dev/null || true)
CLEAN_HOST=$(echo "$SERVICE_URL" | sed 's|https://||')

echo ""
echo -e "  ${GREEN} (⁠ ⁠ꈍ⁠ᴗ⁠ꈍ⁠) DEPLOYED SUCCESSFULLY${RESET}"
echo -e "  ${CYAN}RAW HOST   ${GREEN}https://${CLEAN_HOST}${RESET}"
echo -e "  ${CYAN}MODE       ${GREEN}${MODE} (${CPU} CPU / ${RAM})${RESET}"
echo ""
echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "  ${CYAN}  PROTOCOL     | WS PATH            ${RESET}"
echo -e "  ${YELLOW}  ──────────────────────────────────────────────────────────────${RESET}"
echo -e "  ${GREEN}  VLESS${RESET}        | ${CYAN}/vless-saeka${RESET}"
echo -e "  ${GREEN}  VMess${RESET}        | ${CYAN}/vmess-saeka${RESET}"
echo -e "  ${GREEN}  TROJAN${RESET}       | ${CYAN}/saeka-tojirp${RESET}"
echo -e "  ${GREEN}  Shadowsocks${RESET}  | ${CYAN}/ss-saeka${RESET}"
echo -e "  ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"

# ==============================================================================
# 5. LIFESPAN MONITOR & GITHUB TRACKER
# ==============================================================================
if [ -s "$HOME/.gh_token" ] && [ -n "$CLEAN_HOST" ]; then
    LOCAL_GH_TOKEN=$(cat "$HOME/.gh_token")
    git clone -q "https://${LOCAL_GH_TOKEN}@github.com/qkc404/saeka-gcp-panel.git" gh_temp_deploy >/dev/null 2>&1 || true
    if [ -d "gh_temp_deploy" ]; then
        cd gh_temp_deploy
        touch host.txt
        if ! grep -q -Fx "$CLEAN_HOST" host.txt 2>/dev/null; then 
            echo "$CLEAN_HOST" >> host.txt
            git config user.name "Saeka Deployer" && git config user.email "deploy@saekacutiee.local"
            git add host.txt
            git commit -m "🚀 Auto-Deploy: Appended ${CLEAN_HOST}" >/dev/null 2>&1 || true
            git push -q origin main >/dev/null 2>&1 || true
        fi
        cd .. && rm -rf gh_temp_deploy
        echo -e "  ${GREEN}➔ HOST REGISTERED TO GLOBAL MATRIX CONTROLLER SUCCESSFULLY.${RESET}"
    fi
fi

REMAINING=3600
echo -e "  ${MAGENTA}🔮 LIVE LIFESPAN MONITOR ENGINE RUNNING${RESET}"
echo -e "  ${CYAN}  Press ${RED}[CTRL+C]${CYAN} to exit safely.${RESET}"
while [ "$REMAINING" -gt 0 ]; do
    printf "\r  ${WHITE}⏱️ NODE LIFETIME: ${RED}%02d:%02d${RESET} ${CYAN}| [CTRL+C] to exit...${RESET}" $((REMAINING/60)) $((REMAINING%60))
    sleep 1
    REMAINING=$((REMAINING - 1))
done
