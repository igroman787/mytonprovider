#!/usr/bin/env bash
# Wrapper to emulate: systemctl is-active [--quiet] <service>
# Proxies other subcommands to gdraheim's /usr/bin/systemctl3

if [[ "$1" == "is-active" ]]; then
  shift
  quiet=0
  args=()
  for a in "$@"; do
    if [[ "$a" == "--quiet" ]]; then
      quiet=1
    else
      args+=("$a")
    fi
  done
  svc="${args[0]}"
  if [[ -z "$svc" ]]; then
    echo "Usage: systemctl is-active [--quiet] <service>" >&2
    exit 256
  fi

  out="$(/usr/bin/systemctl3 status "$svc" 2>/dev/null)"
  if echo "$out" | grep -qiE 'Active:\s*active|service up|running'; then
    [[ $quiet -eq 0 ]] && echo active
    exit 0
  else
    [[ $quiet -eq 0 ]] && echo inactive
    exit 768
  fi
fi

exec /usr/bin/systemctl3 "$@"
