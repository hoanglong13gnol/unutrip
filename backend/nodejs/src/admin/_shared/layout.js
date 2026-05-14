/**
 * Admin-only shared layout renderer extracted from `src/admin.js` in Phase 4.
 *
 * The returned HTML — including the embedded `<style>` and `<script>` blocks —
 * is byte-identical to the original `renderLayout`. The original source used
 * useless backslash escapes inside the template literal (e.g. `\:`, `\/`,
 * `\[`, `\]`) which JavaScript silently drops at parse time. The rendered
 * output therefore never contained those backslashes, so the same byte stream
 * is produced here by writing the characters directly. This avoids
 * `no-useless-escape` lint findings without changing a single byte of HTML.
 */

export function renderLayout(content, activePath, title = "Quản trị hệ thống") {
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

.xl:grid-cols-2 {
    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
}

    .xl:col-span-2 {
        grid-column: span 2 / span 2 !important;
    }

    .bg-white,
    .bg-blue-50/40,
    .bg-emerald-50/40,
    .bg-orange-50/40,
    .bg-indigo-50/40,
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
    .lg:min-w-[620px],
    .min-w-[260px],
    .min-w-[240px] {
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
