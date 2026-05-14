/**
 * Phase 6 — load admin HTML fragments from `src/admin/templates/` and fill
 * named slots. Delimiter ««KEY»» avoids collisions with JSON inside `<pre>`.
 */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const TEMPLATES_DIR = path.join(__dirname, "..", "templates");

const cache = new Map();

export function loadAdminTemplate(filename) {
  const cached = cache.get(filename);
  if (cached !== undefined) return cached;
  const abs = path.join(TEMPLATES_DIR, filename);
  const text = fs.readFileSync(abs, "utf8");
  cache.set(filename, text);
  return text;
}

/** @param {string} template */
/** @param {Record<string, string | number | boolean | null | undefined>} vars */
export function fillAdminTemplate(template, vars) {
  let out = template;
  for (const [key, val] of Object.entries(vars)) {
    const token = `««${key}»»`;
    if (!out.includes(token)) continue;
    out = out.split(token).join(val === null || val === undefined ? "" : String(val));
  }
  return out;
}

/** `nonce="..."` attribute for inline / external script tags (leading space when set). */
export function scriptNonceAttr(cspNonce) {
  return cspNonce ? ` nonce="${cspNonce}"` : "";
}
