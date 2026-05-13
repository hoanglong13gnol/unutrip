import jwt from "jsonwebtoken";
import { getJwtSecret } from "./config/env.js";

const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || "30d";

export function signToken(payload) {
  return jwt.sign(payload, getJwtSecret(), { expiresIn: JWT_EXPIRES_IN });
}

export function authMiddleware(req, res, next) {
  const header = req.header("Authorization") || "";
  const token = header.startsWith("Bearer ") ? header.slice("Bearer ".length).trim() : null;
  if (!token) return res.status(401).json({ success: false, message: "Unauthorized", data: null });

  try {
    const decoded = jwt.verify(token, getJwtSecret());
    req.user = decoded;
    return next();
  } catch {
    return res.status(401).json({ success: false, message: "Invalid token", data: null });
  }
}

