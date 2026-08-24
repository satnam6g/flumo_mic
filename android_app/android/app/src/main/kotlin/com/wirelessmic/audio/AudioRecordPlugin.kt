package com.wirelessmic.audio

import android.content.Context
import android.media.AudioDeviceInfo
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.os.PowerManager
import io.flutter.embedding.engine.plugins.FlutterPlugin
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel
import java.util.concurrent.atomic.AtomicBoolean

class AudioRecordPlugin : FlutterPlugin {

    private lateinit var eventChannel: EventChannel
    private lateinit var methodChannel: MethodChannel
    private var audioThread: Thread? = null
    private val isRecording = AtomicBoolean(false)
    private var audioRecord: AudioRecord? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var wifiLock: WifiManager.WifiLock? = null
    private var appContext: Context? = null
    @Volatile private var useBluetoothMic = false

    companion object {
        private const val EVENT_CHANNEL = "com.wirelessmic/audio_stream"
        private const val METHOD_CHANNEL = "com.wirelessmic/audio_control"
        private const val SAMPLE_RATE = 48000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        appContext = binding.applicationContext
        eventChannel = EventChannel(binding.binaryMessenger, EVENT_CHANNEL)
        methodChannel = MethodChannel(binding.binaryMessenger, METHOD_CHANNEL)

        eventChannel.setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                if (events == null) return
                startRecording(events)
            }

            override fun onCancel(arguments: Any?) {
                stopRecording()
            }
        })

        methodChannel.setMethodCallHandler { call, result ->
            when (call.method) {
                "stop" -> {
                    stopRecording()
                    result.success(true)
                }
                "getMinBufferSize" -> {
                    val minBuf = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
                    result.success(minBuf)
                }
                "setInputSource" -> {
                    val bt = call.argument<Boolean>("bluetooth") ?: false
                    useBluetoothMic = bt
                    if (bt && isRecording.get()) activateBluetoothSco()
                    result.success(true)
                }
                else -> result.notImplemented()
            }
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        stopRecording()
        eventChannel.setStreamHandler(null)
        methodChannel.setMethodCallHandler(null)
        appContext = null
    }

    private fun acquireLocks() {
        val ctx = appContext ?: return

        // CPU wake lock — keeps CPU active when screen is off
        try {
            val powerManager = ctx.getSystemService(Context.POWER_SERVICE) as PowerManager
            wakeLock = powerManager.newWakeLock(
                PowerManager.PARTIAL_WAKE_LOCK,
                "WirelessMic::AudioCaptureLock"
            ).apply {
                acquire(60 * 60 * 1000L) // 1 hour max
            }
        } catch (e: Exception) {
            // Ignore — wake lock is best-effort
        }

        // Wi-Fi lock — keeps Wi-Fi active when screen is off
        try {
            val wifiManager = ctx.applicationContext.getSystemService(Context.WIFI_SERVICE) as WifiManager
            wifiLock = wifiManager.createWifiLock(
                WifiManager.WIFI_MODE_FULL_HIGH_PERF,
                "WirelessMic::WifiStreamLock"
            ).apply {
                acquire()
            }
        } catch (e: Exception) {
            // Ignore — wifi lock is best-effort
        }
    }

    private fun releaseLocks() {
        try {
            if (wakeLock?.isHeld == true) wakeLock?.release()
        } catch (_: Exception) {}
        wakeLock = null

        try {
            if (wifiLock?.isHeld == true) wifiLock?.release()
        } catch (_: Exception) {}
        wifiLock = null
    }

    private fun activateBluetoothSco() {
        val ctx = appContext ?: return
        try {
            val audioManager = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                val devices = audioManager.availableCommunicationDevices
                val btDevice = devices.firstOrNull {
                    it.type == AudioDeviceInfo.TYPE_BLUETOOTH_SCO ||
                    it.type == AudioDeviceInfo.TYPE_BLE_HEADSET
                }
                if (btDevice != null) {
                    audioManager.setCommunicationDevice(btDevice)
                }
            } else {
                audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
                @Suppress("DEPRECATION")
                audioManager.startBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = true
            }
        } catch (_: Exception) {
            // best effort
        }
    }

    private fun deactivateBluetoothSco() {
        val ctx = appContext ?: return
        try {
            val audioManager = ctx.getSystemService(Context.AUDIO_SERVICE) as AudioManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                audioManager.clearCommunicationDevice()
            } else {
                @Suppress("DEPRECATION")
                audioManager.stopBluetoothSco()
                @Suppress("DEPRECATION")
                audioManager.isBluetoothScoOn = false
                audioManager.mode = AudioManager.MODE_NORMAL
            }
        } catch (_: Exception) {
        }
    }

    private fun startRecording(events: EventChannel.EventSink) {
        if (isRecording.get()) return

        val source = if (useBluetoothMic) {
            MediaRecorder.AudioSource.VOICE_COMMUNICATION
        } else {
            MediaRecorder.AudioSource.MIC
        }

        val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
        if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Handler(Looper.getMainLooper()).post {
                events.error("AUDIO_INIT_ERROR", "Failed to get min buffer size", null)
            }
            return
        }

        val bufferSize = minBufferSize * 2

        try {
            audioRecord = AudioRecord(
                source,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                bufferSize
            )
        } catch (e: SecurityException) {
            Handler(Looper.getMainLooper()).post {
                events.error("PERMISSION_ERROR", "Microphone permission not granted", e.message)
            }
            return
        }

        if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
            Handler(Looper.getMainLooper()).post {
                events.error("AUDIO_INIT_ERROR", "AudioRecord failed to initialize", null)
            }
            audioRecord?.release()
            audioRecord = null
            return
        }

        // Acquire wake + wifi locks before starting recording
        acquireLocks()

        if (useBluetoothMic) activateBluetoothSco()

        isRecording.set(true)
        audioRecord?.startRecording()

        // Read chunk size: 4800 bytes = 2400 samples * 2 bytes = 100ms at 48kHz mono 16-bit
        val chunkSize = 4800

        audioThread = Thread({
            val buffer = ByteArray(chunkSize)
            val mainHandler = Handler(Looper.getMainLooper())

            while (isRecording.get()) {
                val bytesRead = audioRecord?.read(buffer, 0, chunkSize) ?: -1

                if (bytesRead > 0) {
                    // Copy the exact bytes read to avoid sending stale data
                    val chunk = if (bytesRead == chunkSize) {
                        buffer.clone()
                    } else {
                        buffer.copyOfRange(0, bytesRead)
                    }

                    mainHandler.post {
                        if (isRecording.get()) {
                            events.success(chunk)
                        }
                    }
                } else if (bytesRead < 0) {
                    mainHandler.post {
                        events.error("AUDIO_READ_ERROR", "AudioRecord read returned $bytesRead", null)
                    }
                    break
                }
            }
        }, "AudioRecordThread")

        audioThread?.priority = Thread.MAX_PRIORITY
        audioThread?.start()
    }

    private fun stopRecording() {
        isRecording.set(false)

        if (useBluetoothMic) deactivateBluetoothSco()

        try {
            audioThread?.join(2000)
        } catch (_: InterruptedException) {}
        audioThread = null

        try {
            audioRecord?.stop()
        } catch (_: IllegalStateException) {}

        try {
            audioRecord?.release()
        } catch (_: Exception) {}

        audioRecord = null

        // Release locks when recording stops
        releaseLocks()
    }
}
