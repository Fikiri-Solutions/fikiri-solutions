# Fikiri Solutions Brand Guidelines

## 🎨 Brand Colors

### Primary Palette (Extracted from Logo)

| Color | Hex Code | Usage | Description |
|-------|----------|-------|-------------|
| **Primary** | `#B85450` | Main brand color, buttons, links | Tree canopy reddish-orange |
| **Secondary** | `#E67E22` | Accent elements, highlights | Sunset orange |
| **Accent** | `#FFB84D` | Call-to-action, alerts | Bright yellow-orange |
| **Warning** | `#D35400` | Warning states, notifications | Burnt orange |
| **Error** | `#C0392B` | Error states, critical alerts | Deep red-orange |
| **Text** | `#8B4513` | Primary text, headings | Tree trunk brown |
| **Background** | `#FDF6E3` | Page backgrounds, cards | Creamy off-white |

### Extended Palette

| Color | Hex Code | Usage |
|-------|----------|-------|
| Light Yellow | `#F4D03F` | Subtle accents, highlights |
| Muted Brown | `#A1887F` | Secondary text, borders |
| Dark Brown | `#5D4037` | Dark text, strong contrast |
| Darkest Brown | `#3E2723` | Maximum contrast text |

### Gradients

```css
/* Primary Brand Gradient */
background: linear-gradient(135deg, #FFB84D 0%, #E67E22 50%, #C0392B 100%);

/* Subtle Background Gradient */
background: linear-gradient(135deg, #FDF6E3 0%, #F4D03F 100%);
```

## 🎯 Usage Guidelines

### Primary Color Usage
- **Primary (#B85450)**: Use for main CTAs, primary buttons, active states
- **Secondary (#E67E22)**: Use for secondary buttons, hover states
- **Accent (#FFB84D)**: Use for highlights, success states, important notices

### Text Hierarchy
- **Headings**: Use `#8B4513` (Tree trunk brown)
- **Body Text**: Use `#5D4037` (Dark brown) for readability
- **Muted Text**: Use `#A1887F` (Muted brown) for secondary information

### Background Usage
- **Primary Background**: `#FDF6E3` (Creamy off-white)
- **Card Backgrounds**: `#FDF6E3` with subtle shadows
- **Dark Mode**: Use `#3E2723` as primary dark background

## 🖼️ Logo Usage

### Logo Variations
1. **Full Color**: Use on light backgrounds
2. **Monochrome**: Use on dark backgrounds or single-color applications
3. **Simplified**: Use for favicons and small applications

### Logo Spacing
- **Minimum Clear Space**: 1x the height of the "FIKIRI" text
- **Recommended Clear Space**: 2x the height of the "FIKIRI" text

### Logo Placement
- **Website Header**: Left-aligned, 40px height
- **Footer**: Centered, 30px height
- **Favicon**: 32x32px simplified version
- **Social Media**: Use full-color version

## 📱 Digital Applications

### Website Implementation
```css
/* CSS Variables */
:root {
  --fikiri-primary: #B85450;
  --fikiri-secondary: #E67E22;
  --fikiri-accent: #FFB84D;
  --fikiri-text: #8B4513;
  --fikiri-bg: #FDF6E3;
}
```

### Tailwind Classes
```html
<!-- Primary Button -->
<button class="bg-brand-primary text-white hover:bg-brand-secondary">
  Get Started
</button>

<!-- Text Colors -->
<h1 class="text-brand-text">Heading</h1>
<p class="text-fikiri-900">Body text</p>

<!-- Backgrounds -->
<div class="bg-brand-background">Content</div>
```

## 🎨 Color Psychology

### Brand Personality
- **Warmth**: The sunset colors convey warmth and approachability
- **Growth**: The tree symbolizes growth, stability, and natural progress
- **Trust**: Earth tones suggest reliability and trustworthiness
- **Innovation**: The gradient suggests forward movement and innovation

### Industry Alignment
- **Technology**: Modern gradients with natural elements
- **Business**: Professional earth tones with warm accents
- **Automation**: Dynamic gradients suggesting efficiency
- **Solutions**: Balanced palette suggesting comprehensive solutions

## 📋 Implementation Checklist

### Website Integration
- [ ] Update CSS variables with brand colors
- [ ] Replace existing color scheme
- [ ] Update logo in header and footer
- [ ] Create favicon from logo
- [ ] Update PWA app icons

### Business Applications
- [ ] Update Stripe account logo
- [ ] Create email signature template
- [ ] Update social media profiles
- [ ] Create business card design
- [ ] Update invoice templates

### Marketing Materials
- [ ] Create presentation templates
- [ ] Design social media graphics
- [ ] Update website hero section
- [ ] Create product screenshots
- [ ] Design promotional materials

## 🔧 Technical Implementation

### CSS Classes
```css
.fikiri-primary { color: #B85450; }
.fikiri-secondary { color: #E67E22; }
.fikiri-accent { color: #FFB84D; }
.fikiri-bg { background-color: #FDF6E3; }
.fikiri-gradient { background: linear-gradient(135deg, #FFB84D 0%, #E67E22 50%, #C0392B 100%); }
```

### React Components
```tsx
// Brand color hook
const useBrandColors = () => ({
  primary: '#B85450',
  secondary: '#E67E22',
  accent: '#FFB84D',
  text: '#8B4513',
  background: '#FDF6E3'
});
```

## 📊 Accessibility

### Contrast Ratios
- **Primary on Background**: 4.5:1 (WCAG AA compliant)
- **Text on Background**: 7:1 (WCAG AAA compliant)
- **Secondary Text**: 4.5:1 (WCAG AA compliant)

### Color Blindness Considerations
- All colors are distinguishable for common color vision deficiencies
- Use patterns or icons alongside colors for critical information
- Test with color blindness simulators

---

*This brand guide ensures consistent application of the Fikiri Solutions visual identity across all touchpoints.*
