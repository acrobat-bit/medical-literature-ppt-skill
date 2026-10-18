#!/usr/bin/env python3
"""Install this skill locally without overwriting a user's different version."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import tempfile

SOURCE = Path(__file__).resolve().parents[1]
NAME = "make-natural-academic-slides"
def inventory(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc' and p.name != '.DS_Store'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills')
    args=parser.parse_args()
    root=args.root.expanduser().resolve();dest=root/NAME
    if dest.exists():
        if inventory(dest)==inventory(SOURCE):
            print(f'已安装且文件一致：{dest}');return
        raise SystemExit(f'未覆盖已有技能：{dest}\n请先保留旧版，或用 --root 指定另一个技能目录。')
    root.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.install-',dir=root))
    try:
        shutil.copytree(SOURCE,stage/NAME,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
        os.rename(stage/NAME,dest)
    finally:
        shutil.rmtree(stage,ignore_errors=True)
    if inventory(SOURCE)!=inventory(dest):raise SystemExit('安装文件校验不一致，请检查目标目录。')
    print(f'安装完成并已核对文件：{dest}')

if __name__=='__main__':main()
