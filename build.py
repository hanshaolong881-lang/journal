#!/usr/bin/env python
"""Build the journal site from markdown entries.
Usage: python build.py [password]
"""
import sys, os, json, hashlib, glob

PASSWORD = sys.argv[1] if len(sys.argv) > 1 else "tongshapai"
password_hash = hashlib.sha256(PASSWORD.encode()).hexdigest()

entries = []
for f in sorted(glob.glob("entries/*.md"), reverse=True):
    with open(f, encoding="utf-8") as fp:
        raw = fp.read().strip()
    html_parts = []
    for line in raw.split("\n"):
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

    date_str = os.path.splitext(os.path.basename(f))[0]
    content_html = "\n".join(html_parts)
    entries.append({"date": date_str, "content": content_html})

with open("template.html", encoding="utf-8") as f:
    html = f.read()

html = html.replace("{{PASSWORD_HASH}}", password_hash)
html = html.replace("{{ENTRIES}}", json.dumps(entries, ensure_ascii=False))

os.makedirs("docs", exist_ok=True)
with open("docs/index.html", "w", encoding="utf-8") as f:
    f.write(html)

print("Built " + str(len(entries)) + " entries -> docs/index.html")
print("Password: " + PASSWORD)
