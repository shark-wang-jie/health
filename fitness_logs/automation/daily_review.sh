#!/bin/bash

set -u
set -o pipefail

REPO_ROOT="${HEALTH_REPO_ROOT:-/Users/wangjie/Documents/health}"
AUTOMATION_DIR="$REPO_ROOT/fitness_logs/automation"
PROMPT_FILE="$AUTOMATION_DIR/daily_codex_prompt.md"
LOG_DIR="${HEALTH_LOG_DIR:-/Users/wangjie/Library/Logs/health}"
LOCK_DIR="${HEALTH_LOCK_DIR:-/Users/wangjie/Library/Caches/com.wangjie.health.daily-review.lock}"
STATE_ROOT="${HEALTH_STATE_ROOT:-/Users/wangjie/Library/Application Support/health-daily-review/state}"
PENDING_DIR="$STATE_ROOT/pending"
COMPLETED_DIR="$STATE_ROOT/completed"

GIT="/usr/bin/git"
PYTHON3="/opt/homebrew/bin/python3"
JQ="/opt/homebrew/bin/jq"
CODEX="/Applications/ChatGPT.app/Contents/Resources/codex"
DATE="/bin/date"
MKDIR="/bin/mkdir"
RM="/bin/rm"
MV="/bin/mv"
CAT="/bin/cat"
SLEEP="/bin/sleep"
SCUTIL="/usr/sbin/scutil"
AWK="/usr/bin/awk"

export HOME="/Users/wangjie"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/Applications/ChatGPT.app/Contents/Resources"
export TZ="Asia/Shanghai"

SCHEDULED_DATE="$($PYTHON3 - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
print((today - timedelta(days=1)).isoformat())
PY
)"

$MKDIR -p "$LOG_DIR" "/Users/wangjie/Library/Caches" "$PENDING_DIR" "$COMPLETED_DIR"

if [ -n "${HEALTH_TARGET_DATE:-}" ]; then
  TARGET_DATE="$HEALTH_TARGET_DATE"
else
  TARGET_DATE=""
  for pending_file in "$PENDING_DIR"/*.pending; do
    [ -e "$pending_file" ] || continue
    candidate="${pending_file##*/}"
    candidate="${candidate%.pending}"
    case "$candidate" in
      ????-??-??)
        if [ "$candidate" \> "$SCHEDULED_DATE" ]; then
          continue
        fi
        if [ -z "$TARGET_DATE" ] || [ "$candidate" \< "$TARGET_DATE" ]; then
          TARGET_DATE="$candidate"
        fi
        ;;
    esac
  done
  TARGET_DATE="${TARGET_DATE:-$SCHEDULED_DATE}"
fi
TARGET_MONTH="${TARGET_DATE%-*}"
TARGET_FILE="$REPO_ROOT/fitness_logs/daily/$TARGET_MONTH/$TARGET_DATE.json"
LOG_FILE="$LOG_DIR/daily-review-$TARGET_DATE.log"
CODEX_LAST_MESSAGE="$LOG_DIR/codex-last-message-$TARGET_DATE-$$.txt"
PENDING_FILE="$PENDING_DIR/$TARGET_DATE.pending"
COMPLETED_FILE="$COMPLETED_DIR/$TARGET_DATE.sha256"
LOCK_OWNED=0
COMPLETED=0

: >"$PENDING_FILE"
exec >>"$LOG_FILE" 2>&1

timestamp() {
  "$DATE" '+%Y-%m-%d %H:%M:%S %Z'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

configure_system_proxy() {
  if [ -n "${HTTPS_PROXY:-${https_proxy:-}}" ] || [ ! -x "$SCUTIL" ]; then
    return 0
  fi
  proxy_settings="$($SCUTIL --proxy 2>/dev/null || true)"
  https_enabled="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPSEnable" && $2 == ":" {print $3; exit}')"
  https_host="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPSProxy" && $2 == ":" {print $3; exit}')"
  https_port="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPSPort" && $2 == ":" {print $3; exit}')"
  if [ "$https_enabled" = "1" ] && [ -n "$https_host" ] && [ -n "$https_port" ]; then
    HTTPS_PROXY="http://$https_host:$https_port"
    https_proxy="$HTTPS_PROXY"
    export HTTPS_PROXY https_proxy
    log "network environment: imported enabled macOS HTTPS proxy"
  fi

  http_enabled="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPEnable" && $2 == ":" {print $3; exit}')"
  http_host="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPProxy" && $2 == ":" {print $3; exit}')"
  http_port="$(printf '%s\n' "$proxy_settings" | $AWK '$1 == "HTTPPort" && $2 == ":" {print $3; exit}')"
  if [ "$http_enabled" = "1" ] && [ -n "$http_host" ] && [ -n "$http_port" ]; then
    HTTP_PROXY="http://$http_host:$http_port"
    http_proxy="$HTTP_PROXY"
    export HTTP_PROXY http_proxy
  fi

  if [ -z "${NO_PROXY:-${no_proxy:-}}" ]; then
    NO_PROXY="localhost,127.0.0.1,::1"
    no_proxy="$NO_PROXY"
    export NO_PROXY no_proxy
  fi
}

retry_delay() {
  case "$1" in
    1) printf '%s\n' "${HEALTH_RETRY_DELAY_1_SECONDS:-15}" ;;
    *) printf '%s\n' "${HEALTH_RETRY_DELAY_2_SECONDS:-45}" ;;
  esac
}

network_retry() {
  retry_label="$1"
  shift
  retry_max="${HEALTH_NETWORK_ATTEMPTS:-3}"
  retry_attempt=1
  while :; do
    log "$retry_label: attempt $retry_attempt/$retry_max"
    if "$@"; then
      log "$retry_label: success"
      return 0
    fi
    if [ "$retry_attempt" -ge "$retry_max" ]; then
      log "$retry_label: failed after $retry_max attempts"
      return 1
    fi
    retry_wait="$(retry_delay "$retry_attempt")"
    log "$retry_label: retrying in ${retry_wait}s"
    "$SLEEP" "$retry_wait"
    retry_attempt=$((retry_attempt + 1))
  done
}

review_fingerprint() {
  "$PYTHON3" - "$REPO_ROOT" "$TARGET_FILE" <<'PY'
import hashlib
import sys
from pathlib import Path

root = Path(sys.argv[1])
target = Path(sys.argv[2])
paths = [
    root / "README.md",
    root / "fitness_logs/AGENTS.md",
    root / "fitness_logs/README.md",
    root / "fitness_logs/CHATGPT_CODEX_WORKFLOW.md",
    root / "fitness_logs/handoff_summary.md",
    root / "fitness_logs/current_plan.json",
    root / "fitness_logs/food_catalog.json",
    root / "fitness_logs/record_tools.py",
    root / "fitness_logs/automation/daily_codex_prompt.md",
    target,
]
digest = hashlib.sha256()
for path in paths:
    try:
        name = str(path.relative_to(root))
    except ValueError:
        name = str(path)
    digest.update(name.encode("utf-8"))
    digest.update(b"\0")
    if path.is_file():
        digest.update(path.read_bytes())
    else:
        digest.update(b"<missing>")
    digest.update(b"\0")
print(digest.hexdigest())
PY
}

mark_completed() {
  completed_fingerprint="$(review_fingerprint)" || return 1
  completed_temp="$COMPLETED_FILE.tmp.$$"
  printf '%s\n' "$completed_fingerprint" >"$completed_temp"
  $MV "$completed_temp" "$COMPLETED_FILE"
  $RM -f "$PENDING_FILE"
  COMPLETED=1
  log "completion state: saved fingerprint=$completed_fingerprint"
}

finish() {
  exit_code=$?
  if [ -f "$CODEX_LAST_MESSAGE" ]; then
    $RM -f "$CODEX_LAST_MESSAGE"
  fi
  if [ "$LOCK_OWNED" -eq 1 ] && [ -f "$LOCK_DIR/pid" ] && [ "$(cat "$LOCK_DIR/pid" 2>/dev/null || true)" = "$$" ]; then
    $RM -rf "$LOCK_DIR"
  fi
  if [ "$exit_code" -eq 0 ]; then
    log "task end: success"
  else
    log "retry state: pending target retained at $PENDING_FILE"
    log "task end: failure exit_code=$exit_code"
  fi
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

log "task start"
log "target date: $TARGET_DATE"
if [ "$TARGET_DATE" != "$SCHEDULED_DATE" ]; then
  log "catch-up target selected; scheduled previous day is $SCHEDULED_DATE"
fi
log "repository: $REPO_ROOT"
configure_system_proxy

if ! $MKDIR "$LOCK_DIR" 2>/dev/null; then
  existing_pid="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
  if [ -n "$existing_pid" ] && kill -0 "$existing_pid" 2>/dev/null; then
    log "failure reason: another daily review is running pid=$existing_pid"
    exit 75
  fi
  stale_lock="$LOCK_DIR.stale.$$"
  if ! $MV "$LOCK_DIR" "$stale_lock" 2>/dev/null || ! $MKDIR "$LOCK_DIR" 2>/dev/null; then
    log "failure reason: could not replace stale lock directory"
    exit 75
  fi
  $RM -rf "$stale_lock"
  log "removed stale lock"
fi
printf '%s\n' "$$" >"$LOCK_DIR/pid"
LOCK_OWNED=1

for dependency in "$GIT" "$PYTHON3" "$JQ" "$CODEX"; do
  if [ ! -x "$dependency" ]; then
    log "failure reason: dependency is not executable: $dependency"
    exit 69
  fi
done
if [ ! -r "$PROMPT_FILE" ]; then
  log "failure reason: missing semantic review prompt: $PROMPT_FILE"
  exit 69
fi

if ! cd "$REPO_ROOT"; then
  log "failure reason: cannot enter repository"
  exit 72
fi

actual_root="$($GIT rev-parse --show-toplevel 2>/dev/null || true)"
branch="$($GIT branch --show-current 2>/dev/null || true)"
if [ "$actual_root" != "$REPO_ROOT" ] || [ "$branch" != "main" ]; then
  log "failure reason: expected repository root $REPO_ROOT on main; got root=$actual_root branch=$branch"
  exit 72
fi

status_before="$($GIT status --porcelain)"
if [ -n "$status_before" ]; then
  log "failure reason: working tree contains pre-existing changes; no files were modified"
  printf '%s\n' "$status_before"
  exit 65
fi

log "current git commit: $($GIT rev-parse HEAD)"
if ! network_retry "git fetch" $GIT fetch origin; then
  log "failure reason: git fetch failed"
  exit 70
fi

log "git rebase origin/main: start"
if ! $GIT rebase origin/main; then
  log "failure reason: git rebase origin/main failed or conflicted; manual resolution required"
  exit 70
fi
log "pull result: success via fetched origin/main and local rebase head=$($GIT rev-parse HEAD)"
synced_remote_sha="$($GIT rev-parse origin/main)"

ahead_count="$($GIT rev-list --count origin/main..HEAD)"
if [ "$ahead_count" -gt 0 ]; then
  unexpected_subjects="$($GIT log --format='%s' origin/main..HEAD | /usr/bin/grep -Ev '^fitness: automated review [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]$' || true)"
  if [ -n "$unexpected_subjects" ]; then
    log "failure reason: local commits ahead of origin/main are not recognized automation commits"
    printf '%s\n' "$unexpected_subjects"
    exit 65
  fi
  log "recovery push: found $ahead_count previously committed automated review commit(s)"
  if ! network_retry "recovery push" $GIT push origin main; then
    log "failure reason: recovery push failed; commit retained locally"
    exit 74
  fi
  synced_remote_sha="$($GIT rev-parse origin/main)"
fi

current_fingerprint="$(review_fingerprint)" || {
  log "failure reason: could not calculate review fingerprint"
  exit 69
}
if [ -f "$COMPLETED_FILE" ] && [ "$(cat "$COMPLETED_FILE" 2>/dev/null || true)" = "$current_fingerprint" ]; then
  log "review result: skipped; target and review rules unchanged since successful review"
  $RM -f "$PENDING_FILE"
  COMPLETED=1
  exit 0
fi

if [ ! -f "$TARGET_FILE" ]; then
  log "deterministic review result: 目标日无记录文件"
  log "Codex semantic review result: skipped because target file is absent"
  log "modified files: none"
  log "commit SHA: none"
  log "push result: skipped"
  log "pending questions: none"
  if ! mark_completed; then
    log "failure reason: could not save completion state"
    exit 69
  fi
  exit 0
fi

log "stage A deterministic review: start"
if ! "$PYTHON3" fitness_logs/record_tools.py recalculate "$TARGET_FILE"; then
  log "recalculate result: failed"
  exit 66
fi
log "recalculate result: success"
if ! "$PYTHON3" fitness_logs/record_tools.py validate "$TARGET_FILE"; then
  log "validate result: failed"
  exit 66
fi
log "validate result: success"
if ! "$PYTHON3" fitness_logs/record_tools.py report "$TARGET_FILE"; then
  log "report result: failed"
  exit 66
fi
log "report result: success"
if ! "$JQ" empty "$TARGET_FILE"; then
  log "jq result: failed"
  exit 66
fi
log "jq result: success"
log "deterministic review result: success"

log "stage B Codex semantic review: start"
if ! {
  $CAT "$PROMPT_FILE"
  printf '\n\nRuntime values:\n- repository: %s\n- target date: %s\n- target JSON: %s\n' "$REPO_ROOT" "$TARGET_DATE" "$TARGET_FILE"
} | "$CODEX" -s workspace-write -a never -C "$REPO_ROOT" exec --ephemeral --color never -o "$CODEX_LAST_MESSAGE" -; then
  log "Codex semantic review result: failed"
  exit 67
fi
log "Codex semantic review result: success"
if [ -s "$CODEX_LAST_MESSAGE" ]; then
  log "Codex semantic review summary:"
  $CAT "$CODEX_LAST_MESSAGE"
fi

log "post-Codex deterministic verification: start"
if ! "$PYTHON3" fitness_logs/record_tools.py recalculate "$TARGET_FILE"; then
  log "post-Codex recalculate result: failed"
  exit 68
fi
log "post-Codex recalculate result: success"
if ! "$PYTHON3" fitness_logs/record_tools.py validate "$TARGET_FILE"; then
  log "post-Codex validate result: failed"
  exit 68
fi
log "post-Codex validate result: success"
if ! "$PYTHON3" fitness_logs/record_tools.py report "$TARGET_FILE"; then
  log "post-Codex report result: failed"
  exit 68
fi
log "post-Codex report result: success"
if ! "$JQ" empty "$TARGET_FILE"; then
  log "post-Codex jq result: failed"
  exit 68
fi
log "post-Codex jq result: success"

pending="$($JQ -c '{missing_sections: (.missing_sections // []), non_energy_pending_notes: (.non_energy_pending_notes // [])}' "$TARGET_FILE")"
log "pending questions: $pending"

if ! $GIT diff --check; then
  log "failure reason: git diff --check failed"
  exit 68
fi

modified_files="$({ $GIT diff --name-only; $GIT ls-files --others --exclude-standard; } | /usr/bin/sort -u)"
if [ -z "$modified_files" ]; then
  log "modified files: none"
  log "commit SHA: none"
  log "push result: skipped; no actual changes"
  if ! mark_completed; then
    log "failure reason: could not save completion state"
    exit 69
  fi
  exit 0
fi
log "modified files:"
printf '%s\n' "$modified_files"

invalid_files="$(printf '%s\n' "$modified_files" | /usr/bin/awk '$0 !~ /^fitness_logs\// {print}')"
if [ -n "$invalid_files" ]; then
  log "failure reason: review modified files outside fitness_logs"
  printf '%s\n' "$invalid_files"
  exit 68
fi

$GIT diff -- fitness_logs/
$GIT add fitness_logs/
staged_files="$($GIT diff --cached --name-only)"
if [ -z "$staged_files" ]; then
  log "commit SHA: none"
  log "push result: skipped; no staged changes"
  if ! mark_completed; then
    log "failure reason: could not save completion state"
    exit 69
  fi
  exit 0
fi
log "staged files:"
printf '%s\n' "$staged_files"
$GIT diff --cached --check
$GIT diff --cached --stat

if ! $GIT commit -m "fitness: automated review $TARGET_DATE"; then
  log "failure reason: git commit failed"
  exit 71
fi
commit_sha="$($GIT rev-parse HEAD)"
log "commit SHA: $commit_sha"

if ! network_retry "pre-push git fetch" $GIT fetch origin; then
  log "push result: skipped because pre-push fetch failed"
  exit 70
fi
current_remote_sha="$($GIT rev-parse origin/main)"
if [ "$current_remote_sha" != "$synced_remote_sha" ]; then
  log "push result: skipped because origin/main changed during review"
  log "failure reason: remote race synced=$synced_remote_sha current=$current_remote_sha; no force push attempted"
  exit 73
fi

if ! network_retry "git push" $GIT push origin main; then
  $GIT fetch origin || true
  log "push result: failed; no force push attempted"
  log "failure reason: origin/main changed or network/authentication failed; manual review required"
  exit 74
fi
log "push result: success commit=$commit_sha"
if ! mark_completed; then
  log "failure reason: push succeeded but completion state could not be saved"
  exit 69
fi
