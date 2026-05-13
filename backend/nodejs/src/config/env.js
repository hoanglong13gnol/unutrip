/**
 * Central place for derived env values and production safety checks.
 * Load root `.env` before reading process.env (ESM imports run before index.js body).
 */
import dotenv from "dotenv";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
dotenv.config({ path: path.resolve(__dirname, "../../../../.env") });

const DEFAULT_JWT_SECRET = "smarttravel_dev_secret_change_me";

export const RAG_BASE_URL =
  process.env.RAG_BASE_URL ||
  process.env.RAG_API_BASE ||
  "http://127.0.0.1:8001";

export function getJwtSecret() {
  return process.env.JWT_SECRET || DEFAULT_JWT_SECRET;
}

export function isDefaultJwtSecret() {
  return getJwtSecret() === DEFAULT_JWT_SECRET;
}

/**
 * Call once at process startup (before accepting traffic).
 */
export function assertSafeProductionConfig() {
  const nodeEnv = process.env.NODE_ENV || "development";
  if (nodeEnv !== "production") return;

  if (isDefaultJwtSecret()) {
    throw new Error(
      "[config] NODE_ENV=production requires JWT_SECRET to be set (not the dev default)."
    );
  }
}
