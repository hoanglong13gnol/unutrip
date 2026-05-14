import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

import { assertSafeProductionConfig } from "./config/env.js";
import { createApp } from "./app.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.BACKEND_PORT || process.env.PORT || 3000);
const HOST = process.env.BACKEND_HOST || process.env.HOST || "0.0.0.0";

async function main() {
  try {
    assertSafeProductionConfig();
    const app = createApp();

    const publicImagesDir = path.join(__dirname, "..", "public", "images");

    app.listen(PORT, HOST, () => {
      console.log(`SmartTravel backend running on http://${HOST}:${PORT}`);
      console.log(`Admin Dashboard: http://${HOST}:${PORT}/admin/dashboard`);
      if (fs.existsSync(publicImagesDir)) {
        console.log(`Serving destination images from: ${publicImagesDir}`);
      }
    });
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
}

main();
