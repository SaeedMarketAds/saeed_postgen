# ================================================================
# Saeed PostGen Studio - Ultra Edition 4.5
# SaeedMarketAds | سوق سعيد
#
# النسخة المصححة:
# - فصل الصورة الخام عن الصورة المضاف عليها النص
# - دعم أفضل للعربية RTL
# - حماية أفضل للخطوط العربية
# - منع تكرار النص عند بناء بطاقة الإعلان
# - تحسين التفاف وتصغير النص
# - الحفاظ على Streamlit + Pollinations + Gemini + TTS
# ================================================================

import asyncio
import io
import os
import re
import tempfile
import urllib.parse

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont


# ================================================================
# 1. LIBRARIES / FALLBACKS
# ================================================================

try:
    from google import genai
    from google.genai import types

    GEMINI_AVAILABLE = True
except Exception:
    genai = None
    types = None
    GEMINI_AVAILABLE = False


try:
    import edge_tts

    EDGE_TTS_AVAILABLE = True
except Exception:
    edge_tts = None
    EDGE_TTS_AVAILABLE = False


try:
    from gtts import gTTS

    GTTS_AVAILABLE = True
except Exception:
    gTTS = None
    GTTS_AVAILABLE = False


try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    ARABIC_SUPPORT = True
except Exception:
    arabic_reshaper = None
    get_display = None
    ARABIC_SUPPORT = False


# ================================================================
# 2. CONFIG
# ================================================================

st.set_page_config(
    page_title="Saeed PostGen Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Saeed PostGen Studio"
BRAND_NAME = "SaeedMarketAds"
VERSION = "4.5 Ultra"

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

TARGET_VERTICAL = (1080, 1920)
TARGET_SQUARE = (1080, 1080)


# ================================================================
# 3. VOICES
# ================================================================

EDGE_VOICES = {
    "🇸🇦 حامد — سعودي": "ar-SA-HamedNeural",
    "🇸🇦 زارية — سعودية": "ar-SA-ZariyahNeural",
    "🇪🇬 شاكر — مصري": "ar-EG-ShakirNeural",
    "🇪🇬 سلمى — مصرية": "ar-EG-SalmaNeural",
    "🇦🇪 فاطمة — إماراتية": "ar-AE-FatimaNeural",
    "🇦🇪 حمد — إماراتي": "ar-AE-HamdanNeural",
    "🇰🇼 نواف — كويتي": "ar-KW-NouraNeural",
    "🇯🇴 سند — أردني": "ar-JO-TaimNeural",
}

GEMINI_VOICES = {
    "Kore — ثابت وقوي": "Kore",
    "Puck — حيوي": "Puck",
    "Charon — معلوماتي": "Charon",
    "Leda — شبابي": "Leda",
    "Aoede — هادئ": "Aoede",
    "Sulafat — دافئ": "Sulafat",
}


# ================================================================
# 4. TEMPLATES
# ================================================================

TEMPLATES = {
    "ذهبي فاخر": {
        "bg": (15, 23, 42),
        "accent": (251, 191, 36),
        "text": (255, 255, 255),
        "sub": (205, 205, 205),
    },
    "أزرق تقني": {
        "bg": (8, 20, 40),
        "accent": (56, 189, 248),
        "text": (255, 255, 255),
        "sub": (185, 205, 225),
    },
    "أخضر عصري": {
        "bg": (10, 30, 24),
        "accent": (52, 211, 153),
        "text": (255, 255, 255),
        "sub": (185, 220, 205),
    },
    "أحمر جريء": {
        "bg": (35, 12, 12),
        "accent": (248, 113, 113),
        "text": (255, 255, 255),
        "sub": (220, 190, 190),
    },
}


# ================================================================
# 5. SESSION STATE
# ================================================================

DEFAULT_MESSAGES = [
    {
        "role": "assistant",
        "content": (
            "أهلاً بك في **Saeed PostGen Studio** 🎬\n"
            "كيف أمكنني مساعدتك في خطتك التسويقية اليوم؟"
        ),
    }
]

SESSION_DEFAULTS = {
    "gallery": [],
    "last_ad_card": None,

    # الصورة التي عليها النص
    "last_generated_image": None,

    # الصورة الخام قبل أي كتابة
    "last_raw_image": None,

    "last_reel_video": None,
    "messages": DEFAULT_MESSAGES.copy(),
}

for key, default in SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ================================================================
# 6. CSS
# ================================================================

st.markdown(
    """
<style>

@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif;
}

.stApp {
    background:
        radial-gradient(
            circle at 70% 20%,
            rgba(180, 130, 255, 0.08),
            transparent 60%
        ),
        radial-gradient(
            circle at 30% 80%,
            rgba(251, 191, 36, 0.05),
            transparent 60%
        ),
        linear-gradient(
            145deg,
            #0b0f1a 0%,
            #141b2b 50%,
            #1a1030 100%
        );
}

.sma-header {
    padding: 25px;
    border-radius: 20px;
    background:
        linear-gradient(
            135deg,
            rgba(180, 130, 255, 0.15),
            rgba(15, 23, 42, 0.9)
        );
    border: 1px solid rgba(180, 130, 255, 0.25);
    margin-bottom: 20px;
    backdrop-filter: blur(5px);
}

.sma-title {
    font-size: 32px;
    font-weight: 800;
    background:
        linear-gradient(
            135deg,
            #fbbf24,
            #f59e0b
        );
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.sma-chat-user {
    padding: 14px 18px;
    border-radius: 16px 16px 2px 16px;
    background: rgba(180, 130, 255, 0.15);
    border: 1px solid rgba(180, 130, 255, 0.2);
    margin: 8px 0;
    color: #e2e8f0;
}

.sma-chat-ai {
    padding: 14px 18px;
    border-radius: 16px 16px 16px 2px;
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid rgba(255,255,255,0.08);
    margin: 8px 0;
    color: #f1f5f9;
}

div.stButton > button {
    border-radius: 12px;
    font-weight: 700;
    min-height: 46px;
    background:
        linear-gradient(
            135deg,
            #fbbf24,
            #f59e0b
        );
    color: #0b0f1a;
    border: none;
}

.sma-info {
    padding: 12px 16px;
    border-radius: 12px;
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.07);
    margin: 10px 0;
}

</style>
""",
    unsafe_allow_html=True,
)


# ================================================================
# 7. CORE UTILITIES
# ================================================================

def get_secret(*names):
    for name in names:
        try:
            value = st.secrets.get(name)
        except Exception:
            value = None

        if value:
            return str(value).strip()

        value = os.getenv(name)

        if value:
            return str(value).strip()

    return ""


def clean_text(text):
    if not text:
        return ""

    text = re.sub(
        r"```(?:text|markdown|python)?",
        "",
        str(text),
        flags=re.IGNORECASE,
    )

    text = text.replace("```", "")

    return text.strip()


def arabic_text(text):
    """
    تجهيز العربية للعرض الصحيح داخل Pillow.
    """
    if not text:
        return ""

    text = str(text)

    if ARABIC_SUPPORT:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            pass

    return text


def prepare_tts_text(text):
    if not text:
        return ""

    text = re.sub(
        r'[^ء-ي\s0-9،.؟!;:()\-"]',
        " ",
        str(text),
    )

    return re.sub(r"\s+", " ", text).strip()


# ================================================================
# 8. ARABIC FONT SYSTEM
# ================================================================

@st.cache_resource
def find_arabic_font_path():
    """
    البحث عن خط عربي حقيقي.
    لا نعتمد على ImageFont.load_default()
    للنصوص العربية.
    """

    candidates = [
        "fonts/Cairo-Bold.ttf",
        "fonts/Cairo-Regular.ttf",

        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in candidates:
        if os.path.isfile(path):
            return path

    return None


def get_font(size=40, bold=True):
    """
    تحميل خط مناسب.
    """

    preferred = [
        "fonts/Cairo-Bold.ttf" if bold else "fonts/Cairo-Regular.ttf",

        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",

        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",

        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    for path in preferred:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue

    # آخر حل فقط
    return ImageFont.load_default()


# ================================================================
# 9. TEXT FITTING
# ================================================================

def text_width(draw, text, font):
    rendered = arabic_text(text)

    bbox = draw.textbbox(
        (0, 0),
        rendered,
        font=font,
    )

    return bbox[2] - bbox[0]


def fit_font_to_width(
    draw,
    text,
    base_font_size,
    max_width,
    bold=True,
    min_size=16,
):
    if not text:
        return get_font(base_font_size, bold)

    size = int(base_font_size)

    while size >= min_size:
        font = get_font(size, bold)

        if text_width(draw, text, font) <= max_width:
            return font

        size -= 2

    return get_font(min_size, bold)


def wrap_text_to_width(draw, text, font, max_width):
    """
    التفاف عربي/إنجليزي بدون قص.
    """

    if not text:
        return []

    words = str(text).split()

    if not words:
        return []

    lines = []
    current = ""

    for word in words:

        candidate = (
            f"{current} {word}".strip()
            if current
            else word
        )

        if text_width(draw, candidate, font) <= max_width:
            current = candidate
        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines


# ================================================================
# 10. DRAW TEXT
# ================================================================

def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill,
    width,
    shadow=True,
):
    if not text:
        return

    rendered = arabic_text(text)

    bbox = draw.textbbox(
        (0, 0),
        rendered,
        font=font,
    )

    tw = bbox[2] - bbox[0]

    x = int((width - tw) / 2)

    if shadow:
        draw.text(
            (x + 3, y + 3),
            rendered,
            font=font,
            fill=(0, 0, 0),
        )

    draw.text(
        (x, y),
        rendered,
        font=font,
        fill=fill,
    )


def draw_wrapped_centered_text(
    draw,
    text,
    y,
    font,
    fill,
    width,
    max_width,
    line_spacing=10,
    shadow=True,
):
    if not text:
        return 0

    lines = wrap_text_to_width(
        draw,
        text,
        font,
        max_width,
    )

    if not lines:
        return 0

    sample_bbox = draw.textbbox(
        (0, 0),
        arabic_text("أب"),
        font=font,
    )

    line_height = (
        sample_bbox[3] - sample_bbox[1]
    ) + line_spacing

    current_y = y

    for line in lines:
        draw_centered_text(
            draw,
            line,
            current_y,
            font,
            fill,
            width,
            shadow=shadow,
        )

        current_y += line_height

    return current_y - y


# ================================================================
# 11. GEMINI
# ================================================================

@st.cache_resource
def get_gemini_client():
    key = get_secret(
        "GEMINI_API_KEY",
        "GEMINI_MAIN_KEY",
    )

    if GEMINI_AVAILABLE and key:
        return genai.Client(api_key=key)

    return None


def gemini_generate_text(
    prompt,
    model=DEFAULT_GEMINI_MODEL,
):
    client = get_gemini_client()

    if not client:
        raise RuntimeError(
            "مفتاح GEMINI_API_KEY غير متاح "
            "أو مكتبة google-genai غير مثبتة."
        )

    system_instruction = (
        "أنت Saeed AI، المساعد الذكي الخاص "
        "بمنصة SaeedMarketAds للتسويق الرقمي "
        "وإدارة المحتوى."
    )

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
        ),
    )

    return clean_text(
        getattr(response, "text", "")
    )


# ================================================================
# 12. POLLINATIONS IMAGE
# ================================================================

def generate_pollinations_image(
    prompt,
    width=1024,
    height=1024,
):
    if not prompt:
        raise ValueError("وصف الصورة فارغ.")

    enhanced = (
        "Commercial product photography, "
        "professional studio setup, "
        "ultra detailed, high quality, "
        "clean commercial composition, "
        f"{prompt}"
    )

    encoded_prompt = urllib.parse.quote(
        enhanced
    )

    url = (
        f"{POLLINATIONS_BASE}"
        f"{encoded_prompt}"
        f"?width={width}"
        f"&height={height}"
        f"&nologo=true"
    )

    response = requests.get(
        url,
        timeout=90,
        headers={
            "User-Agent": "SaeedMarketAds/4.5"
        },
    )

    response.raise_for_status()

    image = Image.open(
        io.BytesIO(response.content)
    ).convert("RGB")

    return image, url


# ================================================================
# 13. IMAGE FIT
# ================================================================

def fit_image_to_canvas(image, size):
    if image is None:
        return None

    image = image.convert("RGB")

    target_w, target_h = size
    source_w, source_h = image.size

    scale = max(
        target_w / source_w,
        target_h / source_h,
    )

    new_w = int(source_w * scale)
    new_h = int(source_h * scale)

    image = image.resize(
        (new_w, new_h),
        Image.Resampling.LANCZOS,
    )

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


# ================================================================
# 14. TEXT OVERLAY
# ================================================================

def add_text_overlay(
    image,
    title="",
    brand=BRAND_NAME,
    contact="",
):
    """
    إضافة النصوص إلى نسخة من الصورة الخام.

    مهم:
    لا نعدل الصورة الأصلية.
    """

    if image is None:
        return None

    img_with_text = image.copy().convert("RGB")

    draw = ImageDraw.Draw(
        img_with_text
    )

    width, height = img_with_text.size

    content_width = int(
        width * 0.88
    )

    # ------------------------------------------------------------
    # Brand
    # ------------------------------------------------------------

    if brand:
        brand_font = fit_font_to_width(
            draw,
            brand,
            max(24, int(height * 0.045)),
            content_width,
            bold=True,
            min_size=18,
        )

        draw_centered_text(
            draw,
            brand,
            int(height * 0.045),
            brand_font,
            (255, 255, 255),
            width,
            shadow=True,
        )

    # ------------------------------------------------------------
    # Title
    # ------------------------------------------------------------

    if title:
        title_font = fit_font_to_width(
            draw,
            title,
            max(24, int(height * 0.055)),
            content_width,
            bold=True,
            min_size=18,
        )

        # صندوق شبه شفاف خلف العنوان
        overlay = Image.new(
            "RGBA",
            img_with_text.size,
            (0, 0, 0, 0),
        )

        overlay_draw = ImageDraw.Draw(
            overlay
        )

        title_y = int(
            height * 0.72
        )

        title_height = max(
            100,
            int(height * 0.16),
        )

        overlay_draw.rounded_rectangle(
            (
                int(width * 0.04),
                title_y - 20,
                int(width * 0.96),
                min(
                    height - 20,
                    title_y + title_height,
                ),
            ),
            radius=30,
            fill=(0, 0, 0, 150),
        )

        img_with_text = Image.alpha_composite(
            img_with_text.convert("RGBA"),
            overlay,
        ).convert("RGB")

        draw = ImageDraw.Draw(
            img_with_text
        )

        draw_wrapped_centered_text(
            draw,
            title,
            title_y,
            title_font,
            (255, 215, 0),
            width,
            content_width,
            line_spacing=8,
            shadow=True,
        )

    # ------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------

    if contact:
        contact_font = fit_font_to_width(
            draw,
            contact,
            max(20, int(height * 0.035)),
            content_width,
            bold=True,
            min_size=16,
        )

        draw_centered_text(
            draw,
            contact,
            int(height * 0.90),
            contact_font,
            (255, 255, 255),
            width,
            shadow=True,
        )

    return img_with_text


# ================================================================
# 15. AD CARD
# ================================================================

def build_ad_card(
    product_name,
    storage,
    ram,
    price,
    contact,
    template_name,
    product_image=None,
):
    """
    بناء بطاقة الإعلان النهائية.

    product_image هنا يجب أن تكون الصورة الخام،
    وليس صورة سبق أن أضيف عليها نص.
    """

    if template_name not in TEMPLATES:
        template_name = "ذهبي فاخر"

    tmpl = TEMPLATES[
        template_name
    ]

    W, H = TARGET_SQUARE

    canvas = Image.new(
        "RGB",
        (W, H),
        tmpl["bg"],
    )

    draw = ImageDraw.Draw(canvas)

    content_width = W - 140

    # ============================================================
    # HEADER
    # ============================================================

    draw.rounded_rectangle(
        (50, 40, W - 50, 140),
        radius=20,
        fill=tmpl["accent"],
    )

    header_text = (
        "SaeedMarketAds • العرض الذهبي"
    )

    header_font = fit_font_to_width(
        draw,
        header_text,
        38,
        W - 120,
        bold=True,
        min_size=20,
    )

    draw_centered_text(
        draw,
        header_text,
        65,
        header_font,
        tmpl["bg"],
        W,
        shadow=False,
    )

    # ============================================================
    # PRODUCT IMAGE
    # ============================================================

    img_box = (
        90,
        170,
        W - 90,
        600,
    )

    if product_image is not None:

        fit_img = fit_image_to_canvas(
            product_image,
            (
                img_box[2] - img_box[0],
                img_box[3] - img_box[1],
            ),
        )

        canvas.paste(
            fit_img,
            (
                img_box[0],
                img_box[1],
            ),
        )

    else:

        draw.rounded_rectangle(
            img_box,
            radius=25,
            outline=tmpl["accent"],
            width=3,
        )

        placeholder = "PRODUCT"

        placeholder_font = get_font(
            42,
            True,
        )

        draw_centered_text(
            draw,
            placeholder,
            350,
            placeholder_font,
            tmpl["accent"],
            W,
            shadow=False,
        )

    # ============================================================
    # PRODUCT NAME
    # ============================================================

    if product_name:

        name_font = fit_font_to_width(
            draw,
            product_name,
            54,
            content_width,
            bold=True,
            min_size=24,
        )

        draw_wrapped_centered_text(
            draw,
            product_name,
            640,
            name_font,
            tmpl["text"],
            W,
            content_width,
            line_spacing=8,
            shadow=True,
        )

    # ============================================================
    # SPECS
    # ============================================================

    specs_parts = []

    if storage:
        specs_parts.append(
            f"التخزين: {storage}"
        )

    if ram:
        specs_parts.append(
            f"الرام: {ram}"
        )

    specs = "  |  ".join(
        specs_parts
    )

    if specs:

        specs_font = fit_font_to_width(
            draw,
            specs,
            30,
            content_width,
            bold=False,
            min_size=18,
        )

        draw_centered_text(
            draw,
            specs,
            720,
            specs_font,
            tmpl["sub"],
            W,
            shadow=False,
        )

    # ============================================================
    # PRICE
    # ============================================================

    draw.rounded_rectangle(
        (200, 790, W - 200, 920),
        radius=25,
        fill=tmpl["accent"],
    )

    price_text = (
        f"{price} ريال"
        if price
        else "السعر عند الطلب"
    )

    price_font = fit_font_to_width(
        draw,
        price_text,
        50,
        W - 440,
        bold=True,
        min_size=22,
    )

    draw_centered_text(
        draw,
        price_text,
        825,
        price_font,
        tmpl["bg"],
        W,
        shadow=False,
    )

    # ============================================================
    # CONTACT
    # ============================================================

    if contact:

        contact_text = (
            f"للتواصل والطلب: {contact}"
        )

        contact_font = fit_font_to_width(
            draw,
            contact_text,
            32,
            content_width,
            bold=True,
            min_size=18,
        )

        draw_centered_text(
            draw,
            contact_text,
            970,
            contact_font,
            tmpl["text"],
            W,
            shadow=True,
        )

    # ============================================================
    # FOOTER
    # ============================================================

    footer = (
        "سوق سعيد • دليلك الذكي للتسويق الرقمي"
    )

    footer_font = fit_font_to_width(
        draw,
        footer,
        24,
        content_width,
        bold=False,
        min_size=16,
    )

    draw_centered_text(
        draw,
        footer,
        1020,
        footer_font,
        tmpl["sub"],
        W,
        shadow=False,
    )

    return canvas


# ================================================================
# 16. TTS
# ================================================================

def run_async(coro):
    try:
        return asyncio.run(coro)

    except RuntimeError:
        loop = asyncio.new_event_loop()

        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


async def _edge_tts_process(
    text,
    voice,
    out_path,
    rate="+0%",
    pitch="+0Hz",
):
    communicator = edge_tts.Communicate(
        prepare_tts_text(text),
        voice,
        rate=rate,
        pitch=pitch,
    )

    await communicator.save(
        out_path
    )


def generate_voice(
    text,
    engine,
    voice,
    rate="+0%",
    pitch="+0Hz",
):
    extension = (
        ".wav"
        if engine == "Gemini TTS"
        else ".mp3"
    )

    fd, out_path = tempfile.mkstemp(
        suffix=extension
    )

    os.close(fd)

    if (
        engine == "Edge TTS"
        and EDGE_TTS_AVAILABLE
    ):
        run_async(
            _edge_tts_process(
                text,
                voice,
                out_path,
                rate,
                pitch,
            )
        )

        return out_path, "Edge TTS"

    if GTTS_AVAILABLE:

        tts = gTTS(
            text=prepare_tts_text(text),
            lang="ar",
            slow=False,
        )

        tts.save(out_path)

        return out_path, "gTTS"

    raise RuntimeError(
        "تعذر معالجة النص الصوتي."
    )


# ================================================================
# 17. SIDEBAR
# ================================================================

with st.sidebar:

    st.markdown(
        """
        <h2 style='text-align:center; color:#fbbf24;'>
            Saeed Studio
        </h2>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        f"الإصدار: {VERSION}"
    )

    st.divider()

    if st.button(
        "🗑️ مسح الذاكرة المؤقتة",
        use_container_width=True,
    ):
        st.session_state.gallery = []
        st.session_state.last_generated_image = None
        st.session_state.last_raw_image = None
        st.session_state.last_ad_card = None
        st.rerun()

    st.divider()

    st.markdown(
        """
        <div class="sma-info">
        <b>نظام الصور:</b><br>
        الصورة الخام منفصلة عن الصورة التي تحتوي على النص.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ================================================================
# 18. HEADER
# ================================================================

st.markdown(
    """
    <div class="sma-header">

        <div class="sma-title">
            🎬 Saeed PostGen Studio
        </div>

        <div style="color:#cbd5e1;">
            الاستوديو الذكي المتكامل لإدارة وإنشاء المحتوى التسويقي
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ================================================================
# 19. TABS
# ================================================================

tab_ai, tab_image, tab_ad, tab_gallery = st.tabs(
    [
        "💬 الذكاء الاصطناعي",
        "🎨 توليد الصور",
        "📱 بطاقة الإعلان",
        "🖼️ المعرض",
    ]
)


# ================================================================
# 20. TAB 1 — AI
# ================================================================

with tab_ai:

    for msg in st.session_state.messages:

        css_class = (
            "sma-chat-user"
            if msg["role"] == "user"
            else "sma-chat-ai"
        )

        name = (
            "أنت"
            if msg["role"] == "user"
            else "🤖 Saeed AI"
        )

        content = (
            str(msg["content"])
            .replace("\n", "<br>")
        )

        st.markdown(
            f"""
            <div class="{css_class}">
                <b>{name}</b><br>
                {content}
            </div>
            """,
            unsafe_allow_html=True,
        )

    user_input = st.chat_input(
        "اكتب أفكارك التسويقية هنا..."
    )

    if user_input:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        try:

            bot_response = gemini_generate_text(
                user_input
            )

        except Exception as error:

            bot_response = (
                "⚠️ خطأ أثناء المعالجة: "
                f"{error}"
            )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": bot_response,
            }
        )

        st.rerun()


# ================================================================
# 21. TAB 2 — IMAGE GENERATOR
# ================================================================

with tab_image:

    st.subheader(
        "🎨 مولد الصور التسويقية"
    )

    prompt_in = st.text_area(
        "وصف الصورة التسويقية المطلوبة:",
        placeholder=(
            "هاتف أبل آيفون باللون البرتقالي "
            "على خلفية سوداء فاخرة، "
            "إضاءة استوديو احترافية..."
        ),
        height=120,
    )

    col_a, col_b = st.columns(2)

    with col_a:

        ad_title = st.text_input(
            "نص الإعلان على الصورة",
            "",
            placeholder="مثال: خصم 30% لفترة محدودة",
        )

    with col_b:

        ad_contact = st.text_input(
            "رقم التواصل على الصورة",
            "",
            placeholder="مثال: 967770000000",
        )

    if st.button(
        "✨ إنتاج الصورة الآن",
        type="primary",
        use_container_width=True,
    ):

        if not prompt_in.strip():

            st.warning(
                "الرجاء إدخال وصف الصورة أولاً."
            )

        else:

            with st.spinner(
                "جاري إنشاء الصورة..."
            ):

                try:

                    # ------------------------------------------------
                    # STEP 1
                    # توليد الصورة الخام
                    # ------------------------------------------------

                    raw_image, image_url = (
                        generate_pollinations_image(
                            prompt_in
                        )
                    )

                    # ------------------------------------------------
                    # STEP 2
                    # حفظ الصورة الخام منفصلة
                    # ------------------------------------------------

                    st.session_state.last_raw_image = (
                        raw_image
                    )

                    # ------------------------------------------------
                    # STEP 3
                    # إضافة النص
                    # ------------------------------------------------

                    final_image = add_text_overlay(
                        raw_image,
                        title=ad_title,
                        brand=BRAND_NAME,
                        contact=ad_contact,
                    )

                    # ------------------------------------------------
                    # STEP 4
                    # حفظ الصورة النهائية
                    # ------------------------------------------------

                    st.session_state.last_generated_image = (
                        final_image
                    )

                    # ------------------------------------------------
                    # STEP 5
                    # المعرض
                    # ------------------------------------------------

                    st.session_state.gallery.append(
                        {
                            "title": "صورة مولدة",
                            "image": final_image,
                        }
                    )

                    st.success(
                        "✅ تم إنشاء الصورة وتركيب النص بنجاح."
                    )

                    st.image(
                        final_image,
                        caption=(
                            "الصورة النهائية "
                            "بعد تركيب النص"
                        ),
                        use_container_width=True,
                    )

                    st.caption(
                        "الصورة الخام محفوظة داخليًا "
                        "لاستخدامها في بطاقة الإعلان."
                    )

                except Exception as error:

                    st.error(
                        "⚠️ تعذر توليد الصورة: "
                        f"{error}"
                    )


# ================================================================
# 22. TAB 3 — AD CARD
# ================================================================

with tab_ad:

    st.subheader(
        "📱 إنشاء بطاقة الإعلان"
    )

    col1, col2 = st.columns(2)

    with col1:

        p_name = st.text_input(
            "اسم المنتج",
            "iPhone 17 Pro Max",
        )

        p_storage = st.text_input(
            "المساحة",
            "512GB",
        )

        p_ram = st.text_input(
            "الرام",
            "16GB",
        )

    with col2:

        p_price = st.text_input(
            "السعر",
            "4800",
        )

        p_contact = st.text_input(
            "رقم التواصل",
            "967770000000",
        )

        p_tmpl = st.selectbox(
            "القالب التصميمي",
            list(TEMPLATES.keys()),
        )

    st.divider()

    use_ai_img = st.checkbox(
        "استخدام الصورة الخام المولدة بالذكاء الاصطناعي",
        value=bool(
            st.session_state.last_raw_image
        ),
    )

    p_img_file = st.file_uploader(
        "رفع صورة المنتج (اختياري)",
        type=[
            "png",
            "jpg",
            "jpeg",
            "webp",
        ],
    )

    # ============================================================
    # IMPORTANT:
    # هنا نستخدم الصورة الخام فقط.
    # ============================================================

    p_img = None

    if (
        use_ai_img
        and st.session_state.last_raw_image
        is not None
    ):

        p_img = (
            st.session_state.last_raw_image
        )

        st.success(
            "🖼️ سيتم استخدام الصورة الخام "
            "بدون النص السابق."
        )

    elif p_img_file:

        try:

            p_img = Image.open(
                p_img_file
            ).convert("RGB")

        except Exception as error:

            st.error(
                "⚠️ تعذر قراءة الصورة: "
                f"{error}"
            )

    if st.button(
        "🚀 صمم البطاقة",
        type="primary",
        use_container_width=True,
    ):

        try:

            card = build_ad_card(
                product_name=p_name,
                storage=p_storage,
                ram=p_ram,
                price=p_price,
                contact=p_contact,
                template_name=p_tmpl,
                product_image=p_img,
            )

            st.session_state.last_ad_card = card

            st.session_state.gallery.append(
                {
                    "title": (
                        f"إعلان - {p_name}"
                    ),
                    "image": card,
                }
            )

            st.success(
                "✅ تم إنشاء بطاقة الإعلان."
            )

            st.image(
                card,
                caption="بطاقة الإعلان النهائية",
                use_container_width=True,
            )

        except Exception as error:

            st.error(
                "⚠️ تعذر إنشاء البطاقة: "
                f"{error}"
            )


# ================================================================
# 23. TAB 4 — GALLERY
# ================================================================

with tab_gallery:

    st.subheader(
        "🖼️ معرض التصاميم"
    )

    if not st.session_state.gallery:

        st.info(
            "المعرض فارغ حالياً."
        )

    else:

        cols = st.columns(3)

        for index, item in enumerate(
            reversed(
                st.session_state.gallery
            )
        ):

            with cols[index % 3]:

                st.image(
                    item["image"],
                    caption=item["title"],
                    use_container_width=True,
                )


# ================================================================
# 24. DEBUG / STATUS
# ================================================================

with st.expander(
    "🔧 حالة النظام",
    expanded=False,
):

    col1, col2, col3 = st.columns(3)

    with col1:

        st.write(
            "Gemini:",
            "✅ متاح"
            if GEMINI_AVAILABLE
            else "❌ غير متاح",
        )

    with col2:

        st.write(
            "Edge TTS:",
            "✅ متاح"
            if EDGE_TTS_AVAILABLE
            else "❌ غير متاح",
        )

    with col3:

        st.write(
            "Arabic RTL:",
            "✅ متاح"
            if ARABIC_SUPPORT
            else "⚠️ غير متاح",
        )

    font_path = find_arabic_font_path()

    if font_path:

        st.success(
            f"الخط المستخدم: {font_path}"
        )

    else:

        st.warning(
            "⚠️ لم يتم العثور على خط عربي "
            "مخصص؛ سيتم استخدام الخط الاحتياطي."
        )

    st.write(
        "الصورة الخام محفوظة:",
        st.session_state.last_raw_image is not None,
    )

    st.write(
        "الصورة النهائية محفوظة:",
        st.session_state.last_generated_image is not None,
    )

    st.write(
        "بطاقة الإعلان محفوظة:",
        st.session_state.last_ad_card is not None,
    )
