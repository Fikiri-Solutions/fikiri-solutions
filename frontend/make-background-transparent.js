const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const assetsDir = path.join(__dirname, 'src/assets');
const logoFile = 'logo-full.png';
const logoPath = path.join(assetsDir, logoFile);
const tempPath = path.join(assetsDir, `temp-${logoFile}`);

async function makeBackgroundTransparentPreserveColors() {
  try {
    console.log(`Processing ${logoFile} to make beige background transparent while preserving colors...`);

    // First, let's restore the original image
    await sharp("/Users/mac/Downloads/Fikiri_logo.png")
      .png({
        compressionLevel: 9,
        adaptiveFiltering: true,
        force: true
      })
      .toFile(tempPath);

    // Now create a mask for the beige background
    // The beige background is very light, so we'll use a threshold approach
    const mask = await sharp(tempPath)
      .threshold(245) // Make very light colors (beige) white
      .negate() // Invert: white becomes black, dark colors become white
      .png()
      .toBuffer();

    // Apply the mask to the original image to create transparency
    await sharp(tempPath)
      .composite([{
        input: mask,
        blend: 'dest-in' // Use mask as alpha channel
      }])
      .png({
        compressionLevel: 9,
        adaptiveFiltering: true,
        force: true
      })
      .toFile(logoPath);

    // Clean up temp file
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }

    console.log(`✅ Made ${logoFile} background transparent while preserving all colors and details.`);
  } catch (error) {
    console.error(`❌ Failed to process ${logoFile}:`, error.message);
    // Clean up temp file if it exists
    if (fs.existsSync(tempPath)) {
      fs.unlinkSync(tempPath);
    }
  }
}

makeBackgroundTransparentPreserveColors();