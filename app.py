# ================================================================
# Saeed PostGen Studio
# SaeedMarketAds | سوق سعيد
# ================================================================
# تطبيق Streamlit موحد ونظيف
#
# الأقسام:
#   1) Saeed AI
#   2) مولد الصور
#   3) بطاقة الإعلان
#   4) صانع الريلز
#   5) المعرض
# ================================================================

import asyncio
import base64
import io
import os
import re
import tempfile
import urllib.parse
import wave
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter


# ================================================================
# OPTIONAL LIBRARIES
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

# MoviePy compatibility
MOVIEPY_AVAILABLE = False
try:
    from moviepy.editor import (
        AudioFileClip,
        CompositeAudioClip,
        CompositeVideoClip,
        ImageClip,
        VideoFileClip,
        concatenate_videoclips,
    )
    MOVIEPY_AVAILABLE = True
except Exception:
    try:
        from moviepy import (
            AudioFileClip,
            CompositeAudioClip,
            CompositeVideoClip,
            ImageClip,
            VideoFileClip,
            concatenate_videoclips,
        )
        MOVIEPY_AVAILABLE = True
    except Exception:
        MOVIEPY_AVAILABLE = False


# ================================================================
# PAGE CONFIG
# ================================================================

st.set_page_config(
    page_title="Saeed PostGen Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ================================================================
# CONSTANTS
# ================================================================

APP_NAME = "Saeed PostGen Studio"
BRAND_NAME = "SaeedMarketAds"
VERSION = "4.2"

# تم التحديث إلى gemini-2.5-flash لضمان الاستقرار وعدم حدوث 503
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

TARGET_VERTICAL = (1080, 1920)
TARGET_SQUARE = (1080, 1080)


# ================================================================
# VOICES
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
    "Achernar — ناعم": "Achernar",
    "Alnilam — رسمي": "Alnilam",
    "Gacrux — ناضج": "Gacrux",
    "Sulafat — دافئ": "Sulafat",
    "Achird — ودود": "Achird",
}


# ================================================================
# AD TEMPLATES
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
# SESSION STATE
# ================================================================

if "gallery" not in st.session_state:
    st.session_state.gallery = []

if "last_ad_card" not in st.session_state:
    st.session_state.last_ad_card = None

if "last_generated_image" not in st.session_state:
    st.session_state.last_generated_image = None

if "last_reel_video" not in st.session_state:
    st.session_state.last_reel_video = None

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "أهلاً بك في **Saeed PostGen Studio** 🎬\n\n"
                "أنا Saeed AI، أساعدك في كتابة الإعلان، "
                "تجهيز النص، وصناعة المحتوى التسويقي."
            ),
        }
    ]


# ================================================================
# CSS
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
        radial-gradient(circle at 70% 20%, rgba(180, 130, 255, 0.08), transparent 60%),
        radial-gradient(circle at 30% 80%, rgba(251, 191, 36, 0.05), transparent 60%),
        linear-gradient(145deg, #0b0f1a 0%, #141b2b 50%, #1a1030 100%);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b0f1a 0%, #161d2f 100%);
    border-right: 1px solid rgba(180, 130, 255, 0.25);
}

.sma-header {
    padding: 30px;
    border-radius: 28px;
    background: linear-gradient(135deg, rgba(180, 130, 255, 0.15), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(180, 130, 255, 0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    margin-bottom: 25px;
    backdrop-filter: blur(4px);
}

.sma-logo { font-size: 48px; }
.sma-title {
    font-size: 34px;
    font-weight: 800;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
.sma-subtitle { color: #cbd5e1; font-size: 16px; letter-spacing: 0.5px; }

div.stButton > button {
    border-radius: 14px;
    font-weight: 700;
    min-height: 48px;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    color: #0b0f1a;
    border: none;
    transition: 0.3s;
    box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
}

div.stButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 20px rgba(251, 191, 36, 0.5);
}

div.stDownloadButton > button {
    border-radius: 14px;
    font-weight: 700;
    background: linear-gradient(135deg, #8b5cf6, #6d28d9);
    color: white;
    border: none;
    transition: 0.3s;
}

div.stDownloadButton > button:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}
</style>
""",
    unsafe_allow_html=True,
)


# ================================================================
# HELPERS
# ================================================================

def get_secret(*names):
    for name in names:
        try:
            value = st.secrets.get(name)
            if value:
                return str(value).strip()
        except Exception:
            pass
        value = os.getenv(name)
        if value:
            return value.strip()
    return ""


def get_gemini_key():
    return get_secret("GEMINI_API_KEY", "GEMINI_MAIN_KEY")


def clean_text(text):
    if not text:
        return ""
    text = str(text)
    text = re.sub(r"```(?:text|markdown|python)?", "", text, flags=re.IGNORECASE)
    text = text.replace("```", "")
    return text.strip()


def arabic_text(text):
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
    text = re.sub(r'[^ء-ي\s0-9،.؟!;:()\-"]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ================================================================
# FONTS
# ================================================================

FONT_BOLD_PATHS = [
    "fonts/Cairo-Bold.ttf",
    "fonts/Tajawal-Bold.ttf",
    "fonts/Amiri-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
]

FONT_REGULAR_PATHS = [
    "fonts/Cairo-Regular.ttf",
    "fonts/Tajawal-Regular.ttf",
    "fonts/Amiri-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
]


def get_font(size=40, bold=True):
    paths = FONT_BOLD_PATHS if bold else FONT_REGULAR_PATHS
    for path in paths:
        try:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ================================================================
# IMAGE HELPERS
# ================================================================

def fit_image_to_canvas(image, size, mode="contain", bg_color=(15, 23, 42)):
    """
    تعديل دالة الاحتواء لتضمن ظهور الهاتف بالكامل دون اقتصاص (Contain).
    """
    image = image.convert("RGB")
    target_w, target_h = size
    src_w, src_h = image.size

    if mode == "cover":
        scale = max(target_w / src_w, target_h / src_h)
        new_size = (int(src_w * scale), int(src_h * scale))
        image = image.resize(new_size, Image.Resampling.LANCZOS)
        left = max(0, (image.width - target_w) // 2)
        top = max(0, (image.height - target_h) // 2)
        return image.crop((left, top, left + target_w, top + target_h))
    else:
        # Contain Mode - إظهار كامل الجهاز بنفس الأبعاد بمنتصف المساحة
        scale = min(target_w / src_w, target_h / src_h)
        new_w, new_h = int(src_w * scale), int(src_h * scale)
        resized_img = image.resize((new_w, new_h), Image.Resampling.LANCZOS)

        canvas = Image.new("RGB", (target_w, target_h), bg_color)
        paste_x = (target_w - new_w) // 2
        paste_y = (target_h - new_h) // 2
        canvas.paste(resized_img, (paste_x, paste_y))
        return canvas


def wrap_text(draw, text, font, max_width):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        test = word if not current else current + " " + word
        bbox = draw.textbbox((0, 0), arabic_text(test), font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_centered_text(draw, text, y, font, fill, canvas_width):
    rendered = arabic_text(text)
    bbox = draw.textbbox((0, 0), rendered, font=font)
    width = bbox[2] - bbox[0]
    x = (canvas_width - width) // 2
    draw.text((x, y), rendered, font=font, fill=fill)


def add_caption_band(image, caption, position="bottom"):
    image = image.convert("RGBA")
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = get_font(46, True)

    max_width = image.width - 100
    lines = wrap_text(draw, caption, font, max_width)[:3]

    line_height = 65
    padding = 25
    band_height = len(lines) * line_height + padding * 2
    y0 = 0 if position == "top" else image.height - band_height

    draw.rectangle((0, y0, image.width, y0 + band_height), fill=(0, 0, 0, 170))

    y = y0 + padding
    for line in lines:
        rendered = arabic_text(line)
        bbox = draw.textbbox((0, 0), rendered, font=font)
        tw = bbox[2] - bbox[0]
        x = (image.width - tw) // 2
        draw.text((x, y), rendered, font=font, fill=(255, 255, 255, 255))
        y += line_height

    return Image.alpha_composite(image, overlay).convert("RGB")


# ================================================================
# POLLINATIONS
# ================================================================

def build_pollinations_url(prompt, width=1024, height=1024):
    encoded = urllib.parse.quote(prompt, safe="")
    return f"{POLLINATIONS_BASE}{encoded}?width={width}&height={height}&nologo=true"


def generate_pollinations_image(prompt, width=1024, height=1024):
    enhanced_prompt = (
        "Full phone visible, center frame, professional commercial product photography, "
        "studio lighting, detailed back design, no cropped body, high resolution, " + prompt
    )
    url = build_pollinations_url(enhanced_prompt, width, height)
    response = requests.get(url, timeout=120, headers={"User-Agent": "SaeedMarketAds/4.2"})
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert("RGB")
    return image, url


# ================================================================
# GALLERY
# ================================================================

def add_to_gallery(image, title="تصميم Saeed"):
    if image is None:
        return
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    st.session_state.gallery.append({"title": title, "data": buffer.getvalue()})
    if len(st.session_state.gallery) > 30:
        st.session_state.gallery = st.session_state.gallery[-30:]


def bytes_to_image(data):
    return Image.open(io.BytesIO(data)).convert("RGB")


# ================================================================
# GEMINI TEXT
# ================================================================

@st.cache_resource
def get_gemini_client(api_key):
    if not GEMINI_AVAILABLE or not api_key:
        return None
    return genai.Client(api_key=api_key)


def gemini_generate_text(prompt, model=DEFAULT_GEMINI_MODEL):
    api_key = get_gemini_key()
    if not api_key:
        raise RuntimeError("لم يتم العثور على GEMINI_API_KEY.")

    client = get_gemini_client(api_key)
    if client is None:
        raise RuntimeError("مكتبة google-genai غير مثبتة.")

    system_instruction = """
أنت Saeed AI داخل منصة SaeedMarketAds.
دورك:
- مساعد تسويقي ذكي ومستشار إعلانات.
- اكتب إعلانات احترافية متوافقة مع السوق اليمني والخليجي والعربي.
- اجعل النصوص واضحة، جذابة ومباشرة.
"""
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.7,
            max_output_tokens=1800,
        ),
    )

    text = getattr(response, "text", None)
    if not text:
        raise RuntimeError("Gemini لم يرجع نصاً.")
    return clean_text(text)


# ================================================================
# AD CARD BUILDER
# ================================================================

def build_ad_card(product_name, storage, ram, price, contact, template_name, product_image=None):
    template = TEMPLATES[template_name]
    W, H = TARGET_SQUARE

    canvas = Image.new("RGB", (W, H), template["bg"])
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((-200, -200, 500, 500), fill=(*template["accent"], 45))
    glow = glow.filter(ImageFilter.GaussianBlur(60))

    canvas = Image.alpha_composite(canvas.convert("RGBA"), glow).convert("RGB")
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((50, 40, W - 50, 150), radius=28, fill=template["accent"])
    header_font = get_font(42, True)
    draw_centered_text(draw, "SaeedMarketAds • عرض حصري", 70, header_font, template["bg"], W)

    image_area = (90, 190, W - 90, 620)
    box_w = image_area[2] - image_area[0]
    box_h = image_area[3] - image_area[1]

    if product_image is not None:
        try:
            # ضمان احتواء الصورة بالكامل داخل الإطار بدون قص الجهاز
            product = fit_image_to_canvas(product_image, (box_w, box_h), mode="contain", bg_color=template["bg"])
            canvas.paste(product, (image_area[0], image_area[1]))
        except Exception:
            pass
    else:
        draw.rounded_rectangle(image_area, radius=35, outline=template["accent"], width=3)
        emoji_font = get_font(100, True)
        draw_centered_text(draw, "📱", 330, emoji_font, template["accent"], W)

    title_font = get_font(56, True)
    draw_centered_text(draw, product_name, 665, title_font, template["text"], W)

    spec_font = get_font(32, False)
    specs = []
    if storage: specs.append(f"التخزين: {storage}")
    if ram: specs.append(f"الرام: {ram}")
    spec_text = "  •  ".join(specs)

    if spec_text:
        draw_centered_text(draw, spec_text, 755, spec_font, template["sub"], W)

    price_box = (230, 830, W - 230, 970)
    draw.rounded_rectangle(price_box, radius=30, fill=template["accent"])
    price_font = get_font(58, True)
    draw_centered_text(draw, f"{price} ريال", 860, price_font, template["bg"], W)

    badge_font = get_font(26, True)
    badges = ["✓ ضمان", "✓ أصلي", "✓ توصيل سريع"]
    x = 90
    for badge in badges:
        draw.rounded_rectangle((x, 1010, x + 270, 1080), radius=20, outline=template["accent"], width=2)
        draw.text((x + 20, 1028), arabic_text(badge), font=badge_font, fill=template["text"])
        x += 300

    contact_font = get_font(34, True)
    draw_centered_text(draw, f"واتساب: {contact}", 1120, contact_font, template["text"], W)

    footer_font = get_font(26, False)
    draw_centered_text(draw, "سوق سعيد • دليلك الذكي للتسويق العالمي 🌐", 1220, footer_font, template["sub"], W)

    return canvas


# ================================================================
# INTERFACE MAIN
# ================================================================

# (بقية التبويبات والتفاعلات تدار بسلاسة عبر Streamlit)
