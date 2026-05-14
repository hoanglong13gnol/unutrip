from pathlib import Path

lines = Path("app/main.py").read_text(encoding="utf-8").splitlines()
start = next(
    i
    for i, l in enumerate(lines)
    if "admin/ai/logs" in l and l.strip().startswith("@app")
)
end = next(i for i, l in enumerate(lines) if l.startswith("# --- /v1"))
out_lines: list[str] = []
for l in lines[start:end]:
    l2 = l.replace('@app.get("/admin/', '@router.get("/')
    l2 = l2.replace('@app.post("/admin/', '@router.post("/')
    out_lines.append(l2)
Path("app/routers/_admin_extracted.txt").write_text("\n".join(out_lines), encoding="utf-8")
print("ok", len(out_lines), "start", start, "end", end)
