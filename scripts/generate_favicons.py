# Favicon and PWA Assets Generator
# Creates all required favicon and PWA assets with Fikiri brand colors

import os
from PIL import Image, ImageDraw, ImageFont
import json

# Brand colors from logo
BRAND_COLORS = {
    'primary': '#B33B1E',
    'secondary': '#E7641C', 
    'accent': '#F39C12',
    'text': '#4B1E0C',
    'background': '#F7F3E9'
}

def hex_to_rgb(hex_color):
    """Convert hex color to RGB tuple"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def create_favicon(size, filename):
    """Create favicon with brand colors"""
    # Create image with brand background
    img = Image.new('RGBA', (size, size), hex_to_rgb(BRAND_COLORS['background']) + (255,))
    draw = ImageDraw.Draw(img)
    
    # Draw simplified tree icon
    center = size // 2
    
    # Tree trunk (brown)
    trunk_width = max(2, size // 8)
    trunk_height = size // 3
    trunk_x = center - trunk_width // 2
    trunk_y = size - trunk_height
    draw.rectangle([trunk_x, trunk_y, trunk_x + trunk_width, size], 
                   fill=hex_to_rgb(BRAND_COLORS['text']))
    
    # Tree canopy (primary brand color)
    canopy_radius = size // 3
    canopy_y = center - canopy_radius // 2
    draw.ellipse([center - canopy_radius, canopy_y, 
                  center + canopy_radius, canopy_y + canopy_radius], 
                 fill=hex_to_rgb(BRAND_COLORS['primary']))
    
    # Save favicon
    img.save(f'frontend/public/{filename}', 'PNG')
    print(f"Created {filename} ({size}x{size})")

def create_app_icon(size, filename):
    """Create app icon for PWA"""
    # Create image with gradient background
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Create gradient background
    for y in range(size):
        # Gradient from accent to primary
        ratio = y / size
        r1, g1, b1 = hex_to_rgb(BRAND_COLORS['accent'])
        r2, g2, b2 = hex_to_rgb(BRAND_COLORS['primary'])
        
        r = int(r1 + (r2 - r1) * ratio)
        g = int(g1 + (g2 - g1) * ratio)
        b = int(b1 + (b2 - b1) * ratio)
        
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
    
    # Draw tree icon (white for contrast)
    center = size // 2
    
    # Tree trunk
    trunk_width = max(3, size // 6)
    trunk_height = size // 3
    trunk_x = center - trunk_width // 2
    trunk_y = size - trunk_height
    draw.rectangle([trunk_x, trunk_y, trunk_x + trunk_width, size], 
                   fill=(255, 255, 255, 255))
    
    # Tree canopy
    canopy_radius = size // 3
    canopy_y = center - canopy_radius // 2
    draw.ellipse([center - canopy_radius, canopy_y, 
                  center + canopy_radius, canopy_y + canopy_radius], 
                 fill=(255, 255, 255, 255))
    
    # Save app icon
    img.save(f'frontend/public/{filename}', 'PNG')
    print(f"Created {filename} ({size}x{size})")

def create_apple_touch_icon(size, filename):
    """Create Apple touch icon"""
    # Create image with rounded corners
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Create rounded rectangle background
    corner_radius = size // 8
    draw.rounded_rectangle([0, 0, size, size], 
                          radius=corner_radius,
                          fill=hex_to_rgb(BRAND_COLORS['background']) + (255,))
    
    # Draw tree icon
    center = size // 2
    
    # Tree trunk
    trunk_width = max(3, size // 6)
    trunk_height = size // 3
    trunk_x = center - trunk_width // 2
    trunk_y = size - trunk_height
    draw.rectangle([trunk_x, trunk_y, trunk_x + trunk_width, size], 
                   fill=hex_to_rgb(BRAND_COLORS['text']))
    
    # Tree canopy
    canopy_radius = size // 3
    canopy_y = center - canopy_radius // 2
    draw.ellipse([center - canopy_radius, canopy_y, 
                  center + canopy_radius, canopy_y + canopy_radius], 
                 fill=hex_to_rgb(BRAND_COLORS['primary']))
    
    # Save Apple touch icon
    img.save(f'frontend/public/{filename}', 'PNG')
    print(f"Created {filename} ({size}x{size})")

def create_manifest():
    """Create PWA manifest file"""
    manifest = {
        "name": "Fikiri Solutions",
        "short_name": "Fikiri",
        "description": "AI-powered business automation platform",
        "start_url": "/",
        "display": "standalone",
        "background_color": BRAND_COLORS['background'],
        "theme_color": BRAND_COLORS['primary'],
        "orientation": "portrait-primary",
        "icons": [
            {
                "src": "/favicon-16x16.png",
                "sizes": "16x16",
                "type": "image/png"
            },
            {
                "src": "/favicon-32x32.png",
                "sizes": "32x32",
                "type": "image/png"
            },
            {
                "src": "/apple-touch-icon.png",
                "sizes": "180x180",
                "type": "image/png"
            },
            {
                "src": "/android-chrome-192x192.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/android-chrome-512x512.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ],
        "categories": ["business", "productivity", "utilities"],
        "lang": "en",
        "dir": "ltr"
    }
    
    with open('frontend/public/manifest.json', 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print("Created manifest.json")

def create_browserconfig():
    """Create browserconfig.xml for Windows tiles"""
    browserconfig = '''<?xml version="1.0" encoding="utf-8"?>
<browserconfig>
    <msapplication>
        <tile>
            <square70x70logo src="/mstile-70x70.png"/>
            <square150x150logo src="/mstile-150x150.png"/>
            <square310x310logo src="/mstile-310x310.png"/>
            <wide310x150logo src="/mstile-310x150.png"/>
            <TileColor>#B33B1E</TileColor>
        </tile>
    </msapplication>
</browserconfig>'''
    
    with open('frontend/public/browserconfig.xml', 'w') as f:
        f.write(browserconfig)
    
    print("Created browserconfig.xml")

def create_splash_screens():
    """Create splash screens for PWA"""
    splash_sizes = [
        (640, 1136),   # iPhone 5
        (750, 1334),   # iPhone 6/7/8
        (828, 1792),   # iPhone XR
        (1125, 2436),  # iPhone X/XS
        (1242, 2688),  # iPhone XS Max
        (1536, 2048),  # iPad
        (2048, 2732)   # iPad Pro
    ]
    
    for width, height in splash_sizes:
        img = Image.new('RGBA', (width, height), hex_to_rgb(BRAND_COLORS['background']) + (255,))
        draw = ImageDraw.Draw(img)
        
        # Calculate logo size (1/3 of screen width)
        logo_size = min(width, height) // 3
        center_x = width // 2
        center_y = height // 2
        
        # Draw tree icon
        # Tree trunk
        trunk_width = max(3, logo_size // 6)
        trunk_height = logo_size // 3
        trunk_x = center_x - trunk_width // 2
        trunk_y = center_y + logo_size // 6
        draw.rectangle([trunk_x, trunk_y, trunk_x + trunk_width, trunk_y + trunk_height], 
                       fill=hex_to_rgb(BRAND_COLORS['text']))
        
        # Tree canopy
        canopy_radius = logo_size // 3
        canopy_y = center_y - canopy_radius // 2
        draw.ellipse([center_x - canopy_radius, canopy_y, 
                      center_x + canopy_radius, canopy_y + canopy_radius], 
                     fill=hex_to_rgb(BRAND_COLORS['primary']))
        
        filename = f'splash-{width}x{height}.png'
        img.save(f'frontend/public/{filename}', 'PNG')
        print(f"Created {filename}")

def main():
    """Generate all favicon and PWA assets"""
    print("Generating favicon and PWA assets...")
    
    # Create public directory if it doesn't exist
    os.makedirs('frontend/public', exist_ok=True)
    
    # Generate favicons
    favicon_sizes = [16, 32, 48, 64]
    for size in favicon_sizes:
        create_favicon(size, f'favicon-{size}x{size}.png')
    
    # Generate app icons
    app_icon_sizes = [192, 512]
    for size in app_icon_sizes:
        create_app_icon(size, f'android-chrome-{size}x{size}.png')
    
    # Generate Apple touch icon
    create_apple_touch_icon(180, 'apple-touch-icon.png')
    
    # Generate Windows tiles
    tile_sizes = [70, 150, 310]
    for size in tile_sizes:
        create_app_icon(size, f'mstile-{size}x{size}.png')
    
    # Create wide tile
    create_app_icon(310, 'mstile-310x150.png')
    
    # Generate splash screens
    create_splash_screens()
    
    # Create manifest and browserconfig
    create_manifest()
    create_browserconfig()
    
    print("\nAll favicon and PWA assets generated successfully!")
    print("\nGenerated files:")
    print("- favicon-16x16.png, favicon-32x32.png, favicon-48x48.png, favicon-64x64.png")
    print("- apple-touch-icon.png")
    print("- android-chrome-192x192.png, android-chrome-512x512.png")
    print("- mstile-70x70.png, mstile-150x150.png, mstile-310x310.png, mstile-310x150.png")
    print("- splash-*.png (various sizes)")
    print("- manifest.json")
    print("- browserconfig.xml")

if __name__ == '__main__':
    main()
