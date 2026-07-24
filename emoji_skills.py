from langchain.tools import tool
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import imageio
import cv2
import numpy as np
import os
import glob
from typing import List, Optional

from config import (
    WECHAT_EMOJI_SIZE,
    QQ_EMOJI_SIZE,
    get_unique_path,
    load_image_rgba,
    pil_to_cv2,
    cv2_to_pil,
)

_REMBG_AVAILABLE = None
_REMBG_REMOVE = None


def _get_remove_func():
    global _REMBG_AVAILABLE, _REMBG_REMOVE
    if _REMBG_AVAILABLE is True:
        return _REMBG_REMOVE
    if _REMBG_AVAILABLE is False:
        return None
    try:
        from rembg import remove as _remove
        _REMBG_REMOVE = _remove
        _REMBG_AVAILABLE = True
        return _REMBG_REMOVE
    except Exception:
        _REMBG_AVAILABLE = False
        return None


@tool("图片背景抠图技能")
def remove_bg(img_path: str, save_path: Optional[str] = None) -> str:
    """
    技能：上传图片自动抠图，生成透明底表情图（未安装rembg时降级为不抠图直接返回）
    :param img_path: 本地输入图片路径
    :param save_path: 抠图后保存路径（可选）
    :return: 处理完成的图片路径
    """
    input_img = Image.open(img_path).convert("RGBA")
    remove_fn = _get_remove_func()
    if remove_fn is not None:
        out_img = remove_fn(input_img)
    else:
        out_img = input_img
        if not save_path:
            save_path = get_unique_path("no_bg_emoji", "png")
        out_img.save(save_path)
        return f"未安装rembg，跳过抠图步骤直接返回（pip install rembg 可启用抠图），路径：{save_path}"
    if not save_path:
        save_path = get_unique_path("no_bg_emoji", "png")
    out_img.save(save_path)
    return f"抠图完成，保存路径：{save_path}"


@tool("表情尺寸适配技能")
def resize_emoji(img_path: str, platform: str = "wechat") -> str:
    """
    技能：适配微信/QQ标准表情包尺寸，等比缩放并居中裁剪
    :param img_path: 输入图片路径
    :param platform: 目标平台，可选 wechat / qq
    :return: 处理后图片路径
    """
    img = Image.open(img_path).convert("RGBA")
    target_size = WECHAT_EMOJI_SIZE if platform == "wechat" else QQ_EMOJI_SIZE
    tw, th = target_size
    sw, sh = img.size
    scale = max(tw / sw, th / sh)
    new_w, new_h = int(sw * scale), int(sh * scale)
    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - tw) // 2
    top = (new_h - th) // 2
    img = img.crop((left, top, left + tw, top + th))
    save_p = get_unique_path(f"{platform}_size_emoji", "png")
    img.save(save_p)
    return f"{platform}尺寸适配完成，路径：{save_p}"


@tool("静态表情美化技能")
def beauty_emoji(img_path: str, bright: int = 10, smooth: bool = True,
                 contrast: float = 1.1, saturation: float = 1.1) -> str:
    """
    技能：提亮、磨皮、增强对比度和饱和度美化静态表情包
    :param img_path: 输入图片路径
    :param bright: 亮度提升值（0-50）
    :param smooth: 是否开启磨皮
    :param contrast: 对比度增强系数（1.0-1.5）
    :param saturation: 饱和度增强系数（1.0-1.5）
    :return: 处理后图片路径
    """
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return f"读取图片失败：{img_path}"
    if len(img.shape) == 3 and img.shape[2] == 4:
        bgr = img[:, :, :3]
        alpha = img[:, :, 3]
    else:
        bgr = img
        alpha = None

    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    h, s, v = cv2.split(hsv)
    lim = 255 - bright
    v[v > lim] = 255
    v[v <= lim] += bright
    s = np.clip(s * saturation, 0, 255)
    final_hsv = cv2.merge((h, s, v)).astype(np.uint8)
    res = cv2.cvtColor(final_hsv, cv2.COLOR_HSV2BGR)

    lab = cv2.cvtColor(res, cv2.COLOR_BGR2LAB).astype(np.float32)
    l, a, b = cv2.split(lab)
    l = np.clip((l - 128) * contrast + 128, 0, 255)
    lab = cv2.merge((l, a, b)).astype(np.uint8)
    res = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    if smooth:
        res = cv2.bilateralFilter(res, 5, 50, 50)

    if alpha is not None:
        res = cv2.merge((res, alpha))

    save_p = get_unique_path("beauty_emoji", "png")
    cv2.imwrite(save_p, res)
    return f"表情美化完成，路径：{save_p}"


@tool("多图合成GIF动图技能")
def make_gif_emoji(img_list: List[str], duration: float = 0.3, loop: int = 0) -> str:
    """
    技能：多张图片合成微信QQ通用GIF动图表情包
    :param img_list: 图片路径列表，按帧顺序排列
    :param duration: 单帧时长，单位秒
    :param loop: 循环次数，0表示无限循环
    :return: 生成的GIF路径
    """
    frames = []
    for p in img_list:
        frame = Image.open(p).convert("RGBA")
        frames.append(frame)
    if not frames:
        return "图片列表为空，无法生成GIF"
    gif_path = get_unique_path("dynamic_emoji", "gif")
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(duration * 1000),
        loop=loop,
        disposal=2
    )
    return f"GIF动图表情包生成成功，路径：{gif_path}"


@tool("单图逐帧抖动动图技能")
def shake_gif_from_single(img_path: str, frame_num: int = 6,
                          offset_range: int = 8, rotation: int = 3) -> str:
    """
    技能：单张图片自动生成抖动摇摆动态表情包
    :param img_path: 输入单张图片路径
    :param frame_num: 生成帧数
    :param offset_range: 抖动偏移像素范围
    :param rotation: 最大旋转角度（度）
    :return: 抖动GIF路径
    """
    base_img = load_image_rgba(img_path)
    w, h = base_img.size
    shake_frames = []
    for i in range(frame_num):
        dx = int(np.random.randint(-offset_range, offset_range + 1))
        dy = int(np.random.randint(-offset_range, offset_range + 1))
        angle = int(np.random.randint(-rotation, rotation + 1))
        rotated = base_img.rotate(angle, resample=Image.Resampling.BICUBIC, expand=False)
        new_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        new_img.paste(rotated, (dx, dy), rotated)
        shake_frames.append(new_img)
    out_gif = get_unique_path("shake_dynamic", "gif")
    shake_frames[0].save(
        out_gif,
        save_all=True,
        append_images=shake_frames[1:],
        duration=200,
        loop=0,
        disposal=2
    )
    return f"单图抖动动图生成完成，路径：{out_gif}"


@tool("动图压缩适配微信发送")
def compress_gif(gif_path: str, max_size_kb: int = 500) -> str:
    """
    技能：压缩GIF体积，适配微信表情包大小限制，自动迭代缩小尺寸
    :param gif_path: 输入GIF路径
    :param max_size_kb: 目标最大体积（单位KB）
    :return: 压缩后GIF路径
    """
    compress_path = get_unique_path("compress_wechat", "gif")
    try:
        frames = imageio.mimread(gif_path, memtest=False)
    except Exception as e:
        return f"读取GIF失败：{e}"
    target_size = (200, 200)
    best_path = compress_path
    for scale in [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4]:
        new_w = max(1, int(target_size[0] * scale))
        new_h = max(1, int(target_size[1] * scale))
        new_frames = []
        for f in frames:
            if len(f.shape) == 2:
                f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
            elif f.shape[2] == 4:
                f = cv2.cvtColor(f, cv2.COLOR_RGBA2RGB)
            elif f.shape[2] == 3:
                pass
            else:
                f = f[:, :, :3]
            resized = cv2.resize(f, (new_w, new_h))
            new_frames.append(resized)
        try:
            imageio.mimsave(compress_path, new_frames, duration=0.25)
        except Exception as _e:
            pil_frames = [Image.fromarray(cv2.cvtColor(f, cv2.COLOR_BGR2RGB)) for f in new_frames]
            if pil_frames:
                pil_frames[0].save(
                    compress_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=250,
                    loop=0,
                    disposal=2
                )
        if os.path.exists(compress_path):
            size_kb = os.path.getsize(compress_path) / 1024
            best_path = compress_path
            if size_kb <= max_size_kb:
                break
    return f"微信适配压缩动图完成，路径：{best_path}"


_COLOR_MAP = {
    "white": (255, 255, 255),
    "black": (0, 0, 0),
    "red": (255, 0, 0),
    "yellow": (255, 255, 0),
    "blue": (0, 0, 255),
    "green": (0, 255, 0),
    "pink": (255, 100, 180),
}


def _parse_color(name: str, default=(255, 255, 255)):
    return _COLOR_MAP.get((name or "").lower(), default)


def _load_font(font_size: int):
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, font_size)
            except Exception:
                continue
    return ImageFont.load_default()


@tool("文字贴纸添加技能")
def add_text_sticker(img_path: str, text: str, position: str = "bottom",
                     font_size: int = 32, font_color: str = "white",
                     stroke_color: str = "black", stroke_width: int = 2) -> str:
    """
    技能：在表情包上添加自定义文字气泡贴纸（支持描边）
    :param img_path: 输入图片路径
    :param text: 要添加的文字内容
    :param position: 文字位置 top/bottom/center
    :param font_size: 字体大小
    :param font_color: 字体颜色 white/black/red/yellow/blue/green
    :param stroke_color: 描边颜色
    :param stroke_width: 描边宽度
    :return: 处理后图片路径
    """
    img = load_image_rgba(img_path)
    draw = ImageDraw.Draw(img)
    w, h = img.size
    fc = _parse_color(font_color, (255, 255, 255))
    sc = _parse_color(stroke_color, (0, 0, 0))
    font = _load_font(font_size)

    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]

    if position == "top":
        pos = ((w - tw) // 2, int(h * 0.05))
    elif position == "center":
        pos = ((w - tw) // 2, (h - th) // 2)
    else:
        pos = ((w - tw) // 2, max(0, int(h * 0.85 - th)))

    if stroke_width > 0:
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx != 0 or dy != 0:
                    draw.text((pos[0] + dx, pos[1] + dy), text, font=font, fill=sc)
    draw.text(pos, text, font=font, fill=fc)

    save_p = get_unique_path("text_emoji", "png")
    img.save(save_p)
    return f"文字贴纸添加完成，路径：{save_p}"


@tool("特效变换技能")
def apply_effect(img_path: str, effect: str = "flip_h") -> str:
    """
    技能：对图片应用各种特效变换（翻转、旋转、镜像、鱼眼、黑白、怀旧、模糊、锐化）
    :param img_path: 输入图片路径
    :param effect: 特效类型：flip_h水平翻转/flip_v垂直翻转/rotate_90/rotate_180/mirror镜像/fisheye鱼眼/grayscale黑白/sepia怀旧/blur模糊/sharpen锐化
    :return: 处理后图片路径
    """
    img = load_image_rgba(img_path)
    w, h = img.size

    if effect == "flip_h":
        result = img.transpose(Image.FLIP_LEFT_RIGHT)
    elif effect == "flip_v":
        result = img.transpose(Image.FLIP_TOP_BOTTOM)
    elif effect == "rotate_90":
        result = img.rotate(90, expand=True, resample=Image.Resampling.BICUBIC)
    elif effect == "rotate_180":
        result = img.rotate(180, expand=True, resample=Image.Resampling.BICUBIC)
    elif effect == "mirror":
        result = Image.new("RGBA", (w * 2, h))
        result.paste(img, (0, 0))
        result.paste(img.transpose(Image.FLIP_LEFT_RIGHT), (w, 0))
    elif effect == "fisheye":
        cv_img = pil_to_cv2(img)
        K = np.array([[w, 0, w / 2], [0, h, h / 2], [0, 0, 1]], dtype=np.float32)
        D = np.array([-0.5, 0.2, 0, 0, 0], dtype=np.float32)
        map1, map2 = cv2.initUndistortRectifyMap(K, D, None, K, (w, h), 5)
        fisheye_img = cv2.remap(cv_img, map1, map2, cv2.INTER_LINEAR)
        result = cv2_to_pil(fisheye_img).convert("RGBA")
    elif effect == "grayscale":
        result = img.convert("L").convert("RGBA")
    elif effect == "sepia":
        arr = np.array(img.convert("RGB"))
        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        tr = 0.393 * r + 0.769 * g + 0.189 * b
        tg = 0.349 * r + 0.686 * g + 0.168 * b
        tb = 0.272 * r + 0.534 * g + 0.131 * b
        sepia_arr = np.stack([np.clip(tr, 0, 255), np.clip(tg, 0, 255), np.clip(tb, 0, 255)], axis=2).astype(np.uint8)
        result = Image.fromarray(sepia_arr).convert("RGBA")
    elif effect == "blur":
        result = img.filter(ImageFilter.GaussianBlur(radius=2))
    elif effect == "sharpen":
        result = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150))
    else:
        result = img

    save_p = get_unique_path(f"effect_{effect}", "png")
    result.save(save_p)
    return f"特效{effect}应用完成，路径：{save_p}"


@tool("边框装饰技能")
def add_border_decoration(img_path: str, style: str = "rounded",
                          border_width: int = 8, border_color: str = "white",
                          shadow: bool = True, bg_color: Optional[str] = None) -> str:
    """
    技能：为表情包添加外框、圆角、阴影等边框装饰（支持霓虹光效）
    :param img_path: 输入图片路径
    :param style: 边框样式 rounded圆角/solid直线框/dashed虚线框/neon霓虹光
    :param border_width: 边框宽度像素
    :param border_color: 边框颜色 white/black/red/yellow/blue/green/pink
    :param shadow: 是否添加阴影
    :param bg_color: 可选背景色填充
    :return: 处理后图片路径
    """
    img = load_image_rgba(img_path)
    w, h = img.size
    pad = border_width + (20 if shadow else 0)
    canvas = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    bc = _parse_color(border_color, (255, 255, 255))

    if shadow:
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(shadow_layer)
        shadow_box = (pad + 6, pad + 6, pad + w + 6, pad + h + 6)
        for r_idx in range(5, 0, -1):
            alpha = 40 - r_idx * 6
            sd.rounded_rectangle(shadow_box, radius=20, fill=(0, 0, 0, max(0, alpha)))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(radius=3))
        canvas = Image.alpha_composite(canvas, shadow_layer)

    draw = ImageDraw.Draw(canvas)
    box = (pad, pad, pad + w, pad + h)

    bg_fill = None
    if bg_color:
        c = _parse_color(bg_color, None)
        if c is not None:
            bg_fill = (c[0], c[1], c[2], 255)

    if style == "rounded":
        if bg_fill:
            draw.rounded_rectangle(box, radius=20, fill=bg_fill)
        for i in range(border_width):
            b = (pad - i, pad - i, pad + w + i, pad + h + i)
            draw.rounded_rectangle(b, radius=20, outline=bc, width=1)
    elif style == "solid":
        if bg_fill:
            draw.rectangle(box, fill=bg_fill)
        draw.rectangle(box, outline=bc, width=border_width)
    elif style == "dashed":
        if bg_fill:
            draw.rectangle(box, fill=bg_fill)
        dash_len = 10
        for i in range(0, w, dash_len * 2):
            draw.line([(pad + i, pad), (pad + i + dash_len, pad)], fill=bc, width=border_width)
            draw.line([(pad + i, pad + h), (pad + i + dash_len, pad + h)], fill=bc, width=border_width)
        for i in range(0, h, dash_len * 2):
            draw.line([(pad, pad + i), (pad, pad + i + dash_len)], fill=bc, width=border_width)
            draw.line([(pad + w, pad + i), (pad + w, pad + i + dash_len)], fill=bc, width=border_width)
    elif style == "neon":
        for glow in range(8, 0, -1):
            alpha = int(40 * (glow / 8))
            neon_color = (bc[0], bc[1], bc[2], alpha)
            glow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
            gd = ImageDraw.Draw(glow_layer)
            gb = (pad - glow, pad - glow, pad + w + glow, pad + h + glow)
            gd.rounded_rectangle(gb, radius=20, outline=neon_color, width=3)
            glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=glow))
            canvas = Image.alpha_composite(canvas, glow_layer)
        draw.rounded_rectangle(box, radius=20, outline=bc, width=border_width)

    canvas.paste(img, (pad, pad), img)
    save_p = get_unique_path(f"border_{style}", "png")
    canvas.save(save_p)
    return f"边框装饰{style}添加完成，路径：{save_p}"


@tool("批量生成表情包技能")
def batch_process_emoji(folder_path: str, platform: str = "wechat",
                        remove_background: bool = True, apply_beauty: bool = True,
                        make_shake: bool = True, add_text: Optional[str] = None) -> str:
    """
    技能：文件夹内图片批量一键转表情包，自动执行抠图、适配、美化、加字、生成动图等步骤
    :param folder_path: 包含图片的文件夹路径
    :param platform: 目标平台 wechat/qq
    :param remove_background: 是否自动抠图
    :param apply_beauty: 是否自动美化
    :param make_shake: 是否生成抖动动图
    :param add_text: 可选批量添加文字
    :return: 处理结果汇总
    """
    extensions = ("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.webp")
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(folder_path, ext)))
    if not files:
        return f"文件夹{folder_path}内未找到图片文件"

    results = []
    count = 0
    for img_path in files:
        try:
            current = img_path
            if remove_background:
                r = remove_bg.invoke({"img_path": current})
                current = r.split("：")[-1]
            r = resize_emoji.invoke({"img_path": current, "platform": platform})
            current = r.split("：")[-1]
            if apply_beauty:
                r = beauty_emoji.invoke({"img_path": current})
                current = r.split("：")[-1]
            if add_text:
                r = add_text_sticker.invoke({"img_path": current, "text": add_text})
                current = r.split("：")[-1]
            if make_shake:
                r = shake_gif_from_single.invoke({"img_path": current})
                results.append(r)
            else:
                results.append(f"静态表情生成完成，路径：{current}")
            count += 1
        except Exception as e:
            results.append(f"处理{os.path.basename(img_path)}失败：{str(e)}")

    summary = f"批量处理完成，成功{count}张，共{len(files)}张。\n" + "\n".join(results[:10])
    if len(results) > 10:
        summary += f"\n...其余{len(results) - 10}条省略"
    return summary


@tool("弹跳动图技能")
def bounce_gif_from_single(img_path: str, frame_num: int = 8, scale_range: float = 0.2) -> str:
    """
    技能：单张图片生成弹跳缩放动态表情包
    :param img_path: 输入单张图片路径
    :param frame_num: 生成帧数
    :param scale_range: 缩放变化幅度（0-1）
    :return: 弹跳GIF路径
    """
    base_img = load_image_rgba(img_path)
    w, h = base_img.size
    frames = []
    for i in range(frame_num):
        phase = (i / frame_num) * 2 * 3.14159
        scale = 1.0 + scale_range * 0.5 + scale_range * 0.5 * np.sin(phase)
        new_w, new_h = max(1, int(w * scale)), max(1, int(h * scale))
        scaled = base_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        new_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        offset_x = (w - new_w) // 2
        offset_y = h - new_h
        new_img.paste(scaled, (offset_x, offset_y), scaled)
        frames.append(new_img)
    out_gif = get_unique_path("bounce_dynamic", "gif")
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=120, loop=0, disposal=2)
    return f"弹跳动图生成完成，路径：{out_gif}"


@tool("呼吸淡入动图技能")
def breathe_gif_from_single(img_path: str, frame_num: int = 10) -> str:
    """
    技能：单张图片生成透明度呼吸淡入淡出动态表情包
    :param img_path: 输入单张图片路径
    :param frame_num: 生成帧数
    :return: 呼吸动图GIF路径
    """
    base_img = load_image_rgba(img_path)
    w, h = base_img.size
    frames = []
    for i in range(frame_num):
        phase = (i / frame_num) * 2 * 3.14159
        alpha_ratio = 0.4 + 0.6 * (0.5 + 0.5 * np.sin(phase))
        frame = base_img.copy()
        r, g, b, a = frame.split()
        a = a.point(lambda x: int(x * alpha_ratio))
        frame = Image.merge("RGBA", (r, g, b, a))
        frames.append(frame)
    out_gif = get_unique_path("breathe_dynamic", "gif")
    frames[0].save(out_gif, save_all=True, append_images=frames[1:], duration=150, loop=0, disposal=2)
    return f"呼吸淡入动图生成完成，路径：{out_gif}"


@tool("全流程表情包生成技能")
def full_pipeline_emoji(img_path: str, platform: str = "wechat",
                        make_dynamic: str = "shake", add_text: Optional[str] = None,
                        text_position: str = "bottom", compress: bool = True) -> str:
    """
    技能：一键全流程生成表情包（抠图→尺寸适配→美化→加字→动图→压缩）
    :param img_path: 输入图片路径
    :param platform: 目标平台 wechat/qq
    :param make_dynamic: 动图类型 shake抖动/bounce弹跳/breathe呼吸/static静态
    :param add_text: 可选添加的文字
    :param text_position: 文字位置 top/bottom/center
    :param compress: 是否压缩适配微信
    :return: 最终结果路径
    """
    current = img_path
    steps = []

    r = remove_bg.invoke({"img_path": current})
    current = r.split("：")[-1]
    steps.append("抠图")

    r = resize_emoji.invoke({"img_path": current, "platform": platform})
    current = r.split("：")[-1]
    steps.append(f"{platform}尺寸适配")

    r = beauty_emoji.invoke({"img_path": current})
    current = r.split("：")[-1]
    steps.append("美化")

    if add_text:
        r = add_text_sticker.invoke({
            "img_path": current,
            "text": add_text,
            "position": text_position
        })
        current = r.split("：")[-1]
        steps.append(f"加文字[{add_text}]")

    final_path = current
    if make_dynamic == "shake":
        r = shake_gif_from_single.invoke({"img_path": current})
        final_path = r.split("：")[-1]
        steps.append("抖动动图")
    elif make_dynamic == "bounce":
        r = bounce_gif_from_single.invoke({"img_path": current})
        final_path = r.split("：")[-1]
        steps.append("弹跳动图")
    elif make_dynamic == "breathe":
        r = breathe_gif_from_single.invoke({"img_path": current})
        final_path = r.split("：")[-1]
        steps.append("呼吸动图")

    if compress and make_dynamic != "static":
        r = compress_gif.invoke({"gif_path": final_path})
        final_path = r.split("：")[-1]
        steps.append("压缩适配")

    return f"全流程处理完成：{'→'.join(steps)}，最终路径：{final_path}"


_ALL_TOOL_FUNCS = [
    remove_bg,
    resize_emoji,
    beauty_emoji,
    make_gif_emoji,
    shake_gif_from_single,
    compress_gif,
    add_text_sticker,
    apply_effect,
    add_border_decoration,
    batch_process_emoji,
    bounce_gif_from_single,
    breathe_gif_from_single,
    full_pipeline_emoji,
]


class EmojiMakerSkill:
    """表情包&动图生成智能体专属Skill集合（容器类，便于组织所有工具）"""

    def __init__(self):
        self.remove_bg = remove_bg
        self.resize_emoji = resize_emoji
        self.beauty_emoji = beauty_emoji
        self.make_gif_emoji = make_gif_emoji
        self.shake_gif_from_single = shake_gif_from_single
        self.compress_gif = compress_gif
        self.add_text_sticker = add_text_sticker
        self.apply_effect = apply_effect
        self.add_border_decoration = add_border_decoration
        self.batch_process_emoji = batch_process_emoji
        self.bounce_gif_from_single = bounce_gif_from_single
        self.breathe_gif_from_single = breathe_gif_from_single
        self.full_pipeline_emoji = full_pipeline_emoji


def get_all_tools():
    return list(_ALL_TOOL_FUNCS)
