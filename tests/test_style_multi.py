#!/usr/bin/env python3
"""2026-09-15 오탐 회귀 — 한 Bash 호출에 여러 대상 명령이 있을 때."""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "git-message-style.py")
# Claude Code 처럼 UTF-8 로 보내고, 훅 입출력 기본값은 cp949 로 두어 Windows 한국어 로캘을 흉내 낸다
ENV = dict(os.environ, PYTHONIOENCODING="cp949")

GOOD_HEREDOC = "git commit -F - <<'A'\n제목 하나 추가\n\n- 본문 하나\nA\n"
GOOD_MERGE = 'git merge --no-ff br -q -m "제목 둘 병합\n\n- 본문 둘"\n'
BAD_MERGE = 'git merge --no-ff br -q -m "병합했습니다."\n'
BAD_COMMIT = 'git commit -m "제목을 추가했다"\n'

CASES = [
    ("commit heredoc + merge -m 둘 다 정상", "ALLOW", GOOD_HEREDOC + "git checkout -q main\n" + GOOD_MERGE),
    ("commit 정상 + merge 위반", "DENY", GOOD_HEREDOC + BAD_MERGE),
    ("merge 정상 + commit 위반", "DENY", BAD_COMMIT + GOOD_MERGE),
    ("commit 둘을 && 로 이어 쓰기", "ALLOW",
     'git commit -m "제목 하나 추가" && git commit -m "제목 둘 정리"'),
    ("commit heredoc 둘", "ALLOW",
     "git commit -F - <<'A'\n첫째 제목 추가\n\n- 본문 A\nA\n"
     "git commit -F - <<'B'\n둘째 제목 정리\n\n- 본문 B\nB\n"),
    ("heredoc 하나가 위반", "DENY",
     "git commit -F - <<'A'\n첫째 제목 추가\n\n- 본문 A\nA\n"
     "git commit -F - <<'B'\n둘째 제목을 정리했다\n\n- 본문 B\nB\n"),
    ("실제로 막혔던 명령 재현", "ALLOW",
     "git add x\n"
     "git commit -q -F - <<'MSG'\n보고6 회차 DAG 과 골드 context 자산 추가\n\n"
     "- assets.py 에 GOLD_CTX 추가\n- task.py 에 3태스크 추가\nMSG\n"
     "git checkout -q main && git reset --hard origin/main -q\n"
     'git merge --no-ff br -q -m "보고6 DAG 병합\n\n- GOLD_CTX 자산으로 연쇄\n- 최초 paused"\n'),
]

fail = 0
for name, want, cmd in CASES:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}, ensure_ascii=False)
    out = subprocess.run([sys.executable, HOOK], input=payload,
                         capture_output=True, encoding="utf-8", env=ENV).stdout.strip()
    got = "DENY" if out else "ALLOW"
    if got == want:
        print("  PASS  %s" % name)
    else:
        fail += 1
        print("  FAIL  %s  기대=%s 실제=%s" % (name, want, got))
        if out:
            reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
            print("        " + reason.split("\n\n")[0].replace("\n", "\n        "))

print("\n  %d/%d" % (len(CASES) - fail, len(CASES)))
sys.exit(1 if fail else 0)
