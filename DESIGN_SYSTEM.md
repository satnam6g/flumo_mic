# Wireless Mic - Design System

This document outlines the core visual language for the Wireless Mic ecosystem, ensuring consistency across the Web, Windows, and Android platforms.

## Color Palette

### Dark Mode (Default)
| Name | Hex Code | Usage |
| :--- | :--- | :--- |
| Background | `#0f172a` | App/Window background |
| Surface/Card | `#1e293b` | Main content cards, dialogs |
| Surface Elevated | `#334155` | Hover states, borders, inputs |
| Primary | `#3b82f6` | Brand color, active states, links |
| Primary Hover | `#2563eb` | Hover states for primary elements |
| Secondary | `#8b5cf6` | Accents, secondary actions |
| Accent/Success | `#10b981` | Success states, connected, Start button |
| Error/Danger | `#ef4444` | Errors, disconnected, Stop button |
| Warning | `#f59e0b` | Warnings, connecting state |
| Text Primary | `#f8fafc` | Main readable text |
| Text Secondary | `#94a3b8` | Subtitles, labels, descriptions |
| Border | `#334155` | Card outlines, dividers |
| Gradient | `linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%)` | Primary buttons, active meters |

### Light Mode
| Name | Hex Code | Usage |
| :--- | :--- | :--- |
| Background | `#ffffff` | App/Window background |
| Surface/Card | `#f8fafc` | Main content cards, dialogs |
| Surface Elevated | `#e2e8f0` | Hover states, borders, inputs |
| Primary | `#2563eb` | Brand color, active states, links |
| Primary Hover | `#1d4ed8` | Hover states for primary elements |
| Secondary | `#7c3aed` | Accents, secondary actions |
| Accent/Success | `#059669` | Success states, connected, Start button |
| Error/Danger | `#dc2626` | Errors, disconnected, Stop button |
| Text Primary | `#0f172a` | Main readable text |
| Text Secondary | `#64748b` | Subtitles, labels, descriptions |
| Border | `#e2e8f0` | Card outlines, dividers |

## Typography
- **Font Family**: 'Inter', 'Segoe UI', system-ui, sans-serif
- **Headings**: 600-700 weight
- **Body**: 400-500 weight
- **IP Address Display**: 2rem (32px), 700 weight, monospace fallback
- **Button Text**: 14px, 600 weight, uppercase tracking
- **Scale**: 12px (small label), 14px (body), 16px (button/list), 20px (card title), 24px (heading), 32px (display).

## Spacing & Layout
- **Base Grid**: 4px
- **Scale**: 4px, 8px, 12px, 16px, 24px, 32px
- **Card Padding**: 24px
- **Button Padding**: 12px 24px
- **Section Spacing**: 20px

## Border Radius
- **Cards**: 12px (Web/Win) to 16px (Android M3)
- **Buttons**: 8px (Web/Win) to 16px (Android M3)
- **Large Containers**: 16px

## Elevations & Shadows
- **Dark Shadow**: `0 4px 6px -1px rgba(0, 0, 0, 0.3)`
- **Light Shadow**: `0 4px 6px -1px rgba(0, 0, 0, 0.1)`
- **Android M3**: Flat by default, subtle elevation for floating cards.

## Animation & Interaction
- **Duration**: 300ms ease-in-out for transitions.
- **Micro-interactions**: Button scale to 1.02 on hover (Windows/Web).
- **LED Indicator**: CSS-like keyframe pulse when connecting/active.

## Cross-Platform Sync
- Use the exact Hex codes defined here.
- Always implement a safe fallback font if 'Inter' fails to load (e.g., system sans-serif).
