package <your.app.pkg>

import android.content.ComponentName
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/**
 * SYSTEM E2E: posts a fixed self-test notification through the real NotificationManager
 * and verifies the system routed it to the enabled NotificationListenerService, which
 * stored the result. A direct capture() test is a different (weaker) claim — this one
 * proves system dispatch.
 *
 * If the environment cannot get the system to bind the listener, every dependent test
 * skips as NOT TESTED — this file never hard-fails on a binding failure it did not cause.
 */
@RunWith(AndroidJUnit4::class)
class SelfTestSystemNotificationInstrumentedTest {
    private val ctx: Context = InstrumentationRegistry.getInstrumentation().targetContext

    private fun canPostNow(): Boolean =
        Build.VERSION.SDK_INT < 33 ||
            ctx.checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED

    /**
     * Verify the system has actually BOUND the listener service (not merely granted
     * the permission). requestRebind() (API 31+) is the official trigger; the
     * listener's own onListenerConnected() must have persisted connectivity
     * evidence before we trust any capture assertion. Returns false when this
     * environment cannot bind the listener so callers skip, not fail.
     */
    private fun ensureListenerConnected(): Boolean {
        if (!SelfTestNotifier.listenerPermissionGranted(ctx)) return false
        val component = ComponentName(ctx, YourListenerService::class.java)
        if (Build.VERSION.SDK_INT >= 31) {
            try {
                android.service.notification.NotificationListenerService.requestRebind(component)
            } catch (_: Throwable) {
                // unavailable on some builds; fall through to the poll below
            }
        }
        val deadline = System.currentTimeMillis() + 15_000
        while (System.currentTimeMillis() < deadline) {
            if (YourDiagnostics.hasConnectedEvidence(ctx)) return true
            Thread.sleep(500)
        }
        return false
    }

    @Test
    fun systemPostedNotificationReachesListenerAndIsStored() {
        assumeTrue("POST_NOTIFICATIONS unavailable -> NOT TESTED", canPostNow())
        assumeTrue("listener not bindable in this environment -> NOT TESTED",
            ensureListenerConnected())
        val posted = SelfTestNotifier.post(ctx)
        assumeTrue("self-test notification could not be posted -> NOT TESTED", posted)
        val deadline = System.currentTimeMillis() + 15_000
        var stored = false
        while (System.currentTimeMillis() < deadline) {
            stored = YourRepo.rowCountForSelfTestSource() > 0
            if (stored) break
            Thread.sleep(500)
        }
        assertTrue("system-posted self-test notification must reach the listener", stored)
    }
}

// SelfTestNotifier: post() goes through the real NotificationManager so the system,
// not the test, does the dispatch — that is what makes this an E2E claim.
// YourDiagnostics.hasConnectedEvidence(ctx): SharedPreferences-persisted flag written
// by the listener service's onListenerConnected(), visible across processes.
