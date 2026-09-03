# ================================================================
# Saeed PostGen Studio - Ultra Edition
# SaeedMarketAds | سوق سعيد
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
from PIL import Image, ImageDraw, ImageFilter


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

# MoviePy V1 & V2 Compatibility Matrix
MOVIEPY_AVAILABLE = False
try:
    from moviepy.editor import (
        AudioFileClip, CompositeAudioClip, CompositeVideoClip,
        ImageClip, VideoFileClip, concatenate_videoclips
    )
    MOVIEPY_AVAILABLE = True
except Exception:
    try:
        from moviepy import (
            AudioFileClip, CompositeAudioClip, CompositeVideoClip,
            ImageClip, VideoFileClip, concatenate_videoclips
        )
        MOVIEPY_AVAILABLE = True
    except Exception:
        MOVIEPY_AVAILABLE = False


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
VERSION = "4.5 Ultra"

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TTS_MODEL = "gemini-2.5-flash-tts-preview"
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt/"

TARGET_VERTICAL = (1080, 1920)
TARGET_SQUARE = (1080, 1080)


# ================================================================
# VOICES & TEMPLATES
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
    ("gallery", []),
    ("last_ad_card", None),
    ("last_generated_image", None),
    ("last_reel_video", None),
    ("messages", [{"role": "assistant", "content": "أهلاً بك في **Saeed PostGen Studio** 🎬\nكيف أمكنني مساعدتك في خطتك التسويقية اليوم؟"}]),
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
div.stButton > button {
    border-radius: 12px; font-weight: 700; min-height: 46px;
    background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #0b0f1a; border: none;
}
</style>
""",
    unsafe_allow_html=True,
)


# ================================================================
# CORE UTILITIES
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
    paths = [
        "fonts/Cairo-Bold.ttf" if bold else "fonts/Cairo-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"
    ]
    for path in paths:
        if os.path.exists(path):
            try: return ImageFont.truetype(path, size)
            except Exception: continue
    return ImageFont.load_default()


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
    if not client:
        raise RuntimeError("مفتاح GEMINI_API_KEY غير متاح أو مكتبة google-genai غير مثبتة.")
    
    sys_instruction = "أنت Saeed AI، المساعد الذكي الخاص بمنصة SaeedMarketAds للتسويق الرقمي وإدارة المحتوى."
    res = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=sys_instruction, temperature=0.7)
    )
    return clean_text(getattr(res, "text", ""))

def generate_pollinations_image(prompt, width=1024, height=1024):
    enhanced = f"Commercial product photography, studio setup, 8k resolution, ultra detailed, {prompt}"
    url = f"{POLLINATIONS_BASE}{urllib.parse.quote(enhanced)}?width={width}&height={height}&nologo=true"
    res = requests.get(url, timeout=60, headers={"User-Agent": "SaeedMarketAds/4.5"})
    res.raise_for_status()
    return Image.open(io.BytesIO(res.content)).convert("RGB"), url

def run_async(coro):
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro)

async def _edge_tts_process(text, voice, out_path, rate="+0%", pitch="+0Hz"):
    comm = edge_tts.Communicate(prepare_tts_text(text), voice, rate=rate, pitch=pitch)
    await comm.save(out_path)

def generate_voice(text, engine, voice, rate="+0%", pitch="+0Hz"):
    fd, out_path = tempfile.mkstemp(suffix=".mp3" if engine != "Gemini TTS" else ".wav")
    os.close(fd)
    
    if engine == "Edge TTS" and EDGE_TTS_AVAILABLE:
        run_async(_edge_tts_process(text, voice, out_path, rate, pitch))
        return out_path, "Edge TTS"
        
    if GTTS_AVAILABLE:
        tts = gTTS(text=prepare_tts_text(text), lang="ar", slow=False)
        tts.save(out_path)
        return out_path, "gTTS"
        
    raise RuntimeError("تعذر معالجة النص الصوتي، المحركات المحددة غير متاحة.")


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

def draw_centered_text(draw, text, y, font, fill, width):
    rendered = arabic_text(text)
    bbox = draw.textbbox((0, 0), rendered, font=font)
    tw = bbox[2] - bbox[0]
    draw.text(((width - tw) // 2, y), rendered, font=font, fill=fill)

def build_ad_card(product_name, storage, ram, price, contact, template_name, product_image=None):
    tmpl = TEMPLATES[template_name]
    W, H = TARGET_SQUARE
    canvas = Image.new("RGB", (W, H), tmpl["bg"])
    draw = ImageDraw.Draw(canvas)

    # Header
    draw.rounded_rectangle((50, 40, W - 50, 140), radius=20, fill=tmpl["accent"])
    draw_centered_text(draw, "SaeedMarketAds • العرض الذهبي", 65, get_font(38, True), tmpl["bg"], W)

    # Image Container
    img_box = (90, 170, W - 90, 600)
    if product_image:
        fit_img = fit_image_to_canvas(product_image, (img_box[2] - img_box[0], img_box[3] - img_box[1]))
        canvas.paste(fit_img, (img_box[0], img_box[1]))
    else:
        draw.rounded_rectangle(img_box, radius=25, outline=tmpl["accent"], width=2)
        draw_centered_text(draw, "📦", 330, get_font(80, True), tmpl["accent"], W)

    # Specs & Info
    draw_centered_text(draw, product_name, 640, get_font(54, True), tmpl["text"], W)
    specs = f"التخزين: {storage}  |  الرام: {ram}" if storage or ram else ""
    draw_centered_text(draw, specs, 720, get_font(30, False), tmpl["sub"], W)

    # Price Tag
    draw.rounded_rectangle((200, 790, W - 200, 920), radius=25, fill=tmpl["accent"])
    draw_centered_text(draw, f"{price} ريال", 825, get_font(50, True), tmpl["bg"], W)

    # Footer
    draw_centered_text(draw, f"للتواصل والطلب: {contact}", 970, get_font(32, True), tmpl["text"], W)
    draw_centered_text(draw, "سوق سعيد • دليلك الذكي للتسويق الرقمي", 1020, get_font(24, False), tmpl["sub"], W)

    return canvas


# ================================================================
# UI PRESENTATION & TABS
# ================================================================

with st.sidebar:
    st.markdown("<h2 style='text-align:center; color:#fbbf24;'>Saeed Studio</h2>", unsafe_allow_html=True)
    st.caption(f"الإصدار: {VERSION}")
    st.divider()
    if st.button("🗑️ مسح الذاكرة المؤقتة", use_container_width=True):
        st.session_state.gallery = []
        st.rerun()

st.markdown("""
<div class="sma-header">
    <div class="sma-title">🎬 Saeed PostGen Studio</div>
    <div style="color:#cbd5e1;">الاستوديو الذكي المتكامل لإدارة وإنشاء المحتوى التسويقي</div>
</div>
""", unsafe_allow_html=True)

tab_ai, tab_image, tab_ad, tab_gallery = st.tabs(["💬 الذكاء الاصطناعي", "🎨 توليد الصور", "📱 بطاقة الإعلان", "🖼️ المعرض"])

# --- TAB 1: Saeed AI ---
with tab_ai:
    for msg in st.session_state.messages:
        cls = "sma-chat-user" if msg["role"] == "user" else "sma-chat-ai"
        st.markdown(f'<div class="{cls}"><b>{"أنت" if msg["role"] == "user" else "🤖 Saeed AI"}</b><br>{msg["content"]}</div>', unsafe_allow_html=True)

    if user_in := st.chat_input("اكتب أفكارك التسويقية هنا..."):
        st.session_state.messages.append({"role": "user", "content": user_in})
        try:
            bot_res = gemini_generate_text(user_in)
        except Exception as e:
            bot_res = f"⚠️ خطأ أثناء المعالجة: {e}"
        st.session_state.messages.append({"role": "assistant", "content": bot_res})
        st.rerun()

# --- TAB 2: Image Gen ---
with tab_image:
    prompt_in = st.text_area("وصف الصورة التسويقية المطلوبة:", placeholder="هاتف أبل آيفون باللون البرتقالي على خلفية سوداء استوديو...")
    if st.button("✨ إنتاج الصورة الان", type="primary"):
        if prompt_in:
            with st.spinner("جاري إنشاء التصميم..."):
                img, _ = generate_pollinations_image(prompt_in)
                st.session_state.last_generated_image = img
                st.session_state.gallery.append({"title": "صورة مولدة", "image": img})
                st.image(img, use_container_width=True)

# --- TAB 3: Ad Card ---
with tab_ad:
    col1, col2 = st.columns(2)
    with col1:
        p_name = st.text_input("اسم المنتج", "iPhone 17 Pro Max")
        p_storage = st.text_input("المساحة", "512GB")
        p_ram = st.text_input("الرام", "16GB")
    with col2:
        p_price = st.text_input("السعر", "4800")
        p_contact = st.text_input("رقم التواصل", "967770000000")
        p_tmpl = st.selectbox("القالب التصميمي", list(TEMPLATES.keys()))
    
    p_img_file = st.file_uploader("رفع صورة المنتج (اختياري)", type=["png", "jpg", "jpeg"])
    p_img = Image.open(p_img_file).convert("RGB") if p_img_file else None

    if st.button("🚀 صمم البطاقة", type="primary"):
        card = build_ad_card(p_name, p_storage, p_ram, p_price, p_contact, p_tmpl, p_img)
        st.session_state.last_ad_card = card
        st.session_state.gallery.append({"title": f"إعلان - {p_name}", "image": card})
        st.image(card, use_container_width=True)

# --- TAB 4: Gallery ---
with tab_gallery:
    if not st.session_state.gallery:
        st.info("المعرض فارغ حالياً.")
    else:
        cols = st.columns(3)
        for idx, item in enumerate(reversed(st.session_state.gallery)):
            with cols[idx % 3]:
                st.image(item["image"], caption=item["title"], use_container_width=True)
