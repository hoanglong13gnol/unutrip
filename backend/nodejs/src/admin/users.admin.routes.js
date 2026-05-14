/**
 * Admin section router: users.
 *
 * Phase 4 split — handler bodies are byte-identical copies of the original
 * `router.{get,post}("/users/…")` blocks in the old `src/admin.js`. The
 * shared helpers (`escapeHtml`, `renderLayout`) now live in `./_shared/*`.
 */

import bcrypt from "bcryptjs";
import * as usersRepository from "../repositories/users.repository.js";
import { fillAdminTemplate, loadAdminTemplate, scriptNonceAttr } from "./_shared/adminTemplate.js";
import { escapeHtml } from "./_shared/escape.js";
import { renderLayout } from "./_shared/layout.js";

export function registerUsersAdminRoutes(router) {
  // 2. Quản lý Người dùng
  router.get("/users", async (req, res) => {
    try {
      const rawQ = typeof req.query.q === "string" ? req.query.q.trim() : "";
      const searchQ = escapeHtml(rawQ);

      let users;
      if (rawQ) {
        const like = `%${rawQ}%`;
        users = await usersRepository.searchAdminUsers({ like });
      } else {
        users = await usersRepository.listAdminUsers();
      }

      const clearFilterLink = rawQ
        ? `<a href="/admin/users" class="inline-flex items-center justify-center bg-white border border-gray-200 text-gray-600 text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition uppercase">Xóa lọc</a>`
        : "";
      const userRows =
        (users.length === 0
          ? `<tr><td colspan="6" class="px-8 py-12 text-center text-gray-400 text-sm">Không có người dùng phù hợp.</td></tr>`
          : "") +
        users
          .map(
            (u) => `
                            <tr class="hover:bg-blue-50/50 transition">
                                <td class="px-8 py-4 text-gray-400 font-bold text-xs">${u.id}</td>
                                <td class="px-8 py-4 font-semibold text-gray-700">${escapeHtml(u.full_name)}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${escapeHtml(u.email)}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${escapeHtml(u.phone || "—")}</td>
                                <td class="px-8 py-4 text-center text-xs font-bold text-gray-400">${new Date(u.created_at).toLocaleDateString("vi-VN")}</td>
                                <td class="px-8 py-4 text-center">
                                    <button type="button" onclick="showUserModal(${u.id})" class="text-blue-400 hover:text-blue-600 transition p-2 mr-1" title="Sửa"><i class="fas fa-edit"></i></button>
                                    <button type="button" onclick="deleteUser(${u.id})" class="text-red-400 hover:text-red-600 transition p-2" title="Xóa"><i class="fas fa-trash-can"></i></button>
                                </td>
                            </tr>
                        `
          )
          .join("");
      const cspNonce = res.locals.cspNonce;
      const content = fillAdminTemplate(loadAdminTemplate("users.content.html"), {
        SEARCH_Q: searchQ,
        CLEAR_FILTER_LINK: clearFilterLink,
        USER_COUNT: users.length,
        USER_ROWS: userRows,
        SCRIPT_NONCE_ATTR: scriptNonceAttr(cspNonce)
      });
      res.send(renderLayout(content, "users", "Quản lý Người dùng", cspNonce));
    } catch (e) {
      res.status(500).send(e.message);
    }
  });

  router.get("/users/api/:id", async (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isFinite(id) || id <= 0) {
        return res.status(400).json({ success: false, message: "ID không hợp lệ" });
      }
      const user = await usersRepository.getAdminUserDetailById(id);
      if (!user) return res.status(404).json({ success: false, message: "Không tìm thấy người dùng" });
      return res.json(user);
    } catch (e) {
      return res.status(500).json({ success: false, message: e.message });
    }
  });

  router.post("/users/save", async (req, res) => {
    try {
      const body = req.body || {};
      const idRaw = body.id;
      const fullName = String(body.full_name || "").trim();
      const email = String(body.email || "").trim().toLowerCase();
      const phoneRaw = String(body.phone || "").trim();
      const phone = phoneRaw || null;
      const password = String(body.password || "").trim();

      if (!fullName) {
        return res.status(400).json({ success: false, message: "Họ tên không được để trống" });
      }
      if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
        return res.status(400).json({ success: false, message: "Email không hợp lệ" });
      }

      const idNum =
        idRaw !== undefined && idRaw !== null && String(idRaw).trim() !== "" ? Number(idRaw) : NaN;

      const emailGate = await usersRepository.adminAssertEmailAvailableForSave({ idNum, email });
      if (!emailGate.ok) {
        if (emailGate.reason === "email_in_use_other") {
          return res
            .status(400)
            .json({ success: false, message: "Email đã được dùng bởi tài khoản khác" });
        }
        return res.status(400).json({ success: false, message: "Email đã tồn tại" });
      }

      if (Number.isFinite(idNum) && idNum > 0) {
        let passwordHash = null;
        if (password) {
          if (password.length < 4) {
            return res.status(400).json({ success: false, message: "Mật khẩu mới phải có ít nhất 4 ký tự" });
          }
          passwordHash = bcrypt.hashSync(password, 10);
        }
        await usersRepository.adminPersistUserSave({ idNum, fullName, email, phone, passwordHash });
        return res.json({ success: true });
      }

      if (!password || password.length < 4) {
        return res.status(400).json({
          success: false,
          message: "Mật khẩu bắt buộc khi tạo mới và phải có ít nhất 4 ký tự"
        });
      }
      const passwordHash = bcrypt.hashSync(password, 10);
      await usersRepository.adminPersistUserSave({ idNum, fullName, email, phone, passwordHash });
      return res.json({ success: true });
    } catch (e) {
      return res.status(500).json({ success: false, message: e.message });
    }
  });

  router.post("/users/delete/:id", async (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isFinite(id) || id <= 0) {
        return res.status(400).json({ success: false, message: "ID không hợp lệ" });
      }
      await usersRepository.deleteUserById(id);
      return res.json({ success: true });
    } catch (e) {
      return res.status(500).json({
        success: false,
        message: e.message || "Không xóa được (kiểm tra ràng buộc CSDL)."
      });
    }
  });
}
