#!/bin/sh
set -eu

: "${PORT:=8080}"
export PANEL_PORT="${PANEL_PORT:-8481}"
export DISPLAY="${DISPLAY:-:99}"

if [ -z "${PANEL_USER:-}" ] || [ -z "${PANEL_PASSWORD:-}" ]; then
    echo "ERRO: configure PANEL_USER e PANEL_PASSWORD nas Variables do Railway."
    exit 1
fi

htpasswd -nbB "$PANEL_USER" "$PANEL_PASSWORD" > /etc/nginx/.htpasswd
chown root:www-data /etc/nginx/.htpasswd
chmod 640 /etc/nginx/.htpasswd

Xvfb "$DISPLAY" -screen 0 1920x1080x24 -ac +extension GLX +render -noreset >/tmp/xvfb.log 2>&1 &

fluxbox >/tmp/fluxbox.log 2>&1 &

x11vnc \
  -display "$DISPLAY" \
  -localhost \
  -forever \
  -shared \
  -rfbport 5900 \
  -nopw \
  -noxdamage \
  -repeat \
  -xkb >/tmp/x11vnc.log 2>&1 &

websockify --web=/usr/share/novnc/ 6080 127.0.0.1:5900 >/tmp/websockify.log 2>&1 &

envsubst '${PORT}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf

rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

uv run python -m ofertas painel 2>&1 | tee /tmp/painel.log &

echo "Serviços iniciados."
echo "Painel/noVNC: porta pública ${PORT}"
echo "Painel interno: ${PANEL_PORT}"
echo "Acesso remoto: /vnc/vnc.html?autoconnect=true&path=websockify&resize=scale"

exec nginx -g 'daemon off;'