const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const assetsDir = path.join(__dirname, 'src/assets');
const logoFile = 'logo-full.png';
const logoPath = path.join(assetsDir, logoFile);
const tempPath = path.join(assetsDir, `temp-${logoFile}`);

async function optimizeTransparentLogo() {
  try {
    console.log(`Optimizing ${logoFile} with transparent background...`);

    // Resize and optimize while preserving transparency
    await sharp(logoPath)
      .resize(400, 400, { 
        fit: 'contain',
        background: { r: 0, g: 0, b: 0, alpha: 0 } // Transparent background
      })
      .png({ 
        compressionLevel: 9,
        adaptiveFiltering: true,
        force: true,
        quality: 85
      })
      .toFile(tempPath);

    // Replace original with optimized version
    fs.renameSync(tempPath, logoPath);

    console.log(`✅ Optimized ${logoFile} with transparent background`);
  } catch (error) {
    console.error(`❌ Failed to optimize ${logoFile}:`, error.message);
    // Clean up temp file if it exists
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }
  }
}

optimizeTransparentLogo();
