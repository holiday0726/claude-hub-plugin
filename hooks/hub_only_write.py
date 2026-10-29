#!/usr/bin/env python3
"""PreToolUse 훅: 허브 폴더 아래 파일은 허브(프로젝트 폴더가 허브 폴더인 세션)만 Edit/Write 한다.

허브 폴더는 플러그인 설정 hub_dir(훅에는 CLAUDE_PLUGIN_OPTION_HUB_DIR)이다. 비어 있으면 아무것도 막지 않는다.
ponytail: Bash 로 쓰는 것(sed -i, >)은 못 막는다. 필요하면 Bash matcher 를 더한다.
"""
import json
import os
import sys

from hubpath import NT, inside, norm

MSG = '허브 폴더 파일은 허브만 고친다. 바꿀 내용은 SendMessage 로 허브 세션에 보고해라.'


def blocked(inp, hub, project='', nt=NT):
    """inp 는 훅 입력, project 는 CLAUDE_PROJECT_DIR(없으면 입력의 cwd 를 쓴다)."""
    ti = inp.get('tool_input') or {}
    f = ti.get('file_path') or ti.get('notebook_path')
    if not hub or not f:
        return False
    root = norm(hub, nt)
    cwd = inp.get('cwd') or ''
    return inside(norm(f, nt, cwd), root) and not inside(norm(project or cwd, nt), root)


def main():
    for s in (sys.stdin, sys.stdout, sys.stderr):
        s.reconfigure(encoding='utf-8')   # Windows 는 기본이 로캘 코드 페이지(cp949)
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        return 0
    if blocked(inp, os.environ.get('CLAUDE_PLUGIN_OPTION_HUB_DIR', ''), os.environ.get('CLAUDE_PROJECT_DIR', '')):
        print(MSG, file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
