import os
import re
import shutil
import traceback
import uuid
import zipfile
from io import BytesIO
from typing import Optional, List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
import glob

from config import SAVE_DIR, UPLOAD_DIR, TEMPLATE_DIR, BASE_DIR
from emoji_agent import (
    create_emoji_agent,
    process_with_agent,
    rule_based_process,
    get_skill_instance,
)

PATH_RE = re.compile(r"[A-Za-z]?:?[\\\/][^\s\"']+\.(?:png|gif|jpg|jpeg|webp)", re.IGNORECASE)

app = FastAPI(title="微信QQ表情包动图生成器", version="2.1.0")

if os.path.isdir(SAVE_DIR):
    app.mount("/output", StaticFiles(directory=SAVE_DIR), name="output")
if os.path.isdir(UPLOAD_DIR):
    app.mount("/upload", StaticFiles(directory=UPLOAD_DIR), name="upload")
_static_dir = os.path.join(BASE_DIR, "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

templates = Jinja2Templates(directory=TEMPLATE_DIR)

emoji_agent = None
skill_instance = get_skill_instance()


@app.on_event("startup")
def on_startup():
    global emoji_agent
    try:
        emoji_agent = create_emoji_agent(verbose=False)
    except Exception:
        emoji_agent = None


def _extract_output_url(result_msg: str) -> Optional[str]:
    path_matches = PATH_RE.findall(result_msg)
    if path_matches:
        last_path = path_matches[-1]
        base = os.path.basename(last_path)
        candidate = os.path.join(SAVE_DIR, base)
        if os.path.exists(candidate):
            return f"/output/{base}"
    return None


def _save_upload(file: UploadFile, subfolder: Optional[str] = None) -> dict:
    raw_name = file.filename or "image.png"
    ext = os.path.splitext(raw_name)[1] or ".png"
    uid = str(uuid.uuid4().hex[:12])
    save_name = f"{uid}{ext}"
    target_dir = UPLOAD_DIR if not subfolder else os.path.join(UPLOAD_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)
    save_path = os.path.join(target_dir, save_name)
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    file_size = os.path.getsize(save_path)
    return {
        "original_name": raw_name,
        "file_name": save_name,
        "file_path": save_path,
        "file_url": f"/upload/{save_name}" if not subfolder else f"/upload/{subfolder}/{save_name}",
        "file_size_kb": round(file_size / 1024, 2),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    return {"status": "success", **_save_upload(file)}


@app.post("/api/upload_batch")
async def upload_batch(files: List[UploadFile] = File(...)):
    results = []
    errors = []
    batch_id = str(uuid.uuid4().hex[:8])
    allowed_exts = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower()
        if ext and ext not in allowed_exts:
            errors.append({"name": f.filename, "reason": "不支持的文件类型"})
            continue
        try:
            info = _save_upload(f, subfolder=f"batch_{batch_id}")
            results.append(info)
        except Exception as e:
            errors.append({"name": f.filename, "reason": str(e)})
    return {
        "status": "success",
        "batch_id": batch_id,
        "count": len(results),
        "items": results,
        "errors": errors,
    }


@app.post("/api/generate")
async def generate_emoji(
    file_path: str = Form(...),
    platform: str = Form("wechat"),
    dynamic_type: str = Form("shake"),
    add_text: Optional[str] = Form(None),
    text_position: str = Form("bottom"),
    use_agent: bool = Form(False),
    custom_prompt: Optional[str] = Form(None),
):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=400, detail=f"文件不存在：{file_path}")

    try:
        if use_agent and custom_prompt:
            result_msg = process_with_agent(custom_prompt, agent=emoji_agent)
            return {
                "status": "success",
                "message": result_msg,
                "download_url": _extract_output_url(result_msg),
            }

        result_msg = rule_based_process(
            img_path=file_path,
            platform=platform,
            dynamic_type=dynamic_type,
            text=add_text,
        )
        return {
            "status": "success",
            "message": result_msg,
            "download_url": _extract_output_url(result_msg),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"处理失败：{str(e)}", "trace": traceback.format_exc()}
        )


@app.post("/api/generate_batch")
async def generate_batch(
    items: str = Form(...),
    platform: str = Form("wechat"),
    dynamic_type: str = Form("shake"),
    add_text: Optional[str] = Form(None),
    text_position: str = Form("bottom"),
    per_image_text: bool = Form(False),
    compress: bool = Form(True),
):
    import json
    try:
        item_list = json.loads(items)
    except Exception:
        raise HTTPException(status_code=400, detail="items 参数必须是 JSON 数组")
    if not isinstance(item_list, list) or not item_list:
        raise HTTPException(status_code=400, detail="请至少选择一张图片")

    outputs = []
    success = 0
    for idx, item in enumerate(item_list):
        file_path = item.get("file_path") if isinstance(item, dict) else item
        if not file_path or not os.path.exists(file_path):
            outputs.append({"index": idx, "status": "error", "message": f"文件不存在：{file_path}"})
            continue
        try:
            text_for_this = add_text
            if per_image_text and isinstance(item, dict):
                name = item.get("original_name") or item.get("file_name") or ""
                stem = os.path.splitext(os.path.basename(name))[0]
                text_for_this = stem if not add_text else f"{add_text}·{stem}"
            result_msg = skill_instance.full_pipeline_emoji.invoke({
                "img_path": file_path,
                "platform": platform,
                "make_dynamic": dynamic_type,
                "add_text": text_for_this,
                "text_position": text_position,
                "compress": compress,
            })
            outputs.append({
                "index": idx,
                "original": item.get("original_name") if isinstance(item, dict) else os.path.basename(file_path),
                "status": "success",
                "message": result_msg,
                "download_url": _extract_output_url(result_msg),
            })
            success += 1
        except Exception as e:
            outputs.append({
                "index": idx,
                "original": item.get("original_name") if isinstance(item, dict) else os.path.basename(file_path or "unknown"),
                "status": "error",
                "message": str(e),
            })

    zip_url = None
    if success >= 2:
        zip_name = f"batch_emoji_{uuid.uuid4().hex[:8]}.zip"
        zip_path = os.path.join(SAVE_DIR, zip_name)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for out in outputs:
                    url = out.get("download_url")
                    if url and url.startswith("/output/"):
                        fname = url[len("/output/"):]
                        fpath = os.path.join(SAVE_DIR, fname)
                        if os.path.exists(fpath):
                            arcname = out.get("original") or fname
                            root, ext = os.path.splitext(arcname)
                            real_ext = os.path.splitext(fname)[1]
                            if ext.lower() != real_ext.lower():
                                arcname = f"{root}{real_ext}"
                            zf.write(fpath, arcname=arcname)
            zip_url = f"/output/{zip_name}"
        except Exception:
            zip_url = None

    return {
        "status": "success",
        "total": len(item_list),
        "success": success,
        "failed": len(item_list) - success,
        "zip_url": zip_url,
        "items": outputs,
    }


def _normalize_gif_frames(frames):
    if not frames:
        return frames
    from PIL import Image
    w = min(f.width for f in frames)
    h = min(f.height for f in frames)
    out = []
    for f in frames:
        if f.width != w or f.height != h:
            f = f.resize((w, h), Image.LANCZOS)
        if f.mode != "RGBA":
            f = f.convert("RGBA")
        out.append(f)
    return out


@app.post("/api/combine_gif")
async def combine_gif(
    items: str = Form(...),
    duration_ms: int = Form(300),
    loop: int = Form(0),
    platform: Optional[str] = Form(None),
    add_text: Optional[str] = Form(None),
    text_position: str = Form("bottom"),
    compress: bool = Form(True),
):
    import json
    try:
        item_list = json.loads(items)
    except Exception:
        raise HTTPException(status_code=400, detail="items 参数必须是 JSON 数组")
    if not isinstance(item_list, list):
        raise HTTPException(status_code=400, detail="items 参数必须是数组")

    frame_paths = []
    for idx, item in enumerate(item_list):
        file_path = item.get("file_path") if isinstance(item, dict) else item
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 张图片不存在：{file_path}")
        try:
            current = file_path
            if platform in ("wechat", "qq"):
                r = skill_instance.resize_emoji.invoke({"img_path": current, "platform": platform})
                current = r.split("：")[-1]
            if add_text:
                per_text = add_text
                if isinstance(item, dict):
                    name = item.get("original_name") or item.get("file_name") or ""
                    stem = os.path.splitext(os.path.basename(name))[0]
                    per_text = f"{add_text}·{stem}"
                r = skill_instance.add_text_sticker.invoke({
                    "img_path": current,
                    "text": per_text,
                    "position": text_position,
                })
                current = r.split("：")[-1]
            frame_paths.append(current)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"第 {idx + 1} 张图片预处理失败：{e}")

    if len(frame_paths) < 2:
        raise HTTPException(status_code=400, detail="合成 GIF 至少需要 2 张图片")

    try:
        from PIL import Image
        raw_frames = [Image.open(p).convert("RGBA") for p in frame_paths]
        norm_frames = _normalize_gif_frames(raw_frames)
        from emoji_skills import get_unique_path
        tmp_gif = get_unique_path("combine_tmp", "gif")
        norm_frames[0].save(
            tmp_gif,
            save_all=True,
            append_images=norm_frames[1:],
            duration=max(50, int(duration_ms)),
            loop=max(0, int(loop)),
            disposal=2,
        )
        final_path = tmp_gif
        if compress:
            r = skill_instance.compress_gif.invoke({"gif_path": tmp_gif})
            if "：" in r:
                candidate = r.split("：")[-1].strip()
                if os.path.exists(candidate):
                    final_path = candidate
        base = os.path.basename(final_path)
        urls = [
            {"index": i,
             "original": item.get("original_name") if isinstance(item, dict) else os.path.basename(item.get("file_path") if isinstance(item, dict) else frame_paths[i]),
             "preview": f"/output/{base}"}
            for i, item in enumerate(item_list)
        ]
        return {
            "status": "success",
            "message": f"多图合成 GIF 完成，共 {len(frame_paths)} 帧，每帧 {max(50, int(duration_ms))}ms",
            "frame_count": len(frame_paths),
            "download_url": f"/output/{base}",
            "preview_url": f"/output/{base}",
            "frames": urls,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"合成 GIF 失败：{str(e)}", "trace": traceback.format_exc()}
        )


@app.get("/api/mode_compare")
def mode_compare():
    return {
        "status": "success",
        "compare": [
            {"item": "输入方式", "agent": "自然语言一句话描述", "rule": "下拉框 / 勾选框固定参数组合"},
            {"item": "步骤规划", "agent": "LLM 自主决定调用哪些工具、顺序是什么（灵活）", "rule": "固定流水线：抠图→尺寸适配→美化→加字→动图→压缩"},
            {"item": "可调用工具", "agent": "全部 13 个工具（特效、边框、单独抠图/压缩/批量等细粒度）", "rule": "仅 1 个全流程聚合工具（full_pipeline_emoji）"},
            {"item": "可实现组合", "agent": "任意：只加边框不动图 / 怀旧特效+抖动 / 只压缩已有 GIF 等", "rule": "仅预设 4×4×2 等有限组合"},
            {"item": "智能纠错", "agent": "有（路径、格式、调用失败 LLM 可重试）", "rule": "无"},
            {"item": "依赖", "agent": "需要 OPENAI_API_KEY（有推理耗时+Token 成本）", "rule": "纯本地图像处理，秒出，无外部依赖"},
            {"item": "稳定性/可重复", "agent": "依赖 LLM 输出质量，同一句两次结果可能略有差异", "rule": "100% 确定可复现"},
            {"item": "适合场景", "agent": "创意灵活、组合复杂、懒得选参数、想自定义工具链", "rule": "日常快速套模板、批量生成、无网/无 Key 环境"},
        ]
    }


@app.post("/api/tool/{tool_name}")
async def call_tool(tool_name: str, params: dict):
    if not hasattr(skill_instance, tool_name):
        raise HTTPException(status_code=400, detail=f"工具不存在：{tool_name}")
    tool = getattr(skill_instance, tool_name)
    try:
        result = tool.invoke(params)
        return {"status": "success", "message": result}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/outputs")
def list_outputs(limit: int = 50):
    files = glob.glob(os.path.join(SAVE_DIR, "*"))
    files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
    items = []
    for f in files[:limit]:
        base = os.path.basename(f)
        items.append({
            "name": base,
            "url": f"/output/{base}",
            "size_kb": round(os.path.getsize(f) / 1024, 2),
            "mtime": os.path.getmtime(f),
            "ext": os.path.splitext(base)[1].lstrip("."),
            "is_zip": base.lower().endswith(".zip"),
        })
    return {"status": "success", "items": items}


@app.get("/api/download/{filename}")
def download_file(filename: str):
    path = os.path.join(SAVE_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(path, filename=filename)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
