# Aurora Design System

**Style**: Soft Premium Modern
**Philosophy**: Sophisticated, diffused, "Northern Lights".

## 1. Core Palette
### Backgrounds
- **Deep Space (Main)**: `#0B0C15`
- **Surface (Glass)**: `bg-white/5 backdrop-blur-xl border-white/10`
- **Surface Hover**: `bg-white/10`

### Typography
- **Primary**: `#EDEDEF` (Soft White)
- **Secondary**: `#9496A1` (Cool Grey)
- **Accent**: `#D4D4D8` (Metallic)

### Accents (Gradients)
- **Aurora Primary**: `bg-gradient-to-r from-purple-400 to-teal-400`
- **Status Green**: `#4ADE80` (Pastel)
- **Status Red**: `#FB7185` (Soft Rose)

## 2. Components
### Card Glass
```css
.card-glass {
  @apply bg-white/3 backdrop-blur-xl border border-white/10 rounded-2xl shadow-lg;
}
```

### Button Aurora
```css
.btn-aurora {
  @apply bg-gradient-to-r from-purple-400 to-teal-400 text-white font-medium px-6 py-2 rounded-lg 
         shadow-[0_0_20px_-5px_rgba(167,139,250,0.5)] hover:shadow-[0_0_30px_-5px_rgba(167,139,250,0.6)] 
         transition-all duration-300;
}
```

### Input Field
```css
.input-field {
  @apply bg-[#1A1B26] text-[#EDEDEF] placeholder-[#9496A1] rounded-lg px-4 py-3 
         focus:outline-none focus:ring-1 focus:ring-purple-400/50 transition-all;
}
```
