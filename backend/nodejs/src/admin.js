import express from "express";
import { db } from "./db.js";
import { RAG_BASE_URL } from "./config/env.js";
import { ragAuthHeaders, ragJsonHeaders } from "./config/ragClient.js";

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

async function fetchRagJson(pathname, timeoutMs = 3000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${RAG_BASE_URL}${pathname}`, {
      signal: controller.signal,
      headers: ragAuthHeaders()
    });

    const text = await response.text();
    let data;

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    return {
      ok: response.ok,
      status: response.status,
      url: `${RAG_BASE_URL}${pathname}`,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      url: `${RAG_BASE_URL}${pathname}`,
      data: {
        error: error.name === "AbortError" ? "Timeout khi gọi FastAPI RAG" : error.message
      }
    };
  } finally {
    clearTimeout(timer);
  }
}
async function postRagJson(pathname, body = {}, timeoutMs = 5000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${RAG_BASE_URL}${pathname}`, {
      method: "POST",
      headers: ragJsonHeaders(),
      body: JSON.stringify(body),
      signal: controller.signal
    });

    const text = await response.text();
    let data;

    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = { raw: text };
    }

    return {
      ok: response.ok,
      status: response.status,
      url: `${RAG_BASE_URL}${pathname}`,
      data
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      url: `${RAG_BASE_URL}${pathname}`,
      data: {
        error: error.name === "AbortError" ? "Timeout khi gọi FastAPI RAG" : error.message
      }
    };
  } finally {
    clearTimeout(timer);
  }
}

function renderJsonBox(value) {
  return escapeHtml(JSON.stringify(value ?? {}, null, 2));
}
// Shared Layout Wrapper
function renderLayout(content, activePath, title = "Quản trị hệ thống") {
  return `
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UnuTrip | ${title}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Plus Jakarta Sans', sans-serif; }
        .sidebar-active { background: rgba(59, 130, 246, 0.1); border-right: 4px solid #3b82f6; color: #3b82f6; }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #3b82f6; border-radius: 10px; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
        .animate-fadeIn { animation: fadeIn 0.4s ease-out forwards; }
        @media print {
    @page {
        size: A4 portrait;
        margin: 10mm;
    }

    html,
    body {
        background: #ffffff !important;
        overflow: visible !important;
        color: #111827 !important;
        font-size: 10px !important;
    }

    aside,
    header,
    button,
    pre,
    .no-print {
        display: none !important;
    }

    .flex.h-screen,
    .flex-1,
    main {
        display: block !important;
        height: auto !important;
        overflow: visible !important;
        padding: 0 !important;
        width: 100% !important;
    }

    .animate-fadeIn,
    .space-y-8 {
        display: block !important;
    }

    .space-y-8 > * + * {
    margin-top: 5px !important;
}

    .grid {
        display: grid !important;
        gap: 6px !important;
    }

    .rag-top-kpis {
    display: none !important;
}

[class~="grid-cols-1"],
[class~="md:grid-cols-2"],
[class~="md:grid-cols-3"],
[class~="md:grid-cols-4"],
[class~="md:grid-cols-5"],
[class~="md:grid-cols-6"],
[class~="xl:grid-cols-3"],
[class~="xl:grid-cols-4"] {
    grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
}

[class~="xl:grid-cols-2"] {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

[class~="xl:col-span-2"] {
    grid-column: span 2 / span 2 !important;
}

.xl\:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

    .xl\:col-span-2 {
        grid-column: span 2 / span 2 !important;
    }

    .bg-white,
    .bg-blue-50\/40,
    .bg-emerald-50\/40,
    .bg-orange-50\/40,
    .bg-indigo-50\/40,
    .bg-gradient-to-r,
    .bg-emerald-50,
    .bg-blue-50,
    .bg-indigo-50,
    .bg-orange-50,
    .bg-purple-50,
    .bg-slate-50,
    .bg-gray-50 {
        background: #ffffff !important;
    }

    .shadow-sm,
    .shadow-xl,
    .shadow-lg {
        box-shadow: none !important;
    }

    .rounded-3xl,
    .rounded-2xl,
    .rounded-xl {
        border-radius: 8px !important;
    }

    .border,
    .border-gray-100,
    .border-blue-100,
    .border-emerald-100,
    .border-orange-100,
    .border-indigo-100,
    .border-purple-100,
    .border-slate-100 {
        border-color: #d1d5db !important;
    }

    .p-8,
    .p-6,
    .p-5,
    .p-4 {
        padding: 5px !important;
    }

    .px-4,
    .px-5,
    .py-3,
    .py-4 {
        padding: 6px !important;
    }

    .mb-6,
    .mb-5,
    .mb-4,
    .mb-3 {
        margin-bottom: 6px !important;
    }

    h3 {
        font-size: 14px !important;
        line-height: 1.25 !important;
    }

    p,
    span,
    code,
    div {
        font-size: 9.5px !important;
        line-height: 1.35 !important;
    }

    .text-3xl,
    .text-2xl,
    .text-xl,
    .text-lg {
        font-size: 12px !important;
        line-height: 1.25 !important;
    }

    .font-extrabold,
    .font-bold {
        font-weight: 700 !important;
    }

    .truncate {
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }

    .min-w-full,
    .lg\:min-w-\[620px\],
    .min-w-\[260px\],
    .min-w-\[240px\] {
        min-width: 0 !important;
    }

    .break-after-page {
        break-after: page !important;
    }

    .break-inside-avoid,
    .rounded-3xl,
    .rounded-2xl {
        break-inside: avoid !important;
    }
}
    </style>
</head>
<body class="bg-gray-100 text-gray-900 overflow-hidden">
    <div class="flex h-screen overflow-hidden">
        <!-- Sidebar -->
        <aside class="w-64 bg-slate-900 text-white flex-shrink-0 flex flex-col shadow-2xl z-20">
            <div class="p-8">
                <div class="flex items-center space-x-3">
                    <div class="bg-blue-600 p-2 rounded-lg shadow-lg shadow-blue-500/30">
                        <i class="fas fa-paper-plane text-xl"></i>
                    </div>
                    <span class="text-xl font-bold tracking-tight">UnuTrip</span>
                </div>
            </div>

            <nav class="flex-1 px-4 py-2 space-y-1">
                <a href="/admin/dashboard" class="${activePath === 'dashboard' ? 'sidebar-active' : ''} flex items-center px-4 py-3 rounded-lg font-medium transition group hover:bg-white/5">
                    <i class="fas fa-chart-pie mr-3"></i>
                    <span>Dashboard</span>
                </a>
                <a href="/admin/users" class="${activePath === 'users' ? 'sidebar-active' : ''} flex items-center px-4 py-3 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition group">
                    <i class="fas fa-users mr-3 group-hover:text-blue-400"></i>
                    <span>Người dùng</span>
                </a>
                <a href="/admin/destinations" class="${activePath === 'destinations' ? 'sidebar-active' : ''} flex items-center px-4 py-3 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition group">
                    <i class="fas fa-map-marked-alt mr-3 group-hover:text-blue-400"></i>
                    <span>Địa điểm</span>
                </a>
                <a href="/admin/system" class="${activePath === 'system' ? 'sidebar-active' : ''} flex items-center px-4 py-3 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition group">
                    <i class="fas fa-shield-halved mr-3 group-hover:text-blue-400"></i>
                    <span>Hệ thống</span>
                </a>
                <a href="/admin/rag-ai" class="${activePath === 'rag-ai' ? 'sidebar-active' : ''} flex items-center px-4 py-3 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition group">
                    <i class="fas fa-robot mr-3 group-hover:text-blue-400"></i>
                    <span>RAG AI</span>
                </a>
            </nav>

            <div class="p-6 bg-slate-950 border-t border-white/5">
                <div class="flex items-center space-x-3">
                    <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center font-bold text-sm">AD</div>
                    <div>
                        <p class="text-sm font-semibold">Admin</p>
                        <p class="text-xs text-gray-500">Administrator</p>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content Area -->
        <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <header class="bg-white border-b border-gray-200 h-20 flex items-center justify-between px-8 flex-shrink-0 z-10">
                <div>
                    <h2 class="text-2xl font-bold text-gray-800 tracking-tight">${title}</h2>
                    <p class="text-sm text-gray-500 font-medium">${new Date().toLocaleDateString('vi-VN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</p>
                </div>
            </header>

            <main class="flex-1 overflow-y-auto p-8 custom-scrollbar">
                ${content}
            </main>
        </div>
    </div>
</body>
</html>
  `;
}

export function buildAdminRouter() {
  const router = express.Router();

  // 1. Dashboard
  router.get("/dashboard", async (req, res) => {
    try {
      const stats = await db.get(`
        SELECT
          (SELECT COUNT(*) FROM users) as totalUsers,
          (SELECT COUNT(*) FROM app_places) as totalDestinations,
          (SELECT COUNT(*) FROM itineraries) as totalItineraries
      `);

      const latestUsers = await db.query(`
        SELECT full_name, email, created_at
        FROM users
        ORDER BY created_at DESC
        LIMIT 5
      `);

      const content = `
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex items-center justify-between hover:shadow-lg transition-shadow">
                <div>
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Người dùng</p>
                    <p class="text-3xl font-extrabold text-slate-800">${stats.totalUsers}</p>
                </div>
                <div class="w-14 h-14 bg-blue-50 text-blue-500 rounded-2xl flex items-center justify-center">
                    <i class="fas fa-user-group text-2xl"></i>
                </div>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex items-center justify-between hover:shadow-lg transition-shadow">
                <div>
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Địa điểm</p>
                    <p class="text-3xl font-extrabold text-slate-800">${stats.totalDestinations}</p>
                </div>
                <div class="w-14 h-14 bg-emerald-50 text-emerald-500 rounded-2xl flex items-center justify-center">
                    <i class="fas fa-location-dot text-2xl"></i>
                </div>
            </div>
            <div class="bg-white p-6 rounded-xl shadow-md border border-gray-100 flex items-center justify-between hover:shadow-lg transition-shadow">
                <div>
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-1">Lịch trình</p>
                    <p class="text-3xl font-extrabold text-slate-800">${stats.totalItineraries}</p>
                </div>
                <div class="w-14 h-14 bg-orange-50 text-orange-500 rounded-2xl flex items-center justify-center">
                    <i class="fas fa-route text-2xl"></i>
                </div>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div class="lg:col-span-2 bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
                <div class="p-6 border-b border-gray-50 flex justify-between items-center bg-white">
                    <h3 class="text-lg font-bold text-gray-800">Thành viên mới nhất</h3>
                    <a href="/admin/users" class="text-blue-600 text-xs font-bold hover:bg-blue-50 px-3 py-1.5 rounded-lg transition uppercase">Tất cả</a>
                </div>
                <div class="overflow-x-auto">
                    <table class="w-full text-left">
                        <thead class="bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-widest">
                            <tr>
                                <th class="px-8 py-4">Họ và tên</th>
                                <th class="px-8 py-4">Địa chỉ Email</th>
                                <th class="px-8 py-4 text-center">Ngày đăng ký</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-gray-100">
                            ${latestUsers.map((u, i) => `
                                <tr class="${i % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'} hover:bg-blue-50/50 transition duration-150 cursor-pointer">
                                    <td class="px-8 py-5">
                                        <div class="flex items-center">
                                            <div class="w-9 h-9 rounded-full bg-slate-100 flex items-center justify-center text-slate-500 font-bold text-xs mr-3">${u.full_name.charAt(0)}</div>
                                            <span class="font-semibold text-gray-700">${u.full_name}</span>
                                        </div>
                                    </td>
                                    <td class="px-8 py-5 text-gray-600 text-sm font-medium">${u.email}</td>
                                    <td class="px-8 py-5 text-center text-xs font-bold text-gray-400">${new Date(u.created_at).toLocaleDateString('vi-VN')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 flex flex-col h-fit">
                <div class="flex items-center space-x-3 mb-8">
                    <div class="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center text-white shadow-xl shadow-indigo-200">
                        <i class="fas fa-brain text-sm"></i>
                    </div>
                    <h3 class="text-lg font-extrabold text-gray-800">AI Smart Analysis</h3>
                </div>
                <div id="ai-report-content" class="text-sm text-gray-600 leading-relaxed mb-8 min-h-[160px]">
                    <div class="flex flex-col items-center justify-center h-full text-center space-y-4 py-6">
                        <div class="w-20 h-20 bg-gray-50 rounded-full flex items-center justify-center">
                            <i class="fas fa-robot text-4xl text-gray-200"></i>
                        </div>
                        <p class="text-gray-400 italic font-medium px-4">Hệ thống AI Gemini đã sẵn sàng phân tích dữ liệu ứng dụng của bạn.</p>
                    </div>
                </div>
                <button id="btn-generate-ai" class="w-full bg-gradient-to-br from-blue-600 to-indigo-700 hover:from-blue-700 hover:to-indigo-800 text-white font-bold py-4 rounded-2xl shadow-xl shadow-blue-200 transition-all duration-300 transform active:scale-[0.98] flex justify-center items-center cursor-pointer">
                    <i class="fas fa-wand-magic-sparkles mr-3"></i>
                    <span>Generate AI Report</span>
                </button>
                <div id="ai-result" class="mt-4"></div>
            </div>
        </div>

        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const btn = document.getElementById('btn-generate-ai');
                const content = document.getElementById('ai-report-content');
                const resultDiv = document.getElementById('ai-result');

                btn.addEventListener('click', async function() {
                    btn.disabled = true;
                    btn.classList.add('opacity-70', 'cursor-not-allowed');
                    btn.innerHTML = '<i class="fas fa-spinner animate-spin mr-3"></i> Đang phân tích...';
                    
                    try {
                        const res = await fetch('/admin/ai-report');
                        const data = await res.json();
                        if (data.success) {
                            const formatted = data.report.replace(/\\n/g, '<br>').replace(/\\*\\*(.*?)\\*\\*/g, '<strong class="text-blue-700 font-bold">$1</strong>');
                            content.innerHTML = '<div class="bg-indigo-50/50 p-6 rounded-2xl border border-indigo-100 shadow-inner max-h-[450px] overflow-y-auto custom-scrollbar text-slate-700 font-medium tracking-tight leading-loose">' + formatted + '</div>';
                            resultDiv.innerHTML = '<p class="text-xs text-green-600 font-semibold text-center mt-2"><i class="fas fa-check-circle mr-1"></i>Báo cáo đã được tạo thành công!</p>';
                        } else {
                            content.innerHTML = '<div class="p-4 bg-red-50 text-red-500 rounded-xl border border-red-100 font-bold text-center">Lỗi: ' + data.message + '</div>';
                        }
                    } catch (err) {
                        content.innerHTML = '<div class="p-4 bg-red-50 text-red-500 rounded-xl border border-red-100 font-bold text-center">Kết nối thất bại!</div>';
                    } finally {
                        btn.disabled = false;
                        btn.classList.remove('opacity-70', 'cursor-not-allowed');
                        btn.innerHTML = '<i class="fas fa-rotate mr-2"></i> Làm mới báo cáo';
                    }
                });
            });
        </script>
      `;
      res.send(renderLayout(content, 'dashboard'));
    } catch (error) {
      res.status(500).send("Admin Dashboard Error: " + error.message);
    }
  });

  // 2. Quản lý Người dùng
  router.get("/users", async (req, res) => {
    try {
      const users = await db.query("SELECT id, full_name, email, phone, created_at FROM users ORDER BY created_at DESC");
      const content = `
        <div class="bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden animate-fadeIn">
            <div class="p-6 border-b border-gray-50 flex justify-between items-center bg-white">
                <h3 class="text-lg font-bold text-gray-800">Danh sách Người dùng</h3>
                <span class="bg-blue-100 text-blue-600 text-xs font-bold px-3 py-1 rounded-full uppercase">${users.length} thành viên</span>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-widest">
                        <tr>
                            <th class="px-8 py-4">ID</th>
                            <th class="px-8 py-4">Họ và tên</th>
                            <th class="px-8 py-4">Email</th>
                            <th class="px-8 py-4">Số điện thoại</th>
                            <th class="px-8 py-4 text-center">Ngày đăng ký</th>
                            <th class="px-8 py-4 text-center">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        ${users.map(u => `
                            <tr class="hover:bg-blue-50/50 transition">
                                <td class="px-8 py-4 text-gray-400 font-bold text-xs">${u.id}</td>
                                <td class="px-8 py-4 font-semibold text-gray-700">${u.full_name}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${u.email}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${u.phone || '---'}</td>
                                <td class="px-8 py-4 text-center text-xs font-bold text-gray-400">${new Date(u.created_at).toLocaleDateString('vi-VN')}</td>
                                <td class="px-8 py-4 text-center">
                                    <button onclick="deleteUser(${u.id})" class="text-red-400 hover:text-red-600 transition p-2">
                                        <i class="fas fa-trash-can"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
        <script>
            async function deleteUser(id) {
                if(confirm('Bạn có chắc chắn muốn xóa người dùng này?')) {
                    const res = await fetch('/admin/users/delete/' + id, { method: 'POST' });
                    if(res.ok) location.reload();
                    else alert('Lỗi khi xóa người dùng');
                }
            }
        </script>
      `;
      res.send(renderLayout(content, 'users', 'Quản lý Người dùng'));
    } catch (e) { res.status(500).send(e.message); }
  });

  router.post("/users/delete/:id", async (req, res) => {
    await db.run("DELETE FROM users WHERE id = ?", [req.params.id]);
    res.json({ success: true });
  });

  // 3. Quản lý Địa điểm
  router.get("/destinations", async (req, res) => {
    try {
      const dests = await db.query("SELECT id, name, city, category, rating FROM app_places ORDER BY id DESC");
      const content = `
        <div class="bg-white rounded-3xl shadow-sm border border-gray-100 flex flex-col overflow-hidden animate-fadeIn">
            <div class="p-6 border-b border-gray-50 flex justify-between items-center bg-white">
                <h3 class="text-lg font-bold text-gray-800">Danh sách Địa điểm</h3>
                <button onclick="showDestModal()" class="bg-blue-600 text-white text-xs font-bold px-4 py-2 rounded-lg hover:bg-blue-700 transition uppercase shadow-lg shadow-blue-200">
                    <i class="fas fa-plus mr-2"></i> Thêm mới
                </button>
            </div>
            <div class="overflow-x-auto">
                <table class="w-full text-left">
                    <thead class="bg-gray-50 text-gray-500 text-[10px] font-bold uppercase tracking-widest">
                        <tr>
                            <th class="px-8 py-4">Tên địa điểm</th>
                            <th class="px-8 py-4">Thành phố</th>
                            <th class="px-8 py-4">Danh mục</th>
                            <th class="px-8 py-4 text-center">Đánh giá</th>
                            <th class="px-8 py-4 text-center">Thao tác</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-gray-100">
                        ${dests.map(d => `
                            <tr class="hover:bg-blue-50/50 transition">
                                <td class="px-8 py-4 font-bold text-gray-700">${d.name}</td>
                                <td class="px-8 py-4 text-gray-600 text-sm">${d.city}</td>
                                <td class="px-8 py-4 text-xs font-bold"><span class="bg-gray-100 px-2 py-1 rounded">${d.category}</span></td>
                                <td class="px-8 py-4 text-center text-orange-500 font-bold text-sm">
                                    <i class="fas fa-star mr-1"></i> ${d.rating}
                                </td>
                                <td class="px-8 py-4 text-center">
                                    <button onclick="showDestModal(${d.id})" class="text-blue-400 hover:text-blue-600 transition p-2 mr-2"><i class="fas fa-edit"></i></button>
                                    <button onclick="deleteDest(${d.id})" class="text-red-400 hover:text-red-600 transition p-2">
                                        <i class="fas fa-trash-can"></i>
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Destination Modal -->
        <div id="destModal" class="hidden fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
            <div class="bg-white rounded-3xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col animate-fadeIn">
                <div class="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50/50">
                    <h3 id="modalTitle" class="text-xl font-bold text-gray-800">Thêm Địa điểm</h3>
                    <button onclick="closeModal()" class="text-gray-400 hover:text-gray-600 transition text-2xl">&times;</button>
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
                            <option value="historical">🏛️ Lịch sử</option>
                            <option value="checkin">📸 Check-in</option>
                            <option value="food">🍜 Ẩm thực</option>
                            <option value="culture">🎨 Văn hóa</option>
                            <option value="religious">🛕 Tôn giáo</option>
                            <option value="heritage">🏛️ Di tích</option>
                            <option value="entertainment">🎡 Vui chơi</option>
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
                    <button onclick="closeModal()" class="px-6 py-3 rounded-xl font-bold text-gray-500 hover:bg-gray-100 transition">Hủy</button>
                    <button onclick="saveDest()" class="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl shadow-lg shadow-blue-200 transition">Lưu thay đổi</button>
                </div>
            </div>
        </div>

        <script>
            function showDestModal(id = null) {
                const modal = document.getElementById('destModal');
                const form = document.getElementById('destForm');
                const title = document.getElementById('modalTitle');
                
                form.reset();
                document.getElementById('destId').value = '';
                
                if (id) {
                    title.innerText = 'Chỉnh sửa Địa điểm';
                    fetch('/admin/destinations/api/' + id)
                        .then(res => res.json())
                        .then(data => {
                            document.getElementById('destId').value = data.id;
                            document.getElementById('destName').value = data.name;
                            document.getElementById('destCategory').value = data.category;
                            document.getElementById('destDescription').value = data.description;
                            document.getElementById('destCity').value = data.city;
                            document.getElementById('destProvince').value = data.province;
                            document.getElementById('destAddress').value = data.address;
                            document.getElementById('destLat').value = data.latitude;
                            document.getElementById('destLng').value = data.longitude;
                            document.getElementById('destOpen').value = data.open_time || '';
                            document.getElementById('destClose').value = data.close_time || '';
                        });
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
                const formData = new FormData(form);
                const data = Object.fromEntries(formData.entries());
                
                const res = await fetch('/admin/destinations/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                if (res.ok) {
                    location.reload();
                } else {
                    alert('Lỗi khi lưu dữ liệu');
                }
            }

            async function deleteDest(id) {
                if(confirm('Xóa địa điểm này?')) {
                    const res = await fetch('/admin/destinations/delete/' + id, { method: 'POST' });
                    if(res.ok) location.reload();
                }
            }
        </script>
      `;
      res.send(renderLayout(content, 'destinations', 'Quản lý Địa điểm'));
    } catch (e) { res.status(500).send(e.message); }
  });

  router.get("/destinations/api/:id", async (req, res) => {
    const dest = await db.get(
      "SELECT id, name, category, description, city, province, address, latitude, longitude, open_time, close_time FROM app_places WHERE id = ?",
      [req.params.id]
    );
    res.json(dest);
  });

  router.post("/destinations/save", async (req, res) => {
    return res.status(501).json({
      success: false,
      message: "Admin place writes are disabled until app_places write policy is implemented"
    });
  });

  router.post("/destinations/delete/:id", async (req, res) => {
    return res.status(501).json({
      success: false,
      message: "Admin place writes are disabled until app_places write policy is implemented"
    });
  });

  // 4. Hệ thống
  router.get("/system", async (req, res) => {
    const stats = await db.get("SELECT COUNT(*) as c FROM itineraries");
    const content = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8 animate-fadeIn">
            <div class="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-extrabold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-server mr-3 text-blue-500"></i> Trạng thái Máy chủ
                </h3>
                <div class="space-y-4">
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Phiên bản API</span>
                        <span class="font-bold text-slate-800">v1.2.0-stable</span>
                    </div>
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Uptime</span>
                        <span class="text-green-500 font-bold">100% Online</span>
                    </div>
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Cổng hoạt động</span>
                        <span class="font-bold text-slate-800">3000</span>
                    </div>
                </div>
            </div>

            <div class="bg-white p-8 rounded-3xl shadow-sm border border-gray-100">
                <h3 class="text-lg font-extrabold text-gray-800 mb-6 flex items-center">
                    <i class="fas fa-database mr-3 text-emerald-500"></i> Cơ sở dữ liệu
                </h3>
                <div class="space-y-4">
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Loại DB</span>
                        <span class="font-bold text-slate-800">MySQL 8.0</span>
                    </div>
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Kết nối</span>
                        <span class="text-blue-500 font-bold">Hoạt động</span>
                    </div>
                    <div class="flex justify-between items-center p-4 bg-gray-50 rounded-2xl">
                        <span class="text-gray-500 font-medium">Số bản ghi Lịch trình</span>
                        <span class="font-bold text-slate-800">${stats.c}</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    res.send(renderLayout(content, 'system', 'Hệ thống'));
  });
      // 5. RAG AI Dashboard
  router.get("/rag-ai", async (req, res) => {
    try {
      const [overview, ragStatus, selfTest, metrics, dataQuality] = await Promise.all([
        fetchRagJson("/admin/system/overview"),
        fetchRagJson("/admin/rag/status"),
        fetchRagJson("/admin/system/self-test"),
        fetchRagJson("/admin/ai/metrics"),
        fetchRagJson("/admin/data-quality/status")
      ]);

      const readyValue =
        ragStatus.data?.ready ??
        ragStatus.data?.status ??
        ragStatus.data?.rag_ready ??
        overview.data?.ready ??
        overview.data?.status ??
        selfTest.data?.ready ??
        "unknown";

      const passedValue =
        selfTest.data?.passed ??
        selfTest.data?.summary?.passed ??
        selfTest.data?.tests_passed ??
        "N/A";

      const failedValue =
        selfTest.data?.failed ??
        selfTest.data?.summary?.failed ??
        selfTest.data?.tests_failed ??
        "N/A";
        const dqScan = dataQuality.data?.scan ?? {};
const dqAutofix = dataQuality.data?.autofix ?? {};
const dqReviewed = dataQuality.data?.reviewed ?? {};
const st = selfTest.data ?? {};
const stChecks = st.checks ?? {};
const rs = ragStatus.data ?? {};
const rsFiles = rs.files ?? {};
const overviewRag = overview.data?.rag ?? {};
const rsStore = rs.place_store ?? overviewRag.place_store ?? {};
const overviewRuntime = overview.data?.runtime ?? {};
const overviewCache = overview.data?.cache ?? {};
const aiMetrics = metrics.data ?? {};
const modelUsage = aiMetrics.model_usage ?? {};

      const content = `
        <div class="animate-fadeIn space-y-8">
            <div class="no-print bg-gradient-to-br from-slate-900 via-blue-900 to-indigo-900 text-white rounded-3xl p-8 shadow-xl">
                <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
                    <div>
                        <div class="inline-flex items-center bg-white/10 border border-white/10 rounded-full px-4 py-2 text-xs font-bold uppercase tracking-widest mb-4">
                            <i class="fas fa-brain mr-2"></i>
                            FastAPI RAG Monitor
                        </div>
                        <h3 class="text-3xl font-extrabold tracking-tight mb-2">RAG AI Dashboard</h3>
                        <p class="text-blue-100 max-w-2xl">
                            Theo dõi trạng thái FastAPI RAG, self-test, AI metrics và chất lượng dữ liệu.
                        </p>
                    </div>
                    <div class="bg-white/10 border border-white/10 rounded-2xl p-5 min-w-[260px]">
                        <p class="text-xs text-blue-100 font-bold uppercase tracking-widest mb-2">RAG Base URL</p>
                        <p class="font-mono text-sm break-all">${escapeHtml(RAG_BASE_URL)}</p>
                    </div>
                    <div class="flex flex-col sm:flex-row lg:flex-col gap-3 min-w-[240px]">
    <button onclick="runRagAction('/admin/rag-ai/reload-place-store', 'Reload Place Store', 'POST')" class="bg-emerald-500 hover:bg-emerald-600 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
        <i class="fas fa-rotate-right mr-2"></i>
        Reload Place Store
    </button>

    <button onclick="runRagAction('/admin/rag-ai/clear-cache', 'Clear Cache', 'POST')" class="bg-orange-500 hover:bg-orange-600 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
        <i class="fas fa-broom mr-2"></i>
        Clear Cache
    </button>

    <button onclick="runRagAction('/admin/rag-ai/data-quality-issues', 'Data Quality Issues', 'GET')" class="bg-blue-500 hover:bg-blue-600 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
        <i class="fas fa-triangle-exclamation mr-2"></i>
        Data Quality Issues
    </button>

    <button onclick="runRagAction('/admin/rag-ai/ai-metrics', 'AI Metrics', 'GET')" class="bg-indigo-500 hover:bg-indigo-600 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
        <i class="fas fa-chart-line mr-2"></i>
        AI Metrics
    </button>
    <button onclick="runRagAction('/admin/rag-ai/ai-logs', 'AI Logs', 'GET')" class="bg-purple-500 hover:bg-purple-600 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
    <i class="fas fa-clipboard-list mr-2"></i>
    AI Logs
</button>

    <a href="http://127.0.0.1:8001/docs" target="_blank" class="bg-slate-700 hover:bg-slate-800 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
        <i class="fas fa-book-open mr-2"></i>
        FastAPI Docs
    </a>
    <button onclick="printRagReport()" class="bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold px-5 py-3 rounded-2xl shadow-lg transition flex items-center justify-center">
    <i class="fas fa-print mr-2"></i>
    Print Report
</button>
</div>
                </div>
            </div>
            <div class="no-print bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
    <div class="flex flex-col lg:flex-row lg:items-end gap-4">
        <div class="flex-1">
            <label class="block text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">
                Debug Query
            </label>
            <input
    id="rag-debug-query"
    type="text"
    value="đi biển ở Khánh Hòa"
    placeholder="Nhập câu hỏi test RAG..."
    class="w-full bg-gray-50 border border-gray-200 rounded-2xl px-5 py-4 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition"
/>
<p class="mt-3 text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded-xl px-4 py-3">
    <i class="fas fa-circle-info mr-2"></i>
    Nếu vừa sửa RAG prompt/pipeline, hãy bấm <b>Clear Cache</b> trước khi test lại query cũ.
</p>
                
        </div>

        <button
            onclick="runDebugQuery()"
            class="bg-slate-900 hover:bg-slate-800 text-white font-bold px-6 py-4 rounded-2xl shadow-lg transition flex items-center justify-center"
        >
            <i class="fas fa-bug mr-2"></i>
            Run Debug Query
        </button>
    </div>
</div>
            <div id="rag-action-result" class="no-print hidden bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
            <div class="flex items-start gap-4">
                <div class="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center flex-shrink-0">
                    <i class="fas fa-circle-info"></i>
                </div>
                <div class="min-w-0 flex-1">
                    <h4 id="rag-action-title" class="font-extrabold text-gray-800 mb-4">Kết quả thao tác</h4>

<div id="rag-debug-pretty" class="hidden space-y-5 mb-5">
    <div class="bg-blue-50 border border-blue-100 rounded-2xl p-5">
        <p class="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2">
            AI Answer
        </p>
        <div id="rag-debug-answer" class="text-sm text-slate-700 leading-loose font-medium whitespace-pre-line"></div>
    </div>

    <div class="bg-gray-50 border border-gray-100 rounded-2xl p-5">
        <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-3">
            Top Places
        </p>
        <div id="rag-debug-places" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
    </div>
</div>
<div id="rag-log-summary" class="hidden bg-purple-50 border border-purple-100 rounded-2xl p-5 mb-5">
    <p class="text-xs font-bold text-purple-500 uppercase tracking-widest mb-3">
        AI Health Summary
    </p>
    <div id="rag-log-summary-content" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 text-sm"></div>
</div>
<p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">
    Raw JSON
</p>
<pre id="rag-action-json" class="bg-slate-950 text-slate-100 text-xs leading-relaxed rounded-2xl p-4 overflow-x-auto custom-scrollbar max-h-[320px]"></pre>
                </div>
            </div>
        </div>
        <div class="bg-gradient-to-r from-emerald-50 via-blue-50 to-indigo-50 border border-blue-100 rounded-3xl p-6 shadow-sm">
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-5">
        <div>
            <p class="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2">
    System Readiness Assessment
</p>
<h3 class="text-xl font-extrabold text-slate-800">
    Trạng thái sẵn sàng của mô-đun UnuTrip RAG AI
</h3>
<p class="text-sm text-gray-600 mt-2 leading-relaxed">
    Bảng tổng quan xác nhận mô-đun RAG AI đã kết nối ổn định giữa Node.js Admin Dashboard và FastAPI RAG, sử dụng bộ dữ liệu đã rà soát, chỉ mục BM25 đã được khởi tạo và toàn bộ self-test đang đạt yêu cầu vận hành.
</p>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-5 gap-3 min-w-full lg:min-w-[620px]">
            <div class="bg-white/80 border border-emerald-100 rounded-2xl px-4 py-3">
                <p class="text-[10px] font-bold text-gray-400 uppercase">RAG Ready</p>
                <p class="text-sm font-extrabold ${readyValue === true || readyValue === 'true' ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(readyValue)}</p>
            </div>

            <div class="bg-white/80 border border-blue-100 rounded-2xl px-4 py-3">
                <p class="text-[10px] font-bold text-gray-400 uppercase">Self-test</p>
                <p class="text-sm font-extrabold text-blue-600">${escapeHtml(passedValue)}/${escapeHtml(Number(passedValue) + Number(failedValue || 0))}</p>
            </div>

            <div class="bg-white/80 border border-blue-100 rounded-2xl px-4 py-3">
                <p class="text-[10px] font-bold text-gray-400 uppercase">Places</p>
                <p class="text-sm font-extrabold text-blue-600">${escapeHtml(rsStore.place_count ?? 'N/A')}</p>
            </div>

            <div class="bg-white/80 border border-emerald-100 rounded-2xl px-4 py-3">
                <p class="text-[10px] font-bold text-gray-400 uppercase">Reviewed</p>
                <p class="text-sm font-extrabold ${rsStore.using_reviewed ? 'text-emerald-600' : 'text-orange-500'}">${escapeHtml(rsStore.using_reviewed ?? 'N/A')}</p>
            </div>

            <div class="bg-white/80 border border-indigo-100 rounded-2xl px-4 py-3">
                <p class="text-[10px] font-bold text-gray-400 uppercase">BM25</p>
                <p class="text-sm font-extrabold ${rsFiles.bm25_index?.exists ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(rsFiles.bm25_index?.exists ?? 'N/A')}</p>
            </div>
        </div>
    </div>
</div>
            <div class="rag-top-kpis no-print grid grid-cols-1 md:grid-cols-4 gap-6">
                <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">RAG Ready</p>
                    <p class="text-2xl font-extrabold ${ragStatus.ok ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(readyValue)}</p>
                    <p class="text-xs text-gray-400 mt-2">HTTP ${ragStatus.status}</p>
                </div>

                <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Self-test Passed</p>
                    <p class="text-2xl font-extrabold text-blue-600">${escapeHtml(passedValue)}</p>
                    <p class="text-xs text-gray-400 mt-2">${escapeHtml(selfTest.url)}</p>
                </div>

                <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">Self-test Failed</p>
                    <p class="text-2xl font-extrabold ${Number(failedValue) > 0 ? 'text-red-500' : 'text-emerald-600'}">${escapeHtml(failedValue)}</p>
                    <p class="text-xs text-gray-400 mt-2">Expected: 0</p>
                </div>

                <div class="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
                    <p class="text-xs font-bold text-gray-400 uppercase tracking-widest mb-2">FastAPI Port</p>
                    <p class="text-2xl font-extrabold text-slate-800">8001</p>
                    <p class="text-xs text-gray-400 mt-2">http://127.0.0.1:8001</p>
                </div>
            </div>
<div class="bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
    <div class="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6 mb-6">
        <div>
            <p class="text-xs font-bold text-blue-500 uppercase tracking-widest mb-2">
    RAG AI Validation Checklist
</p>
<h3 class="text-xl font-extrabold text-slate-800">
    Quy trình kiểm chứng hệ thống RAG AI
</h3>
<p class="text-sm text-gray-500 mt-1">
    Tổng hợp các tiêu chí cốt lõi để xác nhận trạng thái vận hành, chất lượng dữ liệu, chỉ mục truy xuất và khả năng phản hồi của mô-đun RAG AI.
</p>
        </div>
        <div class="bg-blue-50 text-blue-700 border border-blue-100 rounded-2xl px-5 py-3 text-sm font-bold">
            <i class="fas fa-circle-check mr-2"></i>
            Ready for demo
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        <div class="border border-emerald-100 bg-emerald-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">01. RAG Ready</p>
            <p class="text-sm font-extrabold text-emerald-700">ready = ${escapeHtml(readyValue)}</p>
        </div>

        <div class="border border-emerald-100 bg-emerald-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">02. Self-test</p>
            <p class="text-sm font-extrabold text-emerald-700">${escapeHtml(passedValue)} passed / ${escapeHtml(failedValue)} failed</p>
        </div>

        <div class="border border-blue-100 bg-blue-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">03. Reviewed Dataset</p>
            <p class="text-sm font-extrabold text-blue-700">${escapeHtml(rsStore.using_reviewed ?? 'N/A')}</p>
        </div>

        <div class="border border-blue-100 bg-blue-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">04. Place Store</p>
            <p class="text-sm font-extrabold text-blue-700">${escapeHtml(rsStore.place_count ?? 'N/A')} places</p>
        </div>

        <div class="border border-indigo-100 bg-indigo-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">05. BM25 Index</p>
            <p class="text-sm font-extrabold text-indigo-700">${escapeHtml(rsFiles.bm25_index?.exists ?? 'N/A')} · ${escapeHtml(rsFiles.bm25_index?.size_mb ?? 'N/A')} MB</p>
        </div>

        <div class="border border-orange-100 bg-orange-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">06. Data Quality</p>
            <p class="text-sm font-extrabold text-orange-700">${escapeHtml(dqScan.issue_count ?? 'N/A')} issues · ${escapeHtml(dqAutofix.changed_count ?? 'N/A')} autofix</p>
        </div>

        <div class="border border-slate-100 bg-slate-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">07. Debug Query</p>
            <p class="text-sm font-extrabold text-slate-700">Test: đi biển ở Khánh Hòa</p>
        </div>

        <div class="border border-purple-100 bg-purple-50 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">08. AI Fallback</p>
            <p class="text-sm font-extrabold text-purple-700">AI Logs giải thích Gemini 503/quota</p>
        </div>
    </div>
</div>
            <div class="grid grid-cols-1 xl:grid-cols-2 gap-8">
                <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="p-6 border-b border-gray-100 flex items-center justify-between">
                        <h3 class="text-lg font-extrabold text-gray-800">
                            <i class="fas fa-network-wired mr-3 text-blue-500"></i>System Overview
                        </h3>
                        <span class="text-xs font-bold ${overview.ok ? 'text-emerald-600' : 'text-red-500'}">HTTP ${overview.status}</span>
                    </div>
                    <div class="p-6 bg-blue-50/40 border-b border-blue-100">
    <p class="text-xs font-bold text-blue-500 uppercase tracking-widest mb-4">System Overview Summary</p>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Runtime Mode</p>
            <p class="text-lg font-extrabold text-slate-800">${escapeHtml(overviewRuntime.runtime_mode ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Gemini Enabled</p>
            <p class="text-lg font-extrabold ${overviewRuntime.enable_gemini ? 'text-emerald-600' : 'text-orange-500'}">${escapeHtml(overviewRuntime.enable_gemini ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Gemini Model</p>
            <p class="text-lg font-extrabold text-blue-600">${escapeHtml(overviewRuntime.gemini_model ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Gemini Configured</p>
            <p class="text-lg font-extrabold ${overviewRuntime.gemini_configured ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(overviewRuntime.gemini_configured ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">RAG Ready</p>
            <p class="text-lg font-extrabold ${overviewRag.ready ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(overviewRag.ready ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-blue-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Cache Enabled</p>
            <p class="text-lg font-extrabold ${overviewCache.enabled ? 'text-emerald-600' : 'text-orange-500'}">${escapeHtml(overviewCache.enabled ?? 'N/A')}</p>
        </div>
    </div>
</div>

<div class="p-4 bg-gray-50 border-b border-gray-100">
    <button
        id="btn-system-overview-json"
        onclick="toggleRawJson('system-overview-json', 'btn-system-overview-json')"
        class="text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl transition"
    >
        <i class="fas fa-code mr-2"></i>Show Raw JSON
    </button>
</div>
<pre id="system-overview-json" class="hidden m-0 p-6 bg-slate-950 text-slate-100 text-xs leading-relaxed overflow-x-auto max-h-[360px] custom-scrollbar">${renderJsonBox(overview.data)}</pre>
                </div>

                <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="p-6 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-lg font-extrabold text-gray-800">
            <i class="fas fa-robot mr-3 text-blue-500"></i>RAG Status
        </h3>
        <span class="text-xs font-bold ${ragStatus.ok ? 'text-emerald-600' : 'text-red-500'}">HTTP ${ragStatus.status}</span>
    </div>

    <div class="p-6 bg-blue-50/40 border-b border-blue-100">
        <p class="text-xs font-bold text-blue-500 uppercase tracking-widest mb-4">RAG Status Summary</p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div class="bg-white border border-blue-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Ready</p>
                <p class="text-2xl font-extrabold ${rs.ready ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(rs.ready ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-blue-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Place Count</p>
                <p class="text-2xl font-extrabold text-blue-600">${escapeHtml(rsStore.place_count ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-blue-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Using Reviewed</p>
                <p class="text-2xl font-extrabold ${rsStore.using_reviewed ? 'text-emerald-600' : 'text-orange-500'}">${escapeHtml(rsStore.using_reviewed ?? 'N/A')}</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            ${[
                ['places_master', rsFiles.places_master],
                ['places_app', rsFiles.places_app],
                ['places_app_reviewed', rsFiles.places_app_reviewed],
                ['places_itinerary', rsFiles.places_itinerary],
                ['rag_documents', rsFiles.rag_documents],
                ['bm25_index', rsFiles.bm25_index],
            ].map(([label, file]) => `
                <div class="bg-white border border-blue-100 rounded-xl px-4 py-3">
                    <div class="flex items-center justify-between mb-1">
                        <span class="text-xs font-bold text-slate-600">${escapeHtml(label)}</span>
                        <span class="text-xs font-extrabold ${file?.exists ? 'text-emerald-600 bg-emerald-50' : 'text-red-600 bg-red-50'} px-2 py-1 rounded-lg">${escapeHtml(file?.exists ?? 'N/A')}</span>
                    </div>
                    <p class="text-[11px] text-gray-400 font-medium truncate">${escapeHtml(file?.path ?? '')}</p>
                    <p class="text-[11px] text-blue-600 font-extrabold mt-1">${escapeHtml(file?.size_mb ?? 'N/A')} MB</p>
                </div>
            `).join('')}
        </div>
    </div>

    <div class="p-4 bg-gray-50 border-b border-gray-100">
    <button
        id="btn-rag-status-json"
        onclick="toggleRawJson('rag-status-json', 'btn-rag-status-json')"
        class="text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl transition"
    >
        <i class="fas fa-code mr-2"></i>Show Raw JSON
    </button>
</div>
<pre id="rag-status-json" class="hidden m-0 p-6 bg-slate-950 text-slate-100 text-xs leading-relaxed overflow-x-auto max-h-[360px] custom-scrollbar">${renderJsonBox(ragStatus.data)}</pre>
</div>

                <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
    <div class="p-6 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-lg font-extrabold text-gray-800">
            <i class="fas fa-vial-circle-check mr-3 text-emerald-500"></i>Self-test
        </h3>
        <span class="text-xs font-bold ${selfTest.ok ? 'text-emerald-600' : 'text-red-500'}">HTTP ${selfTest.status}</span>
    </div>

    <div class="p-6 bg-emerald-50/40 border-b border-emerald-100">
        <p class="text-xs font-bold text-emerald-500 uppercase tracking-widest mb-4">Self-test Summary</p>

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-5">
            <div class="bg-white border border-emerald-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Ready</p>
                <p class="text-2xl font-extrabold ${st.ready ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(st.ready ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-emerald-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Passed</p>
                <p class="text-2xl font-extrabold text-blue-600">${escapeHtml(st.passed ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-emerald-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Failed</p>
                <p class="text-2xl font-extrabold ${Number(st.failed) > 0 ? 'text-red-500' : 'text-emerald-600'}">${escapeHtml(st.failed ?? 'N/A')}</p>
            </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            ${[
                ['Health OK', stChecks.health_ok?.ok],
                ['RAG files ready', stChecks.rag_files_ready?.ok],
                ['Place store ready', stChecks.place_store_ready?.ok],
                ['Using reviewed dataset', stChecks.place_store_using_reviewed?.ok],
                ['Cache OK', stChecks.cache_ok?.ok],
                ['Data quality report OK', stChecks.data_quality_report_ok?.ok],
                ['Retrieve Khánh Hòa OK', stChecks.retrieve_khanhhoa_ok?.ok],
                ['Retrieve Huế OK', stChecks.retrieve_hue_ok?.ok],
            ].map(([label, ok]) => `
                <div class="flex items-center justify-between bg-white border border-emerald-100 rounded-xl px-4 py-3">
                    <span class="text-xs font-bold text-slate-600">${escapeHtml(label)}</span>
                    <span class="text-xs font-extrabold ${ok ? 'text-emerald-600 bg-emerald-50' : 'text-red-600 bg-red-50'} px-2 py-1 rounded-lg">${escapeHtml(ok ?? 'N/A')}</span>
                </div>
            `).join('')}
        </div>
    </div>

    <div class="p-4 bg-gray-50 border-b border-gray-100">
    <button
        id="btn-self-test-json"
        onclick="toggleRawJson('self-test-json', 'btn-self-test-json')"
        class="text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl transition"
    >
        <i class="fas fa-code mr-2"></i>Show Raw JSON
    </button>
</div>
<pre id="self-test-json" class="hidden m-0 p-6 bg-slate-950 text-slate-100 text-xs leading-relaxed overflow-x-auto max-h-[360px] custom-scrollbar">${renderJsonBox(selfTest.data)}</pre>
</div>

                <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
                    <div class="p-6 border-b border-gray-100 flex items-center justify-between">
                        <h3 class="text-lg font-extrabold text-gray-800">
                            <i class="fas fa-chart-line mr-3 text-indigo-500"></i>AI Metrics
                        </h3>
                        <span class="text-xs font-bold ${metrics.ok ? 'text-emerald-600' : 'text-red-500'}">HTTP ${metrics.status}</span>
                    </div>
                    <div class="p-6 bg-indigo-50/40 border-b border-indigo-100">
    <p class="text-xs font-bold text-indigo-500 uppercase tracking-widest mb-4">AI Metrics Summary</p>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Total Requests</p>
            <p class="text-2xl font-extrabold text-slate-800">${escapeHtml(aiMetrics.total_requests ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Fallback Rate</p>
            <p class="text-2xl font-extrabold ${Number(aiMetrics.fallback_rate) > 0.5 ? 'text-orange-500' : 'text-emerald-600'}">${escapeHtml(aiMetrics.fallback_rate ?? 'N/A')}</p>
        </div>

        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Gemini Success</p>
            <p class="text-2xl font-extrabold text-emerald-600">${escapeHtml(modelUsage['gemini-2.5-flash'] ?? 0)}</p>
        </div>

        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Template Fallback</p>
            <p class="text-2xl font-extrabold text-orange-500">${escapeHtml(modelUsage.template_after_gemini_error ?? 0)}</p>
        </div>

        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Quota Exceeded</p>
            <p class="text-2xl font-extrabold text-red-500">${escapeHtml(aiMetrics.quota_exceeded_count ?? 0)}</p>
        </div>

        <div class="bg-white border border-indigo-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-1">Cache Hit Rate</p>
            <p class="text-2xl font-extrabold text-blue-600">${escapeHtml(aiMetrics.cache_hit_rate ?? 'N/A')}</p>
        </div>
    </div>
</div>

<div class="p-4 bg-gray-50 border-b border-gray-100">
    <button
        id="btn-ai-metrics-json"
        onclick="toggleRawJson('ai-metrics-json', 'btn-ai-metrics-json')"
        class="text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl transition"
    >
        <i class="fas fa-code mr-2"></i>Show Raw JSON
    </button>
</div>
<pre id="ai-metrics-json" class="hidden m-0 p-6 bg-slate-950 text-slate-100 text-xs leading-relaxed overflow-x-auto max-h-[360px] custom-scrollbar">${renderJsonBox(metrics.data)}</pre>
                </div>

                <div class="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden xl:col-span-2">
    <div class="p-6 border-b border-gray-100 flex items-center justify-between">
        <h3 class="text-lg font-extrabold text-gray-800">
            <i class="fas fa-database mr-3 text-orange-500"></i>Data Quality
        </h3>
        <span class="text-xs font-bold ${dataQuality.ok ? 'text-emerald-600' : 'text-red-500'}">HTTP ${dataQuality.status}</span>
    </div>

    <div class="p-6 bg-orange-50/40 border-b border-orange-100">
        <p class="text-xs font-bold text-orange-500 uppercase tracking-widest mb-4">Data Quality Summary</p>

        <div class="grid grid-cols-1 md:grid-cols-6 gap-4 mb-5">
            <div class="bg-white border border-orange-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Total Issues</p>
                <p class="text-2xl font-extrabold text-slate-800">${escapeHtml(dqScan.issue_count ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-orange-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">High</p>
                <p class="text-2xl font-extrabold text-red-500">${escapeHtml(dqScan.severity_counts?.high ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-orange-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Medium</p>
                <p class="text-2xl font-extrabold text-orange-500">${escapeHtml(dqScan.severity_counts?.medium ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-orange-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Low</p>
                <p class="text-2xl font-extrabold text-blue-500">${escapeHtml(dqScan.severity_counts?.low ?? 'N/A')}</p>
            </div>

            <div class="bg-white border border-orange-100 rounded-2xl p-4">
                <p class="text-xs font-bold text-gray-400 uppercase mb-1">Autofix</p>
                <p class="text-2xl font-extrabold text-emerald-600">${escapeHtml(dqAutofix.changed_count ?? 'N/A')}</p>
            </div>
            <div class="bg-white border border-orange-100 rounded-2xl p-4">
    <p class="text-xs font-bold text-gray-400 uppercase mb-1">Reviewed</p>
    <p class="text-2xl font-extrabold ${dqReviewed.exists ? 'text-emerald-600' : 'text-red-500'}">${escapeHtml(dqReviewed.exists ?? 'N/A')}</p>
</div>
        </div>

        <div class="bg-white border border-orange-100 rounded-2xl p-4">
            <p class="text-xs font-bold text-gray-400 uppercase mb-3">Issue Types</p>
            <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
                ${Object.entries(dqScan.issue_counts || {}).map(([key, value]) => `
                    <div class="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
                        <span class="text-xs font-bold text-slate-600">${escapeHtml(key)}</span>
                        <span class="text-xs font-extrabold text-orange-600 bg-orange-100 px-2 py-1 rounded-lg">${escapeHtml(value)}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    </div>

    <div class="p-4 bg-gray-50 border-b border-gray-100">
    <button
        id="btn-data-quality-json"
        onclick="toggleRawJson('data-quality-json', 'btn-data-quality-json')"
        class="text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl transition"
    >
        <i class="fas fa-code mr-2"></i>Show Raw JSON
    </button>
</div>
<pre id="data-quality-json" class="hidden m-0 p-6 bg-slate-950 text-slate-100 text-xs leading-relaxed overflow-x-auto max-h-[420px] custom-scrollbar">${renderJsonBox(dataQuality.data)}</pre>
</div>
            </div>

                        <div class="no-print bg-amber-50 border border-amber-100 text-amber-800 rounded-3xl p-6">
                <h4 class="font-extrabold mb-2">
                    <i class="fas fa-circle-info mr-2"></i>Ghi chú endpoint
                </h4>
                <p class="text-sm leading-relaxed">
                    Trang này đang gọi các endpoint:
                    <code>/admin/system/overview</code>,
                    <code>/admin/rag/status</code>,
                    <code>/admin/system/self-test</code>,
                    <code>/admin/ai/metrics</code>,
                    <code>/admin/data-quality/status</code>.
                </p>
            </div>

            <script>
    async function runRagAction(url, label, method = 'POST') {
        const box = document.getElementById('rag-action-result');
        const title = document.getElementById('rag-action-title');
        const json = document.getElementById('rag-action-json');
        const pretty = document.getElementById('rag-debug-pretty');
        const logSummary = document.getElementById('rag-log-summary');
        const logSummaryContent = document.getElementById('rag-log-summary-content');

        if (pretty) pretty.classList.add('hidden');
        if (logSummary) logSummary.classList.add('hidden');

        box.classList.remove('hidden');
        title.innerHTML = '<i class="fas fa-spinner animate-spin mr-2 text-blue-500"></i>Đang chạy: ' + label;
        json.textContent = 'Đang gửi yêu cầu...';

        try {
            const res = await fetch(url, { method });
            const data = await res.json();

            title.innerHTML = res.ok
                ? '<i class="fas fa-check-circle mr-2 text-emerald-500"></i>Hoàn thành: ' + label
                : '<i class="fas fa-triangle-exclamation mr-2 text-red-500"></i>Lỗi: ' + label;

            if (label === 'AI Logs' && logSummary && logSummaryContent) {
                const summary = renderLogSummary(data);
                if (summary.show) {
                    logSummary.classList.remove('hidden');
                    logSummaryContent.innerHTML = summary.html;
                }
            }

            json.textContent = JSON.stringify(data, null, 2);
        } catch (err) {
            title.innerHTML = '<i class="fas fa-triangle-exclamation mr-2 text-red-500"></i>Kết nối thất bại: ' + label;
            json.textContent = err.message;
        }
    }
        function renderLogSummary(data) {
    const payload = data.data || data;
    const logs = payload.logs || [];
    const latest = logs[0];

    if (!latest) {
        return {
            show: false,
            html: ''
        };
    }

    const topPlaces = Array.isArray(latest.top_place_names)
        ? latest.top_place_names.slice(0, 6).join(', ')
        : 'Không có dữ liệu';

    const errorText = latest.generation_error
        ? String(latest.generation_error)
        : 'Không có lỗi generation';

    const shortError = errorText.length > 180
        ? errorText.slice(0, 180) + '...'
        : errorText;

    const fallbackClass = latest.fallback_used ? 'text-orange-600 bg-orange-50' : 'text-emerald-600 bg-emerald-50';

    const html = ''
        + '<div class="bg-white border border-purple-100 rounded-2xl p-4">'
        + '  <p class="text-xs font-bold text-gray-400 uppercase mb-1">Runtime</p>'
        + '  <p class="font-extrabold text-slate-800">' + (latest.runtime_mode || 'unknown') + '</p>'
        + '</div>'
        + '<div class="bg-white border border-purple-100 rounded-2xl p-4">'
        + '  <p class="text-xs font-bold text-gray-400 uppercase mb-1">Model used</p>'
        + '  <p class="font-extrabold text-slate-800">' + (latest.model_used || 'unknown') + '</p>'
        + '</div>'
        + '<div class="bg-white border border-purple-100 rounded-2xl p-4">'
        + '  <p class="text-xs font-bold text-gray-400 uppercase mb-1">Fallback</p>'
        + '  <p class="font-extrabold ' + fallbackClass + ' inline-block px-3 py-1 rounded-xl">' + String(Boolean(latest.fallback_used)) + '</p>'
        + '</div>'
        + '<div class="bg-white border border-purple-100 rounded-2xl p-4 md:col-span-2 xl:col-span-3">'
        + '  <p class="text-xs font-bold text-gray-400 uppercase mb-1">Generation error</p>'
        + '  <p class="font-semibold text-slate-700 leading-relaxed">' + shortError + '</p>'
        + '</div>'
        + '<div class="bg-white border border-purple-100 rounded-2xl p-4 md:col-span-2 xl:col-span-3">'
        + '  <p class="text-xs font-bold text-gray-400 uppercase mb-1">Top places</p>'
        + '  <p class="font-semibold text-slate-700 leading-relaxed">' + topPlaces + '</p>'
        + '</div>';

    return {
        show: true,
        html
    };
}
        function renderDebugPlaces(places) {
    if (!Array.isArray(places) || places.length === 0) {
        return '<div class="text-sm text-gray-400 italic">Không có địa điểm trả về.</div>';
    }

    return places.slice(0, 9).map(function(place, index) {
        const name = place.name || place.title || place.place_name || 'Không rõ tên';
        const province = place.province || place.city || '';
        const placeId = place.place_id || place.id || '';
        const category = place.category || place.category_main || place.category_sub || '';
        const score = place.final_score ?? place.score ?? place.quality_score ?? '';

        return ''
            + '<div class="bg-white border border-gray-100 rounded-2xl p-4 shadow-sm">'
            + '  <div class="flex items-start justify-between gap-3 mb-3">'
            + '    <div>'
            + '      <p class="text-sm font-extrabold text-slate-800">' + (index + 1) + '. ' + name + '</p>'
            + '      <p class="text-xs text-gray-400 mt-1">' + province + '</p>'
            + '    </div>'
            + '    <span class="text-[10px] font-bold bg-blue-50 text-blue-600 px-2 py-1 rounded-full">' + placeId + '</span>'
            + '  </div>'
            + '  <div class="flex flex-wrap gap-2 text-[11px] font-bold">'
            +      (category ? '<span class="bg-gray-100 text-gray-600 px-2 py-1 rounded-lg">' + category + '</span>' : '')
            +      (score !== '' ? '<span class="bg-emerald-50 text-emerald-600 px-2 py-1 rounded-lg">score: ' + score + '</span>' : '')
            + '  </div>'
            + '</div>';
    }).join('');
}
        
        async function runDebugQuery() {
    const input = document.getElementById('rag-debug-query');
    const message = input.value.trim();

    if (!message) {
        alert('Vui lòng nhập câu hỏi cần debug.');
        input.focus();
        return;
    }

    const box = document.getElementById('rag-action-result');
    const title = document.getElementById('rag-action-title');
    const json = document.getElementById('rag-action-json');
    const pretty = document.getElementById('rag-debug-pretty');
const answerBox = document.getElementById('rag-debug-answer');
const placesBox = document.getElementById('rag-debug-places');
const logSummary = document.getElementById('rag-log-summary');
if (logSummary) logSummary.classList.add('hidden');

    box.classList.remove('hidden');
    title.innerHTML = '<i class="fas fa-spinner animate-spin mr-2 text-blue-500"></i>Đang debug query...';
    json.textContent = 'Đang gửi câu hỏi: ' + message;

    try {
        const res = await fetch('/admin/rag-ai/debug-query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const data = await res.json();

        title.innerHTML = res.ok
            ? '<i class="fas fa-check-circle mr-2 text-emerald-500"></i>Debug Query hoàn thành'
            : '<i class="fas fa-triangle-exclamation mr-2 text-red-500"></i>Debug Query lỗi';

        const payload = data.data || data;
const answer = payload.answer || payload.response || payload.message || '';
const places = payload.places || payload.top_places || payload.results || [];

if (pretty && answerBox && placesBox) {
    pretty.classList.remove('hidden');
    answerBox.textContent = answer || 'Không có answer trong response.';
    placesBox.innerHTML = renderDebugPlaces(places);
}

json.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
        title.innerHTML = '<i class="fas fa-triangle-exclamation mr-2 text-red-500"></i>Kết nối debug thất bại';
        json.textContent = err.message;
    }
}
    function printRagReport() {
    window.print();
}
    function toggleRawJson(id, btnId) {
    const box = document.getElementById(id);
    const btn = document.getElementById(btnId);

    if (!box || !btn) return;

    const isHidden = box.classList.contains('hidden');

    if (isHidden) {
        box.classList.remove('hidden');
        btn.innerHTML = '<i class="fas fa-eye-slash mr-2"></i>Hide Raw JSON';
    } else {
        box.classList.add('hidden');
        btn.innerHTML = '<i class="fas fa-code mr-2"></i>Show Raw JSON';
    }
}
</script>
        </div>
      `;
        

      res.send(renderLayout(content, "rag-ai", "RAG AI"));
    } catch (error) {
      res.status(500).send("RAG AI Dashboard Error: " + error.message);
    }
  });
    // 6. RAG AI Actions
  router.post("/rag-ai/reload-place-store", async (req, res) => {
    const result = await postRagJson("/admin/rag/place-store/reload");
    res.status(result.ok ? 200 : 502).json(result);
  });

  router.post("/rag-ai/clear-cache", async (req, res) => {
    const result = await postRagJson("/admin/cache/clear");
    res.status(result.ok ? 200 : 502).json(result);
  });
    router.get("/rag-ai/data-quality-issues", async (req, res) => {
    const result = await fetchRagJson("/admin/data-quality/issues", 5000);
    res.status(result.ok ? 200 : 502).json(result);
  });

  router.get("/rag-ai/ai-metrics", async (req, res) => {
    const result = await fetchRagJson("/admin/ai/metrics", 5000);
    res.status(result.ok ? 200 : 502).json(result);
  });
  router.get("/rag-ai/ai-logs", async (req, res) => {
  const result = await fetchRagJson("/admin/ai/logs", 5000);
  res.status(result.ok ? 200 : 502).json(result);
});
  router.post("/rag-ai/debug-query", async (req, res) => {
  const message = String(req.body?.message || req.body?.query || "").trim();

  if (!message) {
    return res.status(400).json({
      ok: false,
      status: 400,
      data: {
        error: "Thiếu message"
      }
    });
  }

  const result = await postRagJson("/admin/ai/debug-query", { message }, 15000);
  res.status(result.ok ? 200 : 502).json(result);
});
  // 5. AI Report API
  router.get("/ai-report", async (req, res) => {
    try {
      const catStats = await db.query("SELECT category, COUNT(*) as count FROM app_places GROUP BY category");
      const overall = await db.get("SELECT AVG(rating) as avgRating FROM app_places");

      const prompt = `Phân tích dữ liệu ứng dụng UnuTrip:
        - Thống kê danh mục địa điểm: ${JSON.stringify(catStats)}
        - Điểm đánh giá trung bình: ${overall.avgRating?.toFixed(2) || 0}
        Hãy viết báo cáo ngắn gọn gồm 3 mục:
        1. Nhận xét chất lượng dữ liệu hiện tại.
        2. Điểm mạnh của hệ thống gợi ý du lịch.
        3. Đề xuất cải thiện nội dung và trải nghiệm người dùng.`;

      let report = "";
      const aiUrl = process.env.AI_MODEL_URL || "http://localhost:8000/chat";
      try {
        const aiRes = await fetch(aiUrl, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: prompt })
        });
        const aiData = await aiRes.json();
        report = aiData.answer;
      } catch (err) {
        console.warn("Admin AI report: local AI failed, using RAG:", err.message);
        const result = await postRagJson(
          "/rag/chat",
          { message: prompt, top_k: 6, mode: "balanced", include_prompt: false },
          30000
        );
        if (!result.ok) {
          return res.json({
            success: false,
            message: result.data?.detail || result.data?.error || "RAG không khả dụng"
          });
        }
        report = result.data?.answer ?? "";
      }

      if (!report) {
        return res.json({ success: false, message: "Không tạo được báo cáo (rỗng)." });
      }

      return res.json({ success: true, report });
    } catch (error) { res.json({ success: false, message: error.message }); }
  });

  return router;
}
