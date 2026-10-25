# Emulator / adb Preflight

## Confirm device online

```bash
adb devices -l          # emulator-5554 device ...
```

## Before each connected-test run

Running `connectedDebugAndroidTest` reinstalls the APK → app private data + granted runtime permissions are wiped between runs. Redo the preflight every run:

```bash
# 1. APK installed (fail fast: `pm grant` errors 'package not found' when it isn't)
adb shell pm list packages | grep <applicationId>
adb install -r app/build/outputs/apk/debug/app-debug.apk

# 2. Runtime permissions (API 33+ POST_NOTIFICATIONS, etc.)
adb shell pm grant <applicationId> android.permission.POST_NOTIFICATIONS

# 3. Register the listener with the system service layer, not just the setting
adb shell cmd notification allow_listener <applicationId>/<full.ListenerServiceClassName>

# 4. enabled_notification_listeners is a FULL VALUE OVERWRITE — read it first, append, write back
CURRENT=$(adb shell settings get secure enabled_notification_listeners)
adb shell settings put secure enabled_notification_listeners "${CURRENT}:<applicationId>/<full.ListenerServiceClassName>"
adb shell settings get secure enabled_notification_listeners   # verify ours is there AND others weren't clobbered
```

`cmd notification allow_listener` drives the system service layer; `settings put secure enabled_notification_listeners` drives the Settings UI. Both matter — a test that only does one can see "granted" while the service layer hasn't registered the component.

## Run + verify

```bash
./gradlew --no-daemon :app:compileDebugAndroidTestKotlin   # fast gate before the full run
./gradlew --no-daemon :app:connectedDebugAndroidTest
ls app/build/outputs/androidTest-results/connected/         # TEST-*.xml per device
```

Read the XML per class — a device line's `tests=` count is that device's total; count `skipped` and `failures` per class so a real failure doesn't hide behind a `0 failed` device summary that counts skips.

Honest classification in the report:

- **PASS** — ran, assertions held
- **FAIL** — ran, assertion broke (cite the failing line + root cause)
- **SKIPPED / NOT TESTED** — precondition (permission, device capability, real account) unavailable; say so explicitly, never report as PASS

## Granting a permission is not binding a service

For `NotificationListenerService` specifically, see `notification-listener-e2e.md` — `enabled_notification_listeners` membership + `POST_NOTIFICATIONS` are preconditions only; the test must still verify the system actually bound the listener.
