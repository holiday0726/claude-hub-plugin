# agent-hub

허브와 슈퍼바이저 체계를 Claude Code 플러그인 하나로 묶은 저장소다. 허브 세션이 여러 작업 세션에 일을 나눠 맡기고 보고를 받아 기록하는 방식(허브 폴더의 `CLAUDE.md`, `COORDINATION.md`)과, 그걸 돕는 대시보드, 훅, 스킬이 들어 있다. 저장소가 그대로 로컬 마켓플레이스이기도 해서 `claude plugin marketplace add <이 폴더>` 로 붙인다.

## 들어 있는 것

| 구성 | 위치 | 하는 일 |
|---|---|---|
| 대시보드 | `dashboard/` | 떠 있는 Claude Code, Codex 세션과 허브 폴더의 `agents.json`, `decisions.json`, `STATUS.md`, `dev-occupancy.json` 을 읽기만 하는 로컬 화면. Python 표준 라이브러리만 쓴다. 화면 설명은 [dashboard/README.md](dashboard/README.md) |
| 훅: 대시보드 열기 | `hooks/open_dashboard.py` | SessionStart. 프로젝트 폴더가 허브 폴더일 때만 대시보드를 확인하고, 꺼져 있으면 띄운다. `orca` 설정이 켜져 있고 `orca` 명령이 있으면 Orca 탭으로 연다 |
| 훅: 허브 폴더 쓰기 보호 | `hooks/hub_only_write.py` | PreToolUse(Edit, Write, NotebookEdit). 프로젝트 폴더가 허브 폴더 밖인 세션이 허브 폴더 파일을 고치려 하면 막는다 |
| 훅: git 문구 검사 | `hooks/git-message-style.py` | PreToolUse(Bash, PowerShell). git commit, merge, tag, revert 와 gh pr create, edit 문구가 개조식 규칙을 어기면 막는다. `CLAUDE_GIT_STYLE=off` 로 잠시 끈다 |
| 스킬 | `skills/humanizer`, `skills/git-message` | `/agent-hub:humanizer`, `/agent-hub:git-message`. humanizer 는 blader/humanizer(MIT)를 고치지 않고 넣었다 |
| 허브 규칙 틀 | `templates/hub/` | 범용 `CLAUDE.md`, `COORDINATION.md`, `STATUS.md` 와 빈 `agents.json`, `decisions.json`, `dev-occupancy.json` |
| 설정 예시 | `examples/` | 플러그인이 대신 넣어 줄 수 없는 설정(권한, 모델, 슈퍼바이저 설정) |
| 시험 | `tests/`, `dashboard/test_server.py` | 아래 "시험" 절 |

훅은 모두 Python 으로 돌고, `hooks/hooks.json` 은 셸을 거치지 않는 exec 형식이다(`command` 가 설정값 `python`, `args` 가 스크립트 경로). 그래서 Windows 에서 훅을 Git Bash 가 돌리든 PowerShell 이 돌리든 같게 동작한다.

## 플러그인 설정값

설치할 때 `--config 키=값` 으로 주거나, 나중에 `claude plugin configure agent-hub@agent-hub` 또는 세션 안 `/plugin configure agent-hub@agent-hub` 로 바꾼다.

| 키 | 필수 | 뜻 | 설정 안 하면 |
|---|---|---|---|
| `python` | 예 | 훅을 돌릴 Python 3 명령. Linux 와 macOS 는 `python3`, Windows 는 `python.exe` 절대 경로(아래 "설치" 절)를 권장한다 | 훅 셋이 모두 "Plugin option python isn't set" 오류로 돌지 않는다 |
| `hub_dir` | 예 | 허브 폴더 절대 경로. Windows 는 `C:/Users/<나>/hub` 처럼 `/` 로 쓴다 | 대시보드 훅과 쓰기 보호 훅이 아무것도 하지 않는다 |
| `dashboard_port` | 아니오 | 대시보드 포트(127.0.0.1) | 4990 |
| `orca` | 아니오 | Orca 탭 열기 | 켜짐(`orca` 명령이 없으면 그냥 건너뜀) |

`claude plugin install` 은 묻지 않으므로 `python` 과 `hub_dir` 는 꼭 `--config` 로 준다. 포트와 Orca 는 훅이 스스로 기본값을 쓴다(Claude Code 2.1.312 에서 설정하지 않은 값은 매니페스트에 기본값이 있어도 훅에 전달되지 않는 것을 확인했다).

## 받기

GitHub 에서 clone 한다. 아래 예시는 Windows PowerShell 에서 `C:\Users\<나>\claude-hub-plugin` 에 둔다.

```powershell
cd $HOME
git clone https://github.com/holiday0726/claude-hub-plugin.git
```

- `.gitattributes` 가 스크립트를 LF 로 고정하므로 git 의 `core.autocrlf` 설정과 관계없이 그대로 받아진다.
- 로컬 경로 마켓플레이스는 플러그인을 캐시로 복사하지 않고 이 폴더를 그대로 읽는다. 설치한 뒤 이 폴더를 옮기거나 지우면 플러그인이 깨진다. 새 판으로 바꿀 때는 이 폴더에서 `git pull` 하고 세션을 다시 열거나 `/reload-plugins` 를 한다.

### 대안: 인터넷이 안 되는 PC 로 묶어 옮기기

저장소가 있는 곳에서 main 을 둘 중 하나로 묶는다.

```sh
cd claude-hub-plugin          # main 이 꺼내져 있는 폴더
git bundle create ../agent-hub.bundle HEAD main          # git 이력까지
git archive --format=zip -o ../agent-hub.zip main        # 파일만
```

- bundle 에 `HEAD` 를 같이 넣어야 받는 쪽이 브랜치 이름 없이 clone 해도 main 을 꺼낸다.
- 같은 커밋을 가리키는 브랜치를 더 넣으면 받는 쪽 git 이 그중 이름순으로 앞선 것을 꺼낼 수 있다(git 2.43, 받는 쪽 `init.defaultBranch` 가 없을 때 확인). 그래서 main 하나만 넣는다.

파일을 옮긴 뒤(scp, WinSCP 등) PowerShell 에서 푼다.

```powershell
cd $HOME
git clone agent-hub.bundle claude-hub-plugin                       # bundle 이면, main 이 꺼내진다
Expand-Archive agent-hub.zip -DestinationPath claude-hub-plugin    # zip 이면
```

## 설치

Python 3.8 이상과 Claude Code 가 있어야 한다. 훅은 셸 없이 `python` 설정값을 그대로 실행하므로, Windows 에서는 PATH 찾기와 Microsoft Store 의 가짜 `python3` 바로가기를 피하려고 `python.exe` 절대 경로를 쓴다.

```powershell
py -3 -c "import sys; print(sys.executable)"      # py 런처가 없으면: python -c "import sys; print(sys.executable)"
# 예: C:\Users\<나>\AppData\Local\Programs\Python\Python312\python.exe  ->  역슬래시를 / 로 바꿔 쓴다
```

마켓플레이스를 붙이고 설치한다. 경로는 모두 `/` 로 쓴다. 경로에 빈칸이 있으면 `"python=C:/Program Files/Python312/python.exe"` 처럼 통째로 따옴표로 묶는다.

```powershell
claude plugin marketplace add C:/Users/<나>/claude-hub-plugin
claude plugin install agent-hub@agent-hub --config python=C:/Users/<나>/AppData/Local/Programs/Python/Python312/python.exe --config hub_dir=C:/Users/<나>/hub
claude plugin details agent-hub@agent-hub     # Skills (2), Hooks (2) 가 보이면 됨
```

- 포트를 바꾸려면 `--config dashboard_port=4991`, Orca 탭을 끄려면 `--config orca=false` 를 더한다.
- 사용자 범위(`--scope user`, 기본)로 설치해야 쓰기 보호 훅이 모든 세션에 걸린다.
- 세션 안에서 하려면 `/plugin marketplace add C:/Users/<나>/claude-hub-plugin`, `/plugin install agent-hub@agent-hub` 뒤 `/plugin configure agent-hub@agent-hub` 창에서 `python` 과 `hub_dir` 를 넣는다. `python` 칸에는 위에서 얻은 `python.exe` 경로를 넣는다.
- `python=py` 도 될 수 있지만, 셸 없이 실행할 때 `py` 를 PATH 에서 찾는지는 Windows 에서 확인하지 못했다.

## 허브 폴더 만들기

```powershell
$hub = "C:\Users\<나>\hub"
$src = "C:\Users\<나>\claude-hub-plugin"
New-Item -ItemType Directory -Force "$hub\.claude" | Out-Null
Copy-Item "$src\templates\hub\*" $hub
Copy-Item "$src\examples\hub.settings.json" "$hub\.claude\settings.json"
Copy-Item "$src\examples\supervisor.settings.json" "$hub\supervisor.settings.json"
```

그다음 손으로 채운다.

1. `$hub\.claude\settings.json`: `deny` 의 `<레인 저장소>` 자리에 허브가 직접 고치면 안 되는 저장소 경로를, `additionalDirectories` 에 그 저장소들의 상위 폴더를 넣는다. 자리표시가 남아 있으면 지운다. 이 파일이 허브 세션의 모델과 권한이다.
2. `$hub\supervisor.settings.json`: 슈퍼바이저에게 허락할 일을 `autoMode.allow` 에 문장으로 쓰고, `<레인 저장소들의 상위 폴더>` 를 바꾼다. 허브가 슈퍼바이저를 띄울 때 `--settings` 로 붙인다.
3. 사용자 설정 `%USERPROFILE%\.claude\settings.json` 에 `examples/user.settings.json` 의 두 키(`model`, `crossSessionInbound`)를 손으로 합친다. 파일을 통째로 덮지 않는다. `crossSessionInbound: accept` 가 있어야 세션 사이 메시지가 권한 모드와 관계없이 바로 전달된다.
4. `agents.json` 의 `resident.hub.cwd` 에 허브 폴더 경로를 넣는다. 허브 세션 이름을 `hub` 로 두면(세션 안에서 `/rename hub`) 대시보드 흐름 그래프 가운데에 온다. 이름을 바꾸면 `agents.json` 키도 같이 바꾼다.
5. `CLAUDE.md`, `COORDINATION.md` 의 `<...>` 자리(레인, 인터페이스, 공유 자원)를 프로젝트에 맞게 채운다.

플러그인이 넣어 주지 못하는 이유: 플러그인 설정 파일은 `agent`, `subagentStatusLine` 두 키만 받는다. 권한, 모델, 환경변수는 위처럼 각 설정 파일에 직접 넣어야 한다.

## 대시보드 확인

```powershell
cd C:\Users\<나>\hub
claude
```

세션이 열릴 때 "대시보드 http://127.0.0.1:4990 떠 있음" 이 보이면 브라우저로 그 주소를 연다. 현황 탭 머리에 허브 폴더의 `STATUS.md` 경로가 보이면 허브 폴더를 제대로 읽는 것이다.

- "안 뜸(로그 …)" 이면 그 로그를 본다. 로그는 `%USERPROFILE%\.claude\plugins\data\agent-hub-agent-hub\dashboard-4990.log` 이고 첫 줄에 서버 pid 가 있다.
- 서버 끄기: 로그의 pid 로 `Stop-Process -Id <pid>`.
- 손으로 띄우기: `$env:HUB_DIR = "C:\Users\<나>\hub"; py -3 C:\Users\<나>\claude-hub-plugin\dashboard\server.py`

훅 확인:

1. 허브 폴더 밖(예: 아무 저장소)에서 `claude` 를 열고 "C:/Users/<나>/hub/STATUS.md 맨 끝에 한 줄 더해 줘" 라고 하면 "허브 폴더 파일은 허브만 고친다" 로 막혀야 한다.
2. 아무 git 저장소에서 "git commit -m '파서를 고쳤습니다' 로 커밋해 줘" 라고 하면 문구 규칙 위반으로 막혀야 한다.

Windows 에서 시험 파일도 돌려 보면 확인 범위가 넓어진다. 특히 `test_open_dashboard.py` 는 Windows 의 서버 띄우기(숨은 콘솔, 작업 객체 이탈)와 Windows 경로 판정을 실제로 거친다.

```powershell
cd C:\Users\<나>\claude-hub-plugin
py -3 tests\test_hub_only_write.py; py -3 tests\test_style_basic.py; py -3 tests\test_style_multi.py; py -3 tests\test_open_dashboard.py; py -3 dashboard\test_server.py
```

## 시험

Linux(Python 3.12, Claude Code 2.1.312)에서 돌린 명령이다. 시험 파일은 Windows 에서도 돌도록 만들었지만(심볼릭 링크와 Linux 경로 표는 Windows 에서 건너뜀) Windows 에서 돌려 보지는 않았다.

```sh
python3 dashboard/test_server.py         # 대시보드 서버 파서, 정렬, 합치기
python3 tests/test_hub_only_write.py     # 경로 판정(Windows 꼴 19, Linux 꼴 7)과 훅 실행 5
python3 tests/test_style_basic.py        # git 문구 기본 규칙 36 + PowerShell 2
python3 tests/test_style_multi.py        # 한 호출에 여러 git 명령 7
python3 tests/test_open_dashboard.py     # 대시보드 훅: 허브 밖 무동작, 허브에서 기동, 중복 기동 없음
claude plugin validate --strict .        # 마켓플레이스와 플러그인 매니페스트
```

- 훅 시험은 훅의 표준 입출력 기본값을 cp949 로 두고(`PYTHONIOENCODING=cp949`) UTF-8 입력을 보내 Windows 한국어 로캘을 흉내 낸다. 원래 훅은 이 조건에서 한글 위반 문구를 그냥 통과시켰다.
- `test_open_dashboard.py` 는 빈 포트를 골라 서버를 실제로 띄우고, 로그의 pid 로만 끈다.

## 원본과 달라진 점

- 원본은 허브 폴더 경로를 스크립트와 `server.py` 에 고정했다. 이제는 설정값 `hub_dir`(훅)과 환경변수 `HUB_DIR`, `PORT`(대시보드)로 받는다.
- 쓰기 보호 훅은 bash 와 jq 대신 Python 이다. 허브 판정은 `CLAUDE_PROJECT_DIR`(없으면 훅 입력 cwd) 기준이라, 허브 세션이 Bash 로 다른 폴더에 `cd` 해도 허브로 본다.
- 대시보드 열기 훅은 curl, setsid 대신 Python 이고, 플러그인이 모든 세션에 붙으므로 허브 폴더에서만 동작한다.
- Windows 대비: 훅과 서버가 파일과 표준 입출력을 UTF-8 로 읽고 쓴다. 서버는 `shutil.which` 로 `claude.exe` 나 npm 의 `claude.cmd` 를 찾는다. git 문구 훅은 PowerShell 도구도 검사한다.

## 한계와 Windows 에서 확인 못 한 것

- 쓰기 보호는 Edit, Write, NotebookEdit 만 막는다. Bash 나 PowerShell 로 쓰는 것(`sed -i`, `>`, `Set-Content`)은 못 막는다.
- Windows 에서 확인하지 못한 것:
  - exec 형식 훅이 `python` 설정값을 실행하는지. 절대 경로는 PATH 찾기가 없어 가장 안전하고, `py` 나 `python` 같은 이름만 주면 Claude Code 가 PATH 에서 `.exe` 를 찾는지에 달렸다. 안 되면 훅 셋이 모두 돌지 않는다.
  - 대시보드 서버가 세션이 끝난 뒤에도 사는지. 숨은 콘솔과 작업 객체 이탈(`CREATE_BREAKAWAY_FROM_JOB`, 막히면 빼고 다시)로 띄우지만, Claude Code 가 훅 자식 프로세스를 작업 객체로 묶어 같이 끄는지는 모른다.
  - 서버가 2~3초마다 부르는 `claude agents` 가 콘솔 창을 띄우지 않는지.
  - `claude agents --json --all`, `claude logs` 가 Windows 에서 같은 형식으로 나오는지. background 세션(`claude --bg`)이 Windows 에서 되는지.
  - `~/.claude/projects` 아래 기록 폴더 이름이 Linux 와 같은 규칙(영숫자 밖은 `-`)인지. 다르면 서버가 전체 검색으로 찾으니 느릴 뿐 동작은 한다.
  - `C:/` 로 쓴 `hub_dir` 를 Claude Code 가 그대로 넘기는지. 훅은 `C:\`, `C:/`, `/c/` 를 모두 같은 폴더로 본다.
  - PowerShell 도구의 git 명령 따옴표(`@'...'@` 여러 줄 문자열, 백틱 줄바꿈)는 검사기가 bash 처럼 읽으므로 일부 형식을 놓칠 수 있다.
- Windows 에서는 `/proc` 가 없어 Codex 세션이 모두 종료로 보인다.
- 사용량 줄의 Claude 값은 `~/.claude/statusline-tee.sh` 가 쓰는 `~/.claude/usage.json` 을 읽는다. 이 상태줄 스크립트는 플러그인에 없어서, 따로 넣지 않으면 "파일 없음" 이다.
- 사용자 설정에 같은 일을 하는 훅을 따로 등록해 두었다면, 이 플러그인을 사용자 범위로 설치했을 때 검사가 두 번 돈다. 한쪽을 뺀다.

## 라이선스와 출처

이 저장소는 MIT 라이선스다([LICENSE](LICENSE)). 함께 든 것은 각자의 라이선스 파일을 그대로 둔다.

- `skills/humanizer`: [blader/humanizer](https://github.com/blader/humanizer), MIT, `skills/humanizer/LICENSE`
- `dashboard/vendor/xterm.js`, `xterm.css`: [xterm.js](https://github.com/xtermjs/xterm.js) 5.5.0, MIT, `dashboard/vendor/xterm-LICENSE`
- `dashboard/vendor/WantedSansVariable.woff2`: [Wanted Sans](https://github.com/wanteddev/wanted-sans) 1.0.3, SIL OFL 1.1, `dashboard/vendor/WantedSans-OFL.txt`
