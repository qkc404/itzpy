#!/bin/bash
# ==============================================================================
# 4N1 FAST DEPLOYER (ENVOY PRO EDITION)
# ENGINEERED BY SAEKA TOJIRP | OPTIMIZED FOR SMOOTH DEPLOYMENT
# ==============================================================================
set -euo pipefail

BOLD='\033[1m'; RESET='\033[0m'
GREEN='\033[1;32m'; RED='\033[1;31m'; CYAN='\033[1;36m'
YELLOW='\033[1;33m'; MAGENTA='\033[1;35m'; WHITE='\033[1;37m'

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
echo -e "  ${BOLD}${WHITE}4N1 FAST DEPLOYER (ENVOY PRO EDITION)${RESET}"
echo -e "  ${MAGENTA}MADE BY SAEKA TOJIRP${RESET}"
echo -e "  ${GREEN}fb.com/saekacutiee${RESET}"
echo ""

PROJECT_ID=$(gcloud config get-value project 2>/dev/null | tr -d '[:space:]')
if [ -z "$PROJECT_ID" ]; then
    echo -e "  ${RED}ERROR: No active GCP project detected. Please run 'gcloud init'.${RESET}"
    exit 1
fi
echo -e "  ${CYAN}PROJECT: ${GREEN}${PROJECT_ID}${RESET}\n"

gcloud services enable cloudbuild.googleapis.com run.googleapis.com containerregistry.googleapis.com --project="$PROJECT_ID" --quiet >/dev/null 2>&1 &
spinner $! "ENABLING REQUIRED GCP SERVICES" || true

echo -e "\n  ${CYAN}SELECT DEPLOYMENT REGION:${RESET}"
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
    echo -e "  ${YELLOW}REMOTE TOKEN UNAVAILABLE.${RESET}"
    echo -ne "  ${MAGENTA}PLEASE PASTE GITHUB TOKEN MANUALLY (Hidden): ${RESET}"
    read -r -s MANUAL_TOKEN || true
    echo "$MANUAL_TOKEN" | tr -d '\r\n[:space:]' > ~/.gh_token
    echo -e "\n\n  ${GREEN}TOKEN SAVED SECURELY.${RESET}\n"
fi

echo -ne "  ${CYAN}SERVICE NAME [envoy-proxy]: ${RESET}"
read -r INPUT_NAME || true
SERVICE_NAME=${INPUT_NAME:-envoy-proxy}

echo ""
echo -e "  ${CYAN}SELECT MODE:${RESET}"
echo -e "  ${YELLOW}1) BROWSING (1 vCPU / 2Gi)  2) STREAMING (2 vCPU / 4Gi)${RESET}"
echo -e "  ${YELLOW}3) GAMING   (4 vCPU / 8Gi)  4) ULTRA     (8 vCPU / 16Gi)${RESET}"
echo ""
echo -ne "  ${CYAN}CHOICE: ${RESET}"
read -r MODE_CHOICE || true

case "$MODE_CHOICE" in
    1) CPU="1"; RAM="2Gi"; MODE="BROWSING";;
    2) CPU="2"; RAM="4Gi"; MODE="STREAMING";;
    3) CPU="4"; RAM="8Gi"; MODE="GAMING";;
    *) CPU="8"; RAM="16Gi"; MODE="ULTRA";;
esac

# ==============================================================================
# 3. DYNAMIC WORKSPACE & ASSET GENERATION
# ==============================================================================
WORKSPACE="/tmp/${SERVICE_NAME}_deploy"

# ENHANCED: Moved trap up here so cleanup happens even if workspace prep/build fails
cleanup_routine() {
    echo -e "\n\n  ${YELLOW}⚠️ INITIATING PIPELINE CLEANUP...${RESET}"
    rm -rf "$WORKSPACE"
    rm -f "$HOME/.gh_token"
    echo -e "  ${GREEN}DEPLOYER PIPELINE DISENGAGED CLEANLY.${RESET}\n"
    exit 0
}
trap cleanup_routine INT TERM EXIT

rm -rf "$WORKSPACE" && mkdir -p "$WORKSPACE" && cd "$WORKSPACE"
echo -ne "  ${CYAN}GENERATING SERVER ASSETS...${RESET}\n"

WORKSPACE="/tmp/${SERVICE_NAME}_deploy"

cleanup_routine() {
    echo -e "\n\n  ${YELLOW}⚠️ INITIATING PIPELINE CLEANUP...${RESET}"
    rm -rf "$WORKSPACE"
    echo -e "  ${GREEN}DEPLOYER PIPELINE DISENGAGED CLEANLY.${RESET}\n"
    exit 0
}
trap cleanup_routine INT TERM EXIT

rm -rf "$WORKSPACE" && mkdir -p "$WORKSPACE" && cd "$WORKSPACE"
echo -ne "\n  ${CYAN}GENERATING ENVOY & XRAY ASSETS...${RESET}\n"

cat <<'EOF' > Dockerfile
FROM teddysun/xray:latest AS xray-bin
FROM envoyproxy/envoy:v1.31.10
COPY --from=xray-bin /usr/bin/xray /usr/local/bin/xray
RUN apt-get update && apt-get install -y ca-certificates wget netcat-openbsd && rm -rf /var/lib/apt/lists/*
COPY config.json /etc/xray.json
COPY envoy.yaml /etc/envoy/envoy.yaml
EXPOSE 8080
CMD ["/bin/sh", "-c", "/usr/local/bin/xray run -c /etc/xray.json & sleep 2 && exec envoy -c /etc/envoy/envoy.yaml --log-level warn"]
EOF

# Fetch config.json with robust fallback
curl -sL "https://raw.githubusercontent.com/qkc404/saeka-gcp-panel/main/config.json" > config.json || true
if [ ! -s config.json ]; then
    echo -e "  ${YELLOW}REMOTE CONFIG UNAVAILABLE. GENERATING LOCAL FALLBACK...${RESET}"
    cat <<'EOF' > config.json
{
  "log": {"loglevel": "warn"},
  "inbounds": [
    {
      "port": 10000, "listen": "127.0.0.1", "protocol": "trojan",
      "settings": {"clients": [{"password": "saeka"}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/saeka-tojirp"}}
    },
    {
      "port": 10003, "listen": "127.0.0.1", "protocol": "vmess",
      "settings": {"clients": [{"id": "saeka", "alterId": 0}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/vmess-saeka"}}
    },
    {
      "port": 10006, "listen": "127.0.0.1", "protocol": "vless",
      "settings": {"clients": [{"id": "saeka"}], "decryption": "none"},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/vless-saeka"}}
    },
    {
      "port": 10009, "listen": "127.0.0.1", "protocol": "shadowsocks",
      "settings": {"clients": [{"password": "saeka", "method": "aes-256-gcm"}]},
      "streamSettings": {"network": "ws", "wsSettings": {"path": "/ss-saeka"}}
    }
  ],
  "outbounds": [{"protocol": "freedom"}]
}
EOF

cat <<'EOF' > envoy.yaml
static_resources:
  listeners:
  - name: listener_0
    address:
      socket_address: { address: 0.0.0.0, port_value: 8080 }
    filter_chains:
    - filters:
      - name: envoy.filters.network.http_connection_manager
        typed_config:
          "@type": type.googleapis.com/envoy.extensions.filters.network.http_connection_manager.v3.HttpConnectionManager
          stat_prefix: ingress_http
          upgrade_configs:
          - upgrade_type: websocket
          route_config:
            name: local_route
            virtual_hosts:
            - name: backend_services
              domains: ["*"]
              routes:
              - match: { prefix: "/saeka-tojirp" }
                route: { cluster: xray_trojan }
              - match: { prefix: "/vmess-saeka" }
                route: { cluster: xray_vmess }
              - match: { prefix: "/vless-saeka" }
                route: { cluster: xray_vless }
              - match: { prefix: "/ss-saeka" }
                route: { cluster: xray_ss }
              - match: { prefix: "/" }
                direct_response: { status: 200, body: { inline_string: "QWIKLABS INSTANCE ACTIVE" } }
          http_filters:
          - name: envoy.filters.http.router
            typed_config:
              "@type": type.googleapis.com/envoy.extensions.filters.http.router.v3.Router
  clusters:
  - name: xray_trojan
    connect_timeout: 2s
    type: STRICT_DNS
    load_assignment:
      cluster_name: xray_trojan
      endpoints:
      - lb_endpoints:
        - endpoint: { address: { socket_address: { address: 127.0.0.1, port_value: 10000 } } }
  - name: xray_vmess
    connect_timeout: 2s
    type: STRICT_DNS
    load_assignment:
      cluster_name: xray_vmess
      endpoints:
      - lb_endpoints:
        - endpoint: { address: { socket_address: { address: 127.0.0.1, port_value: 10003 } } }
  - name: xray_vless
    connect_timeout: 2s
    type: STRICT_DNS
    load_assignment:
      cluster_name: xray_vless
      endpoints:
      - lb_endpoints:
        - endpoint: { address: { socket_address: { address: 127.0.0.1, port_value: 10006 } } }
  - name: xray_ss
    connect_timeout: 2s
    type: STRICT_DNS
    load_assignment:
      cluster_name: xray_ss
      endpoints:
      - lb_endpoints:
        - endpoint: { address: { socket_address: { address: 127.0.0.1, port_value: 10009 } } }
EOF

gcloud builds submit --tag "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" --project="$PROJECT_ID" --quiet > build.log 2>&1 &
if ! spinner $! "BUILDING ENVOY CONTAINER IMAGE"; then
    echo -e "\n  ${RED}BUILD FAILED. Displaying build.log:${RESET}"
    cat build.log
    exit 1
fi

gcloud run deploy "$SERVICE_NAME" \
  --image "gcr.io/${PROJECT_ID}/${SERVICE_NAME}" \
  --platform managed --region "$REGION" \
  --cpu "$CPU" --memory "$RAM" --port 8080 \
  --execution-environment=gen2 \
  --timeout 3600 \
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
echo -e "  ${CYAN}RAW HOST   ${GREEN}${SERVICE_URL}${RESET}"
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
echo -e "  ${WHITE}  VLESS LINK:${RESET}"
echo -e "  ${MAGENTA}vless://saeka@${CLEAN_HOST}:443?encryption=none&security=tls&sni=${CLEAN_HOST}&type=ws&host=${CLEAN_HOST}&path=/vless-saeka#${SERVICE_NAME}${RESET}"
echo ""

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
        echo -e "  ${GREEN}➔ HOST REGISTERED TO GLOBAL MATRIX CONTROLLER SUCCESSFULLY.${RESET}"
    fi
fi

REMAINING=3600
echo -e "  ${MAGENTA}🔮 LIVE LIFESPAN MONITOR ENGINE RUNNING${RESET}"
echo -e "  ${CYAN}  Press ${RED}[CTRL+C]${CYAN} to exit safely.${RESET}"
while [ "$REMAINING" -gt 0 ]; do
    printf "\r  ${WHITE}⏱️ NODE LIFETIME: ${RED}%02d:%02d${RESET} ${CYAN}| [CTRL+C] to exit...${RESET}" $((REMAINING/60)) $((REMAINING%60))
    sleep 1
    REMAINING=$((REMAINING - 1))
done
