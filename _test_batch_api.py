import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from emoji_agent import get_skill_instance

folder = "_sample"
if not os.path.isdir(folder):
    print("测试文件夹不存在：", folder); sys.exit(1)

from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

# 1. 测 /api/mode_compare
print("1️⃣  测 /api/mode_compare...")
r = client.get("/api/mode_compare")
assert r.status_code == 200 and r.json()["status"] == "success"
print("   OK, 维度数：", len(r.json()["compare"]))

# 2. 上传4张文件
files = []
for fp in sorted(glob.glob(os.path.join(folder, "*"))):
    files.append(("files", (os.path.basename(fp), open(fp, "rb"), "image/png")))
print("2️⃣  批量上传...")
r = client.post("/api/upload_batch", files=files)
for _, (_, fh, _) in files:
    fh.close()
print("   状态:", r.status_code, "; 成功上传:", r.json()["count"])
assert r.status_code == 200 and r.json()["count"] >= 3
items = r.json()["items"]

# 3. 批量生成
print("3️⃣  批量生成 2 张测试...")
sub = items[:2]
payload = {
    "items": json.dumps(sub),
    "platform": "wechat",
    "dynamic_type": "bounce",
    "add_text": "可爱",
    "text_position": "top",
    "per_image_text": "true",
    "compress": "true",
}
r = client.post("/api/generate_batch", data=payload)
print("   状态:", r.status_code, "; 成功数:", r.json()["success"], "/", r.json()["total"], "; zip:", bool(r.json()["zip_url"]))
assert r.status_code == 200 and r.json()["success"] == 2
assert r.json()["zip_url"], "应返回打包 ZIP 链接"

# 4. 测输出列表里出现 zip
print("4️⃣  测 /api/outputs 出现 zip...")
r = client.get("/api/outputs?limit=30")
outs = r.json()["items"]
print("   输出总数：", len(outs), "; zip数:", sum(1 for x in outs if x.get("is_zip")))

# 5. 再单独测下 generate 单图（规则模式）
print("5️⃣  测单图 generate ...")
payload2 = {
    "file_path": items[2]["file_path"],
    "platform": "wechat",
    "dynamic_type": "breathe",
    "add_text": "哈哈哈",
    "text_position": "bottom",
}
r = client.post("/api/generate", data=payload2)
print("   状态:", r.status_code, "; url:", r.json().get("download_url"))
assert r.status_code == 200 and r.json().get("download_url")

print("✅ 所有接口测试通过")
