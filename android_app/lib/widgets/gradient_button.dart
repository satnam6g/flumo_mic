import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';

class GradientButton extends StatelessWidget {
  final String text;
  final IconData icon;
  final LinearGradient gradient;
  final VoidCallback? onPressed;
  final bool isPulsing;

  const GradientButton({
    Key? key,
    required this.text,
    required this.icon,
    required this.gradient,
    this.onPressed,
    this.isPulsing = false,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final isDisabled = onPressed == null;

    Widget button = Container(
      height: 56,
      decoration: BoxDecoration(
        gradient: isDisabled ? null : gradient,
        color: isDisabled ? Colors.grey.withOpacity(0.3) : null,
        borderRadius: BorderRadius.circular(16),
        boxShadow: isDisabled
            ? []
            : [
                BoxShadow(
                  color: gradient.colors.first.withOpacity(0.4),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                )
              ],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onPressed,
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(icon, color: isDisabled ? Colors.grey : Colors.white),
              const SizedBox(width: 8),
              Text(
                text.toUpperCase(),
                style: TextStyle(
                  color: isDisabled ? Colors.grey : Colors.white,
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  letterSpacing: 1.2,
                ),
              ),
            ],
          ),
        ),
      ),
    );

    if (isPulsing && !isDisabled) {
      button = button.animate(onPlay: (controller) => controller.repeat())
          .shimmer(duration: 2000.ms, color: Colors.white24)
          .scaleXY(begin: 1.0, end: 1.02, duration: 1000.ms, curve: Curves.easeInOut)
          .then(delay: 0.ms)
          .scaleXY(begin: 1.02, end: 1.0, duration: 1000.ms, curve: Curves.easeInOut);
    }

    return button;
  }
}
