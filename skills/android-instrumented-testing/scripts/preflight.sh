#!/bin/bash
# Emulator preflight for connected tests: install APK, grant runtime permissions,
# register the notification listener, then verify each step.
# Usage: bash preflight.sh <applicationId> <full.ListenerServiceClassName> <path/to/app-debug.apk>
# Not idempotent about enabled_notification_listeners: it appends to the existing
# value, it does not clobber other listeners.
set -euo pipefail
APK_ID="${1:?applicationId}"; LSN="${2:?full.listener.service.class}"; APK="${3:?path/to/apk}"
ADB="${ADB:-adb}"

$ADB shell pm list packages | grep -q "$APK_ID" || {
  echo "installing $APK"; $ADB install -r "$APK"; }
$ADB shell pm grant "$APK_ID" android.permission.POST_NOTIFICATIONS \
  || echo "POST_NOTIFICATIONS grant failed (pre-API-33 or install state)"
$ADB shell cmd notification allow_listener "$APK_ID/$LSN"
CUR=$($ADB shell settings get secure enabled_notification_listeners | tr -d '\r')
NEEDED="$APK_ID/$LSN"
case ":$CUR:" in *":$NEEDED:"*) ;; *) $ADB shell settings put secure enabled_notification_listeners "$CUR:$NEEDED" ;; esac
echo "--- verify ---"
$ADB shell settings get secure enabled_notification_listeners | tr ';' '\n' | grep -i "$APK_ID" \
  && echo "preflight OK" || { echo "preflight FAILED"; exit 1; }
