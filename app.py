# ================================================================
# Saeed PostGen Studio - Production Candidate (v4.5.7)
# SaeedMarketAds | سوق سعيد
# ================================================================

import asyncio
import concurrent.futures
import io
import logging
import os
import re
import shutil
import tempfile
import traceback
import urllib.parse
import uuid
import wave
from datetime import datetime

import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont

# إعداد السجلات للتتبع والتشخيص
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


# ================================================================
# DIRECTORIES & STORAGE SETUP
# ================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
IMAGES_DIR = os.path.join(OUTPUTS_DIR, "images")
CARDS_DIR = os.path.join(OUTPUTS_DIR, "cards")
REELS_DIR = os.path.join(OUTPUTS_DIR, "reels")

for folder in [OUTPUTS_DIR, IMAGES_DIR, CARDS_DIR, REELS_DIR]:
    os.makedirs(folder, exist_ok=True)


# ================================================================
# LIBRARIES LOAD & FALLBACKS
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

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception:
    np = None
    NUMPY_AVAILABLE = False

MOVIEPY_AVAILABLE = False
try:
    import moviepy.editor as mpe
    from moviepy.editor import (
        AudioFileClip, ImageClip, VideoClip, concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except Exception:
    try:
        import moviepy as mpe
        from moviepy import (
            AudioFileClip, ImageClip, VideoClip, concatenate_videoclips
        )
        MOVIEPY_AVAILABLE = True
    except Exception:
        mpe = None
        MOVIEPY_AVAILABLE = False

REEL_STACK_READY = MOVIEPY_AVAILABLE and NUMPY_AVAILABLE
FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))


# ================================================================
# CONFIG & CONSTANTS
# ================================================================

st.set_page_config(
    page_title="Saeed PostGen Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

APP_NAME = "Saeed PostGen Studio"
BRAND_NAME = "SaeedMarketAds"
VERSION = "4.5.7 Production Candidate"

DEFAULT_GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_TTS_MODEL = "gemini-3.6-flash-preview-tts"

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

TARGET_VERTICAL = (1080, 1920)
TARGET_SQUARE = (1080, 1080)

GEMINI_TTS_SAMPLE_RATE = 24000
GEMINI_TTS_CHANNELS = 1
GEMINI_TTS_SAMPLE_WIDTH = 2

GEMINI_TTS_PROMPT = """
اقرأ النص التالي بالعربية الفصحى بصوت إعلاني احترافي.
النبرة: واثقة، دافئة، جذابة ومحفزة.

تعليمات الأداء الصوتي:
- استخدم وقفات طبيعية قصيرة بين الجمل والفقرات.
- أكد بنبرتك على الأسعار، العروض، والكلمات المفتاحية المهمة.
- اجعل البداية مشوقة وجاذبة للانتباه، والختام حاسمًا ومحفزًا لاتخاذ إجراء (CTA).
- لا تغنِّ ولا تستخدم أسلوب الإلقاء الشعري.
- لا تضف أي مؤثرات صوتية أو خلفيات موسيقية.
- التزم بالنص المرفق حرفيًا بدون زيادة، نقصان، أو تعديل أي كلمة.

النص المراد قراءته:
{text}
"""


# ================================================================
# VOICES & TEMPLATES
# ================================================================

EDGE_VOICES = {
    "🇸🇦 حامد": "ar-SA-HamedNeural",
    "🇸🇦 زارية": "ar-SA-ZariyahNeural",
    "🇪🇬 شاكر": "ar-EG-ShakirNeural",
    "🇪🇬 سلمى": "ar-EG-SalmaNeural",
    "🇦🇪 فاطمة": "ar-AE-FatimaNeural",
    "🇦🇪 حمد": "ar-AE-HamdanNeural",
}

GEMINI_VOICES = {
    "Puck (حيوية وإعلان)": "Puck",
    "Charon (رسمي وثقيل)": "Charon",
    "Kore (هادئ ومتزن)": "Kore",
    "Fenrir (قوي وعميق)": "Fenrir",
    "Aoede (أنثوي متزن)": "Aoede",
    "Sulafat (دافئ ومؤثر)": "Sulafat",
}

TEMPLATES = {
    "ذهبي فاخر": {"bg": (15, 23, 42), "accent": (251, 191, 36), "text": (255, 255, 255), "sub": (205, 205, 205)},
    "أزرق تقني": {"bg": (8, 20, 40), "accent": (56, 189, 248), "text": (255, 255, 255), "sub": (185, 205, 225)},
    "أخضر عصري": {"bg": (10, 30, 24), "accent": (52, 211, 153), "text": (255, 255, 255), "sub": (185, 220, 205)},
    "أحمر جريء": {"bg": (35, 12, 12), "accent": (248, 113, 113), "text": (255, 255, 255), "sub": (220, 190, 190)},
}


# ================================================================
# SESSION STATE INITIALIZATION
# ================================================================

for key, default in [
    ("last_ad_card", None),
    ("last_generated_image", None),
    ("last_raw_image", None),
    ("last_reel_video", None),
    ("temp_files", []),
    ("scene_list", [str(uuid.uuid4()), str(uuid.uuid4())]),
    ("messages", [{"role": "assistant", "content": f"أهلاً بك في **{APP_NAME} v{VERSION}** 🎬\nنسخة التجربة المتقدمة (Production Candidate) جاهزة لاختباراتك الميدانية!"}]),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ================================================================
# STYLING (CSS)
# ================================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Cairo', sans-serif; }
.stApp {
    background: radial-gradient(circle at 70% 20%, rgba(180, 130, 255, 0.08), transparent 60%),
                radial-gradient(circle at 30% 80%, rgba(251, 191, 36, 0.05), transparent 60%),
                linear-gradient(145deg, #0b0f1a 0%, #141b2b 50%, #1a1030 100%);
}
.sma-header {
    padding: 25px; border-radius: 20px;
    background: linear-gradient(135deg, rgba(180, 130, 255, 0.15), rgba(15, 23, 42, 0.9));
    border: 1px solid rgba(180, 130, 255, 0.25);
    margin-bottom: 20px; backdrop-filter: blur(5px);
}
.sma-title {
    font-size: 32px; font-weight: 800;
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.sma-chat-user {
    padding: 14px 18px; border-radius: 16px 16px 2px 16px;
    background: rgba(180, 130, 255, 0.15); border: 1px solid rgba(180, 130, 255, 0.2);
    margin: 8px 0; color: #e2e8f0;
}
.sma-chat-ai {
    padding: 14px 18px; border-radius: 16px 16px 16px 2px;
    background: rgba(30, 41, 59, 0.85); border: 1px solid rgba(255,255,255,0.08);
    margin: 8px 0; color: #f1f5f9;
}
div.stButton > button, div.stDownloadButton > button {
    border-radius: 12px; font-weight: 700; min-height: 46px;
    background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #0b0f1a; border: none;
}
</style>
""",
    unsafe_allow_html=True,
)


# ================================================================
# UTILITIES & PERSISTENCE
# ================================================================

def get_secret(*names):
    for name in names:
        val = st.secrets.get(name) or os.getenv(name)
        if val:
            return str(val).strip()
    return ""

def clean_text(text):
    if not text: return ""
    text = re.sub(r"```(?:text|markdown|python)?", "", str(text), flags=re.IGNORECASE)
    return text.replace("```", "").strip()

def arabic_text(text):
    if not text: return ""
    if ARABIC_SUPPORT:
        try:
            return get_display(arabic_reshaper.reshape(str(text)))
        except Exception: pass
    return str(text)

def prepare_tts_text(text):
    if not text: return ""
    text = re.sub(r'[^ء-ي\s0-9،.؟!;:()\-"]', ' ', str(text))
    return re.sub(r'\s+', ' ', text).strip()

def get_font(size=40, bold=True):
    font_names = [
        "fonts/Cairo-Bold.ttf" if bold else "fonts/Cairo-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    ]
    for path in font_names:
        if os.path.isfile(path):
            try: return ImageFont.truetype(path, size)
            except Exception: continue
    return ImageFont.load_default()

def save_image_to_disk(image, folder, prefix="img"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{prefix}_{timestamp}.png"
    filepath = os.path.join(folder, filename)
    image.save(filepath, format="PNG")
    return filepath

def get_disk_gallery():
    items = []
    folders = [(IMAGES_DIR, "صورة مولدة", "image"), (CARDS_DIR, "بطاقة إعلان", "image"), (REELS_DIR, "فيديو ريل", "video")]
    for folder, cat, media_type in folders:
        if os.path.exists(folder):
            for fname in sorted(os.listdir(folder), reverse=True):
                ext = fname.lower()
                if (media_type == "image" and ext.endswith((".png", ".jpg", ".jpeg"))) or (media_type == "video" and ext.endswith(".mp4")):
                    fpath = os.path.join(folder, fname)
                    items.append({"title": f"{cat} ({fname[:15]})", "path": fpath, "type": media_type})
    return items

def register_temp_file(path):
    if path and path not in st.session_state.temp_files:
        st.session_state.temp_files.append(path)

def cleanup_temp_files():
    removed = 0
    for p in st.session_state.temp_files:
        try:
            if p and os.path.exists(p):
                os.remove(p)
                removed += 1
        except Exception as e:
            logging.warning(f"تعذر حذف الملف المؤقت {p}: {e}")
    st.session_state.temp_files = []
    return removed

def image_to_png_bytes(image):
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


# ================================================================
# ASYNC & MOVIEPY COMPATIBILITY HELPERS
# ================================================================

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(lambda: asyncio.run(coro))
            return future.result()
    else:
        return asyncio.run(coro)

def _clip_set_duration(clip, duration):
    return clip.set_duration(duration) if hasattr(clip, "set_duration") else clip.with_duration(duration)

def _clip_set_audio(clip, audio):
    return clip.set_audio(audio) if hasattr(clip, "set_audio") else clip.with_audio(audio)

def _clip_set_fps(clip, fps):
    return clip.set_fps(fps) if hasattr(clip, "set_fps") else clip.with_fps(fps)

def create_animated_clip(make_frame_fn, duration, fps=24):
    vc_cls = getattr(mpe, "VideoClip", VideoClip)
    try:
        clip = vc_cls(make_frame=make_frame_fn, duration=duration)
    except TypeError:
        clip = vc_cls(make_frame_fn, duration=duration)
    return _clip_set_fps(clip, fps)

def apply_safe_transitions(scene_clips, crossfade_duration=0.4):
    if len(scene_clips) <= 1 or crossfade_duration <= 0:
        return concatenate_videoclips(scene_clips, method="compose")

    try:
        padding = crossfade_duration
        processed_clips = []
        for i, clip in enumerate(scene_clips):
            if i > 0:
                if hasattr(clip, "crossfadein"):
                    processed_clips.append(clip.crossfadein(padding))
                elif hasattr(mpe, "vfx") and hasattr(mpe.vfx, "crossfadein"):
                    processed_clips.append(mpe.vfx.crossfadein(clip, padding))
                else:
                    processed_clips.append(clip)
            else:
                processed_clips.append(clip)
        
        return concatenate_videoclips(processed_clips, padding=-padding, method="compose")
    except Exception as e:
        logging.warning(f"تعذر تطبيق الانتقال التدريجي ({e})، سيتم التحول للقص المباشر.")
        return concatenate_videoclips(scene_clips, method="compose")


# ================================================================
# ENGINE IMPLEMENTATIONS
# ================================================================

@st.cache_resource
def get_gemini_client():
    key = get_secret("GEMINI_API_KEY", "GEMINI_MAIN_KEY")
    if GEMINI_AVAILABLE and key:
        return genai.Client(api_key=key)
    return None

def gemini_generate_text(prompt, model=DEFAULT_GEMINI_MODEL):
    client = get_gemini_client()
    if not client: raise RuntimeError("مفتاح GEMINI_API_KEY غير متاح.")
    sys_instruction = f"أنت Saeed AI، المساعد الذكي الخاص بمنصة {BRAND_NAME}."
    res = client.models.generate_content(
        model=model, contents=prompt,
        config=types.GenerateContentConfig(system_instruction=sys_instruction, temperature=0.7)
    )
    return clean_text(getattr(res, "text", ""))

def generate_pollinations_image(prompt, width=1024, height=1024):
    enhanced = f"Commercial product photography, studio setup, 8k resolution, ultra detailed, {prompt}"
    url = f"{POLLINATIONS_BASE}{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true"
    res = requests.get(url, timeout=60, headers={"User-Agent": "SaeedMarketAds/4.5"})
    res.raise_for_status()
    return Image.open(io.BytesIO(res.content)).convert("RGB"), url

async def _edge_tts_process(text, voice, out_path, rate="+0%", pitch="+0Hz"):
    comm = edge_tts.Communicate(prepare_tts_text(text), voice, rate=rate, pitch=pitch)
    await comm.save(out_path)

def gemini_tts_generate(text, voice_name, out_path):
    client = get_gemini_client()
    if not client:
        raise RuntimeError("مفتاح GEMINI_API_KEY غير متاح أو مكتبة google-genai غير مثبتة.")

    clean = prepare_tts_text(text)
    if not clean:
        raise RuntimeError("النص الصوتي فارغ.")

    directed_prompt = GEMINI_TTS_PROMPT.format(text=clean)

    response = client.models.generate_content(
        model=GEMINI_TTS_MODEL,
        contents=directed_prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                language_code="ar-XA",
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=voice_name
                    )
                ),
            ),
        ),
    )

    audio_bytes = None
    if getattr(response, "candidates", None):
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None):
                data = getattr(part.inline_data, "data", None)
                if data:
                    audio_bytes = data
                    break

    if not audio_bytes:
        raise RuntimeError("Gemini استجاب بدون بيانات صوتية.")

    with wave.open(out_path, "wb") as wf:
        wf.setnchannels(GEMINI_TTS_CHANNELS)
        wf.setsampwidth(GEMINI_TTS_SAMPLE_WIDTH)
        wf.setframerate(GEMINI_TTS_SAMPLE_RATE)
        wf.writeframes(audio_bytes)

    return out_path

def generate_voice(text, engine, voice, rate="+0%", pitch="+0Hz", strict_mode=False):
    note = ""
    if engine == "Gemini TTS":
        if GEMINI_AVAILABLE and get_gemini_client():
            fd, out_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            try:
                gemini_tts_generate(text, voice, out_path)
                register_temp_file(out_path)
                return out_path, "Gemini TTS", "✅ تم توليد الصوت بنجاح عبر محرك Gemini TTS الأصلي."
            except Exception as e:
                if strict_mode:
                    raise RuntimeError(f"فشل Gemini TTS في وضع Strict الصارم: {e}")
                note = f"⚠️ Gemini TTS → فشل ({e}) \n🔄 Fallback → التحويل التلقائي إلى Edge TTS."
        else:
            if strict_mode: raise RuntimeError("Gemini TTS غير متاح.")
            note = "⚠️ Gemini TTS غير متاح \n🔄 Fallback → التحويل التلقائي إلى Edge TTS."

    if engine in ("Edge TTS", "Gemini TTS") and EDGE_TTS_AVAILABLE:
        fd, out_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        try:
            edge_voice = voice if engine == "Edge TTS" else list(EDGE_VOICES.values())[0]
            run_async(_edge_tts_process(text, edge_voice, out_path, rate, pitch))
            register_temp_file(out_path)
            used_msg = "Edge TTS" + (" (الاحتياطي)" if engine == "Gemini TTS" else "")
            return out_path, used_msg, note
        except Exception as e:
            note += f"\n⚠️ فشل Edge TTS أيضاً ({e})."

    if GTTS_AVAILABLE:
        fd, out_path = tempfile.mkstemp(suffix=".mp3")
        os.close(fd)
        tts = gTTS(text=prepare_tts_text(text), lang="ar", slow=False)
        tts.save(out_path)
        register_temp_file(out_path)
        return out_path, "gTTS (الاحتياطي النهائي)", note

    raise RuntimeError("تعذر معالجة الصوت بجميع المحركات المتاحة.")


# ================================================================
# CANVAS & GRAPHICS BUILDER
# ================================================================

def fit_image_to_canvas(image, size):
    image = image.convert("RGB")
    tw, th = size
    sw, sh = image.size
    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)
    image = image.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - tw) // 2, (nh - th) // 2
    return image.crop((left, top, left + tw, top + th))

def fit_font_to_width(draw, text, base_font_size, max_width, bold=True):
    rendered = arabic_text(text)
    size = base_font_size
    font = get_font(size, bold)
    while size > 16:
        bbox = draw.textbbox((0, 0), rendered, font=font)
        if (bbox[2] - bbox[0]) <= max_width: break
        size -= 2
        font = get_font(size, bold)
    return font

def draw_centered_text(draw, text, y, font, fill, width, shadow=True):
    rendered = arabic_text(text)
    bbox = draw.textbbox((0, 0), rendered, font=font)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    if shadow: draw.text((x + 2, y + 2), rendered, font=font, fill=(0, 0, 0))
    draw.text((x, y), rendered, font=font, fill=fill)

def build_ad_card(product_name, storage, ram, price, contact, template_name, product_image=None):
    tmpl = TEMPLATES[template_name]
    W, H = TARGET_SQUARE
    canvas = Image.new("RGB", (W, H), tmpl["bg"])
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((50, 40, W - 50, 140), radius=20, fill=tmpl["accent"])
    header_font = fit_font_to_width(draw, f"{BRAND_NAME} • العرض الذهبي", 38, W - 120, bold=True)
    draw_centered_text(draw, f"{BRAND_NAME} • العرض الذهبي", 65, header_font, tmpl["bg"], W, shadow=False)

    img_box = (90, 170, W - 90, 600)
    if product_image:
        fit_img = fit_image_to_canvas(product_image, (img_box[2] - img_box[0], img_box[3] - img_box[1]))
        canvas.paste(fit_img, (img_box[0], img_box[1]))
    else:
        draw.rounded_rectangle(img_box, radius=25, outline=tmpl["accent"], width=2)
        draw_centered_text(draw, "📦", 330, get_font(80, True), tmpl["accent"], W, shadow=False)

    name_font = fit_font_to_width(draw, product_name, 50, W - 140, bold=True)
    draw_centered_text(draw, product_name, 640, name_font, tmpl["text"], W)

    specs = f"التخزين: {storage}  |  الرام: {ram}" if storage or ram else ""
    if specs:
        specs_font = fit_font_to_width(draw, specs, 30, W - 140, bold=False)
        draw_centered_text(draw, specs, 720, specs_font, tmpl["sub"], W, shadow=False)

    draw.rounded_rectangle((200, 790, W - 200, 920), radius=25, fill=tmpl["accent"])
    price_font = fit_font_to_width(draw, f"{price} ريال", 50, W - 440, bold=True)
    draw_centered_text(draw, f"{price} ريال", 825, price_font, tmpl["bg"], W, shadow=False)

    contact_text = f"للتواصل والطلب: {contact}" if contact else "تواصل معنا للطلب الآن"
    contact_font = fit_font_to_width(draw, contact_text, 32, W - 140, bold=True)
    draw_centered_text(draw, contact_text, 970, contact_font, tmpl["text"], W)

    return canvas

def build_cta_end_screen(contact_number=""):
    """
    بناء شاشة الـ CTA ثابتة بدون استقبال معامل progress لتجنب إعادتها في كل frame.
    """
    W, H = TARGET_VERTICAL
    canvas = Image.new("RGB", (W, H), (11, 15, 26))
    draw = ImageDraw.Draw(canvas)

    draw.rounded_rectangle((60, H//3 - 80, W - 60, H//3 + 240), radius=35, fill=(251, 191, 36))
    title_font = fit_font_to_width(draw, BRAND_NAME, 68, W - 180, bold=True)
    draw_centered_text(draw, BRAND_NAME, H//3 - 20, title_font, (11, 15, 26), W, shadow=False)

    cta_text = f"اطلب الآن: {contact_number}" if contact_number else "اطلب الآن | تواصل معنا"
    cta_font = fit_font_to_width(draw, cta_text, 52, W - 140, bold=True)
    draw_centered_text(draw, cta_text, H//2 + 100, cta_font, (255, 255, 255), W)

    sub_font = fit_font_to_width(draw, "دليلك الذكي للتسويق الرقمي والمبيعات", 36, W - 140, bold=False)
    draw_centered_text(draw, "دليلك الذكي للتسويق الرقمي والمبيعات", H//2 + 210, sub_font, (203, 213, 225), W, shadow=False)

    return canvas

def add_text_overlay(image, title="", brand=BRAND_NAME, contact=""):
    if image is None: return None
    img_with_text = image.copy()
    draw = ImageDraw.Draw(img_with_text)
    w, h = img_with_text.size

    font_title = fit_font_to_width(draw, title, int(h * 0.05), int(w * 0.9), bold=True) if title else None
    font_brand = get_font(int(h * 0.04), True)

    if brand: draw_centered_text(draw, brand, int(h * 0.05), font_brand, "white", w)
    if title: draw_centered_text(draw, title, int(h * 0.78), font_title, "yellow", w)
    if contact: draw_centered_text(draw, contact, int(h * 0.90), font_brand, "white", w)

    return img_with_text


# ================================================================
# ULTRA REEL ENGINE (OPTIMIZED CTA & ACCURATE TIMING)
# ================================================================

def make_advanced_ken_burns_clip(pil_img, duration, mode="zoom_in", fps=24):
    tw, th = TARGET_VERTICAL
    oversized_dim = (int(tw * 1.30), int(th * 1.30))
    base_img = fit_image_to_canvas(pil_img, oversized_dim)
    bw, bh = base_img.size

    max_x_offset = bw - tw
    max_y_offset = bh - th

    def make_frame(t):
        progress = min(max(t / max(duration, 0.1), 0.0), 1.0)

        if mode == "zoom_in":
            crop_scale = 1.0 - (0.23 * progress)
            w_crop = bw * crop_scale
            h_crop = bh * crop_scale
            left = (bw - w_crop) / 2
            top = (bh - h_crop) / 2
            cropped = base_img.crop((left, top, left + w_crop, top + h_crop))
            return np.array(cropped.resize((tw, th), Image.Resampling.BILINEAR))

        elif mode == "zoom_out":
            crop_scale = 0.77 + (0.23 * progress)
            w_crop = bw * crop_scale
            h_crop = bh * crop_scale
            left = (bw - w_crop) / 2
            top = (bh - h_crop) / 2
            cropped = base_img.crop((left, top, left + w_crop, top + h_crop))
            return np.array(cropped.resize((tw, th), Image.Resampling.BILINEAR))

        elif mode == "pan_left":
            offset_x = int(max_x_offset * progress)
            top_y = max_y_offset // 2
            return np.array(base_img.crop((offset_x, top_y, offset_x + tw, top_y + th)))

        else: # pan_right
            offset_x = int(max_x_offset * (1.0 - progress))
            top_y = max_y_offset // 2
            return np.array(base_img.crop((offset_x, top_y, offset_x + tw, top_y + th)))

    return create_animated_clip(make_frame, duration=duration, fps=fps)

def make_animated_cta_clip(contact_number="", duration=2.5, fps=24):
    """
    تحسين الأداء: بناء صورة Pillow مرة واحدة خارج make_frame لرفع سرعة المعالجة.
    """
    tw, th = TARGET_VERTICAL
    oversized_dim = (int(tw * 1.12), int(th * 1.12))

    cta_pil = build_cta_end_screen(contact_number=contact_number)
    base_img = fit_image_to_canvas(cta_pil, oversized_dim)
    bw, bh = base_img.size

    def make_frame(t):
        progress = min(max(t / max(duration, 0.1), 0.0), 1.0)
        w_crop = bw - ((bw - tw) * progress)
        h_crop = bh - ((bh - th) * progress)
        left = (bw - w_crop) / 2
        top = (bh - h_crop) / 2

        cropped = base_img.crop((left, top, left + w_crop, top + h_crop))
        return np.array(cropped.resize((tw, th), Image.Resampling.BILINEAR))

    return create_animated_clip(make_frame, duration=duration, fps=fps)

def build_reel_video(images, script_text=None, tts_engine=None, voice=None,
                      rate="+0%", pitch="+0Hz", seconds_per_slide=3.0, fps=24,
                      strict_mode=False, enable_motion=True, contact_number="",
                      crossfade_duration=0.4):
    if not REEL_STACK_READY: raise RuntimeError("مكتبة moviepy غير متوفرة.")
    if not FFMPEG_AVAILABLE: raise RuntimeError("برنامج ffmpeg غير مثبت بالبيئة.")
    if not images: raise RuntimeError("قم باختيار مشاهد للريل أولاً.")

    clips_to_cleanup = []
    audio_clip = None
    engine_used, tts_note = None, ""
    total_audio_duration = None

    try:
        if script_text and script_text.strip():
            audio_path, engine_used, tts_note = generate_voice(script_text, tts_engine, voice, rate, pitch, strict_mode)
            audio_clip = AudioFileClip(audio_path)
            clips_to_cleanup.append(audio_clip)
            total_audio_duration = audio_clip.duration

        n = len(images)
        
        # حساب تعويض التداخل الزمني للـ Crossfade لضمان مطابقة زمن الفيديو مع زمن الصوت
        effective_crossfade = crossfade_duration if (n > 1 and crossfade_duration > 0) else 0.0
        total_overlap_loss = (n - 1) * effective_crossfade if n > 1 else 0.0

        if total_audio_duration:
            each = max(1.5, (total_audio_duration + total_overlap_loss) / n)
        else:
            each = seconds_per_slide

        motion_modes = ["zoom_in", "pan_left", "zoom_out", "pan_right"]
        scene_clips = []

        for idx, img in enumerate(images):
            mode = motion_modes[idx % len(motion_modes)]
            if enable_motion:
                clip = make_advanced_ken_burns_clip(img, duration=each, mode=mode, fps=fps)
            else:
                fitted = fit_image_to_canvas(img, TARGET_VERTICAL)
                clip = _clip_set_fps(_clip_set_duration(ImageClip(np.array(fitted)), each), fps)
            scene_clips.append(clip)
            clips_to_cleanup.append(clip)

        scenes_video = apply_safe_transitions(scene_clips, crossfade_duration=effective_crossfade)
        clips_to_cleanup.append(scenes_video)

        if audio_clip:
            scenes_video = _clip_set_audio(scenes_video, audio_clip)

        cta_clip = make_animated_cta_clip(contact_number=contact_number, duration=2.5, fps=fps)
        clips_to_cleanup.append(cta_clip)

        final_video = concatenate_videoclips([scenes_video, cta_clip], method="compose")
        clips_to_cleanup.append(final_video)

        out_path = os.path.join(REELS_DIR, f"reel_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.mp4")
        
        try:
            final_video.write_videofile(out_path, fps=fps, codec="libx264", audio_codec="aac", logger=None)
        except Exception as ffmpeg_err:
            logging.error(f"خطأ أثناء تصدير الفيديو بـ FFmpeg:\n{traceback.format_exc()}")
            raise ffmpeg_err

        return out_path, engine_used, tts_note

    finally:
        for clip in clips_to_cleanup:
            if clip is not None:
                try: clip.close()
                except Exception as e: logging.debug(f"إغلاق مقطع: {e}")


# ================================================================
# UI PRESENTATION & TABS
# ================================================================

with st.sidebar:
    st.markdown("<h2 style='text-align:center; color:#fbbf24;'>Saeed Studio</h2>", unsafe_allow_html=True)
    st.caption(f"الإصدار: {VERSION}")
    st.divider()
    if st.button("🗑️ تنظيف الملفات المؤقتة", use_container_width=True):
        removed = cleanup_temp_files()
        st.toast(f"تم حذف {removed} ملف مؤقت.", icon="🧹")
        st.rerun()

st.markdown(f"""
<div class="sma-header">
    <div class="sma-title">🎬 Saeed PostGen Studio</div>
    <div style="color:#cbd5e1;">الاستوديو الذكي المتكامل — v{VERSION}</div>
</div>
""", unsafe_allow_html=True)

tab_ai, tab_image, tab_ad, tab_reel, tab_gallery = st.tabs(
    ["💬 الذكاء الاصطناعي", "🎨 توليد الصور", "📱 بطاقة الإعلان", "🎬 Ultra Reel", "🖼️ المعرض"]
)

# --- TAB 1: AI Chat ---
with tab_ai:
    for msg in st.session_state.messages:
        cls = "sma-chat-user" if msg["role"] == "user" else "sma-chat-ai"
        st.markdown(f'<div class="{cls}"><b>{"أنت" if msg["role"] == "user" else "🤖 Saeed AI"}</b><br>{msg["content"]}</div>', unsafe_allow_html=True)

    if user_in := st.chat_input("اكتب أفكارك التسويقية هنا..."):
        st.session_state.messages.append({"role": "user", "content": user_in})
        try: bot_res = gemini_generate_text(user_in)
        except Exception as e: bot_res = f"⚠️ خطأ: {e}"
        st.session_state.messages.append({"role": "assistant", "content": bot_res})
        st.rerun()

# --- TAB 2: Image Gen ---
with tab_image:
    prompt_in = st.text_area("وصف الصورة التسويقية المطلوبة:", placeholder="هاتف أبل آيفون على خلفية استوديو زجاجية...")
    col_a, col_b = st.columns(2)
    with col_a: ad_title = st.text_input("نص الإعلان (اختياري)", "")
    with col_b: ad_contact = st.text_input("رقم التواصل (اختياري)", "")

    if st.button("✨ إنتاج الصورة الان", type="primary"):
        if prompt_in:
            with st.spinner("جاري إنشاء التصميم ودفعه للقرص..."):
                try:
                    img, _ = generate_pollinations_image(prompt_in)
                    final_img = add_text_overlay(img, title=ad_title, brand=BRAND_NAME, contact=ad_contact)
                    st.session_state.last_raw_image = img
                    st.session_state.last_generated_image = final_img
                    
                    save_image_to_disk(final_img, IMAGES_DIR, prefix="img")
                    st.success("تم الحفظ في المعرض بفرادة كاملة!")
                    st.image(final_img, use_container_width=True)
                except Exception as e: st.error(f"⚠️ تعذر توليد الصورة: {e}")

# --- TAB 3: Ad Card ---
with tab_ad:
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("اسم المنتج", "iPhone 17 Pro Max")
        p_storage = st.text_input("المساحة", "512GB")
        p_ram = st.text_input("الرام", "16GB")
    with col2:
        p_price = st.text_input("السعر", "4800")
        p_contact = st.text_input("رقم التواصل", "967770000000", key="ad_card_contact")
        p_tmpl = st.selectbox("القالب التصميمي", list(TEMPLATES.keys()))

    use_ai_img = st.checkbox("استخدام الصورة المولدة بالذكاء الاصطناعي", value=bool(st.session_state.last_raw_image))
    p_img = st.session_state.last_raw_image if use_ai_img else None

    if st.button("🚀 صمم البطاقة", type="primary"):
        try:
            card = build_ad_card(p_name, p_storage, p_ram, p_price, p_contact, p_tmpl, p_img)
            st.session_state.last_ad_card = card
            save_image_to_disk(card, CARDS_DIR, prefix="card")
            st.success("تم الحفظ بنجاح!")
            st.image(card, use_container_width=True)
        except Exception as e: st.error(f"⚠️ تعذر إنشاء البطاقة: {e}")

# --- TAB 4: Ultra Reel Maker ---
with tab_reel:
    st.markdown("##### 🎬 محرك Ultra Reel — التحكم الكامل والانتقالات السينمائية")
    
    disk_items = get_disk_gallery()
    available_dict = {}
    if st.session_state.last_raw_image: available_dict["الصورة الخام الحالية"] = st.session_state.last_raw_image
    if st.session_state.last_generated_image: available_dict["الصورة النهائية الحالية"] = st.session_state.last_generated_image
    if st.session_state.last_ad_card: available_dict["بطاقة الإعلان الحالية"] = st.session_state.last_ad_card
    
    for item in disk_items:
        if item["type"] == "image":
            try: available_dict[item["title"]] = Image.open(item["path"]).convert("RGB")
            except Exception as e: logging.warning(f"تعذر فتح الصورة {item['path']}: {e}")

    if not available_dict:
        st.info("قم بتوليد صورة أو بطاقة أولاً لاستخدام صانع الريلز.")
    else:
        col_add, _ = st.columns([1, 4])
        with col_add:
            if st.button("➕ إضافة مشهد جديد"):
                st.session_state.scene_list.append(str(uuid.uuid4()))
                st.rerun()

        selected_images = []
        keys_list = list(available_dict.keys())

        for idx, sc_id in enumerate(st.session_state.scene_list):
            sc_c1, sc_c2, sc_del = st.columns([3, 2, 1])
            with sc_c1:
                choice = st.selectbox(f"المشهد {idx+1}:", keys_list, index=min(idx, len(keys_list)-1), key=f"dynamic_sc_{sc_id}")
                selected_images.append(available_dict[choice])
            with sc_c2:
                st.image(available_dict[choice], height=100)
            with sc_del:
                if len(st.session_state.scene_list) > 1 and st.button("🗑️", key=f"del_sc_{sc_id}"):
                    st.session_state.scene_list.remove(sc_id)
                    st.rerun()

        st.divider()
        script_text = st.text_area("نص التعليق الصوتي للريل", "")
        reel_contact = st.text_input("رقم التواصل لشاشة الـ CTA الختامية (اختياري)", "")

        c_eng, c_st = st.columns([3, 1])
        with c_eng: engine_choice = st.radio("محرك الصوت الرئيسي", ["Gemini TTS", "Edge TTS", "gTTS"], horizontal=True)
        with c_st: strict_mode = st.toggle("وضع Strict الصارم", value=False)

        voice_value = None
        if engine_choice == "Edge TTS": voice_value = EDGE_VOICES[st.selectbox("الصوت", list(EDGE_VOICES.keys()))]
        elif engine_choice == "Gemini TTS": voice_value = GEMINI_VOICES[st.selectbox("الصوت", list(GEMINI_VOICES.keys()))]

        col_m1, col_m2 = st.columns(2)
        with col_m1:
            enable_motion = st.checkbox("تفعيل الحركة السينمائية المتعددة (Ken Burns)", value=True)
            seconds_per_slide = st.slider("مدة عرض المشهد (ثواني)", 1.5, 8.0, 3.0, 0.5)
        with col_m2:
            crossfade_dur = st.slider("مدة التداخل بين المشاهد (ثواني)", 0.0, 1.5, 0.4, 0.1, help="تحديد 0.0 يعني الانتقال المباشر بدون Crossfade")

        if st.button("🎬 إنتاج Ultra Reel الان", type="primary", use_container_width=True):
            with st.spinner("جاري دمج الحركات السينمائية، شاشة CTA، والتنقلات والصوت..."):
                try:
                    out_path, engine_used, tts_note = build_reel_video(
                        images=selected_images, script_text=script_text, tts_engine=engine_choice,
                        voice=voice_value, seconds_per_slide=seconds_per_slide, strict_mode=strict_mode,
                        enable_motion=enable_motion, contact_number=reel_contact, crossfade_duration=crossfade_dur
                    )
                    st.session_state.last_reel_video = out_path
                    if tts_note:
                        if "Fallback" in tts_note or "⚠️" in tts_note:
                            st.warning(tts_note)
                        else:
                            st.success(tts_note)
                    st.video(out_path)
                    with open(out_path, "rb") as f:
                        st.download_button("⬇️ تحميل Ultra Reel MP4", data=f.read(), file_name=os.path.basename(out_path), mime="video/mp4", use_container_width=True)
                except Exception as e: st.error(f"⚠️ تعذر إنتاج الريل: {e}")

# --- TAB 5: Disk Gallery ---
with tab_gallery:
    disk_items = get_disk_gallery()
    if not disk_items:
        st.info("المعرض فارغ حالياً.")
    else:
        st.caption(f"📁 المعرض الدائم (يحتوي على {len(disk_items)} عنصراً على القرص)")
        cols = st.columns(3)
        for idx, item in enumerate(disk_items):
            with cols[idx % 3]:
                try:
                    if item["type"] == "image":
                        img = Image.open(item["path"])
                        st.image(img, caption=item["title"], use_container_width=True)
                        col_dl, col_del = st.columns(2)
                        with col_dl:
                            st.download_button("⬇️ تحميل", data=image_to_png_bytes(img), file_name=os.path.basename(item["path"]), mime="image/png", key=f"dl_disk_{idx}", use_container_width=True)
                        with col_del:
                            if st.button("🗑️ حذف", key=f"del_disk_{idx}", use_container_width=True):
                                os.remove(item["path"])
                                st.rerun()
                    elif item["type"] == "video":
                        st.video(item["path"])
                        st.caption(item["title"])
                        col_dl, col_del = st.columns(2)
                        with col_dl:
                            with open(item["path"], "rb") as vf:
                                st.download_button("⬇️ تحميل MP4", data=vf.read(), file_name=os.path.basename(item["path"]), mime="video/mp4", key=f"dl_vid_{idx}", use_container_width=True)
                        with col_del:
                            if st.button("🗑️ حذف", key=f"del_vid_{idx}", use_container_width=True):
                                os.remove(item["path"])
                                st.rerun()
                except Exception as e:
                    st.error(f"خطأ في تحميل العنصر {item['title']}: {e}")

