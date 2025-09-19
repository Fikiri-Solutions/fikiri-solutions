import sharp from "sharp";
import { globby } from "globby";
import { dirname, join, extname, basename } from "node:path";
import { mkdir } from "node:fs/promises";

const SRC_DIRS = ["public/img", "src/assets"];
const OUT_DIR = "public/optimized";

const targets = await globby(
  SRC_DIRS.map((d) => `${d}/**/*.{png,jpg,jpeg}`),
  { gitignore: true }
);

await mkdir(OUT_DIR, { recursive: true });

for (const file of targets) {
  const base = basename(file, extname(file));
  const dir = join(OUT_DIR, dirname(file).replace(/^public\/|^src\//, ""));
  await mkdir(dir, { recursive: true });

  // AVIF (best), WebP (fallback), and compressed PNG (last-resort)
  await sharp(file).avif({ quality: 45 }).toFile(join(dir, `${base}.avif`));
  await sharp(file).webp({ quality: 60 }).toFile(join(dir, `${base}.webp`));
}
console.log(`Optimized ${targets.length} images → ${OUT_DIR}`);