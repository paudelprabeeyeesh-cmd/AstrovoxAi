#!/bin/sh
# ============================================================================
# AstrovoxAI frontend entrypoint
# ============================================================================
# Renders /etc/nginx/templates/nginx.conf.template into the nginx conf dir
# so domain names, the backend upstream and the TLS paths are environment
# driven rather than hardcoded, then execs nginx.
#
# The security-headers snippet is copied in from the image so every location
# block can `include` it, which is what makes the security headers survive on
# locations that set their own add_header.
# ============================================================================
set -eu

TARGET_DIR="${NGINX_CONF_DIR:-/etc/nginx/conf.d}"
mkdir -p "$TARGET_DIR" /etc/nginx/snippets

SNIPPET_SRC="${ASTROVOX_HEADERS_SNIPPET:-/usr/share/astrovox/security-headers.conf}"
if [ -f "$SNIPPET_SRC" ]; then
    cp "$SNIPPET_SRC" /etc/nginx/snippets/security-headers.conf
else
    echo "astrovox-entrypoint: security headers snippet missing at $SNIPPET_SRC" >&2
    exit 1
fi

TEMPLATE="${ASTROVOX_TEMPLATE:-/etc/nginx/templates/nginx.conf.template}"
if [ ! -f "$TEMPLATE" ]; then
    echo "astrovox-entrypoint: nginx template missing at $TEMPLATE" >&2
    exit 1
fi

# Defaults keep a bare `docker run` working without any environment.
export ASTROVOX_DOMAIN="${ASTROVOX_DOMAIN:-astrovox.ai}"
export ASTROVOX_API_DOMAIN="${ASTROVOX_API_DOMAIN:-api.astrovox.ai}"
export ASTROVOX_BACKEND="${ASTROVOX_BACKEND:-backend:8000}"
# 8080 so a non-root nginx can bind it without CAP_NET_BIND_SERVICE.
export ASTROVOX_HTTP_PORT="${ASTROVOX_HTTP_PORT:-8080}"

# envsubst only the variables this template actually uses; a blanket
# substitution would corrupt nginx's own $host, $uri and $remote_addr.
envsubst '${ASTROVOX_DOMAIN} ${ASTROVOX_API_DOMAIN} ${ASTROVOX_BACKEND} ${ASTROVOX_HTTP_PORT}' \
    < "$TEMPLATE" > "$TARGET_DIR/default.conf"

test -n "$(find "$TARGET_DIR/default.conf" -maxdepth 1 -size +0 2>/dev/null)" \
    || { echo "astrovox-entrypoint: rendered config is empty" >&2; exit 1; }

echo "astrovox-entrypoint: rendered nginx config for ${ASTROVOX_DOMAIN} -> ${ASTROVOX_BACKEND} on :${ASTROVOX_HTTP_PORT}"

exec nginx -g 'daemon off;'
