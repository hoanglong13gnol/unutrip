/**
 * Admin section router: destinations.
 *
 * Phase 4 split — handler bodies are byte-identical copies of the original
 * `router.{get,post}("/destinations/…")` blocks in the old `src/admin.js`.
 * Shared helpers (`escapeHtml`, `renderLayout`, `normalizeAppPlaceCategory`)
 * now live in `./_shared/*`.
 */

import * as destinationsRepository from "../repositories/destinations.repository.js";
import { fillAdminTemplate, loadAdminTemplate, scriptNonceAttr } from "./_shared/adminTemplate.js";
import { escapeHtml } from "./_shared/escape.js";
import { renderLayout } from "./_shared/layout.js";
import { normalizeAppPlaceCategory } from "./_shared/categories.js";

export function registerDestinationsAdminRoutes(router) {
  // 3. Quản lý Địa điểm
  router.get("/destinations", async (req, res) => {
    try {
      const rawQ = typeof req.query.q === "string" ? req.query.q.trim() : "";
      const searchQ = escapeHtml(rawQ);

      let dests;
      if (rawQ) {
        const like = `%${rawQ}%`;
        dests = await destinationsRepository.searchAdminDestinations({ like });
      } else {
        dests = await destinationsRepository.listAdminDestinations();
      }

      const clearFilterLink = rawQ
        ? `<a href="/admin/destinations" class="inline-flex items-center justify-center bg-white border border-gray-200 text-gray-600 text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition uppercase whitespace-nowrap">Xóa lọc</a>`
        : "";
      const destRows =
        (dests.length === 0
          ? `<tr><td colspan="7" class="px-8 py-12 text-center text-gray-400 text-sm">Không có địa điểm phù hợp.</td></tr>`
          : "") +
        dests
          .map(
            (d) => `
                            <tr class="hover:bg-blue-50/50 transition">
                                <td class="px-8 py-4 text-gray-400 font-bold text-xs">${d.id}</td>
                                <td class="px-8 py-4 font-bold text-gray-700">${escapeHtml(d.name)}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${escapeHtml(d.city || "—")}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${escapeHtml(d.province || "—")}</td>
                                <td class="px-8 py-4 text-xs font-bold"><span class="bg-gray-100 px-2 py-1 rounded">${escapeHtml(d.category)}</span></td>
                                <td class="px-8 py-4 text-center text-orange-500 font-bold text-sm">
                                    <i class="fas fa-star mr-1"></i> ${d.rating != null ? Number(d.rating).toFixed(1) : "—"}
                                </td>
                                <td class="px-8 py-4 text-center">
                                    <button type="button" onclick="showDestModal(${d.id})" class="text-blue-400 hover:text-blue-600 transition p-2 mr-1" title="Sửa"><i class="fas fa-edit"></i></button>
                                    <button type="button" onclick="deleteDest(${d.id})" class="text-red-400 hover:text-red-600 transition p-2" title="Xóa"><i class="fas fa-trash-can"></i></button>
                                </td>
                            </tr>
                        `
          )
          .join("");
      const cspNonce = res.locals.cspNonce;
      const content = fillAdminTemplate(loadAdminTemplate("destinations.content.html"), {
        SEARCH_Q: searchQ,
        CLEAR_FILTER_LINK: clearFilterLink,
        DEST_COUNT: dests.length,
        DEST_ROWS: destRows,
        SCRIPT_NONCE_ATTR: scriptNonceAttr(cspNonce)
      });
      res.send(renderLayout(content, "destinations", "Quản lý Địa điểm", cspNonce));
    } catch (e) {
      res.status(500).send(e.message);
    }
  });

  router.get("/destinations/api/:id", async (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isFinite(id) || id <= 0) {
        return res.status(400).json({ success: false, message: "ID không hợp lệ" });
      }
      const dest = await destinationsRepository.getAdminDestinationDetailById(id);
      if (!dest) return res.status(404).json({ success: false, message: "Không tìm thấy địa điểm" });
      return res.json(dest);
    } catch (e) {
      return res.status(500).json({ success: false, message: e.message });
    }
  });

  router.post("/destinations/save", async (req, res) => {
    try {
      const {
        id,
        name,
        description,
        address,
        city,
        province,
        latitude,
        longitude,
        category,
        open_time,
        close_time
      } = req.body;

      const cat = normalizeAppPlaceCategory(category);
      const idNum = id !== undefined && id !== null && id !== "" ? Number(id) : NaN;

      const lat = latitude !== undefined && latitude !== "" ? Number(latitude) : NaN;
      const lng = longitude !== undefined && longitude !== "" ? Number(longitude) : NaN;
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        return res.status(400).json({ success: false, message: "Vĩ độ / kinh độ không hợp lệ" });
      }

      const nameTrim = String(name || "").trim();
      const descTrim = String(description || "").trim();
      if (!nameTrim) {
        return res.status(400).json({ success: false, message: "Tên địa điểm là bắt buộc" });
      }
      if (!descTrim) {
        return res.status(400).json({ success: false, message: "Mô tả là bắt buộc" });
      }

      const addr = address != null ? String(address) : "";
      const cityV = city != null ? String(city) : "";
      const prov = province != null ? String(province) : "";

      if (Number.isFinite(idNum) && idNum > 0) {
        await destinationsRepository.updateAdminDestination({
          id: idNum,
          name: nameTrim,
          description: descTrim,
          address: addr,
          city: cityV,
          province: prov,
          latitude: lat,
          longitude: lng,
          category: cat,
          openTime: open_time || null,
          closeTime: close_time || null
        });
        return res.json({ success: true });
      }

      const nextRow = await destinationsRepository.getNextAppPlaceId();
      const newId = Number(nextRow?.next_id);
      if (!Number.isFinite(newId) || newId <= 0) {
        return res.status(500).json({ success: false, message: "Không tạo được ID mới" });
      }

      const placeKey = `ADM_${newId}`;
      const shortDesc = descTrim.length > 500 ? descTrim.slice(0, 500) : descTrim;

      await destinationsRepository.insertAdminDestination({
        id: newId,
        placeKey,
        name: nameTrim,
        description: descTrim,
        shortDescription: shortDesc,
        address: addr,
        city: cityV,
        province: prov,
        latitude: lat,
        longitude: lng,
        category: cat,
        openTime: open_time || null,
        closeTime: close_time || null
      });
      return res.json({ success: true, id: newId });
    } catch (e) {
      return res.status(500).json({ success: false, message: e.message });
    }
  });

  router.post("/destinations/delete/:id", async (req, res) => {
    try {
      const id = Number(req.params.id);
      if (!Number.isFinite(id) || id <= 0) {
        return res.status(400).json({ success: false, message: "ID không hợp lệ" });
      }
      await destinationsRepository.deleteDestinationById(id);
      return res.json({ success: true });
    } catch (e) {
      return res.status(500).json({
        success: false,
        message: e.message || "Không xóa được (kiểm tra ràng buộc CSDL hoặc bản ghi liên quan)."
      });
    }
  });
}
