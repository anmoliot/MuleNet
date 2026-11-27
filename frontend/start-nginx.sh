#!/bin/sh
set -eu

export MULENET_OIDC_BROWSER_ORIGIN="${MULENET_OIDC_BROWSER_ORIGIN:-}"
if [ -n "$MULENET_OIDC_BROWSER_ORIGIN" ]; then
    case "$MULENET_OIDC_BROWSER_ORIGIN" in
        *[!a-zA-Z0-9.:/-]*) echo 'Invalid explicit OIDC browser origin; refusing generated CSP' >&2; exit 1 ;;
    esac
    if ! printf '%s' "$MULENET_OIDC_BROWSER_ORIGIN" | grep -Eq '^https://[a-zA-Z0-9.-]+(:[0-9]+)?$|^http://(localhost|127\.0\.0\.1)(:[0-9]+)?$'; then
        echo 'Invalid explicit OIDC browser origin; refusing generated CSP' >&2
        exit 1
    fi
fi
envsubst '${MULENET_OIDC_BROWSER_ORIGIN}' < /etc/nginx/site.template > /tmp/mulenet-site.conf
exec nginx -g 'daemon off;'
