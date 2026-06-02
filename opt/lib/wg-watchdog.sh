#!/bin/sh

WG_CONF="${WG_CONF:-/opt/etc/wg-watchdog.conf}"
WG_PID_DIR="${WG_PID_DIR:-/opt/var/run}"
WG_STATE_FILE="${WG_STATE_FILE:-/opt/var/run/wg-watchdog.state}"
WG_SYS_NET="${WG_SYS_NET:-/sys/class/net}"
WG_WEB_ROOT="${WG_WEB_ROOT:-/opt/share/wg-watchdog/www}"
WG_HTTP_PORT="${WG_HTTP_PORT:-18088}"
WG_HTTP_BIND="${WG_HTTP_BIND:-0.0.0.0}"

load_config() {
    ENABLED=1
    WG_INTERFACE=nwg0
    RX_THRESHOLD=0
    TX_THRESHOLD=1024
    POLL_INTERVAL=30
    COOLDOWN=300
    HTTP_BIND=0.0.0.0
    HTTP_PORT=18088
    WEB_ROOT=/opt/share/wg-watchdog/www

    if [ -r "$WG_CONF" ]; then
        # shellcheck disable=SC1090
        . "$WG_CONF"
    fi
}

save_config() {
    tmp="${WG_CONF}.tmp.$$"
    {
        printf 'ENABLED=%s\n' "${ENABLED:-1}"
        printf 'WG_INTERFACE=%s\n' "${WG_INTERFACE:-nwg0}"
        printf 'RX_THRESHOLD=%s\n' "${RX_THRESHOLD:-0}"
        printf 'TX_THRESHOLD=%s\n' "${TX_THRESHOLD:-1024}"
        printf 'POLL_INTERVAL=%s\n' "${POLL_INTERVAL:-30}"
        printf 'COOLDOWN=%s\n' "${COOLDOWN:-300}"
        printf 'HTTP_BIND=%s\n' "${HTTP_BIND:-0.0.0.0}"
        printf 'HTTP_PORT=%s\n' "${HTTP_PORT:-18088}"
        printf 'WEB_ROOT=%s\n' "${WEB_ROOT:-/opt/share/wg-watchdog/www}"
    } >"$tmp"
    mv "$tmp" "$WG_CONF"
}

read_state() {
    LAST_RX=0
    LAST_TX=0
    LAST_BOUNCE=0
    if [ -r "$WG_STATE_FILE" ]; then
        # shellcheck disable=SC1090
        . "$WG_STATE_FILE"
    fi
}

write_state() {
    tmp="${WG_STATE_FILE}.tmp.$$"
    {
        printf 'LAST_RX=%s\n' "${1:-0}"
        printf 'LAST_TX=%s\n' "${2:-0}"
        printf 'LAST_BOUNCE=%s\n' "${3:-0}"
    } >"$tmp"
    mv "$tmp" "$WG_STATE_FILE"
}

iface_path() {
    printf '%s/%s' "$WG_SYS_NET" "${1:-}"
}

iface_exists() {
    [ -d "$(iface_path "$1")" ]
}

read_counter() {
    iface="$1"
    metric="$2"
    file="$(iface_path "$iface")/statistics/$metric"
    [ -r "$file" ] || return 1
    tr -d '\r\n' <"$file"
}

list_interfaces() {
    for d in "$WG_SYS_NET"/*; do
        [ -d "$d" ] || continue
        name="${d##*/}"
        [ "$name" = "lo" ] && continue
        [ -r "$d/uevent" ] || continue
        if grep -q '^DEVTYPE=wireguard$' "$d/uevent" 2>/dev/null; then
            printf '%s\n' "$name"
        fi
    done | awk 'NF && !seen[$0]++'
}

read_interface_info() {
    iface="$1"
    base="$(iface_path "$iface")"
    [ -d "$base" ] || return 1
    status="unknown"
    [ -r "$base/operstate" ] && status="$(tr -d '\r\n' <"$base/operstate")"
    addr=""
    [ -r "$base/address" ] && addr="$(tr -d '\r\n' <"$base/address")"
    cat <<EOF
{
  "name": "$(printf '%s' "$iface" | sed 's/\\/\\\\/g; s/"/\\"/g')",
  "status": "$(printf '%s' "$status" | sed 's/\\/\\\\/g; s/"/\\"/g')",
  "address": "$(printf '%s' "$addr" | sed 's/\\/\\\\/g; s/"/\\"/g')"
}
EOF
}

read_interface_status() {
    iface="$1"
    rx="$(read_counter "$iface" rx_bytes 2>/dev/null || printf '0')"
    tx="$(read_counter "$iface" tx_bytes 2>/dev/null || printf '0')"
    state="unknown"
    [ -r "$(iface_path "$iface")/operstate" ] && state="$(tr -d '\r\n' <"$(iface_path "$iface")/operstate")"
    printf '%s|%s|%s\n' "$rx" "$tx" "$state"
}

bounce_interface() {
    iface="$1"
    command -v ip >/dev/null 2>&1 || return 1
    ip link set dev "$iface" down >/dev/null 2>&1 || return 1
    sleep 2
    ip link set dev "$iface" up >/dev/null 2>&1 || return 1
}

