#!/bin/zsh
set -eu
skill_dir="$(cd "$(dirname "$0")" && pwd)"
if command -v python3 >/dev/null 2>&1; then
  python3 "$skill_dir/scripts/install.py"
else
  print "没有找到 Python 3。可将整个 make-natural-academic-slides 文件夹放到 ~/.codex/skills。"
  exit 1
fi
print "可在 Codex 中使用：\$make-natural-academic-slides"
