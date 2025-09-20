# 📱 Fikiri Solutions Social Media Banner Templates

## LinkedIn Company Banner (1584x396px)

### Design Specifications
- **Dimensions**: 1584x396 pixels
- **Background**: Cream (#F7F3E9) with subtle gradient
- **Logo**: Top-left corner, 120px height
- **Text**: "Transform Your Business with AI-Powered Automation"
- **Colors**: Primary text #4B1E0C, Accent #B33B1E

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .linkedin-banner {
            width: 1584px;
            height: 396px;
            background: linear-gradient(135deg, #F7F3E9 0%, #F39C12 100%);
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            overflow: hidden;
        }
        
        .logo {
            position: absolute;
            top: 30px;
            left: 40px;
            height: 120px;
            width: auto;
        }
        
        .main-text {
            position: absolute;
            top: 50%;
            left: 200px;
            transform: translateY(-50%);
            font-size: 48px;
            font-weight: bold;
            color: #4B1E0C;
            line-height: 1.2;
            max-width: 800px;
        }
        
        .accent-text {
            color: #B33B1E;
        }
        
        .subtitle {
            position: absolute;
            bottom: 40px;
            right: 40px;
            font-size: 24px;
            color: #4B1E0C;
            font-weight: 500;
        }
        
        .tree-pattern {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 300px;
            height: 200px;
            background: url('tree-pattern.svg') no-repeat;
            opacity: 0.1;
        }
    </style>
</head>
<body>
    <div class="linkedin-banner">
        <img src="fikiri-logo.png" alt="Fikiri Solutions" class="logo">
        <div class="main-text">
            Transform Your Business with <span class="accent-text">AI-Powered</span> Automation
        </div>
        <div class="subtitle">fikirisolutions.com</div>
        <div class="tree-pattern"></div>
    </div>
</body>
</html>
```

## Twitter Header (1500x500px)

### Design Specifications
- **Dimensions**: 1500x500 pixels
- **Background**: Animated gradient (#F39C12 → #E7641C → #B33B1E)
- **Logo**: Centered, 150px height
- **Text**: "AI-Powered Business Solutions"
- **Colors**: White text for contrast

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .twitter-header {
            width: 1500px;
            height: 500px;
            background: linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%);
            background-size: 200% 200%;
            animation: gradientShift 3s ease-in-out infinite;
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .logo {
            height: 150px;
            width: auto;
            margin-bottom: 20px;
        }
        
        .main-text {
            font-size: 42px;
            font-weight: bold;
            color: white;
            text-align: center;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 24px;
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="twitter-header">
        <img src="fikiri-logo-white.png" alt="Fikiri Solutions" class="logo">
        <div class="main-text">AI-Powered Business Solutions</div>
        <div class="subtitle">Transform • Automate • Scale</div>
    </div>
</body>
</html>
```

## Facebook Cover (1200x630px)

### Design Specifications
- **Dimensions**: 1200x630 pixels
- **Background**: Cream (#F7F3E9) with tree pattern
- **Logo**: Top-left, 100px height
- **Text**: "Empowering Businesses with Intelligent Automation"
- **Colors**: Primary text #4B1E0C, Accent #B33B1E

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .facebook-cover {
            width: 1200px;
            height: 630px;
            background: #F7F3E9;
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            overflow: hidden;
        }
        
        .logo {
            position: absolute;
            top: 30px;
            left: 30px;
            height: 100px;
            width: auto;
        }
        
        .main-content {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            text-align: center;
            max-width: 800px;
        }
        
        .main-text {
            font-size: 36px;
            font-weight: bold;
            color: #4B1E0C;
            margin-bottom: 15px;
            line-height: 1.3;
        }
        
        .accent-text {
            color: #B33B1E;
        }
        
        .subtitle {
            font-size: 20px;
            color: #4B1E0C;
            margin-bottom: 20px;
        }
        
        .cta-button {
            display: inline-block;
            background: #B33B1E;
            color: white;
            padding: 12px 30px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: 600;
            font-size: 18px;
        }
        
        .tree-pattern {
            position: absolute;
            bottom: 0;
            right: 0;
            width: 200px;
            height: 150px;
            background: url('tree-pattern.svg') no-repeat;
            opacity: 0.05;
        }
    </style>
</head>
<body>
    <div class="facebook-cover">
        <img src="fikiri-logo.png" alt="Fikiri Solutions" class="logo">
        <div class="main-content">
            <div class="main-text">
                Empowering Businesses with <span class="accent-text">Intelligent Automation</span>
            </div>
            <div class="subtitle">AI-Powered Solutions for Modern Enterprises</div>
            <a href="https://fikirisolutions.com" class="cta-button">Get Started</a>
        </div>
        <div class="tree-pattern"></div>
    </div>
</body>
</html>
```

## Instagram Story (1080x1920px)

### Design Specifications
- **Dimensions**: 1080x1920 pixels
- **Background**: Animated gradient
- **Logo**: Centered, 200px height
- **Text**: "Swipe up to transform your business"
- **Colors**: White text for contrast

### HTML/CSS Template
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        .instagram-story {
            width: 1080px;
            height: 1920px;
            background: linear-gradient(135deg, #F39C12 0%, #E7641C 50%, #B33B1E 100%);
            background-size: 200% 200%;
            animation: gradientShift 3s ease-in-out infinite;
            position: relative;
            font-family: 'Inter', Arial, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }
        
        @keyframes gradientShift {
            0%, 100% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
        }
        
        .logo {
            height: 200px;
            width: auto;
            margin-bottom: 40px;
        }
        
        .main-text {
            font-size: 48px;
            font-weight: bold;
            color: white;
            text-align: center;
            margin-bottom: 20px;
            line-height: 1.2;
        }
        
        .subtitle {
            font-size: 28px;
            color: rgba(255, 255, 255, 0.9);
            text-align: center;
            margin-bottom: 40px;
        }
        
        .swipe-up {
            position: absolute;
            bottom: 100px;
            font-size: 24px;
            color: white;
            text-align: center;
        }
        
        .arrow {
            font-size: 36px;
            margin-bottom: 10px;
        }
    </style>
</head>
<body>
    <div class="instagram-story">
        <img src="fikiri-logo-white.png" alt="Fikiri Solutions" class="logo">
        <div class="main-text">Transform Your Business</div>
        <div class="subtitle">with AI-Powered Automation</div>
        <div class="swipe-up">
            <div class="arrow">↑</div>
            <div>Swipe up to get started</div>
        </div>
    </div>
</body>
</html>
```

## Brand Guidelines for Social Media

### Color Usage
- **Primary**: #B33B1E (buttons, strong CTAs)
- **Secondary**: #E7641C (hovers, icons, accents)
- **Accent**: #F39C12 (highlights, graphs, stats)
- **Text**: #4B1E0C (main text, headers)
- **Background**: #F7F3E9 (page backgrounds, cards)

### Typography
- **Headings**: Inter Bold, 36-48px
- **Body Text**: Inter Regular, 18-24px
- **Captions**: Inter Medium, 14-16px

### Logo Usage
- **Minimum Size**: 100px height
- **Clear Space**: 1x logo height minimum
- **Backgrounds**: Use appropriate variant for contrast

### Content Guidelines
- **Tone**: Professional yet approachable
- **Message**: Focus on transformation and automation
- **Call-to-Action**: Always include website link
- **Hashtags**: #FikiriSolutions #AIAutomation #BusinessTransformation
