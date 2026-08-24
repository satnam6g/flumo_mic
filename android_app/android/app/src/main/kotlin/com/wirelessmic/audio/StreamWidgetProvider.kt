package com.wirelessmic.audio

import android.app.PendingIntent
import android.appwidget.AppWidgetManager
import android.appwidget.AppWidgetProvider
import android.content.Context
import android.content.Intent
import android.widget.RemoteViews

class StreamWidgetProvider : AppWidgetProvider() {

    override fun onUpdate(context: Context, appWidgetManager: AppWidgetManager, appWidgetIds: IntArray) {
        for (appWidgetId in appWidgetIds) {
            val views = RemoteViews(context.packageName, R.layout.widget_stream).apply {
                setOnClickPendingIntent(R.id.widget_start, actionIntent(context, "start", appWidgetId, 100))
                setOnClickPendingIntent(R.id.widget_stop, actionIntent(context, "stop", appWidgetId, 200))
            }
            appWidgetManager.updateAppWidget(appWidgetId, views)
        }
    }

    private fun actionIntent(context: Context, action: String, appWidgetId: Int, requestCode: Int): PendingIntent {
        val intent = Intent(context, MainActivity::class.java).apply {
            this.action = "com.wirelessmic.WIDGET_$action"
            putExtra("wm_action", action)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP
        }
        return PendingIntent.getActivity(
            context,
            requestCode + appWidgetId,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
}
