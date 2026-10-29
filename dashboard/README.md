# 에이전트 대시보드

떠 있는 Claude Code 세션과 Codex 세션을 모아 보는 로컬 화면이다. 화면 오른쪽에 세로로 붙여 두고 쓴다(폭 560~720px).
목록에서 세션을 누르면 그 세션의 대화 기록과 세션 창(`claude logs`)을 볼 수 있다. 읽기만 하고, 세션에 입력을 보내거나 멈추지 않는다.

## 실행

```sh
HUB_DIR=~/hub ./run.sh            # http://127.0.0.1:4990, 허브 폴더 ~/hub
HUB_DIR=~/hub PORT=4991 python3 server.py   # 포트 바꾸기
python3 test_server.py   # 기록 파서(Claude, Codex), agents.json 구분, 배치 순서, Codex 합치기, 결정 합치기와 정렬, 사용량 읽기, 메시지 중복 제거와 종류, 시간 창, dev 점유 파일, 처리 토큰 합산, hours 검사, 할 일 묶음과 정렬 점검
CODEX_HOURS=72 ./run.sh  # Codex 세션을 보는 범위(시간, 기본 24)
```

Windows PowerShell 에서는 이렇게 띄운다.

```powershell
$env:HUB_DIR = "C:\Users\<나>\hub"; $env:PORT = "4990"; python dashboard\server.py
```

- `HUB_DIR` 는 허브 폴더다. 이 폴더의 `agents.json`, `decisions.json`, `STATUS.md`, `dev-occupancy.json` 넷을 읽기만 한다. 비우면 서버를 띄운 현재 폴더를 쓴다.
- `PORT` 는 포트다(기본 4990). 주소는 늘 127.0.0.1 이다.
- 플러그인의 SessionStart 훅은 허브 폴더에서 세션이 열릴 때 플러그인 설정값(`hub_dir`, `dashboard_port`)으로 이 두 변수를 채워 서버를 띄운다.

필요한 것은 Python 3.8 이상(표준 라이브러리만)과 PATH 의 `claude` 다. Codex 세션은 `~/.codex` 와 `/proc` 를 읽기만 하므로 `codex` 명령은 필요 없다. 설치와 빌드는 없다.

## 보는 것

맨 위 제목 줄 아래에 남은 사용량 줄이 있고, 그 아래 탭은 다섯 개다. 에이전트(`#/`), 결정(`#/decisions`), 현황(`#/status`), 흐름(`#/flow`), 할 일(`#/todo`). 결정 탭 이름 옆 숫자는 지금 결정이 필요한 건수, 할 일 탭 옆 두 숫자는 진행 중(초록)과 대기(회색) 할 일 건수이며 어느 탭에서도 보인다.

- 목록: `claude agents --json --all` 을 3초마다 읽어 상태로 세 구역에 나눈다(순서는 서버 `arrange()` 가 정한다).
  1. 진행 중: status busy 또는 state working.
  2. 입력 대기: state blocked(권한 승인이나 질문에 멈춤, Clay 색 "입력 필요")와 다음 지시를 기다리는 세션(interactive 의 status idle 등, "지시 대기").
  3. 종료: state done. 맡은 턴을 끝낸 background 세션과 `--all` 에만 나오는 끝난 세션이다. done 말고 다른 끝 상태값은 아직 본 적이 없어 입력 대기로 들어간다. 기본으로 접혀 있고 펼친 상태는 브라우저에 기억한다.
  - 각 구역 안에서는 일회성, 상시, 기타 순이고 같은 종류 안에서는 마지막 활동이 최근인 것이 위다.
- 상시와 일회성: 허브가 관리하는 `<허브 폴더>/agents.json`(읽기만)의 `resident` 에 있는 이름은 상시, `task` 에 있는 이름은 일회성, 둘 다 없으면 기타다. 상시 카드는 채운 바탕에 레인 배지, 일회성 카드는 바탕 없이 점선 테두리에 작업 id(T-…) 배지를 단다. 기타는 배지가 없다. 파일은 목록과 함께 몇 초마다 다시 읽고, 없거나 깨져 있으면 전부 기타로 둔다.
- 카드에는 이름, 배지, 상태 칩, 하는 일(`~/.claude/jobs/<id>/state.json` 의 detail, 입력 필요이면 needs), 마지막 활동(기록 파일 수정 시각)과 시작 뒤 지난 시간, 종류, 작업 폴더 이름이 이 순서로 보인다. pid 는 상세에서 본다.
- 대화: `~/.claude/projects/<cwd>/<sessionId>.jsonl` 을 읽어 사용자 지시, 답, 도구 호출(누르면 입력과 결과), 다른 세션에서 받은 메시지, SendMessage 로 보낸 메시지를 시간순으로 보여 준다. 2초마다 늘어난 부분만 읽고, 맨 아래를 보고 있으면 따라 내려간다. 처음에는 최근 500건만 보여 준다.
- 세션 창: background 세션은 `claude logs <id>` 출력을 터미널처럼 그린다. interactive 세션은 logs 가 없어 대화 탭만 쓰고, 복사할 수 있는 명령으로 `claude --resume <id> --fork-session` 을 보여 준다.
- 결정: 허브가 관리하는 `<허브 폴더>/decisions.json` 의 items 와, 지금 떠 있는 세션 중 입력 필요(blocked)인 세션의 needs 를 합쳐 3초마다 보여 준다. 합치기와 정렬은 서버 `merge_decisions()` 가 한다.
  1. 지금 결정 필요: 묻는 중인 세션(마지막 활동이 최근인 것 먼저)을 맨 위에 두고, 그 아래에 open 항목을 올라온 시각이 최근인 순으로 둔다. 묻는 중인 세션은 "세션이 지금 묻는 중" 칩을 달고 그 세션의 대화로 가는 링크를 보여 준다. 같은 건이 파일 항목과 겹쳐 나올 수 있다. status 가 open, waiting, decided 가 아닌 항목도 여기에 둔다.
  2. 미뤄 둔 것: waiting 항목이다. until 이 날짜인 것을 이른 날짜 순으로 먼저 두고, 날짜가 아닌 것("사용자가 다시 말할 때")은 그 뒤에 둔다.
  3. 결정됨: decided 항목을 decided_at 이 최근인 순으로 둔다. 기본으로 접혀 있다.
  - 카드에는 제목, 출처 세션과 배지, 작업 id, 올라온 시각(미룬 기한, 결정 시각), 자세히(접힘), 선택지, 결정 내용, refs 가 보인다. refs 가 URL 이면 새 탭으로 열고, 아니면 눌러서 그 글자를 복사한다.
  - 읽기만 한다. 결정은 허브와 대화해서 정하고, 허브가 파일을 고친다.
- 흐름: 세션끼리 주고받은 메시지를 그래프와 타임라인으로 보여 준다. 서버 `/api/messages?hours=N`(기본 24, 0 은 전체)을 5초마다 읽는다.
  - 데이터: `~/.claude/projects/*/*.jsonl` 중 수정 시각이 시간 창 안인 기록을 모두 읽는다. 지금 목록에 없는 닫힌 세션도 들어가고, 서브에이전트 기록(`<세션>/subagents/`)은 넣지 않는다. 보낸 쪽은 SendMessage 도구 호출이고, 결과가 success 이면서 msg_id 가 있는 것만 센다. 실패한 것과 msg_id 없이 성공한 것(같은 세션의 서브에이전트 앞)은 뺀다. 받은 쪽은 origin.kind 가 peer 인 사용자 기록과 queued_command 첨부의 `<cross-session-message>` 다. idle 알림, 전달 알림, 서브에이전트 handback, queue-operation 기록은 메시지로 세지 않는다.
  - 중복 제거(서버 `merge_messages()`): 같은 메시지가 보낸 쪽과 받은 쪽 기록에 한 번씩 나온다. 두 쪽에 같은 msg_id 가 남으므로 그것으로 묶고, msg_id 가 없는 받은 기록은 본문 앞 200자 해시와 시각(10분 안)으로 묶는다. 시각, 본문, 요약은 보낸 쪽 것을 쓰고, 받은 쪽은 받는 세션 이름을 정하는 데만 쓴다. 보낸 쪽 기록이 없을 때만 받은 쪽 기록으로 채운다. 받는 쪽이 `uds:…/<pid>.sock` 주소로만 적힌 경우 받은 쪽 기록, 다른 받은 기록의 보낸 주소, 지금 떠 있는 세션 pid 순으로 이름을 찾는다.
  - 노드 이름은 기록의 마지막 agent-name 이다. 이름을 바꾼 세션은 바꾼 이름 하나로 모인다. 같은 이름의 세션 여러 개(다시 띄운 WF2 등)도 한 노드다. 노드 색은 목록의 상태 칩과 같은 규칙이고(진행 중 초록, 입력 필요 점토색, 지시 대기 회색 테, 끝남과 닫힘 흐린 테), 일회성 세션은 점선 테다. agents.json 에도 지금 목록에도 없는 이름은 결정 탭과 같이 닫힌 일회성 세션으로 본다.
  - 그래프: agents.json 에서 lane 이 HUB 인 세션(허브)을 가운데, 나머지를 타원 둘레에 놓는다(상시, 일회성, 기타 순, 같은 종류는 건수 많은 순). 세션이 17개를 넘으면(전체 창은 46개였다) 건수 많은 16개(index.html `RING`)만 바깥 타원에 이름과 함께 두고, 나머지는 안쪽 타원에 이름 없는 작은 점으로 둔다. 점에 올리거나 누르면 이름이 보인다. 간선 두께는 건수의 로그, 화살표는 방향이다. 서로 보낸 두 방향은 따로 휘어 겹치지 않는다. 노드를 누르면 그 세션이 보내거나 받은 메시지만, 간선을 누르면 그 방향 메시지만 아래 목록에 남는다. 다시 누르거나 빈 곳을 누르면 풀린다.
  - 목록: 최신이 위다. 종류 배지(배정, 보고, 알림, 기타)는 본문 맨 앞의 `[배정]` `[보고]` `[알림]` 으로 정한다(`[배정 보완]` 처럼 뒤에 말이 붙어도 같다). `[허브]`, `[허브 결정]`, `[요청]` 등은 기타다. 요약은 SendMessage 의 summary, 없으면 본문 첫 줄이다. 펼치면 본문이 보인다. 응답에는 최근 300건만 실리고 간선 건수는 전부 센다.
  - 시간 창: 1시간, 6시간, 24시간, 전체. 고른 값은 브라우저에 기억한다. hours 가 숫자가 아니거나 음수, nan, inf 이면 400 과 이유를 돌려준다. 기록은 파일마다 읽은 위치를 기억해 늘어난 부분만 읽는다(`claude_scan()`). 처음 전체를 고르면 이 호스트 기준 820MB 를 읽느라 3초쯤 걸린다.
- 할 일: 세션마다 Claude Code 가 쓰는 Todo(작업 목록)를 세션별 카드로 보여 준다. 서버 `/api/todos` 를 3초마다 읽고, 묶기와 정렬은 서버 `todos()` 가 한다.
  - 데이터: `~/.claude/tasks/<sessionId>/<id>.json`(키 id, subject, description, activeForm, status, owner, blocks, blockedBy)이다. 옛 형식 `~/.claude/todos/<sessionId>-agent-<agentId>.json`(항목 목록, 제목은 content)도 같이 읽는다. 읽기만 하고 `.lock`, `.highwatermark` 는 열지 않는다. JSON 이 깨진 파일(쓰는 중)은 그 파일만 건너뛰고, 항목이 하나도 없는 폴더는 카드를 만들지 않는다.
  - 세션 이름은 `claude agents --json --all` 의 sessionId 로 찾는다. 목록에 없는 세션은 sessionId 앞 8자로 보이고 "닫힘" 칩과 함께 흐리게 그린다. 상시와 일회성 배지, 카드 테두리는 에이전트 탭과 같이 agents.json 을 따른다. 이름을 누르면 그 세션 대화로 간다.
  - 카드는 마지막 수정 시각(그 세션 Todo 파일 mtime 의 최댓값)이 최근인 것이 위다. 카드 안은 진행 중, 대기, 끝남 순이고 같은 상태 안에서는 id 를 숫자 순으로 둔다(숫자가 아닌 id 는 뒤). 모르는 status 는 대기 옆에 둔다.
  - 항목은 subject 와 #id, 진행 중이면 그 아래 activeForm 을 초록으로 보인다. description, owner, blockedBy 가 있는 항목은 눌러서 펼친다("맡은 세션", "막는 일").
  - 끝남은 카드마다 기본으로 접혀 있고, 펼친 카드는 브라우저에 기억한다(`todoDone`). 7일(server.py `TODO_STALE`) 넘게 안 바뀐 카드는 기본으로 숨기고 맨 아래 "7일 넘게 안 바뀐 세션 N개 보기"로 펼친다(`todoStale` 로 기억).
  - 탭 옆 건수는 숨긴 오래된 카드를 빼고 센다. 모르는 status 는 세지 않는다.
- 현황: `<허브 폴더>/STATUS.md` 를 5초마다 다시 읽어 마크다운으로 그린다. 위에 파일 수정 시각이 보인다. 넓은 표는 표 상자 안에서만 가로로 움직인다.
- Codex 세션: `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl` 을 읽어 Claude 세션과 같은 목록에 합친다(서버 `codex_rows()`). 카드에 "codex" 배지가 붙고 종류 자리에 `codex exec`, `codex cli`, `codex vscode` 처럼 session_meta 의 source 가 보인다. 배지가 codex 이면 상시와 일회성 구분은 하지 않는다.
  - 범위: 기록 파일 수정 시각이 최근 24시간(`CODEX_HOURS`) 안인 것만 보인다. 살아 있어도 그보다 오래 손대지 않은 세션(몇 주째 열려 있는 codex TUI 등)은 빠진다. 하위 에이전트 스레드(source 가 subagent)는 부모 세션 기록에 "하위 에이전트" 줄로 나오므로 따로 카드를 만들지 않는다.
  - 상태: 이 사용자의 프로세스가 그 rollout 파일이나 `~/.codex/thread-writer-locks/<id>.lock` 을 열고 있으면 살아 있다고 본다(`/proc/<pid>/fd`, 다른 사용자의 codex 는 보지 않는다). 이름이 codex 로 시작하는 프로세스만 세므로 tail, grep 이나 이 서버가 기록을 읽어도 살아 있는 것으로 잡히지 않는다. 살아 있고 마지막 `task_started` 뒤에 `task_complete`, `turn_aborted` 가 없으면 진행 중, 턴이 닫혔으면 지시 대기, 아무 codex 프로세스도 열고 있지 않으면 종료다. Codex 에는 입력 필요 상태를 두지 않는다. 답에 questions 가 달린 기록이 24건 있었지만 모두 delivery async 였고 턴이 끝나지 않고 이어졌다. 그래서 결정 탭에도 Codex 세션은 나오지 않는다.
  - 이름은 `~/.codex/session_index.jsonl` 의 thread_name 이고, 없으면(`codex exec` 는 보통 없다) `codex <id 뒤 8자리>` 다. id 앞부분은 시작 시각이라 같이 띄운 세션끼리 겹친다. 하는 일 자리는 마지막 사용자 지시, 활동은 기록 파일 수정 시각, 시작은 session_meta 의 timestamp 다.
  - 대화: Codex 화면에 보이는 층인 `event_msg` 의 `item_completed` 만 읽는다(서버 `codex_events_of()`). 사용자 지시(UserMessage), 답(AgentMessage), 도구 호출(CommandExecution 은 shell, McpToolCall 은 `서버.도구`, FileChange, 그 밖의 항목은 kind 이름)과 결과, 하위 에이전트 활동, 대화 요약, 턴 중단을 보여 준다. 도구는 끝난 뒤에야 기록되므로 실행 중인 도구는 보이지 않는다. Reasoning 은 암호화되어 있어 뺀다. `response_item` 의 user 메시지는 AGENTS.md 와 스킬 안내가 섞여 있어 쓰지 않는다.
  - 세션 창 탭과 복사 명령은 없다. `codex resume` 은 원래 세션에 이어 쓰므로 보여 주지 않는다.
- 남은 사용량: 제목 줄 바로 아래, 세션 상세를 포함한 모든 화면에 Claude 와 Codex 를 한 줄씩 보여 준다. 서버 `/api/usage` 를 3초마다 읽는다.
  - 창마다 이름(5시간, 주간, 그 밖은 분이나 시간), 남은 %(100 - 사용 %), 리셋까지 남은 시간을 보여 주고, 맨 끝에 값이 기록된 지 얼마나 됐는지를 붙인다. 리셋 시각과 기록 시각(Codex 는 요금제도)은 툴팁으로 본다.
  - 남은 % 가 20 보다 적은 창은 Clay 바탕 알약으로 바꿔 경고한다(index.html `LOW`).
  - 기록이 30분(server.py `USAGE_STALE`)보다 오래되면 "갱신 안 됨"과 마지막 갱신 시각을 붙이고 흐리게 한다. 파일이 없으면 "기록 없음", 깨져 있으면 "읽지 못함"(툴팁에 오류)을 흐리게 보인다. 리셋 시각이 지난 창은 그 % 가 더는 맞지 않으므로 숫자 대신 "리셋됨"을 보인다.
  - Claude: `~/.claude/usage.json` 을 읽는다. statusLine 으로 설치한 `~/.claude/statusline-tee.sh` 가 상태줄 입력의 `rate_limits` 를 `{"at": 밀리초, "rate_limits": {...}}` 로 쓴 파일이다. `five_hour`, `seven_day` 의 `used_percentage` 와 `resets_at`(초)을 쓴다. 필드 구조는 2026-10-26 에 생긴 파일과 claude-hud 의 타입 선언으로 확인했다. 다른 키가 오면 키 이름 그대로 보인다.
  - Codex: `~/.codex/sessions/**/rollout-*.jsonl` 의 `event_msg` `token_count` 에 붙은 `rate_limits` 의 `primary`, `secondary`(각 `used_percent`, `window_minutes`, `resets_at` 초)와 `plan_type` 을 쓴다. 수정 시각이 최근인 rollout 부터 보며 기록 시각(`timestamp`)이 가장 늦은 token_count 를 고른다. 파일 수정 시각이 이미 고른 기록보다 이르면 그 파일부터는 보지 않는다. 읽기는 목록과 같은 `codex_scan()` 을 써서 늘어난 부분만 읽고, `rate_limits` 가 null 인 기록은 건너뛴다. 이 호스트 기록에는 주간(10080분) primary 하나만 있었다.
  - 두 파일 모두 크기와 수정 시각이 그대로면 다시 읽지 않는다. 오래됨 판정은 요청 때마다 한다.
- dev 점유: 사용량 줄 바로 아래 얇은 한 줄에 dev 스택(공유 개발 환경)을 지금 누가 쓰는지 보여 준다. 허브가 관리하는 `<허브 폴더>/dev-occupancy.json`(읽기만)을 서버 `/api/dev` 로 3초마다 읽는다(크기와 수정 시각이 그대로면 다시 파싱하지 않는다).
  - 형식: `{"updated_at": ISO 시각, "items": [{"who", "kind", "what", "since", "until", "note"}]}`. kind 는 run(실행), restart(재기동 예정), deploy(배포)다.
  - 줄 모양: "dev: <who> <what> <경과>". 경과는 since 부터 지난 시간("25분째")이고, since 가 아직 오지 않았으면 "15분 뒤"다. what 이 길면 말줄임하고 kind, 시작과 끝 시각, note 는 툴팁으로 본다. 항목이 여럿이면 첫 항목과 "N건 펼치기" 단추를 보이고, 펼친 상태는 브라우저에 기억한다. 비어 있으면 "쓰는 세션 없음"이다.
  - restart 항목은 맨 앞으로 올리고 점토색 알약으로 경고한다.
  - updated_at 이 2시간(server.py `DEV_STALE`)보다 오래됐거나 없으면 줄을 흐리게 하고 "갱신 N시간 전"을 붙인다.
  - 파일이 없거나 깨져 있으면(JSON 오류, items 가 목록이 아님) 줄을 숨긴다. 사유는 현황 탭 머리(파일 경로 줄 아래)에 흐린 한 줄로 보이고, `/api/dev` 의 state, error 에도 남는다. 목록이 아닌 항목은 건너뛴다.
- 알림: 브라우저 탭 제목에 "(N) 에이전트 대시보드" 로 숫자를 붙인다. N 은 지금 입력 필요(blocked)인 세션 수와, 화면을 보지 않는 동안 새로 온 허브 앞 보고 수의 합이다.
  - 보고는 흐름 탭과 같은 `/api/messages` 에서 받는 쪽이 허브(agents.json 의 lane HUB)이고 종류가 보고인 것이다. 흐름 탭이 아니면 15초마다 24시간 창을 읽는다. 마지막으로 본 보고 시각(`reportMark`)보다 늦은 것이 새 보고다. 처음 열 때는 그때까지의 보고를 새 것으로 치지 않는다.
  - 화면이 보이는 상태(`visibilityState` 가 visible)가 되면 보고 수는 읽음으로 처리한다. 입력 필요 수는 세션이 풀릴 때까지 남는다.
  - 제목 줄의 알림 버튼을 누르면 브라우저 알림 권한을 묻고, 허용하면 켜진다. 켜져 있으면 (a) 세션이 입력 필요로 바뀔 때 "<이름> 입력 필요"(본문은 needs), (b) 허브에게 보고가 새로 올 때 "<보낸 세션> 보고"(본문은 요약)를 띄운다. 한 번에 4건 이상이면 한 장으로 묶는다. 알림을 누르면 그 세션 대화나 흐름 탭으로 간다. 다시 누르면 끈다. 폭이 620px 보다 좁으면 버튼에 종 그림만 남는다.
  - 같은 사건을 두 번 알리지 않도록 알린 것을 브라우저 localStorage(`notified`)에 기억한다. 새로 고침이나 다른 탭에서도 같은 사건은 다시 알리지 않는다. 입력 필요는 세션이 그 상태를 벗어나면 기억을 지워 다음 입력 필요를 새로 알린다. 켜는 순간 이미 입력 필요인 세션은 알리지 않고 그 뒤 바뀌는 것만 알린다. 권한이 막혀 있으면 버튼이 "알림 막힘"으로 꺼진다.
- 토큰: 세션마다 쓴 처리 토큰을 카드 meta 맨 끝("토큰 79.3만"), 사용량 줄 끝("처리 토큰 합계"), 흐름 탭 "세션별 처리 토큰" 막대에 보인다. `/api/agents` 의 각 세션 `tokens` 로 온다. 숫자는 만, 억 단위로 줄이고 정확한 값과 내역은 툴팁으로 본다.
  - 처리 토큰 = 입력(캐시 쓰기 포함, 캐시 읽기 제외) + 출력. 캐시 읽기는 합에 넣지 않고 툴팁 내역에만 따로 보인다.
  - Claude 세션(background, interactive 모두): 기록(.jsonl)의 assistant `message.usage` 에서 input_tokens + cache_creation_input_tokens + output_tokens 다. 그 세션의 서브에이전트 기록(`<세션 id>/subagents/agent-*.jsonl`)도 더한다. 한 API 응답이 내용 블록마다 같은 usage 를 달고 여러 줄로 기록되므로 `message.id` 하나에 한 번만 센다(af61deb7 기록은 1772줄 중 890줄이 반복이었다). `~/.claude/jobs/<id>/state.json` 의 tokens 는 쓰지 않는다.
  - codex 세션: rollout 의 마지막 `token_count.info.total_token_usage` 에서 input_tokens - cached_input_tokens + output_tokens 다. 추론 출력은 출력 안에 들어 있어 따로 더하지 않는다. info 가 null 인 기록은 건너뛴다.
  - 읽기는 메시지와 같은 `claude_scan()`, `codex_scan()` 이 늘어난 부분만 읽는다.
  - 막대는 큰 순이고 처음 5개만 보이며 "더 보기"로 전부 펼친다. 길이는 가장 큰 값에 대한 비율이고 색은 엔진(점토색 Claude, 회색 codex)이다. 같은 이름 세션이 여럿이면 이름 옆에 세션 id 앞 8자리를 붙인다.
- 주소: `#/s/<sessionId>` 는 대화 탭, `#/s/<sessionId>/logs` 는 세션 창 탭, `#/flow` 는 흐름 탭, `#/todo` 는 할 일 탭이다.

## 정해 둔 것

- 127.0.0.1 에만 열고, Host 헤더가 127.0.0.1 이나 localhost 가 아니면 거절한다. 기록 내용은 메모리에서만 다루며 파일로 남기거나 밖으로 보내지 않는다.
- `vendor/xterm.js` 는 xterm.js 5.5.0(MIT)을 그대로 넣은 것이다. `claude logs` 는 커서를 옮겨 가며 그리는 TUI 출력이라 ANSI 색 변환만으로는 화면이 나오지 않아 터미널 에뮬레이터가 필요하다. CDN 없이도 뜨도록 폴더에 넣었다.
- 글꼴은 Wanted Sans Variable 1.0.3(SIL OFL 1.1, `vendor/WantedSans-OFL.txt`)이다. 공식 릴리스의 가변 woff2 를 고치지 않고 `vendor/WantedSansVariable.woff2` 로 넣어 CDN 없이 뜬다. 무게는 400~1000 만 있다. 로그, 경로, 도구 이름은 mono 그대로다.
- 화면 테마는 어두운 쪽이 기본이고 오른쪽 위 버튼으로 밝은 쪽과 바꾼다. 세션 창은 두 테마 모두 어두운 바탕이다.

- 허브 폴더 파일(agents.json, decisions.json, STATUS.md, dev-occupancy.json)은 읽기만 한다. 파일이 없거나 깨져 있어도 화면은 뜬다. 결정 탭은 오류 띠를 보이고 묻는 중인 세션만 보여 주며, 현황 탭은 안내 문구를 보인다.
- 마크다운은 의존성 없이 index.html 의 작은 변환기 `md()` 로 그린다. DOM 노드만 만들고 HTML 문자열은 넣지 않는다.

## 한계

- Windows 에는 `/proc` 가 없어 Codex 세션이 살아 있는지 알 수 없다. Codex 세션은 모두 종료로 보인다.
- 결정 카드의 출처 배지는 agents.json 을 따른다. 일회성 세션은 닫히면 agents.json 의 task 에서 빠진다. 그래서 출처가 agents.json 에도 지금 목록에도 없으면 닫힌 일회성 세션으로 보고 "일회성" 배지와 "닫힘" 을 단다. 상시 세션은 항상 agents.json 에 있다고 가정한 판정이다. 닫힌 세션의 작업 id 는 항목의 task 필드로만 보인다.
- 마크다운 변환기는 제목, 목록(들여쓰기로 중첩), 표, 코드 블록, 인용, 가로줄, 문단과 인라인 코드, 굵게, 링크만 안다. 기울임, 이미지, HTML, 각주는 글자 그대로 나온다. http(s) 가 아닌 링크는 글자만 보이고, 걸린 주소는 툴팁으로 보인다.

- `claude logs` 는 최근 출력만 돌려주므로 화면 중간부터 그려질 수 있다. 이때 위쪽이 비거나 조각이 남는다.
- 데몬 터미널 폭이 200칸 안팎인 세션은 폭에 맞추면 글자가 7px 아래로 줄어든다. 이 경우 세션 창 상자 안에서만 가로로 움직인다.
- Codex 상태 신호의 한계: VS Code 확장에서 연 세션(source vscode)은 app-server 데몬이 기록을 쓴다. 데몬이 쓰는 동안 rollout 이나 잠금 파일을 계속 열어 두는지는 확인하지 못했다(확인한 때 떠 있던 데몬은 아무 rollout 도 열고 있지 않았다). 열어 두지 않는다면 살아 있어도 종료로 보인다. 승인 대기를 알려 주는 기록은 찾지 못해서 승인을 기다리는 codex 는 진행 중으로 보인다. 프로세스가 턴 도중 죽으면 기록에 턴 끝이 없지만 프로세스가 없으므로 종료로 본다. rollout 형식은 공식 문서가 없어 이 호스트의 최근 rollout 80개와 0.163.0 `codex exec` 기록을 열어 보고 맞췄다. 형식이 바뀌면 이름과 상태가 비거나 대화가 빈 채로 나올 수 있다.
- 사용량 줄의 한계: Claude 값은 interactive 세션이 상태줄을 그릴 때만 갱신된다. background 세션만 돌고 있으면 쓰는 쪽이 없어 "갱신 안 됨"이 된다. 갱신 시각은 상태줄이 파일을 쓴 때이지 API 가 그 숫자를 낸 때가 아니다. 여러 interactive 세션이 같은 파일을 덮어쓰므로 쉬고 있던 세션이 옛 숫자를 새 시각으로 쓸 수도 있다. Codex 값은 계정 전체 한도지만 이 호스트에서 codex 가 돌 때만 기록되므로, 다른 곳에서 쓴 양은 다음 기록 전까지 반영되지 않는다. 요금제는 고른 기록의 것만 보인다(이 호스트 기록에는 pro 와 prolite 가 섞여 있다). 리셋 뒤 남은 양은 새 기록이 오기 전까지 알 수 없다.
- 토큰 숫자의 한계: 사용량 줄과 막대의 합은 지금 목록에 있는 세션만 더한다. 처리 토큰은 캐시 읽기를 빼므로 요금이나 사용량 한도와 같은 값이 아니다. codex rollout 의 cache_write_input_tokens 는 이 호스트 기록 86403건 모두 0 이라 따로 더하지 않는다. 값이 생기면 입력에 들어 있는지 다시 봐야 한다.
- interactive 세션은 붙는 명령이 없다. 대신 주는 `--fork-session` 명령은 기록을 새 세션 id 로 복사해 여는 것이라 원래 세션 화면과는 별개다.
