# DESIGN.md — PocketDeck Design System

## 1. Aesthetic Direction (`true-black-flat` Hardware Control Surface)
PocketDeck follows the **Operate** mode discipline (`impeccable`) combined with **Taste-Skill's `true-black-flat`** app-screen architecture and **Emil Kowalski's** motion and mobile-native engineering rules:
- **Flat Tonal Hierarchy:** Elevation is expressed through solid lightness steps (`--bg-base` → `--surface-1` → `--surface-2` → `--surface-3`) and crisp `1px` hairlines (`rgba(255, 255, 255, 0.07)`).
- **Zero Decorative Gradients or Neon Glows:** Cards, keys, and mixer rows never use radial color washes, multi-layer drop shadows, or zero-offset colored neon glows.
- **Color Spent on State & Real Icons (~3–5% Budget):** The interface chrome stays quiet so real extracted 256×256 Windows application icons and active state indicators (`#7C5CFF` electric violet and semantic status dots) read immediately at a glance.

## 2. Typography
- **Primary Font:** Self-hosted `DM Sans` Variable (`400–700`), chosen for crisp geometric legibility at small instrument sizes without falling into overused AI defaults (`Inter`, `Roboto`, `Space Grotesk`).
- **Numeric Discipline:** All telemetry percentages, volume readouts, and counters use `font-variant-numeric: tabular-nums` so numbers never jitter during live polling.
- **Strict Size Floor:** No visible UI text may fall below `11px` (`0.6875rem`). Section headers use sentence case (`13px`, `font-weight: 600`) rather than tiny tracked uppercase labels.
- **Mobile Input Rule:** All `<input>` and `<textarea>` elements use `font-size: 16px` (`1rem`) to prevent iOS Safari from auto-zooming on focus.

## 3. Color & Contrast Tokens
| Token | Value | Role & Contrast |
| :--- | :--- | :--- |
| `--bg-base` | `#08090C` | Primary app chassis canvas |
| `--bg-elevated` | `#0E1015` | Sticky header, sheets, and navigation dock |
| `--surface-1` | `#12151C` | Grouped section panels and linear list containers |
| `--surface-2` | `#181C25` | Resting Stream Deck keycaps and control buttons |
| `--surface-3` | `#222734` | Active / pressed keycaps and selected items |
| `--text-primary` | `#F3F5F8` | Primary labels and tabular numbers (`17.8:1` on base) |
| `--text-secondary` | `#B4BCCF` | Section headers and secondary labels (`9.6:1` on base) |
| `--text-muted` | `#8C95AA` | Sublabels and inactive captions (`≥4.6:1` across all surfaces, WCAG AA compliant) |
| `--accent` | `#7C5CFF` | Active state borders, sliders, and focus indicators |
| `--accent-solid` | `#6344F5` | Filled primary action buttons with `#FFFFFF` text (`5.1:1` WCAG AA contrast) |
| `--status-ok` | `#22C58B` | Online / live telemetry indicator |
| `--status-warn` | `#E5A024` | High load (`>75%`) / caution indicator |
| `--status-danger` | `#E5484D` | Muted / critical load (`>90%`) / destructive action |

## 4. Motion & Touch Ergonomics (Emil Kowalski Rules)
- **Easing Tokens:**
  - `--ease-out: cubic-bezier(0.23, 1, 0.32, 1)` (press feedback, UI transitions)
  - `--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1)` (structural movement)
  - `--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1)` (bottom sheets & drawers)
- **Tactile Key Press:** `:active` uses `transform: scale(0.97)` over `120ms var(--ease-out)`.
- **Hover Gating:** Every `:hover` rule is wrapped in `@media (hover: hover) and (pointer: fine)` so touch taps never leave sticky hover states.
- **Compositor Hold-to-Confirm:** Destructive power actions use a hardware-accelerated `clip-path: inset(0 100% 0 0)` fill (`1150ms linear` on hold, `200ms var(--ease-out)` snap-back on early release).
- **Drag-to-Dismiss Sheets & FLIP Reordering:** Bottom sheets track pointer drag velocity (`> 0.11 px/ms` or `> 35%` height to dismiss), and Deck Edit Mode animates sibling key swaps via FLIP (`getBoundingClientRect` delta transforms).
