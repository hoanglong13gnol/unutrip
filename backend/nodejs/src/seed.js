import bcrypt from "bcryptjs";
import { db, jsonOrNull } from "./db.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// ==================== HELPERS ====================
function rand(min, max) { return Math.floor(Math.random() * (max - min + 1)) + min; }
function pick(arr) { return arr[rand(0, arr.length - 1)]; }
function randFloat(min, max, dec = 1) { return parseFloat((Math.random() * (max - min) + min).toFixed(dec)); }

const VN_FIRST = ["Nguyễn","Trần","Lê","Phạm","Hoàng","Huỳnh","Phan","Vũ","Võ","Đặng","Bùi","Đỗ","Hồ","Ngô","Dương","Lý"];
const VN_MIDDLE = ["Văn","Thị","Đức","Minh","Quốc","Thanh","Ngọc","Hoàng","Xuân","Thu","Thùy","Anh","Hữu","Phương","Quang"];
const VN_LAST = ["An","Bình","Chi","Dũng","Em","Giang","Hà","Khanh","Linh","Mai","Nam","Oanh","Phú","Quân","Sơn","Tú","Uyên","Vy","Yến","Đạt"];

function vnName() { return `${pick(VN_FIRST)} ${pick(VN_MIDDLE)} ${pick(VN_LAST)}`; }

const CATEGORIES = ["beach","mountain","city","heritage","nature"];
const TAGS_POOL = ["culture","food","photography","nature","relax","swim","boat","sunset","nightmarket","themepark","citywalk","hiking","camping","shopping","temple","waterfall","island","coffee","street_food","museum"];

// 50 real Vietnam destinations data
const DESTINATIONS_DATA = [
  { name:"Hồ Gươm", desc:"Biểu tượng trung tâm Hà Nội, phù hợp dạo bộ và khám phá văn hóa.", addr:"Quận Hoàn Kiếm", city:"Hà Nội", prov:"Hà Nội", lat:21.0287, lng:105.8520, cat:"heritage" },
  { name:"Vịnh Hạ Long", desc:"Di sản thiên nhiên thế giới, trải nghiệm du thuyền và hang động.", addr:"TP Hạ Long", city:"Hạ Long", prov:"Quảng Ninh", lat:20.9101, lng:107.1839, cat:"nature" },
  { name:"Bà Nà Hills", desc:"Khu du lịch trên núi nổi tiếng với Cầu Vàng.", addr:"Hòa Ninh, Hòa Vang", city:"Đà Nẵng", prov:"Đà Nẵng", lat:15.9956, lng:107.9962, cat:"mountain" },
  { name:"Phố cổ Hội An", desc:"Không gian cổ kính, ẩm thực đường phố và đèn lồng.", addr:"Trung tâm Hội An", city:"Hội An", prov:"Quảng Nam", lat:15.8801, lng:108.3382, cat:"heritage" },
  { name:"Bãi Sao", desc:"Bãi biển đẹp tại Phú Quốc, cát trắng và nước trong.", addr:"An Thới", city:"Phú Quốc", prov:"Kiên Giang", lat:10.0364, lng:104.0414, cat:"beach" },
  { name:"Chùa Một Cột", desc:"Ngôi chùa cổ kính hình hoa sen giữa lòng Hà Nội.", addr:"Quận Ba Đình", city:"Hà Nội", prov:"Hà Nội", lat:21.0359, lng:105.8341, cat:"heritage" },
  { name:"Sapa", desc:"Thị trấn sương mù với ruộng bậc thang tuyệt đẹp.", addr:"Thị trấn Sa Pa", city:"Sa Pa", prov:"Lào Cai", lat:22.3364, lng:103.8438, cat:"mountain" },
  { name:"Đại Nội Huế", desc:"Quần thể di tích cố đô Huế, di sản văn hóa thế giới.", addr:"Kinh thành Huế", city:"Huế", prov:"Thừa Thiên Huế", lat:16.4698, lng:107.5786, cat:"heritage" },
  { name:"Biển Mỹ Khê", desc:"Một trong những bãi biển đẹp nhất hành tinh.", addr:"Quận Ngũ Hành Sơn", city:"Đà Nẵng", prov:"Đà Nẵng", lat:16.0544, lng:108.2480, cat:"beach" },
  { name:"Núi Fansipan", desc:"Nóc nhà Đông Dương cao 3143m.", addr:"Hoàng Liên", city:"Sa Pa", prov:"Lào Cai", lat:22.3033, lng:103.7750, cat:"mountain" },
  { name:"Phong Nha - Kẻ Bàng", desc:"Vườn quốc gia với hệ thống hang động kỳ vĩ.", addr:"Bố Trạch", city:"Đồng Hới", prov:"Quảng Bình", lat:17.5900, lng:106.2834, cat:"nature" },
  { name:"Cầu Rồng", desc:"Cầu rồng phun lửa và nước, biểu tượng Đà Nẵng.", addr:"Quận Sơn Trà", city:"Đà Nẵng", prov:"Đà Nẵng", lat:16.0610, lng:108.2278, cat:"city" },
  { name:"Tháp Bà Ponagar", desc:"Tháp Chăm cổ nổi tiếng tại Nha Trang.", addr:"Vĩnh Phước", city:"Nha Trang", prov:"Khánh Hòa", lat:12.2654, lng:109.1945, cat:"heritage" },
  { name:"Biển Nha Trang", desc:"Vịnh biển xinh đẹp với nhiều hoạt động thể thao nước.", addr:"Trần Phú", city:"Nha Trang", prov:"Khánh Hòa", lat:12.2388, lng:109.1967, cat:"beach" },
  { name:"Đảo Cát Bà", desc:"Hòn đảo lớn nhất vịnh Lan Hạ, thiên đường du lịch.", addr:"Cát Hải", city:"Hải Phòng", prov:"Hải Phòng", lat:20.7981, lng:107.0500, cat:"nature" },
  { name:"Chợ Bến Thành", desc:"Ngôi chợ truyền thống biểu tượng của Sài Gòn.", addr:"Quận 1", city:"TP HCM", prov:"TP HCM", lat:10.7721, lng:106.6980, cat:"city" },
  { name:"Dinh Độc Lập", desc:"Dinh thự lịch sử nổi tiếng tại Sài Gòn.", addr:"Quận 1", city:"TP HCM", prov:"TP HCM", lat:10.7769, lng:106.6952, cat:"heritage" },
  { name:"Cù Lao Chàm", desc:"Đảo sinh thái với rạn san hô tuyệt đẹp.", addr:"Tân Hiệp", city:"Hội An", prov:"Quảng Nam", lat:15.9500, lng:108.5167, cat:"beach" },
  { name:"Đèo Hải Vân", desc:"Con đèo đẹp nhất Việt Nam nối Huế và Đà Nẵng.", addr:"Hải Vân", city:"Đà Nẵng", prov:"Đà Nẵng", lat:16.1989, lng:108.1322, cat:"nature" },
  { name:"Mũi Né", desc:"Thiên đường cát vàng và thể thao biển.", addr:"Hàm Tiến", city:"Phan Thiết", prov:"Bình Thuận", lat:10.9331, lng:108.2875, cat:"beach" },
  { name:"Đà Lạt", desc:"Thành phố ngàn hoa, khí hậu mát mẻ quanh năm.", addr:"Trung tâm TP", city:"Đà Lạt", prov:"Lâm Đồng", lat:11.9404, lng:108.4583, cat:"city" },
  { name:"Hồ Xuân Hương", desc:"Hồ nước thơ mộng giữa lòng thành phố Đà Lạt.", addr:"Trung tâm", city:"Đà Lạt", prov:"Lâm Đồng", lat:11.9398, lng:108.4397, cat:"nature" },
  { name:"Thác Bản Giốc", desc:"Thác nước hùng vĩ nhất Đông Nam Á.", addr:"Đàm Thủy", city:"Trùng Khánh", prov:"Cao Bằng", lat:22.8548, lng:106.7263, cat:"nature" },
  { name:"Hang Sơn Đoòng", desc:"Hang động lớn nhất thế giới.", addr:"Bố Trạch", city:"Đồng Hới", prov:"Quảng Bình", lat:17.5435, lng:106.1451, cat:"nature" },
  { name:"Chùa Bái Đính", desc:"Quần thể chùa lớn nhất Đông Nam Á.", addr:"Gia Viễn", city:"Ninh Bình", prov:"Ninh Bình", lat:20.2709, lng:105.8492, cat:"heritage" },
  { name:"Tràng An", desc:"Quần thể danh thắng di sản thế giới UNESCO.", addr:"Hoa Lư", city:"Ninh Bình", prov:"Ninh Bình", lat:20.2527, lng:105.9013, cat:"nature" },
  { name:"Cố đô Hoa Lư", desc:"Kinh đô cổ của Việt Nam thời Đinh - Lê.", addr:"Trường Yên", city:"Ninh Bình", prov:"Ninh Bình", lat:20.2756, lng:105.9146, cat:"heritage" },
  { name:"Vườn quốc gia Cúc Phương", desc:"Vườn quốc gia đầu tiên của Việt Nam.", addr:"Cúc Phương", city:"Ninh Bình", prov:"Ninh Bình", lat:20.2520, lng:105.7151, cat:"nature" },
  { name:"Đảo Lý Sơn", desc:"Hòn đảo tiền tiêu với cảnh quan địa chất độc đáo.", addr:"Lý Sơn", city:"Quảng Ngãi", prov:"Quảng Ngãi", lat:15.3800, lng:109.1100, cat:"beach" },
  { name:"Bãi biển An Bàng", desc:"Bãi biển yên tĩnh gần phố cổ Hội An.", addr:"An Bàng", city:"Hội An", prov:"Quảng Nam", lat:15.9055, lng:108.3586, cat:"beach" },
  { name:"Ngũ Hành Sơn", desc:"Năm ngọn núi đá vôi với chùa và hang động.", addr:"Q. Ngũ Hành Sơn", city:"Đà Nẵng", prov:"Đà Nẵng", lat:16.0036, lng:108.2625, cat:"mountain" },
  { name:"Chợ nổi Cái Răng", desc:"Chợ nổi sông nước đặc trưng miền Tây.", addr:"Cái Răng", city:"Cần Thơ", prov:"Cần Thơ", lat:10.0123, lng:105.7530, cat:"city" },
  { name:"Bảo tàng Chứng tích Chiến tranh", desc:"Bảo tàng lịch sử chiến tranh nổi tiếng.", addr:"Quận 3", city:"TP HCM", prov:"TP HCM", lat:10.7794, lng:106.6920, cat:"heritage" },
  { name:"Landmark 81", desc:"Tòa nhà cao nhất Việt Nam, biểu tượng hiện đại.", addr:"Bình Thạnh", city:"TP HCM", prov:"TP HCM", lat:10.7952, lng:106.7219, cat:"city" },
  { name:"Côn Đảo", desc:"Quần đảo lịch sử với bãi biển hoang sơ.", addr:"Côn Đảo", city:"Côn Đảo", prov:"Bà Rịa - Vũng Tàu", lat:8.6841, lng:106.6095, cat:"beach" },
  { name:"Núi Bà Đen", desc:"Ngọn núi cao nhất Nam Bộ.", addr:"Tây Ninh", city:"Tây Ninh", prov:"Tây Ninh", lat:11.3612, lng:106.1107, cat:"mountain" },
  { name:"Vũng Tàu", desc:"Thành phố biển gần Sài Gòn nhất.", addr:"Bãi Sau", city:"Vũng Tàu", prov:"Bà Rịa - Vũng Tàu", lat:10.3460, lng:107.0843, cat:"beach" },
  { name:"Mù Cang Chải", desc:"Ruộng bậc thang đẹp nhất miền Bắc.", addr:"La Pán Tẩn", city:"Mù Cang Chải", prov:"Yên Bái", lat:21.7833, lng:104.0833, cat:"mountain" },
  { name:"Hà Giang Geopark", desc:"Công viên địa chất toàn cầu UNESCO.", addr:"Đồng Văn", city:"Hà Giang", prov:"Hà Giang", lat:23.2765, lng:105.3639, cat:"mountain" },
  { name:"Suối Tiên", desc:"Suối cát đỏ kỳ ảo tại Mũi Né.", addr:"Mũi Né", city:"Phan Thiết", prov:"Bình Thuận", lat:10.9564, lng:108.3012, cat:"nature" },
  { name:"Cầu Vàng", desc:"Cây cầu được bàn tay khổng lồ nâng đỡ tại Bà Nà.", addr:"Bà Nà Hills", city:"Đà Nẵng", prov:"Đà Nẵng", lat:15.9975, lng:107.9950, cat:"city" },
  { name:"Nhà thờ Đức Bà", desc:"Nhà thờ kiến trúc Roman nổi tiếng Sài Gòn.", addr:"Quận 1", city:"TP HCM", prov:"TP HCM", lat:10.7798, lng:106.6990, cat:"heritage" },
  { name:"Phố đi bộ Nguyễn Huệ", desc:"Con phố sôi động nhất Sài Gòn.", addr:"Quận 1", city:"TP HCM", prov:"TP HCM", lat:10.7739, lng:106.7030, cat:"city" },
  { name:"Đầm Sen", desc:"Công viên văn hóa giải trí lớn nhất TPHCM.", addr:"Quận 11", city:"TP HCM", prov:"TP HCM", lat:10.7680, lng:106.6520, cat:"city" },
  { name:"Thiên Mụ Pagoda", desc:"Ngôi chùa cổ nhất Huế bên dòng sông Hương.", addr:"Kim Long", city:"Huế", prov:"Thừa Thiên Huế", lat:16.4539, lng:107.5523, cat:"heritage" },
  { name:"Lăng Khải Định", desc:"Lăng mộ hoàng gia với kiến trúc Đông Tây kết hợp.", addr:"Thủy Bằng", city:"Huế", prov:"Thừa Thiên Huế", lat:16.3928, lng:107.5979, cat:"heritage" },
  { name:"Đảo Nam Du", desc:"Quần đảo hoang sơ phía Nam Phú Quốc.", addr:"Nam Du", city:"Kiên Hải", prov:"Kiên Giang", lat:9.6833, lng:104.3667, cat:"beach" },
  { name:"Hồ Ba Bể", desc:"Hồ nước ngọt tự nhiên lớn nhất Việt Nam.", addr:"Ba Bể", city:"Bắc Kạn", prov:"Bắc Kạn", lat:22.4167, lng:105.6167, cat:"nature" },
  { name:"Tam Đảo", desc:"Thị trấn nghỉ dưỡng trên mây gần Hà Nội.", addr:"Tam Đảo", city:"Vĩnh Phúc", prov:"Vĩnh Phúc", lat:21.4583, lng:105.6417, cat:"mountain" },
  { name:"Bãi Dài Phú Quốc", desc:"Bãi biển dài 20km với cát vàng mịn.", addr:"Gành Dầu", city:"Phú Quốc", prov:"Kiên Giang", lat:10.3256, lng:103.8547, cat:"beach" },
];

const COMMENTS = [
  "Rất đẹp và ấn tượng! Chắc chắn sẽ quay lại.",
  "Cảnh quan tuyệt vời, dịch vụ tốt.",
  "Địa điểm không tệ nhưng hơi đông người.",
  "Ẩm thực ở đây ngon tuyệt vời!",
  "Một trải nghiệm đáng nhớ cho cả gia đình.",
  "Phong cảnh thiên nhiên hùng vĩ, rất đáng đến.",
  "Giá vé hơi cao nhưng xứng đáng.",
  "Nên đến vào buổi sáng sớm để tránh đông.",
  "Đẹp quá, chụp ảnh mê luôn!",
  "Không gian yên tĩnh, thích hợp để thư giãn.",
  "Nước biển trong xanh, cát trắng mịn.",
  "Đồ ăn địa phương rất ngon và rẻ.",
  "Hướng dẫn viên nhiệt tình và vui tính.",
  "Nên mang theo áo mưa vì thời tiết thay đổi.",
  "Tuyệt đối phải thử đặc sản ở đây!",
  "View đẹp mê hồn, nhất là lúc hoàng hôn.",
  "Đường đi hơi khó nhưng cảnh đẹp bù lại.",
  "Rất thích không khí ở đây, mát mẻ quanh năm.",
  "Đã đến 3 lần, lần nào cũng thấy đẹp.",
  "Địa điểm lý tưởng cho chuyến du lịch ngắn ngày.",
];

const TRIP_TITLES = [
  "Khám phá miền Trung", "Hành trình miền Bắc", "Du lịch biển đảo",
  "Về miền Tây sông nước", "Phượt Tây Bắc", "Nghỉ dưỡng cuối tuần",
  "Trải nghiệm văn hóa", "Ăn sập Sài Gòn", "Săn mây Tây Bắc",
  "Tour gia đình", "Tuần trăng mật", "Đi chơi cùng bạn bè",
];

// ==================== SEED FUNCTIONS ====================

async function getCount(table) {
  const row = await db.get(`SELECT COUNT(*) as cnt FROM ${table}`);
  return row?.cnt ?? 0;
}

async function seedUsers() {
  if (await getCount("users") >= 50) return;

  const passwordHash = bcrypt.hashSync("123456", 10);
  
  // Demo user first
  const demoExists = await db.get("SELECT id FROM users WHERE email = ?", ["demo@smarttravel.local"]);
  if (!demoExists) {
    await db.query(
      "INSERT INTO users (full_name, email, password_hash, phone, avatar, preferences_json) VALUES (?, ?, ?, ?, ?, ?)",
      ["Demo User", "demo@smarttravel.local", passwordHash, "0900000000", null, JSON.stringify(["beach","food","culture"])]
    );
  }

  const currentCount = await getCount("users");
  const needed = 50 - currentCount;

  for (let i = 0; i < needed; i++) {
    const email = `user${currentCount + i + 1}@smarttravel.local`;
    
    // Check if user already exists
    const exists = await db.get("SELECT id FROM users WHERE email = ?", [email]);
    if (exists) continue;

    const name = vnName();
    const phone = `09${String(rand(10000000, 99999999))}`;
    const prefs = [];
    const prefCount = rand(1, 3);
    for (let p = 0; p < prefCount; p++) prefs.push(pick(CATEGORIES));
    
    await db.query(
      "INSERT INTO users (full_name, email, password_hash, phone, avatar, preferences_json) VALUES (?, ?, ?, ?, ?, ?)",
      [name, email, passwordHash, phone, null, JSON.stringify([...new Set(prefs)])]
    );
  }
  console.log("✅ Seeded 50 users");
}

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function seedDestinations() {
  const count = await getCount("destinations");
  // Only seed if empty or less than 100
  if (count >= 300) return;

  let sourceData = DESTINATIONS_DATA;
  
  // Try to load from JSON file if exists
  try {
    const jsonPath = path.join(__dirname, "data", "destinations.json");
    if (fs.existsSync(jsonPath)) {
      const fileContent = fs.readFileSync(jsonPath, "utf-8");
      sourceData = JSON.parse(fileContent);
      console.log(`📖 Loading ${sourceData.length} destinations from JSON file...`);
    }
  } catch (err) {
    console.error("Error loading destinations.json, falling back to hardcoded data", err);
  }

  for (const d of sourceData) {
    const name = d.name || d["Tên địa điểm"];
    if (!name) continue;

    // Check if exists
    const exists = await db.get("SELECT id FROM destinations WHERE name = ?", [name]);
    if (exists) continue;

    // Parsing logic for Excel fields
    const desc = d.desc || d["Mô tả"] || "Đang cập nhật mô tả...";
    const prov = d.prov || d["Vị trí"] || "Việt Nam";
    const city = d.city || prov.split(",").pop().trim();
    const addr = d.addr || d["Vị trí"] || city;
    const lat = d.lat || d["latitude"] || 0;
    const lng = d.lng || d["longitude"] || 0;
    const cat = d.cat || d["category"] || "nature";
    
    // Rating parsing: "4.8/5" -> 4.8
    let rating = d.rating || 0;
    if (d["Đánh giá "]) {
      const match = d["Đánh giá "].toString().match(/(\d+\.?\d*)/);
      if (match) rating = parseFloat(match[1]);
    }
    if (rating === 0) rating = randFloat(4.0, 5.0);

    // Images parsing
    let images = [];
    if (d["Ảnh"]) images = [d["Ảnh"]];
    else if (d.images_json) images = jsonOrNull(d.images_json) || [];
    else images = [`https://picsum.photos/seed/${encodeURIComponent(name)}/900/600`];

    // Tags parsing: "\"biển\" , \"vui chơi\"" -> ["biển", "vui chơi"]
    let tags = [];
    if (d["Từ Khóa"]) {
      tags = d["Từ Khóa"].split(",").map(t => t.replace(/["\\]/g, "").trim()).filter(t => t);
    } else if (d.tags_json) {
      tags = jsonOrNull(d.tags_json) || [];
    }
    if (tags.length === 0) {
      const tagCount = rand(2, 4);
      while (tags.length < tagCount) {
        const t = pick(TAGS_POOL);
        if (!tags.includes(t)) tags.push(t);
      }
    }

    // Fee parsing
    let fee = d.entry_fee !== undefined ? d.entry_fee : null;
    if (typeof fee === 'string') {
      const match = fee.match(/(\d+)/);
      fee = match ? parseFloat(match[1]) : 0;
    }

    const openTime = d.open_time || "08:00";
    const closeTime = d.close_time || "18:00";

    await db.query(`
      INSERT INTO destinations
        (name, description, address, city, province, latitude, longitude, category, images_json, rating, review_count, open_time, close_time, entry_fee, tags_json)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      name, desc, addr, city, prov, lat, lng, cat,
      JSON.stringify(images),
      rating, rand(50, 1000), openTime, closeTime, fee,
      JSON.stringify(tags)
    ]);
  }
  console.log(`✅ Seeded destinations (Total count: ${await getCount("destinations")})`);
}

async function seedItineraries() {
  if (await getCount("itineraries") >= 100) return;

  const users = await db.query("SELECT id FROM users");
  const dests = await db.query("SELECT id FROM destinations");
  if (users.length === 0 || dests.length === 0) return;

  const currentCount = await getCount("itineraries");
  const needed = 100 - currentCount;

  for (let i = 0; i < needed; i++) {
    const userId = pick(users).id;
    const totalDays = rand(1, 5);
    const startOffset = rand(1, 60);
    const start = new Date();
    start.setDate(start.getDate() + startOffset);
    const end = new Date(start);
    end.setDate(end.getDate() + totalDays - 1);

    const startStr = start.toISOString().slice(0, 10);
    const endStr = end.toISOString().slice(0, 10);
    const status = pick(["draft", "planned", "completed"]);
    const budget = pick([null, 1000000, 2000000, 5000000, 10000000]);

    const info = await db.run(`
      INSERT INTO itineraries (user_id, title, description, start_date, end_date, total_days, status, estimated_budget)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `, [userId, `${pick(TRIP_TITLES)} #${currentCount + i + 1}`, "Lịch trình được tạo tự động.", startStr, endStr, totalDays, status, budget]);

    const itinId = info.lastInsertRowid;

    for (let d = 0; d < totalDays; d++) {
      const dayDate = new Date(start);
      dayDate.setDate(dayDate.getDate() + d);
      const dayInfo = await db.run(
        "INSERT INTO itinerary_days (itinerary_id, day_number, date) VALUES (?, ?, ?)",
        [itinId, d + 1, dayDate.toISOString().slice(0, 10)]
      );
      const dayId = dayInfo.lastInsertRowid;

      const itemCount = rand(1, 3);
      for (let j = 0; j < itemCount; j++) {
        const destId = pick(dests).id;
        const startH = 8 + j * 3;
        const endH = startH + 2;
        await db.run(`
          INSERT INTO itinerary_items (day_id, destination_id, start_time, end_time, note, order_index)
          VALUES (?, ?, ?, ?, ?, ?)
        `, [dayId, destId, `${String(startH).padStart(2,"0")}:00`, `${String(endH).padStart(2,"0")}:00`, "Tham quan và trải nghiệm", j]);
      }
    }
  }
  console.log("✅ Seeded 100 itineraries");
}

async function seedReviews() {
  if (await getCount("reviews") >= 50) return;

  const users = await db.query("SELECT id FROM users");
  const dests = await db.query("SELECT id FROM destinations");
  if (users.length === 0 || dests.length === 0) return;

  const currentCount = await getCount("reviews");
  const needed = 50 - currentCount;

  for (let i = 0; i < needed; i++) {
    const userId = pick(users).id;
    const destId = pick(dests).id;
    const rating = randFloat(3.0, 5.0);
    const comment = pick(COMMENTS);

    await db.run(
      "INSERT INTO reviews (user_id, destination_id, rating, comment, images_json) VALUES (?, ?, ?, ?, ?)",
      [userId, destId, rating, comment, null]
    );
  }

  // Update destination ratings based on actual reviews
  const destIds = [...new Set((await db.query("SELECT DISTINCT destination_id FROM reviews")).map(r => r.destination_id))];
  for (const did of destIds) {
    const agg = await db.get("SELECT AVG(rating) as avg, COUNT(*) as cnt FROM reviews WHERE destination_id = ?", [did]);
    await db.run("UPDATE destinations SET rating = ?, review_count = ? WHERE id = ?", [
      parseFloat(Number(agg.avg ?? 0).toFixed(1)), Number(agg.cnt ?? 0), did
    ]);
  }
  console.log("✅ Seeded 50 reviews (& updated ratings)");
}

export async function seed() {
  await seedUsers();
  await seedDestinations();
  await seedItineraries();
  await seedReviews();
}
