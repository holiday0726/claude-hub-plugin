#!/usr/bin/env python3
"""SessionStart 훅: 허브 폴더에서 세션이 열리면 에이전트 대시보드가 떠 있는지 보고, 꺼져 있으면 띄운다.

플러그인 설정(훅에는 CLAUDE_PLUGIN_OPTION_* 로 온다): hub_dir, dashboard_port(기본 4990), orca(기본 켬).
플러그인은 모든 세션에 붙으므로 프로젝트 폴더가 허브 폴더가 아니면 아무것도 하지 않는다.
Orca 탭 열기는 Orca 의 Settings > SSH 에서 "Allow this host's orca CLI to control Orca" 가 켜져 있어야 된다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request

from hubpath import inside, native, norm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def opt(key, default=''):
    # 설정하지 않은 값은 기본값이 있어도 환경변수로 오지 않는다(2.1.312 실측)
    return os.environ.get('CLAUDE_PLUGIN_OPTION_' + key.upper()) or default


def up(url):
    try:   # 회사 PC 의 시스템 프록시를 타지 않게 프록시 없이 연다
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url, timeout=2):
            return True
    except OSError:
        return False


def start(hub, port):
    """서버를 훅과 떼어 띄우고 로그 경로를 돌려준다. 훅의 파이프를 물려주면 Claude Code 가 훅 끝을 못 본다."""
    logs = os.environ.get('CLAUDE_PLUGIN_DATA') or tempfile.gettempdir()
    os.makedirs(logs, exist_ok=True)
    log = os.path.join(logs, 'dashboard-%d.log' % port)
    cmd = [sys.executable, os.path.join(ROOT, 'dashboard', 'server.py')]
    env = dict(os.environ, HUB_DIR=hub, PORT=str(port))
    with open(log, 'ab') as out:
        kw = dict(env=env, cwd=hub if os.path.isdir(hub) else None, stdin=subprocess.DEVNULL, stdout=out, stderr=out)
        if os.name != 'nt':
            subprocess.Popen(cmd, start_new_session=True, **kw)
            return log
        # 숨은 콘솔(CREATE_NO_WINDOW)을 주어 서버가 부르는 claude 창이 뜨지 않게 하고, 작업 객체에서 빠져나가 세션이 끝나도 살게 한다
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        try:
            subprocess.Popen(cmd, creationflags=flags | subprocess.CREATE_BREAKAWAY_FROM_JOB, **kw)
        except OSError:   # 작업 객체가 빠져나가기를 막으면 그냥 띄운다
            subprocess.Popen(cmd, creationflags=flags, **kw)
    return log


def orca_tab(url, port):
    orca = shutil.which('orca')
    if not orca:
        return ''
    try:
        tabs = subprocess.run([orca, 'tab', 'list', '--json'], capture_output=True, encoding='utf-8', errors='replace', timeout=10).stdout
        if '127.0.0.1:%d' % port in tabs:
            return ', Orca 탭이 이미 열려 있음'
        made = subprocess.run([orca, 'tab', 'create', '--url', url, '--json'], capture_output=True, encoding='utf-8', errors='replace', timeout=15).stdout
        if re.search(r'"ok":\s*true', made):
            return ', Orca 탭을 열었음'
    except (OSError, subprocess.SubprocessError):
        pass
    return ", Orca 탭 열기 실패(Orca Settings > SSH 에서 이 호스트의 'Allow this host's orca CLI to control Orca' 를 켜야 함)"


def main():
    for s in (sys.stdin, sys.stdout, sys.stderr):
        s.reconfigure(encoding='utf-8')
    try:
        inp = json.load(sys.stdin)
    except ValueError:
        inp = {}
    hub = opt('hub_dir')
    project = os.environ.get('CLAUDE_PROJECT_DIR') or inp.get('cwd') or ''
    if not hub or not project or not inside(norm(project), norm(hub)):
        return 0
    port = int(float(opt('dashboard_port', '4990')))
    url = 'http://127.0.0.1:%d' % port
    log = ''
    if not up(url + '/'):
        log = start(native(hub), port)
        for _ in range(10):
            time.sleep(0.5)
            if up(url + '/'):
                break
    msg = '대시보드 %s %s' % (url, '떠 있음' if up(url + '/') else '안 뜸(로그 %s)' % log)
    if opt('orca', 'true').lower() in ('true', '1', 'yes', 'on'):
        msg += orca_tab(url, port)
    print(json.dumps({'systemMessage': msg}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
