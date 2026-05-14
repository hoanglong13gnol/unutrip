from pathlib import Path

p = Path("rag/pipeline.py")
t = p.read_text(encoding="utf-8")
marker = "\n    # def run("
i = t.find(marker)
if i < 0:
    raise SystemExit("marker not found")
p.write_text(t[:i], encoding="utf-8")
print("trimmed", len(t), "->", i)
