# Aurora Design System

**Style**: Soft Premium Modern
**Philosophy**: Move away from harsh "hacker neon" to a sophisticated, diffused aesthetic. Think "Northern Lights" (Aurora) - soft gradients, matte finishes, and deep slate backgrounds.

## 1. Core Palette

### Backgrounds
- **Deep Space (Main BG)**: `#0B0C15` a very dark, desaturated slate.
- **Surface (Glass)**: `rgba(255, 255, 255, 0.03)` with `backdrop-filter: blur(20px)`.
- **Surface Hover**: `rgba(255, 255, 255, 0.07)`.

### Typography
- **Primary Text**: `#EDEDEF` (Soft White) - High legibility but not blinding.
- **Secondary Text**: `#9496A1` (Cool Grey) - For labels and metadata.
- **Accent Text**: `#D4D4D8` (Metallic).

### Accents (The Aurora)
Do not use these as solid blocks. Use them as gradients or subtle borders.
- **Aurora Primary**: Linear Gradient (`#A78BFA` -> `#2DD4BF`) (Soft Lavender to Teal).
- **Status Green**: `#4ADE80` (Pastel Green) - *Not lime*.
- **Status Red**: `#FB7185` (Soft Rose) - *Not fire engine red*.

## 2. Design Tokens

### Shadows & Glows
- **Soft Glow**: `0 0 40px -10px rgba(167, 139, 250, 0.15)`.
- **Card Shadow**: `0 4px 6px -1px rgba(0, 0, 0, 0.3)`.

### Borders
- **Glass Border**: `1px solid rgba(255, 255, 255, 0.08)`.
- **Active Border**: `1px solid rgba(167, 139, 250, 0.3)`.

## 3. UI Components

### Cards (Glass)
- **Background**: Matte glass (low opacity white on dark).
- **Border**: Thin, subtle white opacity.
- **Corner Radius**: `xl` or `2xl` (16px - 24px) for a friendly feel.

### Buttons
- **Primary**: Soft gradient background, white text, slightly glowing shadow on hover.
- **Secondary**: Ghost style (transparent), white text, subtle hover bg.
- **Destructive**: Rose-tinted ghost or soft rose background.

### Inputs
- **Style**: Filled (very dark grey), no border by default, soft inner glow on focus.
- **Text**: White.
- **Placeholder**: Cool Grey.

## 4. Usage in Tailwind (v4)

We use CSS variables mapped to the `@theme` in `globals.css`.

```css
/* Example Usage */
.card-glass {
  @apply bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl;
}
```
