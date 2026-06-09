#!/bin/bash

set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Password should be the first argument."
  exit 1
fi

APPNAME=mitd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ZIP_PATH="$SCRIPT_DIR/$APPNAME.zip"
ROKU_DEV_TARGET="${ROKU_DEV_TARGET:-192.168.1.102}"
USER=rokudev
PASS=$1

rm -f "$ZIP_PATH"
cd "$SCRIPT_DIR"
zip -r "$ZIP_PATH" manifest source images -x '*.DS_Store'

echo "Installing $APPNAME to host $ROKU_DEV_TARGET"
curl --anyauth -u "$USER:$PASS" -s -S -F "mysubmit=Replace" -F "archive=@$ZIP_PATH" -F "passwd=" "http://$ROKU_DEV_TARGET/plugin_install"
