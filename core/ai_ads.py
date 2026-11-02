from __future__ import annotations

import uuid
from pathlib import Path

from PIL import Image, ImageDraw

from core.engines import (
    generate_image,
    fit_image,
    get_font,
    draw_centered_text,
    clean_text,
    wrap_text,
    validate_generation_text,
    AD_DIR,
)


def generate_ai_ad(
    prompt: str,
    product_name: str = "",
    price: str = "",
    specifications: str = "",
    contact: str = "",
    brand: str = "SaeedMarketAds",
    template: str = "gold",
    width: int = 1080,
    height: int = 1350,
    filename: str | None = None,
):
    guard = validate_generation_text(
        prompt,
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
            "image": None,
        }

    if (width, height) not in (
        (1080, 1350),
        (1080, 1920),
        (1080, 1080),
    ):
        return {
            "success": False,
            "status": "ERROR",
            "message": "مقاس الإعلان غير مدعوم.",
            "path": "",
            "image": None,
        }

    background_name = f"ai_bg_{uuid.uuid4().hex}.png"

    visual_prompt = (
        f"{prompt}, "
        "professional premium advertising background, "
        "photorealistic commercial photography, "
        "no text, no letters, no watermark, "
        "leave clear space for Arabic typography"
    )

    result = generate_image(
        visual_prompt,
        width=width,
        height=height,
        filename=background_name,
    )

    if not result.get("success") or result.get("image") is None:
        return result

    background_path = Path(result["path"])

    try:
        canvas = fit_image(
            result["image"],
            (width, height),
        ).convert("RGBA")

        overlay = Image.new(
            "RGBA",
            canvas.size,
            (0, 0, 0, 0),
        )

        draw = ImageDraw.Draw(overlay)

        draw.rectangle(
            (0, int(height * 0.57), width, height),
            fill=(0, 0, 0, 165),
        )

        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)

        palettes = {
            "gold": (212, 175, 55),
            "blue": (40, 130, 220),
            "green": (40, 170, 100),
            "red": (210, 60, 60),
        }

        accent = palettes.get(template, palettes["gold"])

        draw_centered_text(
            draw,
            clean_text(brand),
            45,
            width,
            get_font(38, bold=True),
            accent,
        )

        title = product_name.strip() or "إعلان مميز"
        title_lines = wrap_text(title, 20).splitlines()

        y = int(height * 0.64)

        for line in title_lines[:3]:
            draw_centered_text(
                draw,
                clean_text(line),
                y,
                width,
                get_font(52, bold=True),
                (255, 255, 255),
            )
            y += 65

        if specifications:
            draw_centered_text(
                draw,
                clean_text(specifications[:100]),
                y + 5,
                width,
                get_font(28),
                (235, 235, 235),
            )

        if price:
            draw_centered_text(
                draw,
                clean_text(price),
                int(height * 0.83),
                width,
                get_font(55, bold=True),
                accent,
            )

        if contact:
            draw_centered_text(
                draw,
                clean_text(contact),
                int(height * 0.93),
                width,
                get_font(27, bold=True),
                (255, 255, 255),
            )

        output_name = filename or f"ai_ad_{uuid.uuid4().hex}.png"
        output_path = AD_DIR / output_name

        final_image = canvas.convert("RGB")
        final_image.save(output_path, format="PNG")

        return {
            "success": True,
            "status": guard["status"],
            "message": "تم إنشاء الإعلان الذكي.",
            "path": str(output_path),
            "image": final_image,
        }

    except Exception as exc:
        return {
            "success": False,
            "status": "ERROR",
            "message": f"تعذر تركيب الإعلان: {exc}",
            "path": "",
            "image": None,
        }

    finally:
        background_path.unlink(missing_ok=True)
