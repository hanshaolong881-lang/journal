#!/usr/bin/env python
"""Build the journal site from markdown entries.
Supports multiple notes per day, separated by '---' in each file.
Usage: python build.py <password> [github_token]
"""
import sys, os, json, hashlib, glob, base64, subprocess
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "tongshapai"
REPO = "hanshaolong881-lang/journal"

# Derive AES key from password
key = hashlib.sha256(("journal-key:" + PASSWORD).encode()).digest()

def get_github_token():
    """Get token from argv, env, or git credential manager."""
    if len(sys.argv) > 2:
        return sys.argv[2]
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except:
        pass
    return ""

def encrypt_token(token):
    """Encrypt GitHub token with AES-GCM."""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, token.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def md_to_html(raw_text):
    """Convert markdown text to HTML (single note block)."""
    html_parts = []
    for line in raw_text.strip().split("\n"):
        line = line.strip()
        if not line:
            if html_parts and not html_parts[-1].endswith("</p>"):
                html_parts.append("</p>")
            continue
        if line.startswith("# "):
            html_parts.append("<h3>" + line[2:] + "</h3>")
        elif line.startswith("## "):
            html_parts.append("<h4>" + line[3:] + "</h4>")
        elif line.startswith("- "):
            if html_parts and html_parts[-1] == "</ul>":
                html_parts.pop()
            else:
                html_parts.append("<ul>")
            html_parts.append("<li>" + line[2:] + "</li>")
            html_parts.append("</ul>")
        else:
            need_open = (
                not html_parts
                or html_parts[-1].endswith("</ul>")
                or html_parts[-1].endswith("</h3>")
                or html_parts[-1].endswith("</h4>")
                or html_parts[-1].endswith("</p>")
            )
            if need_open:
                html_parts.append("<p>")
            elif not html_parts[-1].startswith("<"):
                html_parts.append("<p>")
            html_parts.append(line)
            html_parts.append("</p>")
    return "\n".join(html_parts)

github_token = get_github_token()
encrypted_token = encrypt_token(github_token) if github_token else ""
password_hash = hashlib.sha256(PASSWORD.encode()).hexdigest()

# Build entries — support multiple notes per day
entries = []
for f in sorted(glob.glob("entries/*.md"), reverse=True):
    date_str = os.path.splitext(os.path.basename(f))[0]
    with open(f, encoding="utf-8") as fp:
        raw = fp.read().strip()
    
    # Split by '---' to get multiple notes per day
    notes = [n.strip() for n in raw.split("\n---\n") if n.strip()]
    
    if len(notes) == 1:
        # Single note — same as before
        content_html = md_to_html(notes[0])
        entries.append({"date": date_str, "notes": [{"title": "", "content": content_html}]})
    else:
        # Multiple notes — each gets a title from the first # line
        note_list = []
        for note in notes:
            lines = note.split("\n")
            title = ""
            body_lines = []
            if lines and lines[0].startswith("# "):
                title = lines[0][2:]
                body_lines = lines[1:]
            else:
                body_lines = lines
            body = "\n".join(body_lines).strip()
            content_html = md_to_html(body) if body else md_to_html(note)
            note_list.append({"title": title, "content": content_html})
        entries.append({"date": date_str, "notes": note_list})

with open("template.html", encoding="utf-8") as f:
    html = f.read()

html = html.replace("HASH_PLACEHOLD...", password_hash)
html = html.replace("ENTRIES_PLACEHOLDER", json.dumps(entries, ensure_ascii=False))
html = html.replace("TOKEN_PLACEHO...", encrypted_token)
html = html.replace("{{REPO}}", REPO)

os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Built " + str(len(entries)) + " days -> docs/index.html")
print("Password: " + PASSWORD)
print("Token embedded: " + ("YES" if encrypted_token else "NO"))
