# ================================================================
# SAEED POSTGEN 4.6
# CONTENT GENERATION ENGINES
# FILE: core/engines.py
# ================================================================

from __future__ import annotations

import io
import os
import re
import textwrap
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PIL import Image, ImageDraw, ImageFont

from core.content_guard import check_content


# ----------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------
# ----------------------------------------------------------------
# PATHS
# ----------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

# ----------------------------------------------------------------
# RUNTIME MEDIA PATHS
# ----------------------------------------------------------------
# مسارات مؤقتة قابلة للكتابة على Streamlit Cloud

RUNTIME_DIR = Path("/tmp/saeed_postgen")

MEDIA_DIR = RUNTIME_DIR / "media"

IMAGE_DIR = MEDIA_DIR / "images"
POST_DIR = MEDIA_DIR / "posts"
AD_DIR = MEDIA_DIR / "ads"
REEL_DIR = MEDIA_DIR / "reels"
VIDEO_DIR = MEDIA_DIR / "videos"

for directory in (
    IMAGE_DIR,
    POST_DIR,
    AD_DIR,
    REEL_DIR,
    VIDEO_DIR,
):
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )


# ----------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------

POLLINATIONS_BASE = (
    "https://image.pollinations.ai/prompt/"
)

# ----------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------

POLLINATIONS_BASE = (
    "https://image.pollinations.ai/prompt/"
)

DEFAULT_IMAGE_SIZE = (
    1080,
    1080,
)

POST_SIZE = (
    1080,
    1080,
)

STORY_SIZE = (
    1080,
    1920,
)

AD_SIZE = (
    1080,
    1080,
)

REEL_SIZE = (
    1080,
    1920,
)


# ----------------------------------------------------------------
# FONT
# ----------------------------------------------------------------

FONT_DIR = BASE_DIR / "fonts"

FONT_BOLD = FONT_DIR / "Cairo-Bold.ttf"
FONT_REGULAR = FONT_DIR / "Cairo-Regular.ttf"


def get_font(
    size: int,
    bold: bool = True,
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """
    تحميل خط عربي من مجلد المشروع.
    """

    path = (
        FONT_BOLD
        if bold
        else FONT_REGULAR
    )

    try:

        if path.exists():

            return ImageFont.truetype(
                str(path),
                size,
            )

    except Exception:
        pass

    # fallback
    try:

        return ImageFont.truetype(
            "DejaVuSans.ttf",
            size,
        )

    except Exception:

        return ImageFont.load_default()


# ----------------------------------------------------------------
# TEXT HELPERS
# ----------------------------------------------------------------

def clean_text(text: Any) -> str:
    """
    تنظيف النص.
    """

    if text is None:
        return ""

    text = str(text)

    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def wrap_text(
    text: str,
    width: int = 28,
) -> str:
    """
    تقسيم النص إلى أسطر.
    """

    text = clean_text(text)

    if not text:
        return ""

    return "\n".join(
        textwrap.wrap(
            text,
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


# ----------------------------------------------------------------
# SAFE CONTENT CHECK
# ----------------------------------------------------------------

def validate_generation_text(
    *texts: str,
) -> dict[str, Any]:
    """
    فحص النص قبل إنشاء المحتوى.
    """

    combined = "\n".join(
        clean_text(value)
        for value in texts
        if value
    )

    result = check_content(
        combined
    )

    return {
        "status": result.status.value,
        "score": result.score,
        "reasons": result.reasons,
        "message": result.message,
        "requires_human_review":
            result.requires_human_review,
    }


# ----------------------------------------------------------------
# POLLINATIONS IMAGE
# ----------------------------------------------------------------

def generate_image(
    prompt: str,
    width: int = 1080,
    height: int = 1080,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    إنشاء صورة باستخدام Pollinations.

    ترجع النتيجة على شكل dictionary.
    """

    prompt = clean_text(prompt)

    if not prompt:

        return {
            "success": False,
            "status": "REVIEW",
            "message": "الوصف مطلوب.",
            "path": "",
            "image": None,
        }

    guard = validate_generation_text(
        prompt
    )

    if guard["status"] == "BLOCKED":

        return {
            "success": False,
            "status": "BLOCKED",
            "message": guard["message"],
            "path": "",
            "image": None,
        }

    final_prompt = (
        "professional commercial advertising photography, "
        "premium product advertisement, "
        "clean composition, "
        "high quality, "
        "Arabic market, "
        f"{prompt}"
    )

    encoded_prompt = quote(
        final_prompt,
        safe="",
    )

    url = (
        f"{POLLINATIONS_BASE}"
        f"{encoded_prompt}"
        f"?width={int(width)}"
        f"&height={int(height)}"
        f"&nologo=true"
    )

    try:

        response = requests.get(
            url,
            timeout=90,
        )

        response.raise_for_status()

        image = Image.open(
            io.BytesIO(
                response.content
            )
        ).convert("RGB")

        if filename:

            output_path = (
                IMAGE_DIR / filename
            )

        else:

            output_path = (
                IMAGE_DIR
                / "generated_image.png"
            )

        image.save(
            output_path,
            format="PNG",
        )

        return {
            "success": True,
            "status": guard["status"],
            "message": "تم إنشاء الصورة.",
            "path": str(output_path),
            "image": image,
        }

    except Exception as exc:

        return {
            "success": False,
            "status": "ERROR",
            "message": (
                f"تعذر إنشاء الصورة: {exc}"
            ),
            "path": "",
            "image": None,
        }


# ----------------------------------------------------------------
# IMAGE FIT
# ----------------------------------------------------------------

def fit_image(
    image: Image.Image,
    size: tuple[int, int],
) -> Image.Image:
    """
    قص وتغيير حجم الصورة إلى المقاس المطلوب.
    """

    image = image.convert("RGB")

    target_width, target_height = size

    source_width, source_height = (
        image.size
    )

    source_ratio = (
        source_width / source_height
    )

    target_ratio = (
        target_width / target_height
    )

    if source_ratio > target_ratio:

        new_height = target_height

        new_width = int(
            new_height * source_ratio
        )

    else:

        new_width = target_width

        new_height = int(
            new_width / source_ratio
        )

    image = image.resize(
        (
            new_width,
            new_height,
        ),
        Image.Resampling.LANCZOS,
    )

    left = (
        new_width - target_width
    ) // 2

    top = (
        new_height - target_height
    ) // 2

    return image.crop(
        (
            left,
            top,
            left + target_width,
            top + target_height,
        )
    )


# ----------------------------------------------------------------
# TEXT DRAWING
# ----------------------------------------------------------------

def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    image_width: int,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    """
    رسم نص في منتصف الصورة.
    """

    bbox = draw.textbbox(
        (0, 0),
        text,
        font=font,
    )

    text_width = (
        bbox[2] - bbox[0]
    )

    x = (
        image_width - text_width
    ) // 2

    draw.text(
        (x, y),
        text,
        font=font,
        fill=fill,
    )


def add_text_overlay(
    image: Image.Image,
    title: str = "",
    brand: str = "Saeed PostGen",
    contact: str = "",
    size: tuple[int, int] = POST_SIZE,
) -> Image.Image:
    """
    إضافة هوية ونص تجاري فوق الصورة.
    """

    canvas = fit_image(
        image,
        size,
    ).convert("RGBA")

    draw = ImageDraw.Draw(
        canvas,
        "RGBA",
    )

    width, height = canvas.size

    # ------------------------------------------------------------
    # BRAND
    # ------------------------------------------------------------

    brand_font = get_font(
        38,
        bold=True,
    )

    draw_centered_text(
        draw,
        clean_text(brand),
        35,
        width,
        brand_font,
        (212, 175, 55, 255),
    )

    # ------------------------------------------------------------
    # TITLE PANEL
    # ------------------------------------------------------------

    if title:

        panel_top = int(
            height * 0.60
        )

        panel_bottom = int(
            height * 0.83
        )

        draw.rounded_rectangle(
            (
                45,
                panel_top,
                width - 45,
                panel_bottom,
            ),
            radius=30,
            fill=(0, 0, 0, 185),
        )

        title_font = get_font(
            58,
            bold=True,
        )

        wrapped = wrap_text(
            title,
            width=22,
        )

        lines = wrapped.splitlines()

        line_height = 75

        total_height = (
            len(lines)
            * line_height
        )

        start_y = (
            panel_top
            + (
                (
                    panel_bottom
                    - panel_top
                )
                - total_height
            )
            // 2
        )

        for index, line in enumerate(lines):

            draw_centered_text(
                draw,
                line,
                start_y
                + index * line_height,
                width,
                title_font,
                (255, 255, 255, 255),
            )

    # ------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------

    if contact:

        contact_font = get_font(
            32,
            bold=True,
        )

        draw_centered_text(
            draw,
            clean_text(contact),
            int(height * 0.90),
            width,
            contact_font,
            (255, 255, 255, 255),
        )

    return canvas.convert("RGB")


# ----------------------------------------------------------------
# POST
# ----------------------------------------------------------------

def generate_post(
    title: str,
    prompt: str,
    brand: str = "Saeed PostGen",
    contact: str = "",
    filename: str | None = None,
) -> dict[str, Any]:
    """
    إنشاء منشور مربع.
    """

    guard = validate_generation_text(
        title,
        prompt,
        brand,
        contact,
    )

    if guard["status"] == "BLOCKED":

        return {
            "success": False,
            "status": "BLOCKED",
            "message": guard["message"],
            "path": "",
        }

    image_result = generate_image(
        prompt=prompt,
        width=POST_SIZE[0],
        height=POST_SIZE[1],
    )

    if not image_result["success"]:

        return image_result

    final_image = add_text_overlay(
        image_result["image"],
        title=title,
        brand=brand,
        contact=contact,
        size=POST_SIZE,
    )

    if filename:

        output_path = (
            POST_DIR / filename
        )

    else:

        output_path = (
            POST_DIR
            / "post.png"
        )

    final_image.save(
        output_path,
        format="PNG",
    )

    return {
        "success": True,
        "status": guard["status"],
        "message": "تم إنشاء المنشور.",
        "path": str(output_path),
        "image": final_image,
    }


# ----------------------------------------------------------------
# AD CARD
# ----------------------------------------------------------------

def generate_ad_card(
    product_name: str,
    price: str = "",
    specifications: str = "",
    contact: str = "",
    brand: str = "Saeed PostGen",
    template: str = "gold",
    product_image: Image.Image | None = None,
    filename: str | None = None,
) -> dict[str, Any]:
    """
    إنشاء بطاقة إعلانية تجارية.
    """

    guard = validate_generation_text(
        product_name,
        price,
        specifications,
        contact,
        brand,
    )

    if guard["status"] == "BLOCKED":

        return {
            "success": False,
            "status": "BLOCKED",
            "message": guard["message"],
            "path": "",
        }

    canvas = Image.new(
        "RGB",
        AD_SIZE,
        (11, 15, 25),
    )

    draw = ImageDraw.Draw(
        canvas,
    )

    width, height = canvas.size

    templates = {

        "gold": (
            (212, 175, 55),
            (255, 255, 255),
        ),

        "blue": (
            (40, 130, 220),
            (255, 255, 255),
        ),

        "green": (
            (40, 170, 100),
            (255, 255, 255),
        ),

        "red": (
            (210, 60, 60),
            (255, 255, 255),
        ),

    }

    accent, text_color = templates.get(
        template,
        templates["gold"],
    )

    # ------------------------------------------------------------
    # TOP
    # ------------------------------------------------------------

    draw.rectangle(
        (
            0,
            0,
            width,
            150,
        ),
        fill=accent,
    )

    brand_font = get_font(
        40,
        bold=True,
    )

    draw_centered_text(
        draw,
        clean_text(brand),
        48,
        width,
        brand_font,
        (10, 10, 10),
    )

    # ------------------------------------------------------------
    # PRODUCT IMAGE
    # ------------------------------------------------------------

    image_box = (
        80,
        190,
        width - 80,
        590,
    )

    draw.rounded_rectangle(
        image_box,
        radius=30,
        fill=(25, 30, 42),
    )

    if product_image is not None:

        product_image = fit_image(
            product_image,
            (
                image_box[2] - image_box[0] - 40,
                image_box[3] - image_box[1] - 40,
            ),
        )

        canvas.paste(
            product_image,
            (
                image_box[0] + 20,
                image_box[1] + 20,
            ),
        )

    # ------------------------------------------------------------
    # PRODUCT NAME
    # ------------------------------------------------------------

    name_font = get_font(
        52,
        bold=True,
    )

    name = wrap_text(
        product_name,
        20,
    )

    y = 630

    for line in name.splitlines():

        draw_centered_text(
            draw,
            line,
            y,
            width,
            name_font,
            text_color,
        )

        y += 65

    # ------------------------------------------------------------
    # SPECIFICATIONS
    # ------------------------------------------------------------

    if specifications:

        spec_font = get_font(
            30,
            bold=False,
        )

        draw_centered_text(
            draw,
            clean_text(specifications),
            y + 10,
            width,
            spec_font,
            (210, 210, 210),
        )

    # ------------------------------------------------------------
    # PRICE
    # ------------------------------------------------------------

    if price:

        price_font = get_font(
            58,
            bold=True,
        )

        draw_centered_text(
            draw,
            clean_text(price),
            805,
            width,
            price_font,
            accent,
        )

    # ------------------------------------------------------------
    # CONTACT
    # ------------------------------------------------------------

    if contact:

        contact_font = get_font(
            30,
            bold=True,
        )

        draw_centered_text(
            draw,
            clean_text(contact),
            915,
            width,
            contact_font,
            (255, 255, 255),
        )

    if filename:

        output_path = (
            AD_DIR / filename
        )

    else:

        output_path = (
            AD_DIR
            / "ad_card.png"
        )

    canvas.save(
        output_path,
        format="PNG",
    )

    return {
        "success": True,
        "status": guard["status"],
        "message": "تم إنشاء البطاقة الإعلانية.",
        "path": str(output_path),
        "image": canvas,
    }


# ----------------------------------------------------------------
# REEL
# ----------------------------------------------------------------

def generate_reel(
    title: str,
    prompt: str,
    brand: str = "Saeed PostGen",
    contact: str = "",
    filename: str | None = None,
    duration: int = 10,
) -> dict[str, Any]:
    """
    إنشاء مادة Reel عمودية.

    حاليًا يتم إنشاء صورة Reel جاهزة،
    ويمكن لاحقًا تحويلها إلى فيديو عبر FFmpeg.
    """

    guard = validate_generation_text(
        title,
        prompt,
        brand,
        contact,
    )

    if guard["status"] == "BLOCKED":

        return {
            "success": False,
            "status": "BLOCKED",
            "message": guard["message"],
            "path": "",
        }

    image_result = generate_image(
        prompt=prompt,
        width=REEL_SIZE[0],
        height=REEL_SIZE[1],
    )

    if not image_result["success"]:

        return image_result

    final_image = add_text_overlay(
        image_result["image"],
        title=title,
        brand=brand,
        contact=contact,
        size=REEL_SIZE,
    )

    if filename:

        output_path = (
            REEL_DIR / filename
        )

    else:

        output_path = (
            REEL_DIR
            / "reel_cover.png"
        )

    final_image.save(
        output_path,
        format="PNG",
    )

    return {
        "success": True,
        "status": guard["status"],
        "message": (
            "تم إنشاء تصميم Reel العمودي."
        ),
        "path": str(output_path),
        "image": final_image,
        "duration": duration,
    }


# ----------------------------------------------------------------
# VIDEO
# ----------------------------------------------------------------

def generate_video(
    image_path: str,
    output_path: str | None = None,
    duration: int = 10,
    fps: int = 30,
) -> dict[str, Any]:
    """
    تحويل صورة إلى فيديو MP4 باستخدام FFmpeg.

    يتطلب وجود ffmpeg في النظام.
    """

    image_file = Path(
        image_path
    )

    if not image_file.exists():

        return {
            "success": False,
            "status": "ERROR",
            "message": "الصورة غير موجودة.",
            "path": "",
        }

    if output_path is None:

        output_file = (
            VIDEO_DIR
            / "video.mp4"
        )

    else:

        output_file = Path(
            output_path
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    import shutil
    import subprocess

    ffmpeg = shutil.which(
        "ffmpeg"
    )

    if not ffmpeg:

        return {
            "success": False,
            "status": "ERROR",
            "message": (
                "FFmpeg غير مثبت."
            ),
            "path": "",
        }

    command = [
        ffmpeg,
        "-y",
        "-loop",
        "1",
        "-i",
        str(image_file),
        "-t",
        str(max(1, int(duration))),
        "-r",
        str(max(1, int(fps))),
        "-vf",
        (
            "scale=1080:1920:"
            "force_original_aspect_ratio=decrease,"
            "pad=1080:1920:"
            "(ow-iw)/2:"
            "(oh-ih)/2"
        ),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_file),
    ]

    try:

        subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        return {
            "success": True,
            "status": "APPROVED",
            "message": "تم إنشاء الفيديو.",
            "path": str(output_file),
        }

    except subprocess.CalledProcessError as exc:

        error_text = (
            exc.stderr.decode(
                "utf-8",
                errors="ignore",
            )
            if exc.stderr
            else "خطأ غير معروف."
        )

        return {
            "success": False,
            "status": "ERROR",
            "message": (
                f"تعذر إنشاء الفيديو: {error_text}"
            ),
            "path": "",
        }


# ----------------------------------------------------------------
# ENGINE REGISTRY
# ----------------------------------------------------------------

ENGINE_REGISTRY = {

    "image":
        generate_image,

    "post":
        generate_post,

    "ad_card":
        generate_ad_card,

    "reel":
        generate_reel,

    "video":
        generate_video,

}


def get_engine(
    engine_name: str,
):
    """
    الحصول على محرك حسب الاسم.
    """

    return ENGINE_REGISTRY.get(
        engine_name
          )
