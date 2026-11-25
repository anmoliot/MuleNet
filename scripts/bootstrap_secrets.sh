#!/usr/bin/env sh
set -eu
umask 077
cd "$(dirname "$0")/.."
exec python3 scripts/bootstrap_secrets.py "$@"
