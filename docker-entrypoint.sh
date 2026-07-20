#!/bin/sh
set -eu

./edge-app-binary &
BACKEND_PID=$!

nginx -g 'daemon off;' &
NGINX_PID=$!

trap 'kill "$BACKEND_PID" "$NGINX_PID" 2>/dev/null || true' INT TERM

while kill -0 "$BACKEND_PID" 2>/dev/null && kill -0 "$NGINX_PID" 2>/dev/null; do
  sleep 1
done

kill "$BACKEND_PID" "$NGINX_PID" 2>/dev/null || true
wait "$BACKEND_PID" "$NGINX_PID" 2>/dev/null || true
