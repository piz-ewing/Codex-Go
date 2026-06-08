#!/usr/bin/env bash
set -euo pipefail

# Codex Go launcher.
#
# Default action is "start":
#   1. Ensure Codex.app has a ready CDP page target.
#   2. If Codex is already running with CDP, wait for the page target instead of restarting.
#   3. If Codex is already running without CDP, stop it and relaunch with CDP.
#   4. Once CDP is ready, ensure the local Python bridge is running via uv.
#
# "stop" stops the Python bridge and the normal Codex app process.

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

SOURCE_APP="${SOURCE_APP:-/Applications/Codex.app}"
SOURCE_EXECUTABLE="${SOURCE_EXECUTABLE:-}"
SOURCE_BUNDLE_ID="${SOURCE_BUNDLE_ID:-}"
SUPPORT_DIR="${SUPPORT_DIR:-$HOME/Library/Application Support/Codex Go/CDP Worker}"

CDP_PORT="${CDP_PORT:-39443}"
CDP_ADDRESS="${CDP_ADDRESS:-localhost}"
CDP_READY_ADDRESS="${CDP_READY_ADDRESS:-127.0.0.1}"
CDP_READY_TIMEOUT_SECONDS="${CDP_READY_TIMEOUT_SECONDS:-12}"
CODEX_STOP_TIMEOUT_SECONDS="${CODEX_STOP_TIMEOUT_SECONDS:-8}"
WINDOW_SIZE="${WINDOW_SIZE:-980,650}"
LAUNCHER_STDOUT="$SUPPORT_DIR/main-codex-cdp.out.log"
LAUNCHER_STDERR="$SUPPORT_DIR/main-codex-cdp.err.log"

UV_BIN="${UV_BIN:-uv}"
PYTHON_PORT="${PYTHON_PORT:-${PORT:-8080}}"
PYTHON_HOST="${PYTHON_HOST:-${HOST:-0.0.0.0}}"
PYTHON_READY_TIMEOUT_SECONDS="${PYTHON_READY_TIMEOUT_SECONDS:-10}"
PYTHON_STOP_TIMEOUT_SECONDS="${PYTHON_STOP_TIMEOUT_SECONDS:-6}"
PYTHON_PID_FILE="${PYTHON_PID_FILE:-$SUPPORT_DIR/codex-go-python.pid}"
PYTHON_STDOUT="${PYTHON_STDOUT:-$SUPPORT_DIR/codex-go-python.out.log}"
PYTHON_STDERR="${PYTHON_STDERR:-$SUPPORT_DIR/codex-go-python.err.log}"
TOKEN_FILE="${TOKEN_FILE:-$SUPPORT_DIR/codex-go-token}"

ACTION="${1:-start}"
case "$ACTION" in
  --open|--start)
    ACTION="start"
    shift
    ;;
  --stop)
    ACTION="stop"
    shift
    ;;
  --status|--check)
    ACTION="status"
    shift
    ;;
  -h|--help)
    ACTION="help"
    shift
    ;;
  start|stop|status|restart|help)
    if [[ $# -gt 0 ]]; then
      shift
    fi
    ;;
esac

usage() {
  cat <<EOF
Usage: $(basename "$0") [start|stop|restart|status]

Default:
  start

Actions:
  start      Ensure Codex CDP is ready, then ensure Codex Go Python bridge is running.
  stop       Stop the Python bridge and the normal Codex.app process.
  restart    Restart the Python bridge; leave Codex alone when CDP is already running.
  status     Print CDP, Codex, and Python bridge status.

Environment:
  SOURCE_APP                    Default: /Applications/Codex.app
  SUPPORT_DIR                   Default: ~/Library/Application Support/Codex Go/CDP Worker
  CDP_PORT                      Default: 39443
  CDP_ADDRESS                   Default: localhost
  CDP_READY_TIMEOUT_SECONDS     Default: 12
  UV_BIN                        Default: uv
  PYTHON_PORT                   Default: PORT or 8080
  PYTHON_HOST                   Default: HOST or 0.0.0.0
  PYTHON_READY_TIMEOUT_SECONDS  Default: 10
EOF
}

if [[ "$ACTION" == "help" ]]; then
  usage
  exit 0
fi

if [[ $# -gt 0 ]]; then
  echo "Unexpected arguments: $*" >&2
  usage >&2
  exit 64
fi

if [[ "$ACTION" != "start" && "$ACTION" != "stop" && "$ACTION" != "restart" && "$ACTION" != "status" ]]; then
  echo "Unknown action: $ACTION" >&2
  usage >&2
  exit 64
fi

log() {
  printf '%s\n' "$*"
}

warn() {
  printf '%s\n' "$*" >&2
}

require_executable() {
  local file="$1"
  local label="${2:-$1}"
  if [[ ! -x "$file" ]]; then
    warn "Required executable not found: $label ($file)"
    exit 1
  fi
}

resolve_command() {
  local command_name="$1"
  if [[ "$command_name" == */* ]]; then
    if [[ -x "$command_name" ]]; then
      printf '%s\n' "$command_name"
      return 0
    fi
    return 1
  fi
  command -v "$command_name" 2>/dev/null
}

process_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && /bin/kill -0 "$pid" >/dev/null 2>&1
}

terminate_pids() {
  local label="$1"
  local timeout_seconds="$2"
  shift 2
  local pids=()
  local pid
  local alive
  local deadline

  if [[ $# -eq 0 ]]; then
    log "No $label process found."
    return 0
  fi
  pids=("$@")

  for pid in "${pids[@]}"; do
    if process_alive "$pid"; then
      log "Stopping $label pid $pid"
      /bin/kill "$pid" >/dev/null 2>&1 || true
    fi
  done

  deadline=$((SECONDS + timeout_seconds))
  while (( SECONDS < deadline )); do
    alive=0
    for pid in "${pids[@]}"; do
      if process_alive "$pid"; then
        alive=1
        break
      fi
    done
    [[ "$alive" -eq 0 ]] && return 0
    sleep 0.5
  done

  for pid in "${pids[@]}"; do
    if process_alive "$pid"; then
      warn "Force stopping $label pid $pid"
      /bin/kill -KILL "$pid" >/dev/null 2>&1 || true
    fi
  done
}

require_executable /usr/bin/open open
require_executable /usr/bin/curl curl
require_executable /usr/bin/pgrep pgrep
require_executable /bin/ps ps
require_executable /usr/sbin/lsof lsof

if [[ ! -d "$SOURCE_APP" ]]; then
  warn "Source Codex app not found: $SOURCE_APP"
  exit 1
fi

if [[ -z "$SOURCE_EXECUTABLE" ]]; then
  SOURCE_EXECUTABLE="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleExecutable' "$SOURCE_APP/Contents/Info.plist" 2>/dev/null || true)"
fi
if [[ -z "$SOURCE_BUNDLE_ID" ]]; then
  SOURCE_BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$SOURCE_APP/Contents/Info.plist" 2>/dev/null || true)"
fi
SOURCE_EXECUTABLE_PATH="$SOURCE_APP/Contents/MacOS/$SOURCE_EXECUTABLE"
if [[ -z "$SOURCE_EXECUTABLE" || ! -x "$SOURCE_EXECUTABLE_PATH" ]]; then
  warn "Cannot find executable in $SOURCE_APP"
  exit 1
fi

mkdir -p "$SUPPORT_DIR"

UV_BIN_RESOLVED=""
if [[ "$ACTION" == "start" || "$ACTION" == "restart" ]]; then
  UV_BIN_RESOLVED="$(resolve_command "$UV_BIN" || true)"
  if [[ -z "$UV_BIN_RESOLVED" ]]; then
    warn "Cannot find uv executable: $UV_BIN"
    warn "Install uv first, or set UV_BIN to its absolute path."
    exit 1
  fi
fi

cdp_payload_has_codex_main_page() {
  if [[ -x /usr/bin/python3 ]]; then
    /usr/bin/python3 -c 'import json,sys
try:
  items=json.load(sys.stdin)
except Exception:
  sys.exit(1)
for item in items if isinstance(items, list) else []:
  if item.get("type") == "page" and item.get("webSocketDebuggerUrl") and str(item.get("url") or "").startswith("app://-/index.html"):
    sys.exit(0)
sys.exit(1)'
    return $?
  fi

  local payload
  payload="$(cat)"
  [[ "$payload" == *'"type"'*'page'* && "$payload" == *'"webSocketDebuggerUrl"'* && "$payload" == *'"url"'*'app://-/index.html'* ]]
}

cdp_main_page_ready() {
  local ready_address
  local json_payload
  for ready_address in "$CDP_READY_ADDRESS" "127.0.0.1" "[::1]" "localhost"; do
    json_payload="$(/usr/bin/curl -g -fsS --max-time 1 "http://$ready_address:$CDP_PORT/json/list" 2>/dev/null || true)"
    if [[ -n "$json_payload" ]] && cdp_payload_has_codex_main_page <<<"$json_payload"; then
      return 0
    fi
  done
  return 1
}

cdp_port_listener_pids() {
  /usr/sbin/lsof -nP -tiTCP:"$CDP_PORT" -sTCP:LISTEN 2>/dev/null || true
}

cdp_port_listener_commands() {
  /usr/sbin/lsof -nP -iTCP:"$CDP_PORT" -sTCP:LISTEN 2>/dev/null || true
}

cdp_port_has_codex_listener() {
  local listeners
  listeners="$(cdp_port_listener_commands)"
  [[ "$listeners" == *Codex* || "$listeners" == *SkyComput* ]]
}

codex_cdp_listener_pids() {
  local command_name
  local pid
  cdp_port_listener_commands | awk 'NR > 1 && ($1 ~ /Codex/ || $1 ~ /SkyComput/) { print $2 }' | while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_name="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ -z "$command_name" || "$command_name" == *Codex* || "$command_name" == *SkyComputerUseService* || "$command_name" == *"$SOURCE_APP"* ]]; then
      printf '%s\n' "$pid"
    fi
  done
}

python_port_listener_pids() {
  /usr/sbin/lsof -nP -tiTCP:"$PYTHON_PORT" -sTCP:LISTEN 2>/dev/null || true
}

python_bridge_command_line() {
  local pid="$1"
  /bin/ps -p "$pid" -o command= 2>/dev/null || true
}

python_bridge_command_is_ours() {
  local command_line="$1"
  case "$command_line" in
    *"/bin/zsh"*|*"/bin/bash"*|*"COMMAND_EXIT_CODE"*|*"dump_zsh_state"*)
      return 1
      ;;
  esac
  [[ "$command_line" == *"codex_go.main"* || "$command_line" == *"/codex-go-server"* || "$command_line" == *" uv run codex-go-server"* ]]
}

python_port_foreign_listener_pids() {
  local pid
  local command_line
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(python_bridge_command_line "$pid")"
    [[ -n "$command_line" ]] || continue
    if python_bridge_command_is_ours "$command_line"; then
      continue
    fi
    printf '%s\n' "$pid"
  done < <(python_port_listener_pids)
}

running_inside_codex_host() {
  local pid="${PPID:-}"
  local command_line
  local depth=0
  while [[ -n "$pid" && "$pid" -gt 1 && "$depth" -lt 32 ]]; do
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command_line" == "$SOURCE_EXECUTABLE_PATH"* || "$command_line" == *"$SOURCE_APP"* ]]; then
      return 0
    fi
    pid="$(/bin/ps -p "$pid" -o ppid= 2>/dev/null | tr -d ' ' || true)"
    depth=$((depth + 1))
  done
  return 1
}

warn_if_running_inside_codex_host() {
  if running_inside_codex_host; then
    warn "This script is running inside Codex Desktop."
    warn "Skipping Codex.app quit/restart here so this terminal is not closed with Codex."
    warn "Run stop/restart from Terminal.app or iTerm, or quit Codex manually when needed."
    return 0
  fi
  return 1
}

stop_foreign_python_port_listeners() {
  local pids=()
  local pid
  local command_line
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(python_port_foreign_listener_pids)
  if [[ "${#pids[@]}" -eq 0 ]]; then
    return 1
  fi
  for pid in "${pids[@]}"; do
    command_line="$(python_bridge_command_line "$pid")"
    warn "Stopping stale process on Python bridge port $PYTHON_PORT: pid $pid ($command_line)"
  done
  terminate_pids "stale Python bridge port listener" "$PYTHON_STOP_TIMEOUT_SECONDS" ${pids+"${pids[@]}"}
  return 0
}

print_cdp_port_listeners() {
  local listeners
  listeners="$(/usr/sbin/lsof -nP -iTCP:"$CDP_PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$listeners" ]]; then
    printf 'Processes listening on CDP port %s:\n%s\n' "$CDP_PORT" "$listeners"
  else
    printf 'No process is listening on CDP port %s.\n' "$CDP_PORT"
  fi
}

print_python_port_listeners() {
  local listeners
  listeners="$(/usr/sbin/lsof -nP -iTCP:"$PYTHON_PORT" -sTCP:LISTEN 2>/dev/null || true)"
  if [[ -n "$listeners" ]]; then
    printf 'Processes listening on Python bridge port %s:\n%s\n' "$PYTHON_PORT" "$listeners"
  else
    printf 'No process is listening on Python bridge port %s.\n' "$PYTHON_PORT"
  fi
}

normal_codex_pids() {
  local pid
  local command_line
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    [[ -n "$command_line" ]] || continue
    if [[ "$command_line" == "$SOURCE_EXECUTABLE_PATH"* ]]; then
      printf '%s\n' "$pid"
    fi
  done < <(/usr/bin/pgrep -f -- "$SOURCE_EXECUTABLE_PATH" 2>/dev/null || true)
}

normal_codex_is_running() {
  [[ -n "$(normal_codex_pids)" ]]
}

codex_process_has_cdp_enabled() {
  local command_line="$1"
  [[ "$command_line" == *"--remote-debugging-port=$CDP_PORT"* ]]
}

codex_cdp_instance_running() {
  local pid
  local command_line

  if cdp_port_has_codex_listener; then
    return 0
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    if codex_process_has_cdp_enabled "$command_line"; then
      return 0
    fi
  done < <(normal_codex_pids)
  return 1
}

wait_for_cdp_main_page() {
  local relaunch_on_cleanup="${1:-0}"
  local deadline=$((SECONDS + CDP_READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if cdp_main_page_ready; then
      return 0
    fi
    if kill_skycomputeruse_on_cdp_port_if_blocking; then
      sleep 0.5
      if [[ "$relaunch_on_cleanup" -eq 1 ]]; then
        launch_main_codex_with_cdp
      fi
    fi
    sleep 1
  done
  return 1
}

print_codex_processes() {
  local pid
  local command_line
  local found=1
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    [[ -n "$command_line" ]] || continue
    printf 'Codex process %s: %s\n' "$pid" "$command_line"
    found=0
  done < <(normal_codex_pids)
  if [[ "$found" -ne 0 ]]; then
    printf 'No normal Codex app process found.\n'
  fi
}

stop_normal_codex_processes() {
  local pids=()
  local pid
  if warn_if_running_inside_codex_host; then
    return 0
  fi
  if [[ -n "$SOURCE_BUNDLE_ID" ]]; then
    /usr/bin/osascript -e "tell application id \"$SOURCE_BUNDLE_ID\" to quit" >/dev/null 2>&1 || true
    sleep 1
  fi
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(normal_codex_pids)
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(codex_cdp_listener_pids)
  terminate_pids "Codex" "$CODEX_STOP_TIMEOUT_SECONDS" ${pids+"${pids[@]}"}
}

kill_skycomputeruse_on_cdp_port_if_blocking() {
  local pid
  local command_line
  local killed=1
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    if [[ "$command_line" == *"SkyComputerUseService"* ]]; then
      warn "Killing SkyComputerUseService blocking CDP port $CDP_PORT (pid $pid)"
      /bin/kill "$pid" >/dev/null 2>&1 || true
      killed=0
    fi
  done < <(cdp_port_listener_pids)
  return "$killed"
}

launch_main_codex_with_cdp() {
  local allow_origins
  allow_origins="http://$CDP_ADDRESS:$CDP_PORT,http://127.0.0.1:$CDP_PORT,http://localhost:$CDP_PORT"
  : >"$LAUNCHER_STDOUT"
  : >"$LAUNCHER_STDERR"
  /usr/bin/open -n "$SOURCE_APP" --args \
    "--remote-debugging-address=$CDP_ADDRESS" \
    "--remote-debugging-port=$CDP_PORT" \
    "--remote-allow-origins=$allow_origins" \
    "--window-size=$WINDOW_SIZE" \
    >"$LAUNCHER_STDOUT" 2>"$LAUNCHER_STDERR"
}

print_launch_failure_context() {
  {
    echo "Codex.app was launched, but CDP did not become ready within ${CDP_READY_TIMEOUT_SECONDS}s"
    echo "stdout log: $LAUNCHER_STDOUT"
    echo "stderr log: $LAUNCHER_STDERR"
    echo
    print_runtime_status
    if [[ -s "$LAUNCHER_STDERR" ]]; then
      echo
      echo "Recent launcher stderr:"
      tail -n 20 "$LAUNCHER_STDERR" 2>/dev/null || true
    fi
  } >&2
}

ensure_codex_cdp() {
  local deadline

  if cdp_main_page_ready; then
    log "Codex CDP target already ready: http://$CDP_READY_ADDRESS:$CDP_PORT/json/list"
    return 0
  fi

  if kill_skycomputeruse_on_cdp_port_if_blocking; then
    sleep 0.5
  fi

  if cdp_main_page_ready; then
    log "Codex CDP target ready after port cleanup."
    return 0
  fi

  if codex_cdp_instance_running; then
    log "Codex CDP instance already running; waiting for page target without restarting Codex."
    if wait_for_cdp_main_page; then
      log "Codex CDP target ready: http://$CDP_READY_ADDRESS:$CDP_PORT/json/list"
      return 0
    fi
    warn "Codex CDP instance is running, but the page target did not become ready within ${CDP_READY_TIMEOUT_SECONDS}s."
    print_launch_failure_context
    exit 2
  fi

  if normal_codex_is_running; then
    if warn_if_running_inside_codex_host; then
      warn "Codex is running without CDP, but cannot restart it from inside Codex."
      warn "Quit Codex manually, then run this script again from Terminal.app or iTerm."
      exit 3
    fi
    log "Codex is running without CDP; restarting it with CDP."
    stop_normal_codex_processes
    sleep 1
  fi

  if [[ -n "$(cdp_port_listener_pids)" ]]; then
    warn "CDP port $CDP_PORT is occupied but no Codex page target is ready."
    print_cdp_port_listeners >&2
    exit 4
  fi

  log "Launching Codex.app with CDP on port $CDP_PORT."
  launch_main_codex_with_cdp

  if wait_for_cdp_main_page 1; then
    log "Opened Codex.app with CDP: http://$CDP_READY_ADDRESS:$CDP_PORT/json/list"
    return 0
  fi

  print_launch_failure_context
  exit 2
}

load_access_token() {
  local new_token
  if [[ -n "${CODEX_GO_TOKEN:-}" ]]; then
    return 0
  fi
  if [[ -f "$TOKEN_FILE" ]]; then
    CODEX_GO_TOKEN="$(tr -d '\r\n' <"$TOKEN_FILE")"
  fi
  if [[ -z "${CODEX_GO_TOKEN:-}" ]]; then
    if command -v uuidgen >/dev/null 2>&1; then
      new_token="$(uuidgen | tr '[:upper:]' '[:lower:]')"
    else
      new_token="codex-go-$(date +%s)-$$"
    fi
    CODEX_GO_TOKEN="$new_token"
    printf '%s\n' "$CODEX_GO_TOKEN" >"$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE" >/dev/null 2>&1 || true
  fi
  export CODEX_GO_TOKEN
}

python_bridge_pids() {
  local pid
  local command_line
  local pid_file_pid
  local seen_pids=" "

  append_python_bridge_pid() {
    local candidate="$1"
    [[ -n "$candidate" ]] || return 0
    case "$seen_pids" in
      *" $candidate "*) return 0 ;;
    esac
    seen_pids="${seen_pids}${candidate} "
    printf '%s\n' "$candidate"
  }

  if [[ -f "$PYTHON_PID_FILE" ]]; then
    pid_file_pid="$(tr -dc '0-9' <"$PYTHON_PID_FILE" || true)"
    if [[ -n "$pid_file_pid" ]]; then
      command_line="$(python_bridge_command_line "$pid_file_pid")"
      if python_bridge_command_is_ours "$command_line"; then
        append_python_bridge_pid "$pid_file_pid"
      fi
    fi
  fi

  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(python_bridge_command_line "$pid")"
    python_bridge_command_is_ours "$command_line" || continue
    append_python_bridge_pid "$pid"
  done < <(/usr/bin/pgrep -f -- "[/]codex-go-server|codex_go\.main" 2>/dev/null || true)
}

python_bridge_is_running() {
  [[ -n "$(python_bridge_pids)" ]]
}

python_health_ready() {
  load_access_token
  /usr/bin/curl -g -fsS --max-time 1 "http://127.0.0.1:$PYTHON_PORT/codex/health?token=$CODEX_GO_TOKEN" >/dev/null 2>&1
}

python_health_http_code() {
  load_access_token
  /usr/bin/curl -g -s -o /dev/null -w '%{http_code}' --max-time 1 "http://127.0.0.1:$PYTHON_PORT/codex/health?token=$CODEX_GO_TOKEN" 2>/dev/null || true
}

print_python_processes() {
  local pid
  local command_line
  local found=1
  while IFS= read -r pid; do
    [[ -n "$pid" ]] || continue
    command_line="$(/bin/ps -p "$pid" -o command= 2>/dev/null || true)"
    [[ -n "$command_line" ]] || continue
    printf 'Python bridge process %s: %s\n' "$pid" "$command_line"
    found=0
  done < <(python_bridge_pids)
  if [[ "$found" -ne 0 ]]; then
    printf 'No Codex Go Python bridge process found.\n'
  fi
}

ensure_python_bridge() {
  local deadline
  local pid

  load_access_token

  if python_bridge_is_running; then
    if python_health_ready; then
      log "Python bridge already running on port $PYTHON_PORT."
      print_mobile_access_urls
      return 0
    fi
    warn "Python bridge process is running, but health check failed; restarting with launcher token."
    stop_python_bridge
    sleep 0.5
  fi

  if [[ -n "$(python_port_foreign_listener_pids)" ]]; then
    stop_foreign_python_port_listeners
    sleep 0.5
  fi

  if python_health_ready; then
    log "Python bridge already healthy on port $PYTHON_PORT."
    print_mobile_access_urls
    return 0
  fi

  if [[ -n "$(python_port_listener_pids)" ]]; then
    warn "Python bridge port $PYTHON_PORT is already occupied; not starting another bridge."
    print_python_port_listeners >&2
    exit 5
  fi

  log "Starting Codex Go Python bridge with uv."
  : >"$PYTHON_STDOUT"
  : >"$PYTHON_STDERR"
  (
    cd "$SCRIPT_DIR"
    PORT="$PYTHON_PORT" \
    HOST="$PYTHON_HOST" \
    CODEX_GO_TOKEN="$CODEX_GO_TOKEN" \
    CODEX_GO_CDP_PORT="$CDP_PORT" \
    CODEX_GO_CDP_HOST="$CDP_ADDRESS" \
    "$UV_BIN_RESOLVED" run codex-go-server
  ) >"$PYTHON_STDOUT" 2>"$PYTHON_STDERR" &
  pid="$!"
  printf '%s\n' "$pid" >"$PYTHON_PID_FILE"

  deadline=$((SECONDS + PYTHON_READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    if ! process_alive "$pid"; then
      warn "Python bridge exited during startup."
      warn "stdout log: $PYTHON_STDOUT"
      warn "stderr log: $PYTHON_STDERR"
      [[ -s "$PYTHON_STDERR" ]] && tail -n 20 "$PYTHON_STDERR" >&2 || true
      exit 6
    fi
    if python_health_ready; then
      log "Python bridge ready on port $PYTHON_PORT."
      log "Python logs: $PYTHON_STDOUT / $PYTHON_STDERR"
      print_mobile_access_urls
      return 0
    fi
    sleep 1
  done

  warn "Python bridge started, but health did not become ready within ${PYTHON_READY_TIMEOUT_SECONDS}s."
  warn "stdout log: $PYTHON_STDOUT"
  warn "stderr log: $PYTHON_STDERR"
  [[ -s "$PYTHON_STDERR" ]] && tail -n 20 "$PYTHON_STDERR" >&2 || true
  exit 6
}

stop_python_bridge() {
  local pids=()
  local pid
  while IFS= read -r pid; do
    [[ -n "$pid" ]] && pids+=("$pid")
  done < <(python_bridge_pids)
  terminate_pids "Codex Go Python bridge" "$PYTHON_STOP_TIMEOUT_SECONDS" ${pids+"${pids[@]}"}
  rm -f "$PYTHON_PID_FILE"
}

primary_lan_ipv4() {
  local iface ip
  for iface in en0 en1 bridge0; do
    ip="$(/usr/sbin/ipconfig getifaddr "$iface" 2>/dev/null || true)"
    if [[ -n "$ip" ]]; then
      printf '%s\n' "$ip"
      return 0
    fi
  done
  if [[ -x /usr/bin/python3 ]]; then
    /usr/bin/python3 - <<'PY'
import socket

for info in socket.getaddrinfo(socket.gethostname(), None):
    if info[0] == socket.AF_INET:
        addr = info[4][0]
        if not addr.startswith("127."):
            print(addr)
            break
PY
  fi
}

print_mobile_access_urls() {
  load_access_token
  local lan_ip lan_url local_url
  lan_ip="$(primary_lan_ipv4 2>/dev/null | head -n 1 || true)"
  local_url="http://localhost:$PYTHON_PORT/?token=$CODEX_GO_TOKEN"

  printf '\n'
  printf '%s\n' '========================================'
  printf '%s\n' 'Mobile URLs (copy the full line, including token)'
  printf '%s\n' '========================================'
  if [[ -n "$lan_ip" ]]; then
    lan_url="http://$lan_ip:$PYTHON_PORT/?token=$CODEX_GO_TOKEN"
    printf '%s\n' "LAN:    $lan_url"
  else
    warn 'LAN URL unavailable (no IPv4 detected on en0/en1).'
  fi
  printf '%s\n' "Local:  $local_url"
  printf '%s\n' '========================================'
  printf '\n'
}

print_runtime_status() {
  if cdp_main_page_ready; then
    printf 'CDP status: ready at http://%s:%s/json/list\n' "$CDP_READY_ADDRESS" "$CDP_PORT"
  else
    printf 'CDP status: not ready at http://%s:%s/json/list\n' "$CDP_READY_ADDRESS" "$CDP_PORT"
  fi
  print_cdp_port_listeners
  print_codex_processes
  if python_bridge_is_running && python_health_ready; then
    load_access_token
    printf 'Python bridge status: healthy on port %s\n' "$PYTHON_PORT"
    print_mobile_access_urls
  elif python_bridge_is_running; then
    if [[ "$(python_health_http_code)" == "401" ]]; then
      printf 'Python bridge status: process running, but token does not match %s.\n' "$TOKEN_FILE"
      printf 'Run ./launch-codex-go.sh restart to restart the bridge with the launcher token.\n'
    else
      printf 'Python bridge status: process running, health check not ready.\n'
    fi
  elif python_health_ready; then
    printf 'Python bridge status: health check passed, but no Codex Go Python bridge process was found.\n'
  elif [[ -n "$(python_port_foreign_listener_pids)" ]]; then
    local foreign_pid foreign_command
    foreign_pid="$(python_port_foreign_listener_pids | head -n 1)"
    foreign_command="$(python_bridge_command_line "$foreign_pid")"
    printf 'Python bridge status: not running; port %s is occupied by pid %s (%s).\n' "$PYTHON_PORT" "$foreign_pid" "$foreign_command"
  else
    printf 'Python bridge status: not running.\n'
  fi
  print_python_processes
  print_python_port_listeners
}

print_prepared() {
  log "Codex Go launcher"
  log "Codex app: $SOURCE_APP"
  log "Executable: $SOURCE_EXECUTABLE_PATH"
  log "CDP: http://$CDP_READY_ADDRESS:$CDP_PORT/json/list"
  log "Python bridge: http://localhost:$PYTHON_PORT/"
  log "Support dir: $SUPPORT_DIR"
}

case "$ACTION" in
  start)
    print_prepared
    ensure_codex_cdp
    ensure_python_bridge
    ;;
  stop)
    print_prepared
    stop_python_bridge
    stop_normal_codex_processes
    ;;
  restart)
    print_prepared
    stop_python_bridge
    if codex_cdp_instance_running || cdp_main_page_ready; then
      log "Codex CDP already running; skipping Codex stop during restart."
    else
      stop_normal_codex_processes
    fi
    ensure_codex_cdp
    ensure_python_bridge
    ;;
  status)
    print_prepared
    print_runtime_status
    ;;
esac
