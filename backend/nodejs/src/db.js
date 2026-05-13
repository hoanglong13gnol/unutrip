import mysql from "mysql2/promise";
import dotenv from "dotenv";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// backend/nodejs/src/db.js -> E:/UNUtrip/.env
const envPath = path.resolve(__dirname, "../../../.env");

console.log("[DB_ENV] expected env path:", envPath);
console.log("[DB_ENV] env exists:", fs.existsSync(envPath));

const envResult = dotenv.config({
  path: envPath,
  override: true
});

if (envResult.error) {
  console.error("[DB_ENV] dotenv error:", envResult.error);
} else {
  console.log("[DB_ENV] dotenv loaded keys:", Object.keys(envResult.parsed || {}).join(", "));
}

const selectedDatabase = process.env.DB_NAME || "unudata";

if (selectedDatabase !== "unudata") {
  console.warn(
    `[DB_ENV] DB_NAME=${selectedDatabase} (expected unudata for production parity). Set DB_NAME in .env if this is intentional.`
  );
}

const dbConfig = {
  host: process.env.DB_HOST || "127.0.0.1",
  port: Number(process.env.DB_PORT || 3306),
  user: process.env.DB_USER || "root",
  password: process.env.DB_PASSWORD || "",
  database: selectedDatabase,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
  enableKeepAlive: true,
  keepAliveInitialDelay: 0
};

console.log("[DB] Using database:", dbConfig.database);
console.log("[DB] Host:", dbConfig.host, "Port:", dbConfig.port, "User:", dbConfig.user);

export const pool = mysql.createPool(dbConfig);

export const db = {
  pool,

  query: async (sql, params) => {
    const [results] = await pool.execute(sql, params);
    return results;
  },

  get: async (sql, params) => {
    const [results] = await pool.execute(sql, params);
    return results[0];
  },

  run: async (sql, params) => {
    const [results] = await pool.execute(sql, params);
    return {
      lastInsertRowid: results.insertId,
      changes: results.affectedRows
    };
  }
};

export async function migrate() {
  console.log("[DB] migrate() skipped. Production schema is managed by MySQL dump/import scripts.");
}

export function jsonOrNull(value) {
  if (value === null || value === undefined) return null;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}
// import mysql from "mysql2/promise";
// import dotenv from "dotenv";
// import path from "path";
// import { fileURLToPath } from "url";

// const __filename = fileURLToPath(import.meta.url);
// const __dirname = path.dirname(__filename);

// // E:\UNUtrip\backend\nodejs\src -> E:\UNUtrip\.env
// const envPath = path.resolve(__dirname, "../../../.env");

// dotenv.config({
//   path: envPath,
//   override: true
// });

// console.log("[ENV] loaded from:", envPath);
// console.log("[ENV] DB_NAME =", process.env.DB_NAME);

// const dbConfig = {
//   host: process.env.DB_HOST || "127.0.0.1",
//   port: Number(process.env.DB_PORT || 3306),
//   user: process.env.DB_USER || "root",
//   password: process.env.DB_PASSWORD || "",
//   database: process.env.DB_NAME || "unudata",
//   waitForConnections: true,
//   connectionLimit: 10,
//   queueLimit: 0,
//   enableKeepAlive: true,
//   keepAliveInitialDelay: 0
// };

// console.log("[DB] Using database:", dbConfig.database);

// export const pool = mysql.createPool(dbConfig);

// export const db = {
//   pool,
//   query: async (sql, params) => {
//     const [results] = await pool.execute(sql, params);
//     return results;
//   },
//   // Helper to mimic better-sqlite3 behavior for single results
//   get: async (sql, params) => {
//     const [results] = await pool.execute(sql, params);
//     return results[0];
//   },
//   // Helper to mimic better-sqlite3 behavior for insertions/updates
//   run: async (sql, params) => {
//     const [results] = await pool.execute(sql, params);
//     return { lastInsertRowid: results.insertId, changes: results.affectedRows };
//   }
// };

// export async function migrate() {
//   const connection = await pool.getConnection();
//   try {
//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS users (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         full_name TEXT NOT NULL,
//         email VARCHAR(255) NOT NULL UNIQUE,
//         password_hash TEXT NOT NULL,
//         phone VARCHAR(20),
//         avatar TEXT,
//         preferences_json TEXT,
//         created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS destinations (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         name TEXT NOT NULL,
//         description TEXT NOT NULL,
//         address TEXT NOT NULL,
//         city VARCHAR(255) NOT NULL,
//         province VARCHAR(255) NOT NULL,
//         latitude DOUBLE NOT NULL,
//         longitude DOUBLE NOT NULL,
//         category VARCHAR(100) NOT NULL,
//         images_json TEXT NOT NULL,
//         rating DOUBLE NOT NULL DEFAULT 0,
//         review_count INT NOT NULL DEFAULT 0,
//         open_time VARCHAR(20),
//         close_time VARCHAR(20),
//         entry_fee DOUBLE,
//         tags_json TEXT NOT NULL
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS favorites (
//         user_id INT NOT NULL,
//         destination_id INT NOT NULL,
//         created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
//         PRIMARY KEY (user_id, destination_id),
//         CONSTRAINT fk_fav_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
//         CONSTRAINT fk_fav_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
//       ) ENGINE=InnoDB;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS reviews (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         user_id INT NOT NULL,
//         destination_id INT NOT NULL,
//         rating DOUBLE NOT NULL,
//         comment TEXT NOT NULL,
//         images_json TEXT,
//         created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
//         CONSTRAINT fk_rev_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
//         CONSTRAINT fk_rev_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS itineraries (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         user_id INT NOT NULL,
//         title TEXT NOT NULL,
//         description TEXT,
//         start_date VARCHAR(50) NOT NULL,
//         end_date VARCHAR(50) NOT NULL,
//         total_days INT NOT NULL,
//         status VARCHAR(50) NOT NULL DEFAULT 'planned',
//         estimated_budget DOUBLE,
//         created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
//         CONSTRAINT fk_iti_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS itinerary_days (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         itinerary_id INT NOT NULL,
//         day_number INT NOT NULL,
//         date VARCHAR(50) NOT NULL,
//         CONSTRAINT fk_day_iti FOREIGN KEY (itinerary_id) REFERENCES itineraries(id) ON DELETE CASCADE
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     await connection.query(`
//       CREATE TABLE IF NOT EXISTS itinerary_items (
//         id INT PRIMARY KEY AUTO_INCREMENT,
//         day_id INT NOT NULL,
//         destination_id INT NOT NULL,
//         start_time VARCHAR(20) NOT NULL,
//         end_time VARCHAR(20) NOT NULL,
//         note TEXT,
//         order_index INT NOT NULL,
//         CONSTRAINT fk_item_day FOREIGN KEY (day_id) REFERENCES itinerary_days(id) ON DELETE CASCADE,
//         CONSTRAINT fk_item_dest FOREIGN KEY (destination_id) REFERENCES destinations(id) ON DELETE CASCADE
//       ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
//     `);

//     console.log("Migration successful");
//   } catch (error) {
//     console.error("Migration failed:", error);
//     throw error;
//   } finally {
//     connection.release();
//   }
// }

// export function jsonOrNull(value) {
//   if (value === null || value === undefined) return null;
//   if (typeof value === 'object') return value;
//   try {
//     return JSON.parse(value);
//   } catch {
//     return null;
//   }
// }
