#!/bin/bash
# ==============================================================================
# 4N1 FAST DEPLOYER (UNIFIED SINGLE-SCRIPT EDITION)
# ENGINEERED BY SAEKA TOJIRP | OPTIMIZED FOR SMOOTH DEPLOYMENT
# ==============================================================================
set -e

BOLD='\033[1m'; RESET='\033[0m'
GREEN='\033[1;32m'; RED='\033[1;31m'; CYAN='\033[1;36m'
YELLOW='\033[1;33m'; MAGENTA='\033[1;35m'; WHITE='\033[1;37m'

loading() {
    local t="$1"
    local s="⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    for ((i=0;i<5;i++)); do 
        for ((j=0;j<${#s};j++)); do 
            echo -ne "\r  ${CYAN}${s:$j:1} ${t}...${RESET}"
            sleep 0.05
        done
    done
    echo -ne "\r  ${GREEN}DONE: ${t}${RESET}\n"
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

# Ensure required GCP APIs are enabled (prevents silent gcloud exit status 1)
loading "ENABLING REQUIRED GCP SERVICES"
gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com --project="$PROJECT_ID" --quiet >/dev/null 2>&1 || true

# ==============================================================================
# 1. INTEGRATED REGION SELECTION
# ==============================================================================
echo -e "  ${CYAN}SELECT DEPLOYMENT REGION:${RESET}"
echo -e "  ${YELLOW}1) us-central1   2) us-east1       3) us-west1${RESET}"
echo -e "  ${YELLOW}4) asia-east1    5) asia-southeast1${RESET}"
echo -e "  ${YELLOW}6) europe-west1  7) europe-west4${RESET}"
echo ""
read -r -p "$(echo -e "  ${CYAN}CHOICE [1-7]: ${RESET}")" REGION_CHOICE || true

case "$REGION_CHOICE" in
    2) REGION="us-east1";;
    3) REGION="us-west1";;
    4) REGION="asia-east1";;
    5) REGION="asia-southeast1";;
    6) REGION="europe-west1";;
    7) REGION="europe-west4";;
    *) REGION="us-central1";;
esac
echo -e "  ${GREEN}REGION SET TO: ${REGION}${RESET}\n"

# ==============================================================================
# 2. TOKEN & CONFIGURATION PROMPTS
# ==============================================================================
curl -sL "https://pastebin.com/raw/7rAmCXDp" | tr -d '\r\n[:space:]' > ~/.gh_token || true
if [ ! -s ~/.gh_token ] || ! grep -q "^gh[pousr]_" ~/.gh_token 2>/dev/null; then
    echo -e "  ${YELLOW}REMOTE TOKEN UNAVAILABLE.${RESET}"
    read -r -s -p "$(echo -e "  ${MAGENTA}PLEASE PASTE GITHUB TOKEN MANUALLY (Hidden): ${RESET}")" MANUAL_TOKEN || true
    echo "$MANUAL_TOKEN" | tr -d '\r\n[:space:]' > ~/.gh_token
    echo -e "\n  ${GREEN}TOKEN SAVED SECURELY.${RESET}\n"
fi

read -r -p "$(echo -e "  ${CYAN}SERVICE NAME [prvtspyyy]: ${RESET}")" INPUT_NAME || true
SERVICE_NAME=${INPUT_NAME:-prvtspyyy}

echo ""
echo -e "  ${CYAN}SELECT MODE:${RESET}"
echo -e "  ${YELLOW}1) BROWSING (1 vCPU / 2Gi)  2) STREAMING (2 vCPU / 4Gi)${RESET}"
echo -e "  ${YELLOW}3) GAMING   (4 vCPU / 8Gi)  4) ULTRA     (8 vCPU / 16Gi)${RESET}"
echo ""
read -r -p "$(echo -e "  ${CYAN}CHOICE: ${RESET}")" MODE_CHOICE || true

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
rm -rf "$WORKSPACE" && mkdir -p "$WORKSPACE" && cd "$WORKSPACE"
loading "GENERATING SERVER ASSETS"

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
loading "BUILDING CONTAINER IMAGE"
if ! gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" --project="$PROJECT_ID" --quiet > build.log 2>&1; then
    echo -e "\n  ${RED}BUILD FAILED. Displaying build.log:${RESET}"
    cat build.log
    exit 1
fi

loading "DEPLOYING TO CLOUD RUN IN ${REGION}"
if ! gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform managed --region "$REGION" \
  --cpu "$CPU" --memory "$RAM" --port 8080 \
  --concurrency 1000 --cpu-boost --no-cpu-throttling \
  --timeout 3600 --min-instances 1 --max-instances "$MAX_INSTANCES" \
  --allow-unauthenticated --project="$PROJECT_ID" --quiet > deploy.log 2>&1; then
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

cleanup_routine() {
    echo -e "\n\n  ${YELLOW}⚠️ INITIATING PIPELINE CLEANUP...${RESET}"
    rm -rf "$WORKSPACE"
    rm -f "$HOME/.gh_token"
    echo -e "  ${GREEN}DEPLOYER PIPELINE DISENGAGED CLEANLY.${RESET}\n"
    exit 0
}
trap cleanup_routine INT TERM EXIT

REMAINING=3600
echo -e "  ${MAGENTA}🔮 LIVE LIFESPAN MONITOR ENGINE RUNNING${RESET}"
echo -e "  ${CYAN}  Press ${RED}[CTRL+C]${CYAN} to exit safely.${RESET}"
while [ "$REMAINING" -gt 0 ]; do
    printf "\r  ${WHITE}⏱️ NODE LIFETIME: ${RED}%02d:%02d${RESET} ${CYAN}| [CTRL+C] to exit...${RESET}" $((REMAINING/60)) $((REMAINING%60))
    sleep 1
    REMAINING=$((REMAINING - 1))
done
