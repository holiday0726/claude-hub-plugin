#!/usr/bin/env python3
"""PreToolUse 훅 - git 커밋/머지/태그, gh pr 문구의 작성 규칙 검사.

규칙
- 이모지/이모티콘 금지
- 제목: 72칸 이하, 끝 마침표 없음
- 본문: 개조식(불릿), 서술형 종결어미 금지
- 제목과 본문 사이 빈 줄 1개

해제: CLAUDE_GIT_STYLE=off
"""
import json
import os
import re
import shlex
import sys
import unicodedata

SUBJECT_MAX = 72
BULLET_MAX = 100

# 히어독 본문은 명령이 아니다. 대상 판정 전에 걷어낸다.
HEREDOC = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1\r?\n(.*?)\r?\n[ \t]*\2\b", re.S
)

# 명령 위치(줄머리, ;, &&, ||, |, (, `, $( 뒤)에 있는 git/gh 만 대상으로 본다.
TARGET = re.compile(
    r"(?:\A|[\n;&|(`]|\$\(|\bthen\b|\bdo\b|\belse\b)[ \t]*"
    r"(?:[A-Za-z_][A-Za-z0-9_]*=\S*[ \t]+)*"
    r"(?:git[ \t]+(?:[^\s;&|<>\n]+[ \t]+)*?(?P<git>commit|merge|tag|revert)(?![-\w])"
    r"|gh[ \t]+(?:[^\s;&|<>\n]+[ \t]+)*?pr[ \t]+(?P<pr>create|edit)(?![-\w])"
    r"|gh[ \t]+release[ \t]+create(?![-\w]))"
)

EMOJI = re.compile(
    "["
    "\U0001f000-\U0001faff"
    "\U0001f100-\U0001f1ff"
    "☀-⛿"
    "✀-➿"
    "⬀-⯿"
    "️‍⃣"
    "]"
)
EMOTICON = re.compile(
    r"(?<!\S)(?::-?[)(DPp]|;-?\)|:-?\(|XD|T_T|orz|\^\^)(?!\S)"
)
CHAT_JAMO = re.compile(r"[ㅋㅎㅠㅜ]{2,}")  # ㅋㅋ ㅎㅎ ㅠㅠ ㅜㅜ
NARRATIVE = re.compile(r"(?:[가-힣]다|해요|예요|에요)[.!?]?$")

BULLET = re.compile(r"^\s*(?:[-*•·]\s+|\d+[.)]\s+)")
TRAILER = re.compile(r"^[A-Za-z][A-Za-z0-9-]*:\s")
MD_BLOCK = re.compile(r"^\s*(?:#{1,6}\s|>|\||```|---$|===)")
ATTRIBUTION = re.compile(
    r"^(?:Generated with|Claude-Session|Co-Authored-By|Co-authored-by|Refs|See also)\b"
)


def width(text):
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


def split_targets(cmd):
    """대상 명령을 하나씩 (조각, 그 조각이 여는 heredoc 본문) 으로 나눈다.

    한 Bash 호출에 `git commit -F -` 와 `git merge -m ...` 이 함께 있으면 예전에는
    두 메시지를 문단으로 합쳐 검사해 머지 제목을 본문으로 오해했다. 명령 단위로 갈라야
    각 메시지가 자기 제목을 갖는다.
    """
    bodies = {m.group(2): m.group(3) for m in HEREDOC.finditer(cmd)}
    scan = HEREDOC.sub(lambda m: "<<%s\n%s" % (m.group(2), m.group(2)), cmd)
    hits = list(TARGET.finditer(scan))
    out = []
    for i, hit in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(scan)
        piece = scan[hit.start():end]
        names = re.findall(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)", piece)
        out.append((hit, piece, [bodies[n] for n in names if n in bodies]))
    return out


def flag_values(cmd):
    """-m/--message/-F/--file/--title/--body/--body-file 값을 뽑는다."""
    try:
        tokens = shlex.split(cmd, comments=False)
    except ValueError:
        tokens = []
        pat = r"(?:-m|--message|--body|--title)[= ]\s*'([^']*)'|(?:-m|--message|--body|--title)[= ]\s*\"([^\"]*)\""
        for m in re.finditer(pat, cmd):
            tokens.extend(["-m", m.group(1) or m.group(2) or ""])

    inline = {"-m", "--message", "--body", "--title"}
    fromfile = {"-F", "--file", "--body-file"}
    found = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        kind = None
        val = None
        for name in sorted(inline | fromfile, key=len, reverse=True):
            if tok == name:
                val = tokens[i + 1] if i + 1 < len(tokens) else None
                kind, i = name, i + 1
                break
            if tok.startswith(name + "="):
                val, kind = tok[len(name) + 1:], name
                break
        if kind is None and re.fullmatch(r"-[a-zA-Z]*m", tok):
            val = tokens[i + 1] if i + 1 < len(tokens) else None
            kind, i = "-m", i + 1
        if kind and val and val != "-":
            if kind in fromfile:
                try:
                    with open(val, encoding="utf-8") as fh:
                        val = fh.read()
                except OSError:
                    val = None
            if val:
                found.append((kind, val))
        i += 1
    return found


def check(text, kind, issues):
    lines = text.replace("\r\n", "\n").split("\n")
    if kind == "-m":
        lines = [ln for ln in lines if not ln.startswith("#")]

    for ln in lines:
        if EMOJI.search(ln) or EMOTICON.search(ln) or CHAT_JAMO.search(ln):
            issues.append("이모지/이모티콘 사용: %s" % ln.strip()[:60])

    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines):
        return
    subject = lines[start].strip()

    if width(subject) > SUBJECT_MAX:
        issues.append("제목 %d칸, %d칸 초과: %s" % (width(subject), SUBJECT_MAX, subject[:60]))
    if subject.endswith((".", "。")):
        issues.append("제목 끝 마침표: %s" % subject[:60])
    if NARRATIVE.search(subject):
        issues.append("제목이 서술형: %s" % subject[:60])

    rest = lines[start + 1:]
    if rest and rest[0].strip():
        issues.append("제목과 본문 사이 빈 줄 없음")

    fence = False
    for ln in rest:
        stripped = ln.strip()
        if stripped.startswith("```"):
            fence = not fence
            continue
        if fence or not stripped:
            continue
        if TRAILER.match(stripped) or ATTRIBUTION.match(stripped):
            continue
        if kind == "pr-body" and MD_BLOCK.match(ln):
            continue
        if BULLET.match(ln):
            if width(stripped) > BULLET_MAX:
                issues.append("항목 %d칸, %d칸 초과: %s" % (width(stripped), BULLET_MAX, stripped[:60]))
        elif ln.startswith((" ", "\t")):
            continue
        else:
            issues.append("본문이 개조식(불릿)이 아님: %s" % stripped[:60])
        if NARRATIVE.search(stripped):
            issues.append("서술형 종결어미: %s" % stripped[:60])


RULES = """문구 규칙
- 개조식으로 쓴다. 본문 각 줄은 '- ' 로 시작한다
- 이모지, 이모티콘을 쓰지 않는다
- 제목은 72칸 이하, 끝에 마침표를 붙이지 않는다
- 제목과 본문 사이에 빈 줄 1개를 둔다
- 종결어미('~했습니다', '~한다')를 쓰지 않고 명사형('추가', '수정', '반영')으로 끝낸다
- 한 항목은 한 가지 사실만 담고 100칸을 넘기지 않는다

예시
  브론즈 파서 시그니처 3종 복구

  - 관리손익 시그니처 누락으로 xl_table 189 -> 175 퇴행하던 것 정정
  - p2_powder 700행 기준 재적용
  - 재실행 시 중복 적재 없음 확인"""


def main():
    if os.environ.get("CLAUDE_GIT_STYLE", "").lower() == "off":
        return 0
    for s in (sys.stdin, sys.stdout, sys.stderr):
        s.reconfigure(encoding="utf-8")  # Windows 는 기본이 로캘 코드 페이지(cp949)
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    # Git Bash 가 없는 Windows 에서는 셸 도구가 PowerShell 이다
    if payload.get("tool_name") not in (None, "Bash", "PowerShell"):
        return 0
    cmd = (payload.get("tool_input") or {}).get("command") or ""

    targets = split_targets(cmd)
    if not targets:
        return 0

    issues = []
    seen = set()
    for hit, piece, bodies in targets:
        is_pr = bool(hit.group("pr")) or "gh release create" in piece
        raw = [("-m", b) for b in bodies] + flag_values(piece)
        if not raw:
            continue
        # git 은 한 명령에서 -m 을 여러 번 주면 문단으로 이어 붙인다.
        paras = [v for k, v in raw if k in ("-m", "--message")]
        messages = []
        if paras:
            if is_pr:
                messages += [(k, v) for k, v in raw if k in ("-m", "--message")]
            else:
                messages.append(("-m", "\n\n".join(paras)))
        messages += [(k, v) for k, v in raw if k not in ("-m", "--message")]
        for kind, text in messages:
            if text in seen:
                continue
            seen.add(text)
            eff = kind
            if is_pr and kind in ("--body", "--body-file", "-F", "--file"):
                eff = "pr-body"
            check(text, eff, issues)

    if not issues:
        return 0

    dedup = list(dict.fromkeys(issues))
    reason = "커밋/머지 문구 규칙 위반:\n" + "\n".join("- " + i for i in dedup[:10]) + "\n\n" + RULES
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
        ensure_ascii=False,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
