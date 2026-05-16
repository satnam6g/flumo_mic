import 'dart:async';
import 'dart:io';
import 'dart:convert';
import 'dart:math';
import 'dart:typed_data';
import 'dart:isolate';
import 'package:crypto/crypto.dart';
import 'package:encrypt/encrypt.dart' as encrypt;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_foreground_task/flutter_foreground_task.dart';

void main() {
  runApp(const WirelessMicApp());
}

// Foreground Task Handler
@pragma('vm:entry-point')
void startCallback() {
  FlutterForegroundTask.setTaskHandler(MyTaskHandler());
}

class MyTaskHandler extends TaskHandler {
  @override
  Future<void> onStart(DateTime timestamp, SendPort? sendPort) async {}
  @override
  Future<void> onEvent(DateTime timestamp, SendPort? sendPort) async {}
  @override
  Future<void> onDestroy(DateTime timestamp, SendPort? sendPort) async {}
  @override
  void onRepeatEvent(DateTime timestamp, SendPort? sendPort) {}
  @override
  void onButtonPressed(String id) {}
  @override
  void onNotificationPressed() {
    FlutterForegroundTask.launchApp();
  }
}

class WirelessMicApp extends StatelessWidget {
  const WirelessMicApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Wireless Mic',
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark(),
      home: const MicPage(),
    );
  }
}

class MicPage extends StatefulWidget {
  const MicPage({super.key});

  @override
  State<MicPage> createState() => _MicPageState();
}

class _MicPageState extends State<MicPage> with WidgetsBindingObserver {
  // ── Channels ────────────────────────────────────────────────────────────
  static const _audioStream = EventChannel('com.wirelessmic/audio_stream');
  static const _audioControl = MethodChannel('com.wirelessmic/audio_control');

  // ── State ───────────────────────────────────────────────────────────────
  final TextEditingController _ipController = TextEditingController();
  final TextEditingController _pinController = TextEditingController();
  bool _isStreaming = false;
  String _status = 'Idle';
  int _packetsSent = 0;
  int _bytesSent = 0;
  StreamSubscription? _audioSubscription;
  RawDatagramSocket? _udpSocket;
  SharedPreferences? _prefs;

  // ── Constants ───────────────────────────────────────────────────────────
  static const int _udpPort = 55555;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _initPrefs();
    _initForegroundTask();
  }

  Future<void> _initPrefs() async {
    _prefs = await SharedPreferences.getInstance();
    final savedIp = _prefs?.getString('last_ip') ?? '';
    final savedPin = _prefs?.getString('last_pin') ?? '';
    setState(() {
      _ipController.text = savedIp;
      _pinController.text = savedPin;
    });
  }

  void _initForegroundTask() {
    FlutterForegroundTask.init(
      androidNotificationOptions: AndroidNotificationOptions(
        channelId: 'wireless_mic_channel',
        channelName: 'Wireless Mic Service',
        channelDescription: 'Keeps the microphone streaming active in background',
        channelImportance: NotificationChannelImportance.LOW,
        priority: NotificationPriority.LOW,
        iconData: const NotificationIconData(
          resType: ResourceType.mipmap,
          resPrefix: ResourcePrefix.ic,
          name: 'launcher',
        ),
      ),
      iosNotificationOptions: const IOSNotificationOptions(
        showNotification: true,
        playSound: false,
      ),
      foregroundTaskOptions: const ForegroundTaskOptions(
        interval: 5000,
        isOnceEvent: false,
        autoRunOnBoot: false,
        allowWakeLock: true,
        allowWifiLock: true,
      ),
    );
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _stopStreaming();
    _ipController.dispose();
    super.dispose();
  }

  // ── Permission Handling ─────────────────────────────────────────────────
  Future<bool> _requestPermissions() async {
    var micStatus = await Permission.microphone.status;
    if (!micStatus.isGranted) {
      micStatus = await Permission.microphone.request();
    }
    
    if (Platform.isAndroid) {
      if (await Permission.notification.isDenied) {
        await Permission.notification.request();
      }
    }

    if (micStatus.isPermanentlyDenied) {
      _setStatus('Mic permission denied. Open app settings.');
      openAppSettings();
      return false;
    }

    return micStatus.isGranted;
  }

  // ── Start Streaming ────────────────────────────────────────────────────
  Future<void> _startStreaming() async {
    final ip = _ipController.text.trim();
    final pin = _pinController.text.trim();
    if (ip.isEmpty) {
      _setStatus('Enter the Windows PC IP address.');
      return;
    }
    if (pin.isEmpty || pin.length != 4) {
      _setStatus('Enter the 4-digit Security PIN.');
      return;
    }

    try {
      InternetAddress(ip);
    } catch (_) {
      _setStatus('Invalid IP address: $ip');
      return;
    }

    final hasPermission = await _requestPermissions();
    if (!hasPermission) return;

    _prefs?.setString('last_ip', ip);
    _prefs?.setString('last_pin', pin);
    _setStatus('Starting secure stream...');

    try {
      _udpSocket = await RawDatagramSocket.bind(InternetAddress.anyIPv4, 0);
      _udpSocket!.listen((RawSocketEvent event) {
        if (event == RawSocketEvent.read) {
          final datagram = _udpSocket!.receive();
          if (datagram != null) {
            try {
              final msg = utf8.decode(datagram.data);
              if (msg == 'ERROR:WRONG_PIN') {
                _setStatus('Error: Incorrect PIN entered!');
                _stopStreaming();
              }
            } catch (_) {}
          }
        }
      });
    } catch (e) {
      _setStatus('Failed to create UDP socket: $e');
      return;
    }

    final targetAddress = InternetAddress(ip);
    _packetsSent = 0;
    _bytesSent = 0;
    
    // Setup AES Encryption
    final keyBytes = sha256.convert(utf8.encode(pin)).bytes;
    final aesKey = encrypt.Key(Uint8List.fromList(keyBytes));
    final encrypter = encrypt.Encrypter(encrypt.AES(aesKey, mode: encrypt.AESMode.cbc));
    final random = Random.secure();

    if (await FlutterForegroundTask.isRunningService == false) {
      await FlutterForegroundTask.startService(
        notificationTitle: 'Wireless Mic Secure',
        notificationText: 'Encrypted stream to $ip',
        callback: startCallback,
      );
    }

    _audioSubscription = _audioStream.receiveBroadcastStream().listen(
      (dynamic data) {
        if (data is Uint8List && _udpSocket != null) {
          try {
            // Generate IV
            final ivBytes = Uint8List(16);
            for (int i = 0; i < 16; i++) {
              ivBytes[i] = random.nextInt(256);
            }
            final iv = encrypt.IV(ivBytes);

            // Encrypt and build packet
            final encrypted = encrypter.encryptBytes(data, iv: iv);
            final payload = BytesBuilder();
            payload.add(iv.bytes);
            payload.add(encrypted.bytes);
            final packet = payload.toBytes();

            final sent = _udpSocket!.send(packet, targetAddress, _udpPort);
            if (sent > 0) {
              _packetsSent++;
              _bytesSent += sent;
              if (_packetsSent % 50 == 0 && mounted) {
                _setStatus('Secure Stream to $ip | ${(_bytesSent / 1024 / 1024).toStringAsFixed(1)} MB');
              }
            }
          } catch (e) {
            _setStatus('UDP/Encryption error: $e');
          }
        }
      },
      onError: (e) {
        _setStatus('Stream error: $e');
        _stopStreaming();
      },
    );

    setState(() {
      _isStreaming = true;
    });
  }

  // ── Stop Streaming ─────────────────────────────────────────────────────
  Future<void> _stopStreaming() async {
    await _audioSubscription?.cancel();
    _audioSubscription = null;

    try {
      await _audioControl.invokeMethod('stop');
    } catch (_) {}

    _udpSocket?.close();
    _udpSocket = null;

    if (await FlutterForegroundTask.isRunningService) {
      await FlutterForegroundTask.stopService();
    }

    if (mounted) {
      setState(() {
        _isStreaming = false;
      });
      _setStatus('Stopped. Sent $_packetsSent pkts (${(_bytesSent / 1024 / 1024).toStringAsFixed(2)} MB)');
    }
  }

  void _setStatus(String msg) {
    if (mounted) {
      setState(() => _status = msg);
    }
  }

  @override
  Widget build(BuildContext context) {
    return WithForegroundTask(
      child: Scaffold(
        backgroundColor: const Color(0xFF1E1E24),
        appBar: AppBar(
          backgroundColor: Colors.transparent,
          elevation: 0,
          title: const Text('Wireless Mic', style: TextStyle(color: Colors.white, fontSize: 24)),
        ),
        body: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // IP Input
              TextField(
                controller: _ipController,
                enabled: !_isStreaming,
                keyboardType: TextInputType.number,
                style: const TextStyle(color: Colors.white, fontSize: 18),
                decoration: InputDecoration(
                  labelText: 'Windows PC IP Address',
                  labelStyle: const TextStyle(color: Colors.white70),
                  prefixIcon: const Icon(Icons.laptop, color: Colors.white70),
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white30),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white, width: 2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  disabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              
              const SizedBox(height: 16),
              
              // PIN Input
              TextField(
                controller: _pinController,
                enabled: !_isStreaming,
                keyboardType: TextInputType.number,
                maxLength: 4,
                inputFormatters: [FilteringTextInputFormatter.digitsOnly],
                obscureText: true,
                style: const TextStyle(color: Colors.white, fontSize: 18),
                decoration: InputDecoration(
                  labelText: 'Security PIN (From PC)',
                  labelStyle: const TextStyle(color: Colors.white70),
                  prefixIcon: const Icon(Icons.lock, color: Colors.white70),
                  enabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white30),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white, width: 2),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  disabledBorder: OutlineInputBorder(
                    borderSide: const BorderSide(color: Colors.white12),
                    borderRadius: BorderRadius.circular(8),
                  ),
                ),
              ),
              
              const SizedBox(height: 24),

              // Controls
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.mic, color: Colors.white),
                      label: const Text('Start', style: TextStyle(color: Colors.white, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF4CAF50),
                        disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        elevation: 0,
                      ),
                      onPressed: _isStreaming ? null : _startStreaming,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: ElevatedButton.icon(
                      icon: const Icon(Icons.stop, color: Colors.white54),
                      label: const Text('Stop', style: TextStyle(color: Colors.white54, fontSize: 16)),
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.grey.withOpacity(0.5),
                        disabledBackgroundColor: Colors.grey.withOpacity(0.3),
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
                        elevation: 0,
                      ),
                      onPressed: _isStreaming ? _stopStreaming : null,
                    ),
                  ),
                ],
              ),
              
              const SizedBox(height: 24),

              // Status Box
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  border: Border.all(color: Colors.white30),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(
                          _isStreaming ? Icons.radio_button_checked : Icons.radio_button_unchecked,
                          color: _isStreaming ? Colors.green : Colors.white54,
                          size: 16,
                        ),
                        const SizedBox(width: 8),
                        Text(
                          _isStreaming ? 'STREAMING' : 'IDLE',
                          style: TextStyle(
                            color: _isStreaming ? Colors.green : Colors.white,
                            fontWeight: FontWeight.bold,
                            letterSpacing: 1.1,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    Text(
                      _status,
                      style: const TextStyle(color: Colors.white, fontSize: 14),
                    ),
                  ],
                ),
              ),
              
              const SizedBox(height: 40),
              
              // Instructions
              const Text(
                'Instructions:\n'
                '1. Start the Windows receiver (python main.py)\n'
                '2. Enter the PC\'s IP address and the Security PIN\n'
                '3. Tap Start to securely stream audio\n'
                '4. Audio: 48kHz, AES-256 Encrypted UDP',
                style: TextStyle(color: Colors.white54, fontSize: 14, height: 1.5),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
