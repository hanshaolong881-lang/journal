#!/usr/bin/env python
"""Build the 日省 (Daily Reflection) static journal site from markdown entries.

Supports multiple notes per day separated by '---' lines.
Usage: python build.py [password] [github_token]
"""
from __future__ import annotations

import base64
import glob
import hashlib
import html as html_lib
import json
import os
import re
import subprocess
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "tongshapai"
REPO = "hanshaolong881-lang/journal"

# Derive 256-bit AES-GCM key from password
KEY = hashlib.sha256(("journal-key:" + PASSWORD).encode("utf-8")).digest()


def get_github_token() -> str:
    if len(sys.argv) > 2 and sys.argv[2].strip():
        return sys.argv[2].strip()
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token
    try:
        result = subprocess.run(
            ["git", "credential", "fill"],
            input="protocol=https\nhost=github.com\n\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in result.stdout.strip().splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def encrypt_token(token: str) -> str:
    aesgcm = AESGCM(KEY)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, token.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("ascii")


def inline_md(escaped_text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped_text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def md_to_html(raw_text: str) -> str:
    """Safe, consistent Markdown -> HTML converter matching client-side renderMarkdown()."""
    parts: list[str] = []
    para_lines: list[str] = []
    in_ul = False
    in_ol = False
    in_quote = False

    def flush_para() -> None:
        if para_lines:
            parts.append("<p>" + "<br>".join(para_lines) + "</p>")
            para_lines.clear()

    def close_lists() -> None:
        nonlocal in_ul, in_ol, in_quote
        flush_para()
        if in_ul:
            parts.append("</ul>")
            in_ul = False
        if in_ol:
            parts.append("</ol>")
            in_ol = False
        if in_quote:
            parts.append("</blockquote>")
            in_quote = False

    for raw_line in raw_text.strip().splitlines():
        line = raw_line.strip()
        if not line:
            close_lists()
            continue

        escaped = inline_md(html_lib.escape(line, quote=False))

        if line.startswith("# "):
            close_lists()
            parts.append(f"<h3>{inline_md(html_lib.escape(line[2:].strip(), quote=False))}</h3>")
        elif line.startswith("## "):
            close_lists()
            parts.append(f"<h4>{inline_md(html_lib.escape(line[3:].strip(), quote=False))}</h4>")
        elif line.startswith("> "):
            flush_para()
            if in_ul:
                parts.append("</ul>")
                in_ul = False
            if in_ol:
                parts.append("</ol>")
                in_ol = False
            if not in_quote:
                parts.append("<blockquote>")
                in_quote = True
            parts.append(f"<p>{inline_md(html_lib.escape(line[2:].strip(), quote=False))}</p>")
        elif line.startswith("- ") or line.startswith("* "):
            flush_para()
            if in_ol:
                parts.append("</ol>")
                in_ol = False
            if in_quote:
                parts.append("</blockquote>")
                in_quote = False
            if not in_ul:
                parts.append("<ul>")
                in_ul = True
            parts.append(f"<li>{inline_md(html_lib.escape(line[2:].strip(), quote=False))}</li>")
        else:
            ol_match = re.match(r"^(\d+)[\.\、]\s*(.+)$", line)
            if ol_match:
                flush_para()
                if in_ul:
                    parts.append("</ul>")
                    in_ul = False
                if in_quote:
                    parts.append("</blockquote>")
                    in_quote = False
                if not in_ol:
                    parts.append("<ol>")
                    in_ol = True
                parts.append(f"<li>{inline_md(html_lib.escape(ol_match.group(2).strip(), quote=False))}</li>")
            else:
                if in_ul or in_ol or in_quote:
                    close_lists()
                para_lines.append(escaped)

    close_lists()
    return "\n".join(parts)


def parse_entry_file(raw: str) -> list[dict[str, str]]:
    blocks = [b.strip() for b in re.split(r"\n\s*---\s*\n", raw.strip()) if b.strip()]
    note_list: list[dict[str, str]] = []
    for idx, block in enumerate(blocks):
        lines = block.splitlines()
        title = ""
        body_lines = lines
        if len(blocks) > 1 and lines and lines[0].strip().startswith("# "):
            title = lines[0].strip()[2:].strip()
            body_lines = lines[1:]
        elif len(blocks) == 1 and lines and lines[0].strip().startswith("# "):
            # Extract leading # heading as card title if there is body text beneath it
            candidate_body = "\n".join(lines[1:]).strip()
            if candidate_body:
                title = lines[0].strip()[2:].strip()
                body_lines = lines[1:]
        body = "\n".join(body_lines).strip()
        raw_body = body if body else block
        # Deduplicate accidental consecutive identical notes on the same day
        if note_list and note_list[-1]["title"] == title and note_list[-1]["raw"] == raw_body:
            continue
        note_list.append(
            {
                "title": title,
                "raw": raw_body,
                "content": md_to_html(raw_body),
            }
        )
    return note_list


def main() -> None:
    github_token = get_github_token()
    encrypted_token = encrypt_token(github_token) if github_token else ""

    if not encrypted_token and os.path.exists("docs/index.html"):
        with open("docs/index.html", encoding="utf-8") as existing:
            match = re.search(r'var\s+TOKEN\s*=\s*"([^"]*)";', existing.read())
            if match:
                encrypted_token = match.group(1)

    password_hash = hashlib.sha256(PASSWORD.encode("utf-8")).hexdigest()

    entries = []
    for path in sorted(glob.glob("entries/*.md"), reverse=True):
        date_str = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as fp:
            raw = fp.read().strip()
        if not raw:
            continue
        notes = parse_entry_file(raw)
        if notes:
            entries.append({"date": date_str, "notes": notes})

    with open("template.html", encoding="utf-8") as f:
        html = f.read()

    html = html.replace("HASH_PLACEHOLD...", password_hash)
    html = html.replace("ENTRIES_PLACEHOLDER", json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
    html = html.replace("TOKEN_PLACEHO...", encrypted_token)
    html = html.replace("{{REPO}}", REPO)

    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8", newline="\n") as f:
        f.write(html)

    total_notes = sum(len(e["notes"]) for e in entries)
    print(f"Built {len(entries)} days ({total_notes} notes) -> docs/index.html")
    print(f"Token embedded: {'YES' if encrypted_token else 'NO'}")


if __name__ == "__main__":
    main()
