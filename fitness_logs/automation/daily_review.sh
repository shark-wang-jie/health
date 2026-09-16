#!/bin/bash

set -u
set -o pipefail

REPO_ROOT="/Users/wangjie/Documents/health"
AUTOMATION_DIR="$REPO_ROOT/fitness_logs/automation"
PROMPT_FILE="$AUTOMATION_DIR/daily_codex_prompt.md"
LOG_DIR="/Users/wangjie/Library/Logs/health"
LOCK_DIR="/Users/wangjie/Library/Caches/com.wangjie.health.daily-review.lock"

GIT="/usr/bin/git"
PYTHON3="/opt/homebrew/bin/python3"
JQ="/opt/homebrew/bin/jq"
CODEX="/Applications/ChatGPT.app/Contents/Resources/codex"
DATE="/bin/date"
MKDIR="/bin/mkdir"
RM="/bin/rm"
MV="/bin/mv"
CAT="/bin/cat"

export HOME="/Users/wangjie"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:/Applications/ChatGPT.app/Contents/Resources"
export TZ="Asia/Shanghai"

TARGET_DATE="${HEALTH_TARGET_DATE:-$($PYTHON3 - <<'PY'
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
print((today - timedelta(days=1)).isoformat())
PY
)}"
TARGET_MONTH="${TARGET_DATE%-*}"
TARGET_FILE="$REPO_ROOT/fitness_logs/daily/$TARGET_MONTH/$TARGET_DATE.json"
LOG_FILE="$LOG_DIR/daily-review-$TARGET_DATE.log"
CODEX_LAST_MESSAGE="$LOG_DIR/codex-last-message-$TARGET_DATE-$$.txt"
LOCK_OWNED=0

$MKDIR -p "$LOG_DIR" "/Users/wangjie/Library/Caches"
exec >>"$LOG_FILE" 2>&1

timestamp() {
  "$DATE" '+%Y-%m-%d %H:%M:%S %Z'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
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
    log "task end: failure exit_code=$exit_code"
  fi
}
trap finish EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
trap 'exit 129' HUP

log "task start"
log "target date: $TARGET_DATE"
log "repository: $REPO_ROOT"

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
log "git fetch: start"
if ! $GIT fetch origin; then
  log "failure reason: git fetch failed"
  exit 70
fi
log "git fetch: success"

log "git pull --rebase: start"
if ! $GIT pull --rebase origin main; then
  log "failure reason: git pull --rebase failed or conflicted; manual resolution required"
  exit 70
fi
log "pull result: success head=$($GIT rev-parse HEAD)"
synced_remote_sha="$($GIT rev-parse origin/main)"

if [ ! -f "$TARGET_FILE" ]; then
  log "deterministic review result: 目标日无记录文件"
  log "Codex semantic review result: skipped because target file is absent"
  log "modified files: none"
  log "commit SHA: none"
  log "push result: skipped"
  log "pending questions: none"
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
} | "$CODEX" exec --ephemeral --color never --sandbox workspace-write --ask-for-approval never --cd "$REPO_ROOT" --output-last-message "$CODEX_LAST_MESSAGE" -; then
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

if ! $GIT fetch origin; then
  log "push result: skipped because pre-push fetch failed"
  exit 70
fi
current_remote_sha="$($GIT rev-parse origin/main)"
if [ "$current_remote_sha" != "$synced_remote_sha" ]; then
  log "push result: skipped because origin/main changed during review"
  log "failure reason: remote race synced=$synced_remote_sha current=$current_remote_sha; no force push attempted"
  exit 73
fi

if ! $GIT push origin main; then
  $GIT fetch origin || true
  log "push result: failed; no force push attempted"
  log "failure reason: origin/main changed or network/authentication failed; manual review required"
  exit 74
fi
log "push result: success commit=$commit_sha"
