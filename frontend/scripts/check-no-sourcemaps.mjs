#!/usr/bin/env node
/**
 * Fail the build if production dist/ contains source maps or sourceMappingURL references.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const distDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../dist')
const SOURCE_MAP_REF = /sourceMappingURL\s*=/i

function listFiles(dir, out = []) {
  if (!fs.existsSync(dir)) return out
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) listFiles(full, out)
    else out.push(full)
  }
  return out
}

if (!fs.existsSync(distDir)) {
  console.error('[check-no-sourcemaps] dist/ not found — run vite build first')
  process.exit(1)
}

const files = listFiles(distDir)
const mapFiles = files.filter((file) => file.endsWith('.map'))
const refs = []

for (const file of files) {
  if (!/\.(js|css|mjs|cjs)$/i.test(file)) continue
  const text = fs.readFileSync(file, 'utf8')
  if (SOURCE_MAP_REF.test(text)) {
    refs.push(path.relative(distDir, file))
  }
}

let failed = false

if (mapFiles.length > 0) {
  failed = true
  console.error('[check-no-sourcemaps] Found .map files in dist/:')
  for (const file of mapFiles) {
    console.error(`  - ${path.relative(distDir, file)}`)
  }
}

if (refs.length > 0) {
  failed = true
  console.error('[check-no-sourcemaps] Found sourceMappingURL references in dist/:')
  for (const file of refs) {
    console.error(`  - ${file}`)
  }
}

if (failed) {
  process.exit(1)
}

console.log('[check-no-sourcemaps] OK — no .map files or sourceMappingURL in dist/')
