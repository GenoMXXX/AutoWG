#!/bin/sh
set -eu

PATH=/opt/bin:/opt/sbin:/bin:/sbin

# shellcheck disable=SC1091
. /opt/lib/wg-watchdog.sh

read_post_data() {
    len="${CONTENT_LENGTH:-0}"
    [ "$len" -gt 0 ] || return 0
    dd bs=1 count="$len" 2>/dev/null
}

form_get() {
    key="$1"
    data="${2-}"
    printf '%s' "$data" | tr '&' '\n' | while IFS='=' read -r k v; do
        [ "$k" = "$key" ] || continue
        printf '%s' "${v-}" | sed 's/+/ /g; s/%0D//g; s/%0A/\n/g; s/%20/ /g; s/%3A/:/Ig; s/%2F/\//Ig'
        break
    done
}

json_escape() {
    printf '%s' "${1-}" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\r//g; s/\t/\\t/g'
}

emit_json() {
    printf 'Content-Type: application/json; charset=utf-8\r\n\r\n'
    printf '%s\n' "$1"
}

json_iface_info() {
    iface="$1"
    info="$(read_interface_info "$iface" 2>/dev/null || true)"
    name="$(printf '%s' "$info" | sed -n 's/.*"name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    status="$(printf '%s' "$info" | sed -n 's/.*"status"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    addr="$(printf '%s' "$info" | sed -n 's/.*"address"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')"
    printf '{"name":"%s","status":"%s","address":"%s"}' "$(json_escape "$name")" "$(json_escape "$status")" "$(json_escape "$addr")"
}

json_interfaces() {
    list_interfaces | awk 'BEGIN{printf "["} {gsub(/\\/,"\\\\"); gsub(/"/,"\\\""); sep=(NR==1?"":","); printf "%s\"%s\"", sep, $0} END{printf "]"}'
}

payload() {
    load_config
    iface="${WG_INTERFACE:-nwg0}"
    status_line="$(read_interface_status "$iface" 2>/dev/null || printf '0|0|unknown')"
    rx="${status_line%%|*}"
    rest="${status_line#*|}"
    tx="${rest%%|*}"
    state="${rest#*|}"
    iface_json="$(json_iface_info "$iface")"
    cat <<EOF
{
  "ok": true,
  "config": {
    "enabled": $( [ "${ENABLED:-1}" = "1" ] && printf true || printf false ),
    "wg_interface": "$(json_escape "$iface")",
    "rx_threshold": $(printf '%s' "${RX_THRESHOLD:-0}"),
    "tx_threshold": $(printf '%s' "${TX_THRESHOLD:-1024}"),
    "poll_interval": $(printf '%s' "${POLL_INTERVAL:-30}"),
    "cooldown": $(printf '%s' "${COOLDOWN:-300}"),
    "http_bind": "$(json_escape "${HTTP_BIND:-0.0.0.0}")",
    "http_port": $(printf '%s' "${HTTP_PORT:-18088}"),
    "web_root": "$(json_escape "${WEB_ROOT:-/opt/share/wg-watchdog/www}")"
  },
  "status": {
    "rxbytes": $(printf '%s' "${rx:-0}"),
    "txbytes": $(printf '%s' "${tx:-0}"),
    "interface_status": "$(json_escape "${state:-unknown}")"
  },
  "interface": $iface_json,
  "interfaces": $(json_interfaces),
  "service": {
    "daemon_pid": $( [ -r "${WG_PID_DIR}/wg-watchdog.pid" ] && cat "${WG_PID_DIR}/wg-watchdog.pid" || printf '0' ),
    "web_pid": $( [ -r "${WG_PID_DIR}/wg-watchdog-httpd.pid" ] && cat "${WG_PID_DIR}/wg-watchdog-httpd.pid" || printf '0' )
  }
}
EOF
}

body=""
case "${REQUEST_METHOD:-GET}" in
    POST) body="$(read_post_data)" ;;
    *) body="${QUERY_STRING:-}" ;;
esac

action="$(form_get action "$body")"
action="${action:-status}"

case "$action" in
    toggle)
        load_config
        if [ "${ENABLED:-1}" = "1" ]; then ENABLED=0; else ENABLED=1; fi
        save_config
        emit_json "$(payload)"
        ;;
    bounce)
        load_config
        if bounce_interface "${WG_INTERFACE:-nwg0}"; then
            emit_json '{"ok":true,"message":"bounced"}'
        else
            emit_json '{"ok":false,"message":"bounce failed"}'
        fi
        ;;
    save)
        load_config
        enabled="$(form_get ENABLED "$body")"
        [ -n "$enabled" ] && ENABLED=1 || ENABLED=0
        iface="$(form_get WG_INTERFACE "$body" || true)"
        rx="$(form_get RX_THRESHOLD "$body" || true)"
        tx="$(form_get TX_THRESHOLD "$body" || true)"
        poll="$(form_get POLL_INTERVAL "$body" || true)"
        cooldown="$(form_get COOLDOWN "$body" || true)"
        bind="$(form_get HTTP_BIND "$body" || true)"
        port="$(form_get HTTP_PORT "$body" || true)"
        [ -n "$iface" ] && WG_INTERFACE="$iface"
        [ -n "$rx" ] && RX_THRESHOLD="$rx"
        [ -n "$tx" ] && TX_THRESHOLD="$tx"
        [ -n "$poll" ] && POLL_INTERVAL="$poll"
        [ -n "$cooldown" ] && COOLDOWN="$cooldown"
        [ -n "$bind" ] && HTTP_BIND="$bind"
        [ -n "$port" ] && HTTP_PORT="$port"
        save_config
        emit_json "$(payload)"
        ;;
    status|*)
        emit_json "$(payload)"
        ;;
esac

