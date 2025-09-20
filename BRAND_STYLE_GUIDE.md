# 🎨 Fikiri Solutions Brand Style Guide

## Brand Identity Overview

Fikiri Solutions is an AI-powered business automation platform that transforms how companies operate. Our brand embodies growth, stability, and innovation through natural elements and warm, professional colors.

---

## 🎨 Color Palette

### Primary Colors
| Color | Hex Code | Usage | CMYK | RGB |
|-------|----------|-------|------|-----|
| **Primary Red-Orange** | `#B33B1E` | Buttons, strong CTAs, primary brand elements | 0, 70, 85, 30 | 179, 59, 30 |
| **Bright Orange** | `#E7641C` | Hovers, icons, accents, secondary actions | 0, 55, 90, 10 | 231, 100, 28 |
| **Golden Yellow** | `#F39C12` | Highlights, graphs, stats, success states | 0, 25, 95, 5 | 243, 156, 18 |
| **Deep Red** | `#992D1E` | Alerts, section headers, warning states | 0, 70, 80, 40 | 153, 45, 30 |
| **Tree Brown** | `#4B1E0C` | Text, footer background, primary typography | 0, 25, 50, 70 | 75, 30, 12 |
| **Cream** | `#F7F3E9` | Page background, cards, light backgrounds | 0, 5, 10, 3 | 247, 243, 233 |

### Extended Palette
| Color | Hex Code | Usage |
|-------|----------|-------|
| **Light Cream** | `#FDF6E3` | Subtle backgrounds, borders |
| **Muted Brown** | `#8B4513` | Secondary text, muted elements |
| **Dark Brown** | `#3E2723` | Dark mode text, strong contrast |
| **Darkest Brown** | `#2C1810` | Maximum contrast text |

### Gradients
```css
/* Primary Brand Gradient */
background: linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%);

/* Subtle Background Gradient */
background: linear-gradient(135deg, #F7F3E9 0%, #F39C12 100%);

/* Animated Gradient (for hero sections) */
background: linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%);
background-size: 200% 200%;
animation: gradientShift 3s ease-in-out infinite;
```

---

## 🔤 Typography

### Primary Font Family
**Inter** - Modern, clean, highly readable sans-serif

### Font Weights
- **Light**: 300 (for subtle text)
- **Regular**: 400 (body text)
- **Medium**: 500 (emphasis)
- **SemiBold**: 600 (subheadings)
- **Bold**: 700 (headings)
- **ExtraBold**: 800 (display text)

### Typography Scale
| Element | Size | Weight | Color | Usage |
|---------|------|--------|-------|-------|
| **H1** | 48px | Bold | #4B1E0C | Main page headings |
| **H2** | 36px | Bold | #4B1E0C | Section headings |
| **H3** | 24px | SemiBold | #4B1E0C | Subsection headings |
| **H4** | 20px | SemiBold | #4B1E0C | Card headings |
| **H5** | 18px | Medium | #4B1E0C | Small headings |
| **H6** | 16px | Medium | #4B1E0C | Minor headings |
| **Body Large** | 18px | Regular | #4B1E0C | Important body text |
| **Body** | 16px | Regular | #4B1E0C | Standard body text |
| **Body Small** | 14px | Regular | #4B1E0C | Secondary text |
| **Caption** | 12px | Regular | #4B1E0C | Captions, labels |
| **Button** | 16px | SemiBold | White | Button text |
| **Link** | 16px | Medium | #B33B1E | Links, CTAs |

### Typography Pairings
```css
/* Heading Pairing */
.heading-primary {
    font-family: 'Inter', sans-serif;
    font-size: 48px;
    font-weight: 700;
    color: #4B1E0C;
    line-height: 1.2;
}

/* Body Text Pairing */
.body-text {
    font-family: 'Inter', sans-serif;
    font-size: 16px;
    font-weight: 400;
    color: #4B1E0C;
    line-height: 1.6;
}

/* Accent Text Pairing */
.accent-text {
    font-family: 'Inter', sans-serif;
    font-size: 18px;
    font-weight: 500;
    color: #B33B1E;
    line-height: 1.4;
}
```

---

## 🖼️ Logo Usage

### Logo Variations
1. **Full Color**: Complete logo with all colors (primary)
2. **Monochrome**: Single color version (for dark backgrounds)
3. **Simplified**: Tree icon only (for favicons, small applications)
4. **White**: White version (for dark backgrounds)

### Logo Sizing
| Application | Minimum Size | Recommended Size |
|-------------|--------------|------------------|
| **Website Header** | 120px height | 150px height |
| **Business Card** | 0.5" height | 0.75" height |
| **Social Media** | 100px height | 150px height |
| **Favicon** | 32x32px | 64x64px |
| **Print Materials** | 0.5" height | 1" height |

### Logo Clear Space
- **Minimum Clear Space**: 1x the height of the "FIKIRI" text
- **Recommended Clear Space**: 2x the height of the "FIKIRI" text
- **Never place text or graphics within the clear space**

### Logo Placement
- **Website Header**: Left-aligned, 150px height
- **Footer**: Centered, 100px height
- **Business Cards**: Top-left corner, 0.75" height
- **Social Media**: Centered, 150px height
- **Presentations**: Top-left corner, 120px height

---

## 🎯 Brand Voice & Tone

### Brand Personality
- **Professional**: Expert and knowledgeable
- **Approachable**: Friendly and accessible
- **Innovative**: Forward-thinking and cutting-edge
- **Reliable**: Trustworthy and stable
- **Transformative**: Focused on positive change

### Voice Characteristics
- **Clear**: Easy to understand
- **Confident**: Assured in our solutions
- **Helpful**: Focused on customer success
- **Inspiring**: Motivating action and change

### Tone Guidelines
| Context | Tone | Example |
|---------|------|---------|
| **Website Copy** | Professional, confident | "Transform your business with AI-powered automation" |
| **Social Media** | Friendly, engaging | "Ready to automate your workflow? Let's chat! 🤖" |
| **Email** | Professional, helpful | "We're here to help you succeed with automation" |
| **Support** | Patient, solution-focused | "Let's work together to resolve this issue" |

---

## 🎨 Design Elements

### Buttons
```css
/* Primary Button */
.btn-primary {
    background: #B33B1E;
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 16px;
    border: none;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-primary:hover {
    background: #E7641C;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(179, 59, 30, 0.3);
}

/* Secondary Button */
.btn-secondary {
    background: transparent;
    color: #B33B1E;
    border: 2px solid #B33B1E;
    padding: 10px 22px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 16px;
    cursor: pointer;
    transition: all 0.3s ease;
}

.btn-secondary:hover {
    background: #B33B1E;
    color: white;
}
```

### Cards
```css
/* Standard Card */
.card {
    background: #F7F3E9;
    border: 1px solid rgba(75, 30, 12, 0.1);
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 2px 8px rgba(75, 30, 12, 0.1);
    transition: all 0.3s ease;
}

.card:hover {
    box-shadow: 0 4px 16px rgba(75, 30, 12, 0.15);
    transform: translateY(-2px);
}

/* Gradient Card */
.card-gradient {
    background: linear-gradient(135deg, #F7F3E9 0%, #F39C12 100%);
    border: none;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 4px 16px rgba(243, 156, 18, 0.2);
}
```

### Icons
- **Style**: Outline icons with 2px stroke weight
- **Color**: #B33B1E for primary, #4B1E0C for secondary
- **Size**: 24px for standard, 16px for small, 32px for large
- **Library**: Lucide React or Heroicons

---

## 📱 Responsive Design

### Breakpoints
```css
/* Mobile First Approach */
@media (min-width: 640px) { /* sm */ }
@media (min-width: 768px) { /* md */ }
@media (min-width: 1024px) { /* lg */ }
@media (min-width: 1280px) { /* xl */ }
@media (min-width: 1536px) { /* 2xl */ }
```

### Mobile Considerations
- **Touch Targets**: Minimum 44px height
- **Text Size**: Minimum 16px to prevent zoom
- **Spacing**: Generous padding and margins
- **Navigation**: Clear, accessible menu

---

## 🌙 Dark Mode

### Dark Mode Colors
| Element | Light Mode | Dark Mode |
|---------|------------|-----------|
| **Background** | #F7F3E9 | #2C1810 |
| **Text** | #4B1E0C | #F7F3E9 |
| **Cards** | #F7F3E9 | #3E2723 |
| **Borders** | rgba(75, 30, 12, 0.1) | rgba(247, 243, 233, 0.1) |
| **Primary** | #B33B1E | #B33B1E (unchanged) |
| **Secondary** | #E7641C | #E7641C (unchanged) |

### Dark Mode Implementation
```css
.dark {
    --background: #2C1810;
    --foreground: #F7F3E9;
    --card: #3E2723;
    --border: rgba(247, 243, 233, 0.1);
}
```

---

## 📋 Brand Applications

### Website
- **Hero Section**: Animated gradient background
- **Navigation**: Primary color for active states
- **Buttons**: Primary color with hover effects
- **Cards**: Cream background with subtle shadows
- **Footer**: Tree brown background

### Business Materials
- **Business Cards**: Cream background with gradient border
- **Letterhead**: Logo top-left, cream background
- **Presentations**: Gradient backgrounds, brand colors
- **Brochures**: Cream background with brand accents

### Digital Marketing
- **Social Media**: Gradient backgrounds, brand colors
- **Email Templates**: Cream background, brand colors
- **Banner Ads**: Primary color with white text
- **Landing Pages**: Animated gradient hero sections

---

## ✅ Brand Checklist

### Logo Usage
- [ ] Correct logo variant for context
- [ ] Proper sizing and clear space
- [ ] High-quality image files
- [ ] Consistent placement

### Color Usage
- [ ] Primary colors for CTAs
- [ ] Secondary colors for accents
- [ ] Proper contrast ratios
- [ ] Consistent color values

### Typography
- [ ] Inter font family
- [ ] Proper font weights
- [ ] Consistent sizing scale
- [ ] Good readability

### Design Elements
- [ ] Consistent button styles
- [ ] Proper card designs
- [ ] Appropriate icon usage
- [ ] Responsive layouts

---

*This style guide ensures consistent application of the Fikiri Solutions brand across all touchpoints and materials.*
