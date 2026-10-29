#!/usr/bin/env python3
"""허브 폴더 쓰기 보호 훅 시험: python3 tests/test_hub_only_write.py

경로 판정은 Windows 꼴(nt=True)도 문자열로 시험한다. 훅 실행은 cp949 입출력으로 돌려 Windows 한국어 로캘을 흉내 낸다.
"""
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks')
sys.path.insert(0, HOOKS)
from hub_only_write import MSG, blocked  # noqa: E402
from hubpath import inside, native, norm  # noqa: E402


def W(f, cwd, tool='Write', key='file_path'):
    return {'tool_name': tool, 'tool_input': {key: f}, 'cwd': cwd}


# (이름, 막아야 하나, 훅 입력, hub_dir, CLAUDE_PROJECT_DIR)
NT = [
    ('워커가 허브 파일', True, W(r'C:\Users\Me\hub\STATUS.md', r'C:\work\repo'), r'C:\Users\Me\hub', ''),
    ('대소문자 다름', True, W(r'c:\users\me\HUB\status.md', r'C:\work\repo'), r'C:\Users\Me\hub', ''),
    ('슬래시 섞임', True, W('C:/Users/Me\\hub/agents.json', 'C:/work'), 'C:\\Users\\Me\\hub\\', ''),
    ('Git Bash 꼴 설정', True, W(r'C:\Users\Me\hub\STATUS.md', r'C:\work'), '/c/Users/Me/hub', ''),
    ('Git Bash 꼴 파일', True, W('/c/users/me/hub/x.md', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('cygdrive 꼴', True, W('/cygdrive/C/Users/Me/hub/x.md', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('.. 로 들어감', True, W(r'C:\work\..\Users\Me\hub\x.md', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('상대 경로', True, W(r'..\hub\x.md', r'C:\Users\Me\repo'), r'C:\Users\Me\hub', ''),
    ('NotebookEdit', True, W(r'C:\Users\Me\hub\n.ipynb', r'C:\work', 'NotebookEdit', 'notebook_path'), r'C:\Users\Me\hub', ''),
    ('UNC 경로', True, W(r'\\srv\share\hub\x.md', r'C:\work'), r'\\SRV\share\hub', ''),
    ('허브 자신', False, W(r'C:\Users\Me\hub\STATUS.md', r'C:\Users\Me\hub'), r'C:\Users\Me\hub', ''),
    ('허브 하위 폴더에서', False, W(r'C:\Users\Me\hub\STATUS.md', r'c:\users\me\hub\reports'), r'C:\Users\Me\hub', ''),
    ('허브가 cd 한 뒤', False, W(r'C:\Users\Me\hub\STATUS.md', r'C:\work'), r'C:\Users\Me\hub', r'C:\Users\Me\hub'),
    ('워커가 허브로 cd', True, W(r'C:\Users\Me\hub\STATUS.md', r'C:\Users\Me\hub'), r'C:\Users\Me\hub', r'C:\work'),
    ('이름만 비슷한 폴더', False, W(r'C:\Users\Me\hub2\x.md', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('다른 드라이브', False, W(r'D:\Users\Me\hub\x.md', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('허브 밖 파일', False, W(r'C:\work\a.py', r'C:\work'), r'C:\Users\Me\hub', ''),
    ('hub_dir 비어 있음', False, W(r'C:\Users\Me\hub\x.md', r'C:\work'), '', ''),
    ('파일 경로 없음', False, {'tool_name': 'Write', 'tool_input': {}, 'cwd': r'C:\work'}, r'C:\Users\Me\hub', ''),
]
POSIX = [
    ('워커가 허브 파일', True, W('/home/u/hub/STATUS.md', '/home/u/repo'), '/home/u/hub', ''),
    ('끝 슬래시 설정', True, W('/home/u/hub/a.json', '/home/u/repo'), '/home/u/hub/', ''),
    ('.. 로 들어감', True, W('/home/u/repo/../hub/a', '/home/u/repo'), '/home/u/hub', ''),
    ('허브 자신', False, W('/home/u/hub/STATUS.md', '/home/u/hub'), '/home/u/hub', ''),
    ('이름만 비슷한 폴더', False, W('/home/u/hub2/a', '/home/u/repo'), '/home/u/hub', ''),
    ('Linux 는 대소문자 구별', False, W('/home/u/HUB/a', '/home/u/repo'), '/home/u/hub', ''),
    ('Linux 는 /c 를 드라이브로 보지 않음', False, W('/c/hub/a', '/home/u/repo'), 'C:/hub', ''),
]

fail = 0
# POSIX 표는 realpath 를 쓰므로 Linux, macOS 에서만 돈다
for nt, cases in ((True, NT),) + (((False, POSIX),) if os.name != 'nt' else ()):
    for name, want, inp, hub, project in cases:
        got = blocked(inp, hub, project, nt)
        if got != want:
            fail += 1
            print('FAIL  %s %s  기대=%s 실제=%s' % ('nt' if nt else 'posix', name, want, got))
assert native('/c/Users/x', nt=True) == 'c:/Users/x' and native('/c/Users/x', nt=False) == '/c/Users/x'
assert inside(norm('C:/', nt=True), norm('C:/', nt=True)) and inside('c:/a', 'c:/')

# 훅 실행: Linux 실제 경로(심볼릭 링크 포함), 종료 코드와 UTF-8 stderr
tmp = tempfile.mkdtemp()
hub, repo = os.path.join(tmp, 'hub'), os.path.join(tmp, 'repo')
os.makedirs(hub)
os.makedirs(repo)


def run(f, project, hub_dir=hub):
    env = dict(os.environ, CLAUDE_PLUGIN_OPTION_HUB_DIR=hub_dir, CLAUDE_PROJECT_DIR=project, PYTHONIOENCODING='cp949')
    payload = json.dumps(W(f, project), ensure_ascii=False).encode('utf-8')   # Claude Code 는 UTF-8 로 보낸다
    r = subprocess.run([sys.executable, os.path.join(HOOKS, 'hub_only_write.py')], input=payload, env=env, capture_output=True)
    return r.returncode, r.stderr.decode('utf-8')


assert run(os.path.join(hub, '현황.md'), repo) == (2, MSG + '\n')
if os.name != 'nt':   # Windows 는 심볼릭 링크를 만들려면 관리자 권한이 필요하고, 훅도 링크를 풀지 않는다
    os.symlink(hub, os.path.join(repo, 'hub-link'))
    assert run(os.path.join(repo, 'hub-link', 'STATUS.md'), repo)[0] == 2, '심볼릭 링크로 들어가도 막는다'
assert run(os.path.join(hub, 'STATUS.md'), hub) == (0, '')
assert run(os.path.join(repo, 'a.py'), repo) == (0, '')
assert run(os.path.join(hub, 'STATUS.md'), repo, hub_dir='') == (0, '')

print('%d 건 실패' % fail if fail else 'ok')
sys.exit(1 if fail else 0)
