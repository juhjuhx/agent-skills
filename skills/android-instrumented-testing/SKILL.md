---
name: android-instrumented-testing
description: Android on-device JUnit (connected tests) workflow.
version: 1.0.0
author: Hermes Agent
license: MIT
tags: [Android, instrumented, JUnit, emulator, NotificationListenerService, adb, DEX]
related_skills: [android-app-release-readiness, kuyin-android-engineering]
---

# Android Instrumented Testing

On-device JUnit (`connectedDebugAndroidTest`), emulator preflight, and NotificationListenerService E2E patterns.

## When to Use

- Writing or debugging Android instrumented (on-device JUnit) tests under `androidTest/`.
- Running or fixing `:app:connectedDebugAndroidTest` against an emulator or real device.
- Building a system-level E2E test for a `NotificationListenerService` (post a real notification, verify the listener routed it, assert the persisted result).
- Triage: "connected test fails at dexing," "test reinstalls and loses permissions," "permission granted but service never bound," "backtick test name breaks the build."
- Setting up adb preflight so a headless/emulated run can actually capture a notification.

## Flow

1. Confirm a device is attached (`adb devices`).
2. Preflight: install APK, grant runtime permissions, register listener — see `references/emulator-preflight.md` (or run `scripts/preflight.sh`).
3. Compile gate: `./gradlew :app:compileDebugAndroidTestKotlin` before a full run. One wrong API/import burns a full connect cycle; the compile task alone catches it in seconds.
4. DEX-safe test method names in `androidTest/` — never backtick-names containing spaces (`:app:dexBuilderDebugAndroidTest` rejects space-containing SimpleNames). JVM unit tests can keep readable backtick names; they are never dexed.
5. Mirror the project's existing `androidTest` conventions (imports, helpers, SBN construction). Grep the tree for the symbol/pattern before writing your own.
6. Run `./gradlew :app:connectedDebugAndroidTest`, then read per-class XML in `app/build/outputs/androidTest-results/connected/` and classify honestly: PASS / FAIL / SKIPPED (NOT TESTED).

## Pitfalls

- **Backtick names with spaces in `androidTest`**: rename to camelCase. The compiler accepts them; the dex step fails — so this surfaces only on a full run, not a compile.
- **Granting a listener permission != the listener is bound**: `requestRebind()` + poll for persisted connection evidence; if the system can't bind in this environment, skip with `assumeTrue` (NOT TESTED), never hard-fail or fabricate a pass.
- **Running a connected test reinstalls the APK**, wiping app data + granted runtime permissions between runs: redo preflight (re-grant) every time.
- **`enabled_notification_listeners` is a full-value overwrite** — append to the existing value; clobbering it breaks other listeners.
- **Service lifecycle hooks NPE on unattached instances**: `applicationContext` throws before the first `attachBaseContext`; wrap the diagnostic write in `runCatching`.
- **`StatusBarNotification` constructor varies by API level**: use the 10-arg reflected form on modern toolchains, not the 14-arg public one.
- **Device-level `0 failed` can hide real failures**: a device's `tests=` count includes skips; count `skipped`/`failures` per class from the XML before reporting.

## Support files

- `references/emulator-preflight.md` — adb preflight commands, permission re-grant after reinstall, connected-test run/verification
- `references/notification-listener-e2e.md` — bind precondition, skip-not-fail semantics, cross-process connection evidence, SBN construction in tests
- `templates/notification-listener-e2e-instrumented-test.kt` — E2E test skeleton (post through real NotificationManager, verify DB row, skip when unbindable)
- `scripts/preflight.sh` — install + grant + allow_listener + settings-append, idempotent, verify-gated
