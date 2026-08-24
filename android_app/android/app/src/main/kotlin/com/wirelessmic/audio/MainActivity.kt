package com.wirelessmic.audio

import android.content.Intent
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    companion object {
        @Volatile
        var pendingAction: String? = null   // "start" | "stop" | null
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        flutterEngine.plugins.add(AudioRecordPlugin())
        handleIntent(intent)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.wirelessmic/launch_action")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "popAction" -> {
                        val a = pendingAction
                        pendingAction = null
                        result.success(a)
                    }
                    else -> result.notImplemented()
                }
            }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleIntent(intent)
    }

    private fun handleIntent(intent: Intent?) {
        val action = intent?.getStringExtra("wm_action") ?: return
        if (action == "start" || action == "stop") pendingAction = action
    }
}
