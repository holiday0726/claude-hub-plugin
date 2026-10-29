#!/usr/bin/env python3
"""대시보드 열기 훅 시험: python3 tests/test_open_dashboard.py

임시 허브 폴더와 빈 포트로 훅을 실제로 돌린다. 허브 밖에서는 아무것도 띄우지 않고, 허브에서는 서버를 떼어 띄우며
(훅이 바로 끝나야 한다), 떠 있으면 다시 띄우지 않는지 본다. 띄운 서버는 로그의 pid 로만 끈다.
"""
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
HOOK = os.path.join(REPO, 'hooks', 'open_dashboard.py')

tmp = tempfile.mkdtemp()
hub, work, data = (os.path.join(tmp, d) for d in ('hub', 'work', 'data'))
shutil.copytree(os.path.join(REPO, 'templates', 'hub'), hub)
os.makedirs(work)
with socket.socket() as s:
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
url = 'http://127.0.0.1:%d' % port
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def hook(project):
    env = dict(os.environ, CLAUDE_PLUGIN_OPTION_HUB_DIR=hub, CLAUDE_PLUGIN_OPTION_DASHBOARD_PORT=str(port),
               CLAUDE_PLUGIN_OPTION_ORCA='false', CLAUDE_PROJECT_DIR=project, CLAUDE_PLUGIN_DATA=data,
               PYTHONIOENCODING='cp949')
    payload = json.dumps({'hook_event_name': 'SessionStart', 'source': 'startup', 'cwd': project}).encode()
    t = time.time()
    r = subprocess.run([sys.executable, HOOK], input=payload, env=env, capture_output=True, timeout=30)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')
    return r.stdout.decode('utf-8'), time.time() - t


def get(path):
    with opener.open(url + path, timeout=3) as r:
        return json.load(r)


out, _ = hook(work)
assert out == '', '허브 밖 세션에서는 조용히 끝나야 함: ' + out
try:
    get('/')
    raise AssertionError('허브 밖 세션이 서버를 띄웠음')
except OSError:
    pass

pid = None
try:
    out, took = hook(hub)
    msg = json.loads(out)['systemMessage']
    assert msg == '대시보드 %s 떠 있음' % url, msg
    assert took < 10, '훅이 서버 출력 파이프를 물고 기다렸음: %.1f 초' % took
    log = open(os.path.join(data, 'dashboard-%d.log' % port), encoding='utf-8').read()
    pid = int(re.search(r'pid (\d+)', log).group(1))
    st = get('/api/status')
    assert os.path.samefile(st['path'], os.path.join(hub, 'STATUS.md')), st.get('path')
    assert st['text'].startswith('# 현황판')
    assert get('/api/dev')['items'] == [] and get('/api/decisions')['error'] == ''

    out, took = hook(os.path.join(hub, 'reports'))   # 허브 하위 폴더에서 다시 열기: 떠 있으니 다시 띄우지 않는다
    assert json.loads(out)['systemMessage'].endswith('떠 있음') and took < 3, (out, took)
    assert len(re.findall(r'pid \d+', open(os.path.join(data, 'dashboard-%d.log' % port), encoding='utf-8').read())) == 1
finally:
    if pid:
        os.kill(pid, signal.SIGTERM)
    shutil.rmtree(tmp, ignore_errors=True)
print('ok')
