import sys, os, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app import app
client = TestClient(app)

folder = "_sample"

# 1. 上传 4 张
files = []
for fp in sorted(glob.glob(os.path.join(folder, "*"))):
    files.append(("files", (os.path.basename(fp), open(fp, "rb"), "image/png")))
r = client.post("/api/upload_batch", files=files)
for _, (_, fh, _) in files:
    fh.close()
print("上传数:", r.json()["count"])
assert r.json()["count"] == 4
items = r.json()["items"]

# 2. 合成 4 帧：不加文字，默认参数
print("\n2️⃣  测 /api/combine_gif - 4 帧合成")
payload = {
    "items": json.dumps(items),
    "duration_ms": 250,
    "loop": 0,
    "compress": "true",
}
r = client.post("/api/combine_gif", data=payload)
print("   状态:", r.status_code)
if r.status_code != 200:
    print("   错误:", r.text[:400])
    sys.exit(1)
d = r.json()
print("   message:", d["message"])
print("   frame_count:", d["frame_count"])
print("   download_url:", d["download_url"])
assert d["frame_count"] == 4 and d["download_url"].endswith(".gif")

# 3. 合成 3 帧：指定平台+文字
print("\n3️⃣  测 /api/combine_gif - 指定平台 wechat + 每帧文字")
sub = items[:3]
payload = {
    "items": json.dumps(sub),
    "duration_ms": 400,
    "loop": 1,
    "platform": "wechat",
    "add_text": "冲鸭",
    "text_position": "top",
    "compress": "true",
}
r = client.post("/api/combine_gif", data=payload)
print("   状态:", r.status_code, "; url:", r.json().get("download_url"))
assert r.status_code == 200 and r.json()["frame_count"] == 3

# 4. 只 1 张应该报错
print("\n4️⃣  测边界：1 张应该拒绝")
r = client.post("/api/combine_gif", data={"items": json.dumps([items[0]]), "duration_ms": 300})
print("   状态:", r.status_code, "; 原因:", r.json().get("detail")[:40])
assert r.status_code == 400

print("\n✅ 多图合成 GIF 接口测试通过")
