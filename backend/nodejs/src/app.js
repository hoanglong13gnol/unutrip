import express from "express";
import cors from "cors";
import helmet from "helmet";
import morgan from "morgan";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

import { buildRouter } from "./routes.js";
import { buildAdminRouter } from "./admin.js";
import { requestIdMiddleware } from "./middlewares/requestId.middleware.js";
import { notFoundMiddleware } from "./middlewares/notFound.middleware.js";
import { errorHandlerMiddleware } from "./middlewares/errorHandler.middleware.js";
import { adminAuthMiddleware } from "./middlewares/adminAuth.middleware.js";
import { cspNonceMiddleware } from "./middlewares/cspNonce.middleware.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Express application factory (used by the HTTP server and by tests).
 * @returns {import("express").Express}
 */
export function createApp() {
  const app = express();

  app.use(cspNonceMiddleware);

  app.use(
    helmet({
      crossOriginResourcePolicy: { policy: "cross-origin" },
      contentSecurityPolicy: {
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: [
            "'self'",
            (req, res) => `'nonce-${res.locals.cspNonce}'`,
            "https://cdn.tailwindcss.com"
          ],
          scriptSrcAttr: ["'unsafe-inline'"],
          styleSrc: [
            "'self'",
            "'unsafe-inline'",
            "https://cdnjs.cloudflare.com",
            "https://fonts.googleapis.com"
          ],
          fontSrc: ["'self'", "https://cdnjs.cloudflare.com", "https://fonts.gstatic.com", "data:"],
          imgSrc: ["'self'", "data:", "https:", "http:"],
          connectSrc: ["'self'", "http:", "https:"]
        }
      }
    })
  );

  app.use(cors());
  app.use(express.json({ limit: "2mb" }));
  app.use(morgan("dev"));

  app.use(requestIdMiddleware);

  const uploadsDir = path.join(__dirname, "..", "uploads");
  if (!fs.existsSync(uploadsDir)) fs.mkdirSync(uploadsDir, { recursive: true });
  app.use("/uploads", express.static(uploadsDir));

  const publicImagesDir = path.join(__dirname, "..", "public", "images");
  if (!fs.existsSync(publicImagesDir)) {
    fs.mkdirSync(publicImagesDir, { recursive: true });
  }
  app.use("/images", express.static(publicImagesDir));

  app.use("/api", buildRouter());
  app.use("/admin", adminAuthMiddleware, buildAdminRouter());

  app.use(notFoundMiddleware);
  app.use(errorHandlerMiddleware);

  return app;
}
