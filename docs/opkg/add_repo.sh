#!/bin/sh
set -eu

FEED_LINE='src/gz AutoWG https://genomxxx.github.io/AutoWG/opkg'
CONF_DIR='/opt/etc'
CUSTOM_FEEDS="$CONF_DIR/opkg/customfeeds.conf"
OPKG_CONF="$CONF_DIR/opkg.conf"

mkdir -p "$CONF_DIR/opkg"

target="$CUSTOM_FEEDS"
if [ ! -f "$target" ]; then
    target="$OPKG_CONF"
fi

touch "$target"

if ! grep -Fqx "$FEED_LINE" "$target"; then
    printf '%s\n' "$FEED_LINE" >>"$target"
fi

echo "Added AutoWG feed to $target"
echo "Run: opkg update && opkg install wg-watchdog"
