#!/bin/bash

set -u
set -o pipefail

REPO_ROOT="${HEALTH_REPO_ROOT:-/Users/wangjie/Documents/health}"
RUNNER="${HEALTH_DAILY_REVIEW_RUNNER:-$REPO_ROOT/fitness_logs/automation/daily_review.sh}"
LOG_DIR="${HEALTH_LOG_DIR:-/Users/wangjie/Library/Logs/health}"
STATE_ROOT="${HEALTH_STATE_ROOT:-/Users/wangjie/Library/Application Support/health-daily-review/state}"
STATUS_FILE="$STATE_ROOT/status/latest.json"
WATCHDOG_STATE="$STATE_ROOT/watchdog.json"
WATCHDOG_LOG="$LOG_DIR/watchdog.log"
PYTHON3="/opt/homebrew/bin/python3"
DATE="/bin/date"
MKDIR="/bin/mkdir"

export HOME="/Users/wangjie"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/Applications/ChatGPT.app/Contents/Resources"
export TZ="Asia/Shanghai"

$MKDIR -p "$LOG_DIR" "$STATE_ROOT/status" "$STATE_ROOT/diagnostics"
exec >>"$WATCHDOG_LOG" 2>&1

timestamp() {
  "$DATE" '+%Y-%m-%d %H:%M:%S %Z'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

classify_exit() {
  case "$1" in
    65) printf '%s\n' "workspace_dirty" ;;
    66) printf '%s\n' "deterministic_validation" ;;
    67) printf '%s\n' "codex_semantic" ;;
    68) printf '%s\n' "post_validation" ;;
    69) printf '%s\n' "dependency" ;;
    70) printf '%s\n' "git_sync" ;;
    71) printf '%s\n' "commit" ;;
    72) printf '%s\n' "repository" ;;
    73) printf '%s\n' "remote_race" ;;
    74) printf '%s\n' "git_push" ;;
    75) printf '%s\n' "lock" ;;
    76) printf '%s\n' "automatic_repair" ;;
    *) printf '%s\n' "unknown" ;;
  esac
}

read_watchdog_state() {
  "$PYTHON3" - "$WATCHDOG_STATE" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
try:
    data = json.loads(path.read_text())
except Exception:
    data = {}
print(data.get("signature", ""))
print(int(data.get("consecutive_failures", 0)))
print(int(data.get("next_retry_epoch", 0)))
PY
}

write_watchdog_state() {
  signature_value="$1"
  count_value="$2"
  next_value="$3"
  class_value="$4"
  target_value="$5"
  "$PYTHON3" - "$WATCHDOG_STATE" "$signature_value" "$count_value" "$next_value" "$class_value" "$target_value" <<'PY'
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "signature": sys.argv[2],
    "consecutive_failures": int(sys.argv[3]),
    "next_retry_epoch": int(sys.argv[4]),
    "failure_class": sys.argv[5],
    "target_date": sys.argv[6] or None,
    "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
}
temp = path.with_name(path.name + f".tmp.{os.getpid()}")
temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
temp.replace(path)
PY
}

latest_target() {
  "$PYTHON3" - "$STATUS_FILE" <<'PY'
import json
import sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text()).get("target_date", ""))
except Exception:
    print("")
PY
}

retry_delay() {
  failure_class="$1"
  count="$2"
  case "$failure_class" in
    lock) printf '%s\n' 900 ;;
    git_sync|git_push|remote_race)
      delay=$((900 * (1 << (count > 4 ? 4 : count - 1))))
      [ "$delay" -le 21600 ] || delay=21600
      printf '%s\n' "$delay"
      ;;
    codex_semantic)
      printf '%s\n' 14400
      ;;
    dependency)
      [ "$count" -le 2 ] && printf '%s\n' 900 || printf '%s\n' 3600
      ;;
    deterministic_validation|post_validation|automatic_repair)
      delay=$((3600 * count))
      [ "$delay" -le 21600 ] || delay=21600
      printf '%s\n' "$delay"
      ;;
    *) printf '%s\n' 21600 ;;
  esac
}

resolve_codex() {
  for candidate in \
    "${HEALTH_CODEX_BIN:-}" \
    "/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex" \
    "/Applications/ChatGPT.app/Contents/Resources/codex"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  search_root="${HEALTH_CODEX_SEARCH_ROOT:-/Applications/ChatGPT.app/Contents/Resources}"
  if [ -d "$search_root" ]; then
    discovered_codex="$(/usr/bin/find "$search_root" -type f -name codex -perm -111 2>/dev/null | /usr/bin/head -n 1)"
    if [ -n "$discovered_codex" ]; then
      printf '%s\n' "$discovered_codex"
      return
    fi
  fi
  command -v codex 2>/dev/null || true
}

write_diagnostic() {
  failure_class="$1"
  target="$2"
  count="$3"
  case "$failure_class" in
    deterministic_validation|post_validation|automatic_repair|commit|repository|unknown) ;;
    *) return ;;
  esac
  [ "$count" -eq 1 ] || return
  codex_bin="$(resolve_codex)"
  [ -x "$codex_bin" ] || return
  diagnostic_file="$STATE_ROOT/diagnostics/${target:-unknown}-$(date '+%Y%m%d-%H%M%S').md"
  target_log="$LOG_DIR/daily-review-${target}.log"
  {
    printf 'Analyze this unattended health review failure. Do not edit any file. Identify the likely root cause, the safest deterministic recovery, and whether user facts are required. Repository: %s. Failure class: %s. Target date: %s.\n\nRecent log:\n' "$REPO_ROOT" "$failure_class" "$target"
    if [ -f "$target_log" ]; then
      /usr/bin/tail -n 160 "$target_log"
    else
      printf 'No target log was found.\n'
    fi
  } | "$codex_bin" -s read-only -a never -C "$REPO_ROOT" exec --ephemeral --color never -o "$diagnostic_file" - || true
  log "diagnostic report: $diagnostic_file"
}

now_epoch="$($DATE '+%s')"
state_values="$(read_watchdog_state)"
previous_signature="$(printf '%s\n' "$state_values" | /usr/bin/sed -n '1p')"
previous_count="$(printf '%s\n' "$state_values" | /usr/bin/sed -n '2p')"
next_retry_epoch="$(printf '%s\n' "$state_values" | /usr/bin/sed -n '3p')"

if [ "$now_epoch" -lt "${next_retry_epoch:-0}" ]; then
  log "circuit open; next retry epoch=$next_retry_epoch"
  exit 0
fi

log "daily review invocation: start"
"$RUNNER"
runner_exit=$?
if [ "$runner_exit" -eq 0 ]; then
  target="$(latest_target)"
  write_watchdog_state "" "0" "0" "none" "$target"
  log "daily review invocation: success"
  exit 0
fi

failure_class="$(classify_exit "$runner_exit")"
target="$(latest_target)"
signature="$failure_class:$runner_exit:$target"
if [ "$signature" = "$previous_signature" ]; then
  failure_count=$((previous_count + 1))
else
  failure_count=1
fi
delay="$(retry_delay "$failure_class" "$failure_count")"
next_retry_epoch=$((now_epoch + delay))
write_watchdog_state "$signature" "$failure_count" "$next_retry_epoch" "$failure_class" "$target"
log "daily review invocation: failed exit=$runner_exit class=$failure_class count=$failure_count retry_in=${delay}s"
write_diagnostic "$failure_class" "$target" "$failure_count"
exit "$runner_exit"
