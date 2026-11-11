#!/usr/bin/env python3
# repomap-managed
"""يولّد فهرس الكود التلقائي في docs/code-index.md (ملف منفصل عن repo-map.md اليدوي).
الفهرس لا يُقرأ كاملاً أبداً: يُستعمل بـGrep على اسم رمز فيرجع سطر واحد فقط، فلا يكلّف توكينز عند بدء الجلسة.
إن وُجد الملف الهدف يحدَّث ما بين علامتي repomap:auto فقط. مخرجاته ثابتة بلا طوابع زمنية
حتى لا ينتج commit إلا عند تغيّر الكود فعلاً. بدون اعتماديات: Python 3.8+ فقط.

الاستخدام: python3 tools/repomap.py [--out docs/repo-map.md] [--max-lines 450]
"""
import argparse
import os
import re
import subprocess
import sys

START = "<!-- repomap:auto:start (tools/repomap.py — لا تعدّل يدوياً) -->"
END = "<!-- repomap:auto:end -->"
SKIP_DIRS = {".git", "build", "node_modules", ".gradle", ".claude", ".idea", ".pypackages",
             "__pycache__", "dist", "out", "releases", "snapshots", "vendor", ".venv"}
SRC_EXT = {".kt", ".kts", ".java", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx",
           ".html", ".css", ".yml", ".yaml", ".json", ".xml", ".gradle", ".md", ".rules", ".sh"}
SYMBOL_EXT = {".kt", ".java", ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"}
MAX_BYTES = 600_000
MAX_SYMS = 7

KT = re.compile(r"^(?!\s)(?:@\w+(?:\([^)]*\))?\s+)*(?:(?:public|internal|data|sealed|enum|abstract|open|inline|suspend|annotation|value|tailrec|operator|infix|expect|actual)\s+)*"
                r"(class|object|interface|fun)\s+(?:<[^>]+>\s*)?([A-Za-z_][\w.]*)")
JAVA = re.compile(r"^\s{0,4}(?:public\s+|protected\s+)?(?:static\s+)?(?:final\s+)?(?:abstract\s+)?(class|interface|enum)\s+(\w+)")
PY = re.compile(r"^(?:async\s+)?(class|def)\s+([A-Za-z]\w*)")
JS = re.compile(r"^(?:export\s+)?(?:default\s+)?(?:async\s+)?(function|class)\s+(\w+)|^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?(?:\(|function)")


def files(root):
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
        paths = [p for p in out.decode("utf-8", "replace").split("\0") if p]
    except Exception:
        paths = []
        for d, dirs, fs in os.walk(root):
            dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
            paths += [os.path.relpath(os.path.join(d, f), root) for f in fs]
    keep = []
    for p in sorted(paths):
        parts = p.split("/")
        if any(x in SKIP_DIRS for x in parts[:-1]):
            continue
        if os.path.splitext(p)[1].lower() not in SRC_EXT or p == "docs/code-index.md":
            continue
        full = os.path.join(root, p)
        if os.path.isfile(full) and os.path.getsize(full) <= MAX_BYTES:
            keep.append(p)
    return keep


def symbols(path, text):
    ext = os.path.splitext(path)[1].lower()
    if ext not in SYMBOL_EXT:
        return []
    found = []
    for line in text.splitlines():
        if ext == ".kt":
            m = KT.match(line)
            name = m.group(2) if m and "private" not in line.split(m.group(1))[0] else None
        elif ext == ".java":
            m = JAVA.match(line)
            name = m.group(2) if m else None
        elif ext == ".py":
            m = PY.match(line)
            name = m.group(2) if m and not m.group(2).startswith("_") else None
        else:
            m = JS.match(line)
            name = (m.group(2) or m.group(3)) if m else None
        if name and name not in found:
            found.append(name)
    return found


def build(root, max_lines):
    rows = []
    for p in files(root):
        try:
            with open(os.path.join(root, p), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        rows.append((p, text.count("\n") + 1, symbols(p, text)))
    total = sum(r[1] for r in rows)
    big = sorted(rows, key=lambda r: -r[1])[:8]
    lines = [START, "## Code index (auto)",
             f"> {len(rows)} ملفاً · {total} سطراً. للتفاصيل: Grep باسم الرمز ثم Read بنطاق أسطر، لا تقرأ الملفات الكبيرة كاملة.",
             "> الأكبر: " + " · ".join(f"{os.path.basename(p)} {n}" for p, n, _ in big), ""]
    groups = {}
    for p, n, s in rows:
        groups.setdefault(os.path.dirname(p) or ".", []).append((os.path.basename(p), n, s))
    for d in sorted(groups):
        items = groups[d]
        lines.append(f"### {d}/")
        if len(items) > 60:
            lines.append(f"- {len(items)} ملفاً ({sum(i[1] for i in items)} سطراً) — استخدم Glob/Grep")
            continue
        for name, n, s in items:
            tail = ""
            if s:
                tail = ": " + ", ".join(s[:MAX_SYMS]) + (f" +{len(s) - MAX_SYMS}" if len(s) > MAX_SYMS else "")
            lines.append(f"- {name} ({n}){tail}")
    if len(lines) > max_lines:
        keep = lines[:4]
        for d in sorted(groups):
            items = groups[d]
            keep.append(f"- {d}/ — {len(items)} ملفاً، {sum(i[1] for i in items)} سطراً")
        lines = keep
    lines.append(END)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/code-index.md")
    ap.add_argument("--max-lines", type=int, default=450)
    ap.add_argument("--root", default=".")
    a = ap.parse_args()
    block = build(a.root, a.max_lines)
    out = os.path.join(a.root, a.out)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    old = ""
    if os.path.exists(out):
        with open(out, encoding="utf-8") as fh:
            old = fh.read()
    if START in old and END in old:
        new = old[:old.index(START)] + block + old[old.index(END) + len(END):]
    elif old:
        new = old.rstrip("\n") + "\n\n" + block + "\n"
    else:
        new = ("# code-index (يُولَّد تلقائياً — لا تقرأه كاملاً)\n\n"
               "> الاستعمال: `Grep \"اسم_الرمز\" docs/code-index.md` ثم Read بنطاق أسطر من الملف الناتج.\n\n" + block + "\n")
    if new != old:
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(new)
        print(f"repo-map updated: {a.out}")
    else:
        print("repo-map unchanged")


if __name__ == "__main__":
    sys.exit(main())
