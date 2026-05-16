package com.wirelessmic.audio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
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

    companion object {
        private const val EVENT_CHANNEL = "com.wirelessmic/audio_stream"
        private const val METHOD_CHANNEL = "com.wirelessmic/audio_control"
        private const val SAMPLE_RATE = 48000
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    override fun onAttachedToEngine(binding: FlutterPlugin.FlutterPluginBinding) {
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
                else -> result.notImplemented()
            }
        }
    }

    override fun onDetachedFromEngine(binding: FlutterPlugin.FlutterPluginBinding) {
        stopRecording()
        eventChannel.setStreamHandler(null)
        methodChannel.setMethodCallHandler(null)
    }

    private fun startRecording(events: EventChannel.EventSink) {
        if (isRecording.get()) return

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
                MediaRecorder.AudioSource.MIC,
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
    }
}
