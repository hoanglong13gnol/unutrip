/**
 * Admin section router: destinations.
 *
 * Phase 4 split — handler bodies are byte-identical copies of the original
 * `router.{get,post}("/destinations/…")` blocks in the old `src/admin.js`.
 * Shared helpers (`escapeHtml`, `renderLayout`, `normalizeAppPlaceCategory`)
 * now live in `./_shared/*`.
 */

import { db } from "../db.js";
import * as destinationsRepository from "../repositories/destinations.repository.js";
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
        dests = await db.query(
          `SELECT id, name, city, province, category, rating FROM app_places
           WHERE name LIKE ? OR city LIKE ? OR IFNULL(province,'') LIKE ? OR IFNULL(address,'') LIKE ?
             OR category LIKE ? OR CAST(id AS CHAR) LIKE ?
           ORDER BY id DESC`,
          [like, like, like, like, like, like]
        );
      } else {
        dests = await db.query(
          "SELECT id, name, city, province, category, rating FROM app_places ORDER BY id DESC"
        );
      }

      const content = `
        <div class="bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden animate-fadeIn">
            <div class="p-6 border-b border-gray-50 flex flex-col gap-4 lg:flex-row lg:justify-between lg:items-center bg-white">
                <div>
                    <h3 class="text-lg font-bold text-gray-800">Danh sách Địa điểm</h3>
                    <p class="text-xs text-gray-400 mt-1">Tìm theo tên, thành phố, tỉnh, địa chỉ, danh mục hoặc ID</p>
                </div>
                <div class="flex flex-col sm:flex-row flex-wrap gap-3 items-stretch sm:items-center">
                    <form method="get" action="/admin/destinations" class="flex flex-wrap gap-2 items-center">
                        <input type="search" name="q" value="${searchQ}" placeholder="Tìm kiếm..."
                            class="min-w-[180px] flex-1 sm:flex-none bg-gray-50 border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500">
                        <button type="submit" class="bg-gray-100 text-gray-700 text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-200 transition uppercase whitespace-nowrap">
                            <i class="fas fa-search mr-1"></i> Tìm
                        </button>
                        ${rawQ ? `<a href="/admin/destinations" class="inline-flex items-center justify-center bg-white border border-gray-200 text-gray-600 text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-gray-50 transition uppercase whitespace-nowrap">Xóa lọc</a>` : ""}
                    </form>
                    <div class="flex flex-wrap gap-2 items-center">
                        <button type="button" onclick="showDestModal()" class="bg-blue-600 text-white text-xs font-bold px-4 py-2.5 rounded-xl hover:bg-blue-700 transition uppercase shadow-lg shadow-blue-200 whitespace-nowrap">
                            <i class="fas fa-plus mr-2"></i> Thêm mới
                        </button>
                    </div>
                </div>
                <span class="bg-blue-100 text-blue-600 text-xs font-bold px-3 py-1 rounded-full uppercase self-start lg:self-auto">${dests.length} địa điểm</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-widest">
                        <tr>
                            <th class="px-8 py-4">ID</th>
                            <th class="px-8 py-4">Tên địa điểm</th>
                            <th class="px-8 py-4">Thành phố</th>
                            <th class="px-8 py-4">Tỉnh</th>
                            <th class="px-8 py-4">Danh mục</th>
                            <th class="px-8 py-4 text-center">Đánh giá</th>
                            <th class="px-8 py-4 text-center">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        ${dests.length === 0 ? `<tr><td colspan="7" class="px-8 py-12 text-center text-gray-400 text-sm">Không có địa điểm phù hợp.</td></tr>` : ""}
                        ${dests
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
                          .join("")}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Destination Modal -->
        <div id="destModal" class="hidden fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-3xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-fadeIn">
                <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h3 id="modalTitle" class="text-xl font-bold text-gray-800">Thêm Địa điểm</h3>
                    <button type="button" onclick="closeModal()" class="text-gray-400 hover:text-gray-600 transition text-2xl leading-none">&times;</button>
                </div>
                <form id="destForm" class="p-8 overflow-y-auto custom-scrollbar grid grid-cols-1 md:grid-cols-2 gap-6">
                    <input type="hidden" name="id" id="destId">
                    
                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Tên địa điểm</label>
                        <input type="text" name="name" id="destName" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition">
                    </div>
                    
                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Danh mục</label>
                        <select name="category" id="destCategory" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition">
                            <option value="beach">🏖️ Biển</option>
                            <option value="mountain">⛰️ Núi</option>
                            <option value="city">🏙️ Thành phố</option>
                            <option value="nature">🌿 Thiên nhiên</option>
                            <option value="heritage">🏛️ Lịch sử / Di sản</option>
                            <option value="checkin">📸 Check-in</option>
                            <option value="food">🍜 Ẩm thực</option>
                            <option value="culture">🎨 Văn hóa</option>
                            <option value="religious">🛕 Tôn giáo</option>
                            <option value="other">📌 Khác</option>
                        </select>
                    </div>

                    <div class="space-y-2 md:col-span-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Mô tả</label>
                        <textarea name="description" id="destDescription" rows="3" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition"></textarea>
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Thành phố</label>
                        <input type="text" name="city" id="destCity" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition">
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Tỉnh / Vùng</label>
                        <input type="text" name="province" id="destProvince" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition">
                    </div>

                    <div class="space-y-2 md:col-span-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Địa chỉ chi tiết</label>
                        <input type="text" name="address" id="destAddress" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition">
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Vĩ độ (Latitude)</label>
                        <input type="number" step="any" name="latitude" id="destLat" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Kinh độ (Longitude)</label>
                        <input type="number" step="any" name="longitude" id="destLng" required class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Giờ mở cửa</label>
                        <input type="text" name="open_time" id="destOpen" placeholder="08:00" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                    </div>

                    <div class="space-y-2">
                        <label class="text-xs font-bold text-gray-400 uppercase">Giờ đóng cửa</label>
                        <input type="text" name="close_time" id="destClose" placeholder="22:00" class="w-full bg-gray-50 border border-gray-200 rounded-xl px-4 py-3">
                    </div>
                </form>
                <div class="p-6 bg-gray-50 border-t border-gray-100 flex justify-end space-x-4">
                    <button type="button" onclick="closeModal()" class="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 transition">Hủy</button>
                    <button type="button" onclick="saveDest()" class="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-200 transition">Lưu</button>
                </div>
            </div>
        </div>

        <script>
            function showDestModal(id) {
                const modal = document.getElementById('destModal');
                const form = document.getElementById('destForm');
                const title = document.getElementById('modalTitle');
                
                form.reset();
                document.getElementById('destId').value = '';
                
                if (id) {
                    title.innerText = 'Chỉnh sửa Địa điểm';
                    fetch('/admin/destinations/api/' + id)
                        .then(function(res) { return res.json(); })
                        .then(function(data) {
                            if (!data || !data.id || data.success === false) {
                                alert(data && data.message ? data.message : 'Không tải được dữ liệu');
                                return;
                            }
                            document.getElementById('destId').value = data.id;
                            document.getElementById('destName').value = data.name || '';
                            var cat = (data.category || 'other').toLowerCase();
                            if (cat === 'historical') cat = 'heritage';
                            if (cat === 'entertainment') cat = 'other';
                            var sel = document.getElementById('destCategory');
                            if (!Array.prototype.some.call(sel.options, function(o) { return o.value === cat; })) cat = 'other';
                            sel.value = cat;
                            document.getElementById('destDescription').value = data.description || '';
                            document.getElementById('destCity').value = data.city || '';
                            document.getElementById('destProvince').value = data.province || '';
                            document.getElementById('destAddress').value = data.address || '';
                            document.getElementById('destLat').value = data.latitude != null ? data.latitude : '';
                            document.getElementById('destLng').value = data.longitude != null ? data.longitude : '';
                            document.getElementById('destOpen').value = data.open_time || '';
                            document.getElementById('destClose').value = data.close_time || '';
                        })
                        .catch(function() { alert('Lỗi mạng'); });
                } else {
                    title.innerText = 'Thêm Địa điểm Mới';
                }
                modal.classList.remove('hidden');
            }

            function closeModal() {
                document.getElementById('destModal').classList.add('hidden');
            }

            async function saveDest() {
                const form = document.getElementById('destForm');
                if (!form.checkValidity()) {
                    form.reportValidity();
                    return;
                }
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                const res = await fetch('/admin/destinations/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                const body = await res.json().catch(function() { return {}; });
                if (res.ok && body.success !== false) {
                    location.reload();
                } else {
                    alert(body.message || body.error || 'Lỗi khi lưu dữ liệu');
                }
            }

            async function deleteDest(id) {
                if (!confirm('Xóa địa điểm này khỏi app_places? Thao tác không hoàn tác.')) return;
                const res = await fetch('/admin/destinations/delete/' + id, { method: 'POST' });
                const body = await res.json().catch(function() { return {}; });
                if (res.ok && body.success) {
                    location.reload();
                } else {
                    alert(body.message || 'Lỗi khi xóa');
                }
            }
        </script>
      `;
      res.send(renderLayout(content, "destinations", "Quản lý Địa điểm"));
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
        await db.run(
          `UPDATE app_places
           SET name=?, description=?, address=?, city=?, province=?, latitude=?, longitude=?, category=?, open_time=?, close_time=?
           WHERE id=?`,
          [
            nameTrim,
            descTrim,
            addr,
            cityV,
            prov,
            lat,
            lng,
            cat,
            open_time || null,
            close_time || null,
            idNum
          ]
        );
        return res.json({ success: true });
      }

      const nextRow = await db.get("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM app_places");
      const newId = Number(nextRow?.next_id);
      if (!Number.isFinite(newId) || newId <= 0) {
        return res.status(500).json({ success: false, message: "Không tạo được ID mới" });
      }

      const placeKey = `ADM_${newId}`;
      const shortDesc = descTrim.length > 500 ? descTrim.slice(0, 500) : descTrim;

      await db.run(
        `INSERT INTO app_places (
          id, place_key, name, description, short_description, address, city, province, area,
          latitude, longitude, category, open_time, close_time,
          tags_json, kid_friendly, elderly_friendly, is_active, rating, review_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, '[]', 0, 0, 1, 0, 0)`,
        [
          newId,
          placeKey,
          nameTrim,
          descTrim,
          shortDesc,
          addr,
          cityV,
          prov,
          lat,
          lng,
          cat,
          open_time || null,
          close_time || null
        ]
      );
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
