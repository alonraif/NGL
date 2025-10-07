#!/bin/sh
set -e

mkdir -p /etc/nginx/runtime /var/www/certbot/.well-known/acme-challenge /etc/letsencrypt /etc/nginx/ssl /etc/nginx/ssl/uploaded

# Seed runtime snippets with fallback self-signed certificate
if [ ! -f /etc/nginx/runtime/ssl-enabled.conf ]; then
  cat <<'EOF_SNIPPET' > /etc/nginx/runtime/ssl-enabled.conf
ssl_certificate /etc/nginx/ssl/default.crt;
ssl_certificate_key /etc/nginx/ssl/default.key;
EOF_SNIPPET
fi
: > /etc/nginx/runtime/ssl-redirect.conf

# Background watcher to reload nginx when certificates or runtime snippets change
watch_paths() {
  while inotifywait -r -e modify,create,delete,move /etc/nginx/runtime /etc/letsencrypt >/dev/null 2>&1; do
    nginx -s reload || true
  done
}

if command -v inotifywait >/dev/null 2>&1; then
  watch_paths &
fi

exec nginx -g "daemon off;"
