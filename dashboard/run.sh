#!/bin/sh
# 에이전트 대시보드를 http://127.0.0.1:${PORT:-4990} 에 띄운다(읽기 전용). 허브 폴더는 HUB_DIR(비우면 현재 폴더).
exec python3 "$(dirname "$0")/server.py"
