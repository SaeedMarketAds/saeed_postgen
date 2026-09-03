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
#
# TTS:
#   Gemini TTS -> Edge TTS -> gTTS
#
# Image:
#   Pollinations
#
# Gemini:
#   google-genai
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
VERSION = "4.1"  # تم التحديث للإصدار الجديد

DEFAULT_GEMINI_MODEL = "gemini-3.7-flash"
GEMINI_TTS_MODEL = "gemini-3.1-flash-tts-preview"

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

TARGET_VERTICAL = (1080, 1920)
TARGET_SQUARE = (1080, 1080)


# ================================================================
# VOICES
# ================================================================

# تم ترتيب الأصوات بحيث يكون "حامد" هو الأول (الافتراضي)
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
# CSS - تحسين الألوان والتصميم
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
    background:
        linear-gradient(180deg, #0b0f1a 0%, #161d2f 100%);
    border-right: 1px solid rgba(180, 130, 255, 0.25);
}

/* تحسين البطاقات والعناصر */
.sma-header {
    padding: 30px;
    border-radius: 28px;
    background:
        linear-gradient(135deg,
            rgba(180, 130, 255, 0.15),
            rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(180, 130, 255, 0.25);
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    margin-bottom: 25px;
    backdrop-filter: blur(4px);
}

.sma-logo {
    font-size: 48px;
}

.sma-title {
    font-size: 34px;
    font-weight: 800;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

.sma-subtitle {
    color: #cbd5e1;
    font-size: 16px;
    letter-spacing: 0.5px;
}

.sma-card {
    padding: 22px;
    border-radius: 24px;
    background: rgba(20, 27, 43, 0.7);
    border: 1px solid rgba(255,255,255,0.06);
    backdrop-filter: blur(6px);
    margin-bottom: 18px;
    transition: 0.3s;
}

.sma-card:hover {
    border-color: rgba(180, 130, 255, 0.3);
    box-shadow: 0 4px 20px rgba(180, 130, 255, 0.1);
}

.sma-gold {
    color: #fbbf24;
}

.sma-chat-user {
    padding: 16px 20px;
    border-radius: 20px 20px 6px 20px;
    background: rgba(180, 130, 255, 0.12);
    border: 1px solid rgba(180, 130, 255, 0.2);
    margin: 10px 0;
    color: #e2e8f0;
}

.sma-chat-ai {
    padding: 16px 20px;
    border-radius: 20px 20px 20px 6px;
    background: rgba(30, 41, 59, 0.8);
    border: 1px solid rgba(255,255,255,0.06);
    margin: 10px 0;
    color: #f1f5f9;
}

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

.sma-footer {
    text-align: center;
    padding: 30px;
    color: #94a3b8;
    font-size: 14px;
    border-top: 1px solid rgba(255,255,255,0.05);
    margin-top: 30px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ================================================================
# HELPERS
# ================================================================

def get_secret(*names):
    """البحث عن المفتاح في Streamlit Secrets ثم Environment."""
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
    return get_secret(
        "GEMINI_API_KEY",
        "GEMINI_MAIN_KEY",
    )


def clean_text(text):
    if not text:
        return ""

    text = str(text)

    text = re.sub(
        r"```(?:text|markdown|python)?",
        "",
        text,
        flags=re.IGNORECASE,
    )

    text = text.replace("```", "")

    return text.strip()


def arabic_text(text):
    """تهيئة النص العربي للرسم داخل PIL."""
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
    """
    تحسين النص قبل التحويل الصوتي لضمان نطق أوضح.
    إزالة الرموز غير العربية، توحيد الترقيم.
    """
    if not text:
        return ""

    # حذف الأحرف الغير عربية مع الاحتفاظ بالعلامات الترقيمية الأساسية
    text = re.sub(r'[^ء-ي\s0-9،.؟!;:()\-"]', ' ', text)
    # إزالة المسافات الزائدة
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

def rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    try:
        draw.rounded_rectangle(
            xy,
            radius=radius,
            fill=fill,
            outline=outline,
            width=width,
        )
    except Exception:
        draw.rectangle(
            xy,
            fill=fill,
            outline=outline,
        )


def fit_image_to_canvas(image, size):
    """ملء مساحة canvas مع الحفاظ على النسبة."""
    image = image.convert("RGB")

    target_w, target_h = size
    src_w, src_h = image.size

    scale = max(
        target_w / src_w,
        target_h / src_h,
    )

    new_size = (
        int(src_w * scale),
        int(src_h * scale),
    )

    image = image.resize(
        new_size,
        Image.Resampling.LANCZOS,
    )

    left = max(0, (image.width - target_w) // 2)
    top = max(0, (image.height - target_h) // 2)

    return image.crop(
        (
            left,
            top,
            left + target_w,
            top + target_h,
        )
    )


def wrap_text(draw, text, font, max_width):
    """تقسيم النص إلى أسطر حسب عرض الصورة."""
    words = str(text).split()
    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word

        bbox = draw.textbbox(
            (0, 0),
            arabic_text(test),
            font=font,
        )

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


def draw_centered_text(
    draw,
    text,
    y,
    font,
    fill,
    canvas_width,
):
    rendered = arabic_text(text)

    bbox = draw.textbbox(
        (0, 0),
        rendered,
        font=font,
    )

    width = bbox[2] - bbox[0]

    x = (canvas_width - width) // 2

    draw.text(
        (x, y),
        rendered,
        font=font,
        fill=fill,
    )


def add_caption_band(
    image,
    caption,
    position="bottom",
):
    """إضافة شريط نصي احترافي."""
    image = image.convert("RGBA")

    overlay = Image.new(
        "RGBA",
        image.size,
        (0, 0, 0, 0),
    )

    draw = ImageDraw.Draw(overlay)

    font = get_font(46, True)

    max_width = image.width - 100

    lines = wrap_text(
        draw,
        caption,
        font,
        max_width,
    )

    lines = lines[:3]

    line_height = 65
    padding = 25

    band_height = (
        len(lines) * line_height
        + padding * 2
    )

    if position == "top":
        y0 = 0
    else:
        y0 = image.height - band_height

    draw.rectangle(
        (
            0,
            y0,
            image.width,
            y0 + band_height,
        ),
        fill=(0, 0, 0, 170),
    )

    y = y0 + padding

    for line in lines:
        rendered = arabic_text(line)

        bbox = draw.textbbox(
            (0, 0),
            rendered,
            font=font,
        )

        tw = bbox[2] - bbox[0]

        x = (image.width - tw) // 2

        draw.text(
            (x, y),
            rendered,
            font=font,
            fill=(255, 255, 255, 255),
        )

        y += line_height

    return Image.alpha_composite(
        image,
        overlay,
    ).convert("RGB")


# ================================================================
# POLLINATIONS
# ================================================================

def build_pollinations_url(
    prompt,
    width=1024,
    height=1024,
):
    encoded = urllib.parse.quote(
        prompt,
        safe="",
    )

    return (
        f"{POLLINATIONS_BASE}{encoded}"
        f"?width={width}"
        f"&height={height}"
        f"&nologo=true"
    )


def generate_pollinations_image(
    prompt,
    width=1024,
    height=1024,
):
    enhanced_prompt = (
        "Professional commercial product photography, "
        "premium advertising campaign, "
        "studio lighting, realistic details, "
        "high quality, clean composition, "
        "no humans, no face, no person, "
        "no watermark, "
        + prompt
    )

    url = build_pollinations_url(
        enhanced_prompt,
        width,
        height,
    )

    response = requests.get(
        url,
        timeout=120,
        headers={
            "User-Agent": "SaeedMarketAds/4.0"
        },
    )

    response.raise_for_status()

    image = Image.open(
        io.BytesIO(response.content)
    ).convert("RGB")

    return image, url


# ================================================================
# GALLERY
# ================================================================

def add_to_gallery(image, title="تصميم Saeed"):
    if image is None:
        return

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    st.session_state.gallery.append(
        {
            "title": title,
            "data": buffer.getvalue(),
        }
    )

    # منع تضخم الذاكرة
    if len(st.session_state.gallery) > 30:
        st.session_state.gallery = (
            st.session_state.gallery[-30:]
        )


def bytes_to_image(data):
    return Image.open(
        io.BytesIO(data)
    ).convert("RGB")


# ================================================================
# GEMINI TEXT
# ================================================================

@st.cache_resource
def get_gemini_client(api_key):
    if not GEMINI_AVAILABLE:
        return None

    if not api_key:
        return None

    return genai.Client(
        api_key=api_key
    )


def gemini_generate_text(
    prompt,
    model=DEFAULT_GEMINI_MODEL,
):
    api_key = get_gemini_key()

    if not api_key:
        raise RuntimeError(
            "لم يتم العثور على GEMINI_API_KEY."
        )

    client = get_gemini_client(
        api_key
    )

    if client is None:
        raise RuntimeError(
            "مكتبة google-genai غير مثبتة."
        )

    system_instruction = """
أنت Saeed AI داخل منصة SaeedMarketAds.

دورك:
- مساعد تسويقي ذكي.
- كاتب إعلانات.
- مستشار محتوى.
- متخصص في الأسواق العربية والخليجية واليمن.
- اجعل الردود عملية وقابلة للاستخدام.
- استخدم العربية الفصحى الواضحة.
- لا تدّعي تنفيذ شيء لم يتم تنفيذه.
- عند كتابة إعلان اجعله جذاباً ومختصراً.
"""

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.75,
            max_output_tokens=1800,
        ),
    )

    text = getattr(
        response,
        "text",
        None,
    )

    if not text:
        raise RuntimeError(
            "Gemini لم يرجع نصاً."
        )

    return clean_text(text)


# ================================================================
# ASYNC HELPER
# ================================================================

def run_async(coro):
    """
    تشغيل coroutine حتى إذا كان هناك event loop قائم.
    """
    try:
        asyncio.get_running_loop()

        with ThreadPoolExecutor(
            max_workers=1
        ) as executor:

            future = executor.submit(
                lambda: asyncio.run(coro)
            )

            return future.result()

    except RuntimeError:
        return asyncio.run(coro)


# ================================================================
# GEMINI TTS
# ================================================================

def pcm_to_wav(
    pcm_data,
    output_path,
    sample_rate=24000,
    channels=1,
    sample_width=2,
):
    with wave.open(
        output_path,
        "wb",
    ) as wf:

        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)

        wf.writeframes(pcm_data)


def generate_gemini_tts(
    text,
    voice="Kore",
    output_path=None,
):
    """
    Gemini Native TTS.

    Gemini TTS الحالي يستخدم:
    gemini-3.1-flash-tts-preview
    ويعيد PCM داخل output_audio.
    """

    api_key = get_gemini_key()

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY غير موجود."
        )

    if not GEMINI_AVAILABLE:
        raise RuntimeError(
            "google-genai غير مثبت."
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(
            suffix=".wav"
        )
        os.close(fd)

    client = get_gemini_client(
        api_key
    )

    interaction = client.interactions.create(
        model=GEMINI_TTS_MODEL,
        input=text,
        response_format={
            "type": "audio"
        },
        generation_config={
            "speech_config": [
                {
                    "voice": voice
                }
            ]
        },
    )

    output_audio = getattr(
        interaction,
        "output_audio",
        None,
    )

    if output_audio is None:
        raise RuntimeError(
            "Gemini لم يُرجع ملفاً صوتياً."
        )

    audio_data = getattr(
        output_audio,
        "data",
        None,
    )

    if not audio_data:
        raise RuntimeError(
            "بيانات Gemini الصوتية فارغة."
        )

    if isinstance(
        audio_data,
        str,
    ):
        pcm_data = base64.b64decode(
            audio_data
        )
    else:
        pcm_data = bytes(
            audio_data
        )

    pcm_to_wav(
        pcm_data,
        output_path,
    )

    return output_path


# ================================================================
# EDGE TTS
# ================================================================

async def _edge_generate(
    text,
    voice,
    output_path,
    rate=None,      # نسبة مئوية (+0% إلى +100%) للسرعة
    pitch=None,     # نسبة مئوية للطبقة الصوتية
):
    # تحضير النص
    text = prepare_tts_text(text)
    communicator = edge_tts.Communicate(
        text,
        voice,
        rate=rate,
        pitch=pitch,
    )

    await communicator.save(
        output_path
    )


def generate_edge_tts(
    text,
    voice,
    output_path=None,
    rate="+0%",
    pitch="+0Hz",
):
    if not EDGE_TTS_AVAILABLE:
        raise RuntimeError(
            "Edge TTS غير مثبت."
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(
            suffix=".mp3"
        )
        os.close(fd)

    run_async(
        _edge_generate(
            text,
            voice,
            output_path,
            rate=rate,
            pitch=pitch,
        )
    )

    if not os.path.exists(output_path):
        raise RuntimeError(
            "Edge TTS لم ينشئ الملف."
        )

    if os.path.getsize(output_path) < 100:
        raise RuntimeError(
            "ملف Edge TTS فارغ أو غير صالح."
        )

    return output_path


# ================================================================
# GTTS
# ================================================================

def generate_gtts(
    text,
    output_path=None,
):
    if not GTTS_AVAILABLE:
        raise RuntimeError(
            "gTTS غير مثبت."
        )

    if output_path is None:
        fd, output_path = tempfile.mkstemp(
            suffix=".mp3"
        )
        os.close(fd)

    text = prepare_tts_text(text)
    tts = gTTS(
        text=text,
        lang="ar",
        slow=False,
    )

    tts.save(
        output_path
    )

    return output_path


# ================================================================
# UNIVERSAL VOICE ENGINE
# ================================================================

def generate_voice(
    text,
    engine,
    voice,
    rate="+0%",
    pitch="+0Hz",
):
    """
    ترتيب التشغيل:
      Gemini (إذا كان engine = Gemini TTS)
      Edge (إذا كان engine = Edge TTS)
      gTTS (fallback)
    """

    errors = []

    # ------------------------------------------------------------
    # GEMINI
    # ------------------------------------------------------------

    if engine == "Gemini TTS":
        try:
            path = generate_gemini_tts(
                text,
                voice,
            )

            return path, "Gemini TTS"

        except Exception as exc:
            errors.append(
                f"Gemini: {exc}"
            )

    # ------------------------------------------------------------
    # EDGE
    # ------------------------------------------------------------

    if engine == "Edge TTS":
        try:
            path = generate_edge_tts(
                text,
                voice,
                rate=rate,
                pitch=pitch,
            )

            return path, "Edge TTS"

        except Exception as exc:
            errors.append(
                f"Edge: {exc}"
            )

    # ------------------------------------------------------------
    # FALLBACK
    # ------------------------------------------------------------

    if GTTS_AVAILABLE:
        try:
            path = generate_gtts(
                text
            )

            return path, "gTTS"

        except Exception as exc:
            errors.append(
                f"gTTS: {exc}"
            )

    raise RuntimeError(
        "تعذر إنشاء الصوت:\n"
        + "\n".join(errors)
    )


# ================================================================
# AD CARD
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
    template = TEMPLATES[
        template_name
    ]

    W, H = TARGET_SQUARE

    canvas = Image.new(
        "RGB",
        (W, H),
        template["bg"],
    )

    draw = ImageDraw.Draw(
        canvas
    )

    # ------------------------------------------------------------
    # Decorative glow
    # ------------------------------------------------------------

    glow = Image.new(
        "RGBA",
        (W, H),
        (0, 0, 0, 0),
    )

    glow_draw = ImageDraw.Draw(
        glow
    )

    glow_draw.ellipse(
        (
            -200,
            -200,
            500,
            500,
        ),
        fill=(
            template["accent"][0],
            template["accent"][1],
            template["accent"][2],
            45,
        ),
    )

    glow = glow.filter(
        ImageFilter.GaussianBlur(60)
    )

    canvas = Image.alpha_composite(
        canvas.convert("RGBA"),
        glow,
    ).convert("RGB")

    draw = ImageDraw.Draw(
        canvas
    )

    # ------------------------------------------------------------
    # Header
    # ------------------------------------------------------------

    draw.rounded_rectangle(
        (
            50,
            40,
            W - 50,
            150,
        ),
        radius=28,
        fill=template["accent"],
    )

    header_font = get_font(
        42,
        True,
    )

    draw_centered_text(
        draw,
        "SaeedMarketAds • عرض حصري",
        70,
        header_font,
        template["bg"],
        W,
    )

    # ------------------------------------------------------------
    # Product Image
    # ------------------------------------------------------------

    image_area = (
        90,
        190,
        W - 90,
        620,
    )

    if product_image is not None:

        try:
            product = fit_image_to_canvas(
                product_image,
                (
                    image_area[2] - image_area[0],
                    image_area[3] - image_area[1],
                ),
            )

            canvas.paste(
                product,
                (
                    image_area[0],
                    image_area[1],
                ),
            )

        except Exception:
            pass

    else:

        draw.rounded_rectangle(
            image_area,
            radius=35,
            outline=template["accent"],
            width=3,
        )

        emoji_font = get_font(
            100,
            True,
        )

        draw_centered_text(
            draw,
            "📱",
            330,
            emoji_font,
            template["accent"],
            W,
        )

    # ------------------------------------------------------------
    # Product Name
    # ------------------------------------------------------------

    title_font = get_font(
        62,
        True,
    )

    draw_centered_text(
        draw,
        product_name,
        675,
        title_font,
        template["text"],
        W,
    )

    # ------------------------------------------------------------
    # Specs
    # ------------------------------------------------------------

    spec_font = get_font(
        34,
        False,
    )

    specs = []

    if storage:
        specs.append(
            f"التخزين: {storage}"
        )

    if ram:
        specs.append(
            f"الرام: {ram}"
        )

    spec_text = "  •  ".join(
        specs
    )

    if spec_text:
        draw_centered_text(
            draw,
            spec_text,
            765,
            spec_font,
            template["sub"],
            W,
        )

    # ------------------------------------------------------------
    # Price
    # ------------------------------------------------------------

    price_box = (
        230,
        840,
        W - 230,
        980,
    )

    draw.rounded_rectangle(
        price_box,
        radius=30,
        fill=template["accent"],
    )

    price_font = get_font(
        60,
        True,
    )

    draw_centered_text(
        draw,
        f"{price} ريال",
        870,
        price_font,
        template["bg"],
        W,
    )

    # ------------------------------------------------------------
    # Trust badges
    # ------------------------------------------------------------

    badge_font = get_font(
        27,
        True,
    )

    badges = [
        "✓ ضمان",
        "✓ أصلي",
        "✓ توصيل سريع",
    ]

    x = 90

    for badge in badges:

        width = 270

        draw.rounded_rectangle(
            (
                x,
                1030,
                x + width,
                1100,
            ),
            radius=20,
            outline=template["accent"],
            width=2,
        )

        draw.text(
            (
                x + 20,
                1048,
            ),
            arabic_text(badge),
            font=badge_font,
            fill=template["text"],
        )

        x += 300

    # ------------------------------------------------------------
    # Contact
    # ------------------------------------------------------------

    contact_font = get_font(
        35,
        True,
    )

    draw_centered_text(
        draw,
        f"واتساب: {contact}",
        1150,
        contact_font,
        template["text"],
        W,
    )

    # ------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------

    footer_font = get_font(
        28,
        False,
    )

    draw_centered_text(
        draw,
        "سوق سعيد • دليلك الذكي للتسويق العالمي 🌐",
        1260,
        footer_font,
        template["sub"],
        W,
    )

    return canvas


# ================================================================
# VIDEO HELPERS
# ================================================================

def fit_video_clip(
    clip,
    target_size,
):
    """
    نسخة بسيطة ومتوافقة قدر الإمكان
    مع MoviePy 1.x.
    """

    target_w, target_h = target_size

    src_w = clip.w
    src_h = clip.h

    target_ratio = target_w / target_h
    source_ratio = src_w / src_h

    if source_ratio > target_ratio:

        # الفيديو أعرض
        new_h = target_h

        clip = clip.resize(
            height=new_h
        )

        new_w = clip.w

        x1 = max(
            0,
            int((new_w - target_w) / 2),
        )

        clip = clip.crop(
            x1=x1,
            x2=x1 + target_w,
        )

    else:

        new_w = target_w

        clip = clip.resize(
            width=new_w
        )

        new_h = clip.h

        y1 = max(
            0,
            int((new_h - target_h) / 2),
        )

        clip = clip.crop(
            y1=y1,
            y2=y1 + target_h,
        )

    return clip


def extract_first_sentence(text):
    if not text:
        return ""

    parts = re.split(
        r"[.!؟!\n]+",
        text.strip(),
    )

    for part in parts:
        part = part.strip()

        if part:
            return part[:120]

    return text[:120]


# ================================================================
# REEL GENERATOR
# ================================================================

def create_reel(
    script,
    image_files=None,
    video_file=None,
    voice_engine="Edge TTS",   # تم تغيير الافتراضي إلى Edge TTS
    voice_name="ar-SA-HamedNeural",
    duration=10,
    aspect="9:16",
    caption=None,
    music_file=None,
    music_volume=0.18,
    rate="+0%",
    pitch="+0Hz",
):
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError(
            "MoviePy غير مثبت أو غير متوافق."
        )

    temp_dir = tempfile.mkdtemp(
        prefix="saeed_reel_"
    )

    target_size = (
        TARGET_VERTICAL
        if aspect == "9:16"
        else TARGET_SQUARE
    )

    output_path = os.path.join(
        temp_dir,
        "saeed_reel.mp4",
    )

    clips = []
    opened_resources = []

    try:

        # ========================================================
        # VOICE
        # ========================================================

        voice_path, engine_used = generate_voice(
            script,
            voice_engine,
            voice_name,
            rate=rate,
            pitch=pitch,
        )

        voice_clip = AudioFileClip(
            voice_path
        )

        opened_resources.append(
            voice_clip
        )

        actual_duration = min(
            float(duration),
            float(voice_clip.duration),
        )

        # ========================================================
        # VIDEO
        # ========================================================

        if video_file is not None:

            video_path = os.path.join(
                temp_dir,
                "input_video.mp4",
            )

            with open(
                video_path,
                "wb",
            ) as f:
                f.write(
                    video_file.getbuffer()
                )

            source = VideoFileClip(
                video_path
            )

            opened_resources.append(
                source
            )

            if source.duration < duration:

                loops = int(
                    duration / source.duration
                ) + 1

                video = source.loop(
                    n=loops
                )

            else:
                video = source

            video = video.subclip(
                0,
                min(
                    duration,
                    video.duration,
                ),
            )

            video = fit_video_clip(
                video,
                target_size,
            )

            video = video.without_audio()

            clips = [video]

            final_video = video

        else:

            # ====================================================
            # IMAGES
            # ====================================================

            pil_images = []

            if image_files:

                for uploaded in image_files:

                    data = uploaded.getvalue()

                    image = Image.open(
                        io.BytesIO(data)
                    ).convert("RGB")

                    pil_images.append(
                        image
                    )

            elif st.session_state.last_ad_card is not None:

                pil_images.append(
                    st.session_state.last_ad_card
                )

            elif st.session_state.last_generated_image is not None:

                pil_images.append(
                    st.session_state.last_generated_image
                )

            else:

                fallback = Image.new(
                    "RGB",
                    target_size,
                    (15, 23, 42),
                )

                pil_images.append(
                    fallback
                )

            seconds_per_image = (
                duration / len(pil_images)
            )

            for index, image in enumerate(
                pil_images
            ):

                frame = fit_image_to_canvas(
                    image,
                    target_size,
                )

                if caption:
                    frame = add_caption_band(
                        frame,
                        caption,
                    )

                frame_path = os.path.join(
                    temp_dir,
                    f"frame_{index}.jpg",
                )

                frame.save(
                    frame_path,
                    quality=95,
                )

                clip = ImageClip(
                    frame_path
                ).set_duration(
                    seconds_per_image
                )

                clips.append(
                    clip
                )

            final_video = concatenate_videoclips(
                clips,
                method="compose",
            )

        # ========================================================
        # CAPTION ON VIDEO
        # ========================================================

        if video_file is not None and caption:

            overlay_image = Image.new(
                "RGBA",
                target_size,
                (0, 0, 0, 0),
            )

            overlay_image = add_caption_band(
                Image.new(
                    "RGB",
                    target_size,
                    (0, 0, 0),
                ),
                caption,
            ).convert("RGBA")

            overlay_path = os.path.join(
                temp_dir,
                "caption.png",
            )

            overlay_image.save(
                overlay_path
            )

            caption_clip = (
                ImageClip(
                    overlay_path
                )
                .set_duration(
                    final_video.duration
                )
            )

            final_video = CompositeVideoClip(
                [
                    final_video,
                    caption_clip,
                ],
                size=target_size,
            )

        # ========================================================
        # AUDIO
        # ========================================================

        voice_for_video = voice_clip

        if voice_clip.duration > duration:
            voice_for_video = voice_clip.subclip(
                0,
                duration,
            )

        final_audio = voice_for_video

        # --------------------------------------------------------
        # Music
        # --------------------------------------------------------

        if music_file is not None:

            music_path = os.path.join(
                temp_dir,
                "music.mp3",
            )

            with open(
                music_path,
                "wb",
            ) as f:
                f.write(
                    music_file.getbuffer()
                )

            music_clip = AudioFileClip(
                music_path
            )

            opened_resources.append(
                music_clip
            )

            if music_clip.duration < duration:

                loops = int(
                    duration / music_clip.duration
                ) + 1

                music_clip = music_clip.loop(
                    n=loops
                )

            music_clip = music_clip.subclip(
                0,
                duration,
            )

            music_clip = music_clip.volumex(
                music_volume
            )

            final_audio = CompositeAudioClip(
                [
                    voice_for_video,
                    music_clip,
                ]
            )

        final_video = final_video.set_audio(
            final_audio
        )

        # ========================================================
        # EXPORT
        # ========================================================

        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=2,
            logger=None,
        )

        return output_path, engine_used

    finally:

        for resource in opened_resources:
            try:
                resource.close()
            except Exception:
                pass


# ================================================================
# SIDEBAR
# ================================================================

with st.sidebar:

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:10px 0 20px;
        ">
            <div style="font-size:48px;">🛍️</div>
            <h2 style="margin:0; color:#fbbf24;">
                SaeedMarketAds
            </h2>
            <div style="color:#8b5cf6; font-weight:600;">
                Saeed PostGen Studio
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown(
        "### ⚙️ حالة النظام"
    )

    if GEMINI_AVAILABLE:
        st.success(
            "Gemini SDK: جاهز"
        )
    else:
        st.warning(
            "Gemini SDK: غير مثبت"
        )

    if EDGE_TTS_AVAILABLE:
        st.success(
            "Edge TTS: جاهز"
        )
    else:
        st.warning(
            "Edge TTS: غير مثبت"
        )

    if MOVIEPY_AVAILABLE:
        st.success(
            "MoviePy: جاهز"
        )
    else:
        st.warning(
            "MoviePy: غير مثبت"
        )

    st.divider()

    st.markdown(
        f"""
        **الإصدار:** {VERSION}.0

        **الهوية:** Saeed AI

        **المنصة:** SaeedMarketAds

        **الشعار:**
        دليلك الذكي للتسويق العالمي 🌐
        """
    )

    st.divider()

    if st.button(
        "🗑️ مسح المعرض",
        use_container_width=True,
    ):
        st.session_state.gallery = []

        st.success(
            "تم مسح المعرض."
        )

        st.rerun()


# ================================================================
# HEADER
# ================================================================

st.markdown(
    """
    <div class="sma-header">

        <div class="sma-logo">🎬</div>

        <div class="sma-title">
            Saeed PostGen Studio
        </div>

        <div class="sma-subtitle">
            استوديو سعيد الذكي لصناعة الإعلانات والصور والريلز
        </div>

    </div>
    """,
    unsafe_allow_html=True,
)


# ================================================================
# TABS
# ================================================================

tab_ai, tab_image, tab_ad, tab_reel, tab_gallery = st.tabs(
    [
        "💬 Saeed AI",
        "🎨 مولد الصور",
        "📱 بطاقة الإعلان",
        "🎥 صانع الريلز",
        "🖼️ المعرض",
    ]
)


# ################################################################
# TAB 1 — AI
# ################################################################

with tab_ai:

    st.markdown(
        "## 🤖 Saeed AI"
    )

    st.caption(
        "اكتب فكرتك، وسأحولها إلى محتوى إعلاني أو سينمائي جاهز."
    )

    for message in st.session_state.messages:

        if message["role"] == "user":

            st.markdown(
                f"""
                <div class="sma-chat-user">
                    <b>أنت</b><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.markdown(
                f"""
                <div class="sma-chat-ai">
                    <b>🤖 Saeed AI</b><br>
                    {message["content"]}
                </div>
                """,
                unsafe_allow_html=True,
            )

    prompt = st.chat_input(
        "اكتب فكرة الإعلان أو الفيديو..."
    )

    if prompt:

        st.session_state.messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        with st.spinner(
            "Saeed AI يفكر..."
        ):

            try:

                reply = gemini_generate_text(
                    prompt
                )

            except Exception as exc:

                reply = (
                    "⚠️ تعذر الاتصال بـ Gemini حالياً.\n\n"
                    f"التفاصيل: `{exc}`\n\n"
                    "يمكنك متابعة استخدام مولد الصور وبقية الأدوات."
                )

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": reply,
            }
        )

        st.rerun()


# ################################################################
# TAB 2 — IMAGE GENERATOR
# ################################################################

with tab_image:

    st.markdown(
        "## 🎨 مولد الصور الفوري"
    )

    st.caption(
        "أنشئ صورة إعلانية احترافية ثم أضفها مباشرة إلى المعرض أو استخدمها في الريلز."
    )

    col1, col2 = st.columns(
        [2, 1]
    )

    with col1:

        image_prompt = st.text_area(
            "وصف الصورة",
            placeholder=(
                "مثال: هاتف ذكي فاخر باللون الأسود والذهبي "
                "على سطح زجاجي مع إضاءة استوديو احترافية"
            ),
            height=150,
        )

    with col2:

        image_format = st.selectbox(
            "المقاس",
            [
                "مربع 1:1",
                "عمودي 9:16",
                "أفقي 16:9",
            ],
        )

    if st.button(
        "✨ توليد الصورة",
        type="primary",
        use_container_width=True,
    ):

        if not image_prompt.strip():

            st.warning(
                "اكتب وصف الصورة أولاً."
            )

        else:

            if image_format == "مربع 1:1":
                width, height = 1024, 1024

            elif image_format == "عمودي 9:16":
                width, height = 768, 1365

            else:
                width, height = 1365, 768

            with st.spinner(
                "جاري إنشاء الصورة..."
            ):

                try:

                    image, image_url = (
                        generate_pollinations_image(
                            image_prompt,
                            width,
                            height,
                        )
                    )

                    st.session_state.last_generated_image = image

                    add_to_gallery(
                        image,
                        "صورة مولدة",
                    )

                    st.success(
                        "تم إنشاء الصورة وإضافتها إلى المعرض."
                    )

                except Exception as exc:

                    st.error(
                        f"تعذر إنشاء الصورة: {exc}"
                    )

    if st.session_state.last_generated_image is not None:

        st.divider()

        st.image(
            st.session_state.last_generated_image,
            use_container_width=True,
        )

        buffer = io.BytesIO()

        st.session_state.last_generated_image.save(
            buffer,
            format="PNG",
        )

        st.download_button(
            "⬇️ تنزيل الصورة",
            data=buffer.getvalue(),
            file_name="saeed_generated_image.png",
            mime="image/png",
            use_container_width=True,
        )


# ################################################################
# TAB 3 — AD CARD
# ################################################################

with tab_ad:

    st.markdown(
        "## 📱 صانع بطاقة الإعلان"
    )

    st.caption(
        "أنشئ بطاقة إعلان مربعة جاهزة للنشر على الشبكات الاجتماعية."
    )

    left, right = st.columns(
        [1.3, 1]
    )

    with left:

        product_name = st.text_input(
            "اسم المنتج",
            "هاتف ذكي جديد",
        )

        storage = st.text_input(
            "التخزين",
            "256GB",
        )

        ram = st.text_input(
            "الرام",
            "12GB",
        )

        price = st.text_input(
            "السعر",
            "999",
        )

        contact = st.text_input(
            "رقم واتساب",
            "05xxxxxxxx",
        )

    with right:

        template_name = st.selectbox(
            "التصميم",
            list(TEMPLATES.keys()),
        )

        product_upload = st.file_uploader(
            "صورة المنتج",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
            key="ad_product_upload",
        )

        product_image = None

        if product_upload:

            try:
                product_image = Image.open(
                    product_upload
                ).convert("RGB")

                st.image(
                    product_image,
                    caption="صورة المنتج",
                    use_container_width=True,
                )

            except Exception:
                st.warning(
                    "تعذر قراءة صورة المنتج."
                )

    if st.button(
        "🚀 إنشاء بطاقة الإعلان",
        type="primary",
        use_container_width=True,
    ):

        with st.spinner(
            "جاري تصميم بطاقة الإعلان..."
        ):

            try:

                card = build_ad_card(
                    product_name,
                    storage,
                    ram,
                    price,
                    contact,
                    template_name,
                    product_image,
                )

                st.session_state.last_ad_card = card

                add_to_gallery(
                    card,
                    f"بطاقة {product_name}",
                )

                st.success(
                    "تم إنشاء البطاقة وإضافتها إلى المعرض."
                )

            except Exception as exc:

                st.error(
                    f"حدث خطأ: {exc}"
                )

    if st.session_state.last_ad_card is not None:

        st.divider()

        st.image(
            st.se
