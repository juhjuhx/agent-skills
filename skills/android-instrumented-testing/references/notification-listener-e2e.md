# NotificationListenerService E2E Test Patterns

## Preconditions (from `emulator-preflight.md`)

1. `enabled_notification_listeners` contains the component
2. `POST_NOTIFICATIONS` granted (API 33+, for the app to post its OWN test notification)
3. `cmd notification allow_listener <component>` applied to the system service layer

`POST_NOTIFICATIONS` is only for the app posting its own notifications — it is NOT required to RECEIVE notifications from other apps. Never present it as a LINE/Messenger-capture requirement.

## Verify the listener is actually bound

Granting permission != bound. On API 31+: `NotificationListenerService.requestRebind(component)` is the official trigger.

After `requestRebind`, wait for the service's own `onListenerConnected()` to persist connectivity evidence (SharedPreferences, not just in-memory) before trusting any "captured" assertion — a fixed sleep is not evidence. If the evidence never appears, the system couldn't bind in this environment: `assumeTrue(connected, "listener not bindable in this environment -> NOT TESTED")` and skip. Never hard-fail on this — a test that can't bind a system service in a headless/emulated environment is NOT TESTED, not FAIL.

**Cross-process note**: instrumentation and the listener service share the app process, so an in-process `@Volatile` flag is technically visible to the test — but persist the flag to SharedPreferences anyway: an in-process flag goes stale across service restarts, and UI-process diagnostics need it regardless.

## `onListenerConnected` / `onListenerDisconnected` must be NPE-safe

Driven on a bare (never-attached) service instance, `applicationContext` **throws NPE** — `ContextWrapper.getApplicationContext()` dereferences the null base context; it is not a null return. Wrap the diagnostic write:

```kotlin
override fun onListenerConnected() {
    runCatching {
        val app = applicationContext ?: return@runCatching
        CaptureDiagnostics.markConnected(app)
    }
}
```

So direct-parser tests that instantiate the service and call the hooks don't crash.

## Building `StatusBarNotification` in tests (API 29+)

The 14-arg public constructor was removed on newer APIs; the working form is the 10-arg one, called via reflection:

```kotlin
val ctor = StatusBarNotification::class.java.getConstructor(
    String::class.java, String::class.java, Int::class.javaPrimitiveType,
    String::class.java, Int::class.javaPrimitiveType, Int::class.javaPrimitiveType,
    Int::class.javaPrimitiveType, Notification::class.java,
    android.os.UserHandle::class.java, Long::class.javaPrimitiveType
)
val sbn = ctor.newInstance(pkg, pkg, 0, channel, 0, 0, 0, notification,
    android.os.UserHandle.getUserHandleForUid(Process.myUid()),
    System.currentTimeMillis())
```

Mirror the project's existing instrumented-test constructor call rather than re-deriving it — different toolchains expose different arities.

## DEX-safe test method names (androidTest only)

Backtick-quoted Kotlin test names with spaces compile fine but fail at `dexBuilder` (DEX <040 rejects space-containing SimpleNames). Rename androidTest methods to camelCase; JVM `test/` unit tests can keep readable backtick names since they are never dexed.

## Skip vs. fail — one line per category

- Can't grant the permission / listener won't bind in this env → `assumeTrue` skip (NOT TESTED)
- Permission granted, listener bound, notification posted, no row in DB within the poll window → real FAIL, report it
- Don't let "skipped because the environment couldn't bind" be reported as a pass, and don't let a missing row in a fully-working env be silently skipped
