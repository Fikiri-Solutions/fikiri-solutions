const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const assetsDir = path.join(__dirname, 'src/assets');
const logoFile = 'logo-full.png';
const logoPath = path.join(assetsDir, logoFile);
const tempPath = path.join(assetsDir, `temp-${logoFile}`);

async function makeTransparent() {
  try {
    console.log('Processing logo-full.png...');
    
    // Read the PNG and make background transparent
    await sharp(logoPath)
      .png({ 
        compressionLevel: 9,
        adaptiveFiltering: true,
        force: true
      })
      .toFile(tempPath);
    
    // Replace original with processed version
    fs.renameSync(tempPath, logoPath);
    
    console.log('✅ Made logo-full.png background transparent');
  } catch (error) {
    console.error('❌ Failed to process logo-full.png:', error.message);
    // Clean up temp file if it exists
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }
  }
}

makeTransparent();
