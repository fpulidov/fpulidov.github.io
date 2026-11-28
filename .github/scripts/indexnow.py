"""Tell IndexNow (Bing, Yandex, Seznam, ...) which pages a push added or changed.

Usage: python3 indexnow.py <before_sha> <after_sha> [--dry-run]

Maps changed content/*.md files to their public URLs (frontmatter `url:`,
then `slug:`, then the filename) and submits them in one request. Drafts and
deleted files are skipped. The key file is served from static/.
"""
import json
import re
import subprocess
import sys
import urllib.request

HOST = "thehiddenport.dev"
KEY = "44d279afbc50657b5a40eb3a5d958302"
ENDPOINT = "https://api.indexnow.org/indexnow"


def changed_content_files(before, after):
    if not before or set(before) == {"0"}:
        return []  # first push of a branch: nothing to diff against
    out = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=AM", before, after, "--", "content/"],
        check=True, capture_output=True, text=True,
    ).stdout
    return [p for p in out.splitlines() if p.endswith(".md")]


def frontmatter(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    fields = {}
    if m:
        for line in m.group(1).splitlines():
            kv = re.match(r'^(\w+):\s*"?([^"#]*?)"?\s*$', line)
            if kv:
                fields[kv.group(1)] = kv.group(2)
    return fields


def url_for(path):
    fm = frontmatter(path)
    if fm.get("draft", "").lower() == "true":
        return None
    name = path.rsplit("/", 1)[-1][:-3]
    if name.startswith("_index"):
        return None
    if fm.get("url"):
        return "https://%s/%s/" % (HOST, fm["url"].strip("/"))
    slug = fm.get("slug") or name
    section = path[len("content/"):].rsplit("/", 1)
    prefix = section[0] + "/" if len(section) == 2 else ""
    return "https://%s/%s%s/" % (HOST, prefix, slug)


def main():
    before, after = sys.argv[1], sys.argv[2]
    urls = sorted({u for u in map(url_for, changed_content_files(before, after)) if u})
    if not urls:
        print("IndexNow: no new or changed pages")
        return
    print("IndexNow: submitting\n  " + "\n  ".join(urls))
    if "--dry-run" in sys.argv:
        return
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": "https://%s/%s.txt" % (HOST, KEY),
        "urlList": urls,
    }).encode()
    req = urllib.request.Request(
        ENDPOINT, data=body, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("IndexNow: HTTP %s" % resp.status)


if __name__ == "__main__":
    main()
