#!/usr/bin/env python3
"""git-message-style 훅 회귀 테스트."""
import json
import os
import subprocess
import sys

HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "hooks", "git-message-style.py")
# Claude Code 처럼 UTF-8 로 보내고, 훅 입출력 기본값은 cp949 로 두어 Windows 한국어 로캘을 흉내 낸다
ENV = dict(os.environ, PYTHONIOENCODING="cp949")

CASES = [
    # (이름, 기대, 명령)
    ("이모지 제목", "DENY", 'git commit -m "✨ 파서 복구"'),
    ("PR 본문 이모지", "DENY", 'gh pr create --title "파서 복구" --body "\U0001f916 Generated"'),
    ("서술형 제목", "DENY", 'git commit -m "파서를 복구했습니다"'),
    ("서술형 -ㄴ다", "DENY", 'git commit -m "파서 시그니처를 복구한다"'),
    ("제목 마침표", "DENY", 'git commit -m "파서 시그니처 복구."'),
    ("본문 산문 -m 2회", "DENY",
     'git commit -m "파서 복구" -m "이 커밋은 시그니처가 빠져서 생긴 퇴행을 되돌린다"'),
    ("빈 줄 없음", "DENY", 'git commit -m "파서 복구\n- 시그니처 3종 복구"'),
    ("이모티콘", "DENY", 'git merge --no-ff -m "브랜치 병합 :)"'),
    ("ㅋㅋ", "DENY", 'git commit -m "테스트 통과ㅋㅋ"'),
    ("제목 72칸 초과", "DENY",
     'git commit -m "브론즈 파서 시그니처 3종과 sheet_all 및 data_to_eff 경로를 한꺼번에 복구하고 재적재까지 수행"'),
    ("본문 서술형 불릿", "DENY",
     'git commit -m "파서 복구" -m "- 시그니처 3종을 복구했다"'),
    ("heredoc 이모지", "DENY",
     "git commit -F - <<'EOF'\n\U0001f389 파서 복구\n\n- 퇴행 정정\nEOF"),

    ("정상 단문", "ALLOW", 'git commit -m "브론즈 파서 시그니처 3종 복구"'),
    ("정상 개조식 -m 2회", "ALLOW",
     'git commit -m "브론즈 파서 시그니처 3종 복구" '
     '-m "- xl_table 175 -> 189 퇴행 정정\n- p2_powder 700행 기준 재적용\n\n'
     'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"'),
    ("정상 영문", "ALLOW", 'git commit -m "Restore bronze parser signatures"'),
    ("정상 PR 본문", "ALLOW",
     'gh pr create --title "파서 복구" --body "## 요약\n\n- 시그니처 3종 복구\n- 중복 적재 0건\n\nGenerated with [Claude Code](https://claude.com/claude-code)"'),
    ("머지 정상", "ALLOW", 'git merge --no-ff feature/gold -m "골드 DAG 자산 연쇄 병합"'),
    ("amend no-edit", "ALLOW", "git commit --amend --no-edit"),
    ("git 아님", "ALLOW", "ls -la && cat README.md"),
    ("git status", "ALLOW", "git status --short"),
    ("URL 포함", "ALLOW", 'git commit -m "레포 경로 https://gitlab.example.com/x 로 이관"'),
    ("변수 메시지", "ALLOW", 'git commit -m "$MSG"'),
    ("화살표", "ALLOW", 'git commit -m "브론즈 -> 실버 적재 경로 정리"'),
    ("heredoc 정상", "ALLOW",
     "git commit -F - <<'EOF'\n브론즈 파서 시그니처 3종 복구\n\n- xl_table 퇴행 정정\nEOF"),
    # 오탐 회귀: 히어독 본문에 git 명령 '글자'만 들어 있는 경우
    ("문서 쓰기(글자만)", "ALLOW",
     "cat > /tmp/doc.md <<'EOF'\n훅은 git commit|merge|tag|revert 를 검사한다\n\n제목과 본문\n산문 한 문단\nEOF"),
    ("파이썬 패치 스크립트", "ALLOW",
     "python3 - <<'PY'\nimport re\npat = r\"git\\s+(commit|merge|tag|revert)\"\nprint(pat)\nPY"),
    ("문자열 안 git commit", "ALLOW", 'echo "git commit -m \'테스트했습니다.\'"'),
    ("경로에 git", "ALLOW", "ls /home/user/.claude/hooks/git-message-style.py"),
    ("&& 뒤 정상", "ALLOW", 'cd /tmp/r && git commit -m "테스트 픽스처 정리"'),
    ("&& 뒤 위반", "DENY", 'cd /tmp/r && git commit -m "테스트 픽스처를 정리했습니다"'),
    # git 전역 옵션이 끼어든 형태
    ("git -C 위반", "DENY",
     'git -C /tmp/r -c user.email=t@t -c user.name=t commit -q -m "테스트 파일을 추가했습니다."'),
    ("git -C 정상", "ALLOW", 'git -C /tmp/r commit -q -m "테스트 파일 추가"'),
    ("gh -R pr create 위반", "DENY",
     'gh -R o/r pr create --title "복구했습니다" --body "- 복구"'),
    ("git add commit-notes", "ALLOW", "git add commit-notes.md"),
    ("git log | grep commit", "ALLOW", "git log --oneline | grep commit"),
    ("git commit 없는 merge", "ALLOW", "git merge --abort"),
]


def run(cmd, tool="Bash"):
    payload = json.dumps({"tool_name": tool, "tool_input": {"command": cmd}}, ensure_ascii=False)
    out = subprocess.run(
        [sys.executable, HOOK], input=payload, capture_output=True, encoding="utf-8", env=ENV
    ).stdout.strip()
    return ("DENY", out) if out else ("ALLOW", "")


fail = 0
for name, want, cmd in CASES:
    got, out = run(cmd)
    if got == want:
        print("PASS  %s" % name)
    else:
        fail += 1
        print("FAIL  %s  기대=%s 실제=%s" % (name, want, got))
        if out:
            print("      " + out.replace("\n", "\n      ")[:600])
# Git Bash 없는 Windows 의 PowerShell 도구도 같은 규칙으로 막는다
for name, want, cmd in [("PowerShell 위반", "DENY", 'git commit -m "파서를 복구했습니다"'),
                        ("PowerShell 정상", "ALLOW", 'git commit -m "파서 시그니처 복구"')]:
    got = run(cmd, "PowerShell")[0]
    print("%s  %s" % ("PASS" if got == want else "FAIL", name))
    fail += got != want
print("\n%d/%d" % (len(CASES) + 2 - fail, len(CASES) + 2))
sys.exit(1 if fail else 0)
