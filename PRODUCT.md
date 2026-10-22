# PRODUCT.md — PocketDeck

## Overview
**PocketDeck** is a low-latency, local-network hardware companion web application served directly from a Windows PC over FastAPI. It turns a user's smartphone into a dedicated **Stream Deck, Per-App Audio Mixer, and OBS Cockpit** — used either one-handed in **Portrait** mode or propped on a desk next to the monitor in **Landscape Cockpit** mode.

## Surface Mode
- **Primary Mode:** `Operate` (precision instrument / hardware control surface)
- **Priorities:** Immediate scanability, zero-hesitation touch targets, real Windows application iconography, tactile feedback, and visual quietness during hours of peripheral desk use.
- **Anti-Goals:** Marketing fluff, decorative neon glows, redundant multi-chart KPI tiles, nested icon boxes, or sluggish bounce animations on high-frequency controls.

## Core Workflows
1. **Deck (Launch & Quick Audio):** View live PC telemetry (CPU, RAM, GPU), toggle Discord Mic/Deafen and Master Mute, adjust Master Volume, and tap real Windows application keycaps to launch or focus desktop software.
2. **Deck Editor (Option B CRUD):** Enter Edit Mode to reorder keys via drag-and-drop, delete keys with undo, rename apps, upload custom key icons, or add discovered Windows Start Menu apps (`Get-StartApps`).
3. **Audio Mixer:** Adjust per-process Windows CoreAudio (`pycaw`) volume sliders and mute states in real time with extracted `.exe` icons.
4. **System Controls:** Control Windows media playback (`Play/Pause`, `Prev`, `Next`, `Stop`), send remote keystrokes and shortcuts (`Copy`, `Paste`, `Cut`, `Undo`, `Select All`), sync the Windows clipboard, and trigger power states (`Lock`, `Sleep`, `Restart`, `Shut Down`) protected by a press-and-hold confirmation sheet.
