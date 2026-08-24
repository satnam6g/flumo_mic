package com.wirelessmic.audio

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.service.quicksettings.TileService

/**
 * Quick-settings tile: tapping it opens Wireless Mic and auto-starts the stream
 * using the saved IP/PIN.
 */
class StreamTileService : TileService() {

    override fun onClick() {
        super.onClick()
        val intent = Intent(this, MainActivity::class.java).apply {
            action = "com.wirelessmic.TILE_START"
            putExtra("wm_action", "start")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        startActivityAndCollapseCompat(intent)
    }

    @Suppress("DEPRECATION")
    private fun startActivityAndCollapseCompat(intent: Intent) {
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startActivityAndCollapse(
                android.app.PendingIntent.getActivity(
                    this, 300, intent,
                    android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE
                )
            )
        } else {
            startActivityAndCollapse(intent)
        }
    }

    companion object {
        fun requestTileListening(context: Context) {
            try {
                TileService.requestListeningState(
                    context, ComponentName(context, StreamTileService::class.java)
                )
            } catch (_: Exception) {
            }
        }
    }
}
