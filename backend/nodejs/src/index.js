import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

// import { migrate } from "./db.js";
// import { seed } from "./seed.js";
import { assertSafeProductionConfig } from "./config/env.js";
import { buildRouter } from "./routes.js";
import { buildAdminRouter } from "./admin.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = Number(process.env.BACKEND_PORT || process.env.PORT || 3000);
const HOST = process.env.BACKEND_HOST || process.env.HOST || "0.0.0.0";

async function initApp() {
  try {
    assertSafeProductionConfig();

    // Init DB
    // await migrate();
    // await seed();

    const app = express();

    app.use(
      helmet({
        crossOriginResourcePolicy: { policy: "cross-origin" },
        contentSecurityPolicy: {
          directives: {
            defaultSrc: ["'self'"],
            scriptSrc: ["'self'", "'unsafe-inline'", "https://cdn.tailwindcss.com"],
            scriptSrcAttr: ["'unsafe-inline'"],
            styleSrc: [
              "'self'",
              "'unsafe-inline'",
              "https://cdnjs.cloudflare.com",
              "https://fonts.googleapis.com",
            ],
            fontSrc: ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com", "data:"],
            imgSrc: ["'self'", "data:", "https:", "http:"],
            connectSrc: ["'self'", "http:", "https:"],
          },
        },
      })
    );

    app.use(cors());
    app.use(express.json({ limit: "2mb" }));
    app.use(morgan("dev"));

    // Static uploads
    const uploadsDir = path.join(__dirname, "..", "uploads");
    if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });
    app.use("/uploads", express.static(uploadsDir));

    // Static destination images
    // Serves:
    //   backend/public/images/destinations/<rag_place_id>/<file>.webp
    // as:
    //   http://localhost:3000/images/destinations/<rag_place_id>/<file>.webp
    const publicImagesDir = path.join(__dirname, "..", "public", "images");
    if (!fs.existsSync(publicImagesDir)) {
      fs.mkdirSync(publicImagesDir, { recursive: true });
    }
    app.use("/images", express.static(publicImagesDir));

    // Routes
    app.use("/api", buildRouter());
    app.use("/admin", buildAdminRouter());

    app.listen(PORT, HOST, () => {
      // eslint-disable-next-line no-console
      console.log(`SmartTravel backend running on http://${HOST}:${PORT}`);
      console.log(`Admin Dashboard: http://${HOST}:${PORT}/admin/dashboard`);
      console.log(`Serving destination images from: ${publicImagesDir}`);
    });
  } catch (error) {
    console.error("Failed to start server:", error);
    process.exit(1);
  }
}

initApp();