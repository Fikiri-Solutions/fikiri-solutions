# 💼 Fikiri Solutions Business Card Design

## Front Design (3.5" x 2")

### Design Specifications
- **Dimensions**: 3.5" x 2" (standard business card)
- **Background**: Cream (#F7F3E9) with subtle texture
- **Logo**: Top-left corner, 0.75" height
- **Text**: Primary text #4B1E0C, Accent #B33B1E
- **Border**: Subtle gradient border

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .business-card-front {
            width: 3.5in;
            height: 2in;
            background: #F7F3E9;
            border: 2px solid transparent;
            background-clip: padding-box;
            border-image: linear-gradient(135deg, #F39C12, #E7641C, #B33B1E) 1;
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            padding: 0.2in;
            box-sizing: border-box;
        }
        
        .logo {
            position: absolute;
            top: 0.15in;
            left: 0.15in;
            height: 0.75in;
            width: auto;
        }
        
        .contact-info {
            position: absolute;
            top: 0.15in;
            right: 0.15in;
            text-align: right;
        }
        
        .name {
            font-size: 18px;
            font-weight: bold;
            color: #4B1E0C;
            margin-bottom: 2px;
        }
        
        .title {
            font-size: 12px;
            color: #B33B1E;
            margin-bottom: 8px;
        }
        
        .company {
            font-size: 14px;
            font-weight: 600;
            color: #4B1E0C;
            margin-bottom: 10px;
        }
        
        .contact-details {
            font-size: 10px;
            color: #4B1E0C;
            line-height: 1.3;
        }
        
        .contact-details a {
            color: #B33B1E;
            text-decoration: none;
        }
        
        .tagline {
            position: absolute;
            bottom: 0.15in;
            left: 0.15in;
            font-size: 9px;
            color: #4B1E0C;
            font-style: italic;
            max-width: 2.5in;
        }
        
        .website {
            position: absolute;
            bottom: 0.15in;
            right: 0.15in;
            font-size: 10px;
            color: #B33B1E;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="business-card-front">
        <img src="fikiri-logo.png" alt="Fikiri Solutions" class="logo">
        
        <div class="contact-info">
            <div class="name">[Your Name]</div>
            <div class="title">[Your Title]</div>
            <div class="company">Fikiri Solutions</div>
            <div class="contact-details">
                📧 hello@fikirisolutions.com<br>
                📱 +1 (234) 567-8900<br>
                🌐 fikirisolutions.com
            </div>
        </div>
        
        <div class="tagline">
            Transform your business with AI-powered automation solutions
        </div>
        
        <div class="website">
            fikirisolutions.com
        </div>
    </div>
</body>
</html>
```

## Back Design (3.5" x 2")

### Design Specifications
- **Background**: Gradient (#F39C12 → #E7641C → #B33B1E)
- **Text**: White for contrast
- **Content**: Services overview and QR code
- **Logo**: Simplified version, bottom-right

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .business-card-back {
            width: 3.5in;
            height: 2in;
            background: linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%);
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            padding: 0.2in;
            box-sizing: border-box;
            color: white;
        }
        
        .services-title {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 8px;
            text-align: center;
        }
        
        .services-list {
            font-size: 10px;
            line-height: 1.4;
            margin-bottom: 15px;
        }
        
        .service-item {
            margin-bottom: 3px;
        }
        
        .qr-code {
            position: absolute;
            top: 0.15in;
            right: 0.15in;
            width: 0.6in;
            height: 0.6in;
            background: white;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 8px;
            color: #4B1E0C;
            text-align: center;
        }
        
        .logo-simple {
            position: absolute;
            bottom: 0.15in;
            right: 0.15in;
            height: 0.4in;
            width: auto;
            opacity: 0.8;
        }
        
        .cta-text {
            position: absolute;
            bottom: 0.15in;
            left: 0.15in;
            font-size: 9px;
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="business-card-back">
        <div class="qr-code">
            QR CODE<br>
            fikirisolutions.com
        </div>
        
        <div class="services-title">Our Services</div>
        <div class="services-list">
            <div class="service-item">🤖 AI-Powered Email Automation</div>
            <div class="service-item">📊 Intelligent CRM Management</div>
            <div class="service-item">📈 Business Process Optimization</div>
            <div class="service-item">🔧 Custom Automation Solutions</div>
            <div class="service-item">📱 Multi-Platform Integration</div>
        </div>
        
        <div class="cta-text">Ready to transform your business?</div>
        <img src="fikiri-logo-white.png" alt="Fikiri Solutions" class="logo-simple">
    </div>
</body>
</html>
```

## Print Specifications

### Paper Stock
- **Weight**: 16pt (400gsm) premium cardstock
- **Finish**: Matte or soft-touch lamination
- **Color**: Cream base (#F7F3E9)
- **Texture**: Subtle linen or smooth finish

### Printing Guidelines
- **Resolution**: 300 DPI minimum
- **Color Mode**: CMYK for professional printing
- **Bleed**: 0.125" bleed on all sides
- **Safe Area**: Keep text 0.1" from edges

### Color Conversions
```css
/* CMYK Values for Professional Printing */
--fikiri-primary-cmyk: 0, 70, 85, 30;    /* #B33B1E */
--fikiri-secondary-cmyk: 0, 55, 90, 10;  /* #E7641C */
--fikiri-accent-cmyk: 0, 25, 95, 5;      /* #F39C12 */
--fikiri-text-cmyk: 0, 25, 50, 70;      /* #4B1E0C */
--fikiri-bg-cmyk: 0, 5, 10, 3;           /* #F7F3E9 */
```

## Digital Business Card (vCard)

### vCard Format
```
BEGIN:VCARD
VERSION:3.0
FN:[Your Name]
ORG:Fikiri Solutions
TITLE:[Your Title]
TEL:+1234567890
EMAIL:hello@fikirisolutions.com
URL:https://fikirisolutions.com
NOTE:Transform your business with AI-powered automation solutions
END:VCARD
```

## QR Code Implementation

### QR Code Content
```
https://fikirisolutions.com/contact?ref=business-card&name=[Your Name]
```

### QR Code Generator
```javascript
// Generate QR code for business card
const qrCodeData = {
    url: 'https://fikirisolutions.com/contact',
    name: '[Your Name]',
    title: '[Your Title]',
    company: 'Fikiri Solutions',
    email: 'hello@fikirisolutions.com',
    phone: '+1234567890'
};

// Use QR code library to generate
const qrCode = QRCode.generate(JSON.stringify(qrCodeData));
```

## Brand Guidelines for Business Cards

### Logo Usage
- **Minimum Size**: 0.5" height
- **Clear Space**: 0.1" minimum around logo
- **Variants**: Use full-color on front, simplified on back

### Typography Hierarchy
- **Name**: 18px, Bold, #4B1E0C
- **Title**: 12px, Medium, #B33B1E
- **Company**: 14px, SemiBold, #4B1E0C
- **Contact**: 10px, Regular, #4B1E0C
- **Tagline**: 9px, Italic, #4B1E0C

### Color Usage
- **Primary Text**: #4B1E0C (Tree Brown)
- **Accent Text**: #B33B1E (Primary Red-Orange)
- **Background**: #F7F3E9 (Cream)
- **Gradient**: #F39C12 → #E7641C → #B33B1E

### Content Guidelines
- **Keep it simple**: Essential information only
- **Professional tone**: Clear and concise
- **Call-to-action**: Include website URL
- **Contact methods**: Email, phone, website
