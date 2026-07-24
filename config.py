import os
from PIL import Image, ImageFilter, ImageDraw, ImageFont
import imageio
import cv2
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "emoji_output")
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

WECHAT_EMOJI_SIZE = (240, 240)
QQ_EMOJI_SIZE = (320, 320)
MAX_GIF_SIZE_KB = 500

for d in [SAVE_DIR, UPLOAD_DIR, TEMPLATE_DIR, STATIC_DIR]:
    os.makedirs(d, exist_ok=True)


def get_save_path(filename: str) -> str:
    return os.path.join(SAVE_DIR, filename)


def get_unique_path(prefix: str, ext: str) -> str:
    import time
    timestamp = int(time.time() * 1000)
    return get_save_path(f"{prefix}_{timestamp}.{ext}")


def load_image_rgba(img_path: str) -> Image.Image:
    return Image.open(img_path).convert("RGBA")


def pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    cv_img = np.array(pil_img.convert("RGB"))
    return cv2.cvtColor(cv_img, cv2.COLOR_RGB2BGR)


def cv2_to_pil(cv_img: np.ndarray) -> Image.Image:
    rgb_img = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb_img)
