import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import request from "supertest";
import bcrypt from "bcryptjs";

vi.hoisted(() => {
  process.env.JWT_SECRET = "test-jwt-secret-for-auth-route-tests";
});

const {
  getUserIdByEmail,
  createUser,
  getUserProfileById,
  getUserByEmailWithPasswordHash
} = vi.hoisted(() => ({
  getUserIdByEmail: vi.fn(),
  createUser: vi.fn(),
  getUserProfileById: vi.fn(),
  getUserByEmailWithPasswordHash: vi.fn()
}));

vi.mock("../src/repositories/users.repository.js", () => ({
  getUserIdByEmail,
  createUser,
  getUserProfileById,
  getUserByEmailWithPasswordHash
}));

import { createApp } from "../src/app.js";

function profileRow(id) {
  return {
    id,
    full_name: "Người thử nghiệm",
    email: "newuser@example.com",
    phone: null,
    avatar: null,
    preferences_json: "[]",
    created_at: "2026-01-01T00:00:00.000Z"
  };
}

describe("POST /api/auth/register", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("returns 400 when payload is invalid", async () => {
    const res = await request(createApp())
      .post("/api/auth/register")
      .send({ fullName: "", email: "bad", password: "123" })
      .expect(400);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe("Invalid payload");
    expect(getUserIdByEmail).not.toHaveBeenCalled();
  });

  it("returns 400 when email already exists", async () => {
    getUserIdByEmail.mockResolvedValue({ id: 99 });
    const res = await request(createApp())
      .post("/api/auth/register")
      .send({
        fullName: "X",
        email: "taken@example.com",
        password: "secret1234"
      })
      .expect(400);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe("Email đã tồn tại");
    expect(createUser).not.toHaveBeenCalled();
  });

  it("returns 200 with token and user when registration succeeds", async () => {
    getUserIdByEmail.mockResolvedValue(undefined);
    createUser.mockResolvedValue({ lastInsertRowid: 7 });
    getUserProfileById.mockResolvedValue(profileRow(7));

    const res = await request(createApp())
      .post("/api/auth/register")
      .send({
        fullName: "Người thử nghiệm",
        email: "newuser@example.com",
        password: "secret1234"
      })
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.message).toBe("Đăng ký thành công");
    expect(typeof res.body.token).toBe("string");
    expect(res.body.user.fullName).toBe("Người thử nghiệm");
    expect(res.body.user.email).toBe("newuser@example.com");
    expect(createUser).toHaveBeenCalledTimes(1);
  });
});

describe("POST /api/auth/login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns 400 when payload is invalid", async () => {
    const res = await request(createApp())
      .post("/api/auth/login")
      .send({ email: "x", password: "" })
      .expect(400);
    expect(res.body.success).toBe(false);
    expect(getUserByEmailWithPasswordHash).not.toHaveBeenCalled();
  });

  it("returns 401 when user is unknown", async () => {
    getUserByEmailWithPasswordHash.mockResolvedValue(undefined);
    const res = await request(createApp())
      .post("/api/auth/login")
      .send({ email: "nobody@example.com", password: "whatever" })
      .expect(401);
    expect(res.body.success).toBe(false);
    expect(res.body.message).toBe("Sai email hoặc mật khẩu");
  });

  it("returns 401 when password does not match", async () => {
    getUserByEmailWithPasswordHash.mockResolvedValue({
      id: 3,
      full_name: "U",
      email: "u@example.com",
      password_hash: bcrypt.hashSync("correct-horse", 10),
      phone: null,
      avatar: null,
      preferences_json: "[]",
      created_at: "2026-01-01T00:00:00.000Z"
    });
    const res = await request(createApp())
      .post("/api/auth/login")
      .send({ email: "u@example.com", password: "wrong" })
      .expect(401);
    expect(res.body.message).toBe("Sai email hoặc mật khẩu");
  });

  it("returns 200 with token when credentials are valid", async () => {
    const hash = bcrypt.hashSync("secret1234", 10);
    getUserByEmailWithPasswordHash.mockResolvedValue({
      id: 3,
      full_name: "U",
      email: "u@example.com",
      password_hash: hash,
      phone: null,
      avatar: null,
      preferences_json: "[]",
      created_at: "2026-01-01T00:00:00.000Z"
    });

    const res = await request(createApp())
      .post("/api/auth/login")
      .send({ email: "u@example.com", password: "secret1234" })
      .expect(200);

    expect(res.body.success).toBe(true);
    expect(res.body.message).toBe("Đăng nhập thành công");
    expect(typeof res.body.token).toBe("string");
    expect(res.body.user.email).toBe("u@example.com");
  });
});
