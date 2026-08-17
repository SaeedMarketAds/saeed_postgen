# ==========================================
# Saeed PostGen - أداة متكاملة لتوليد الريلز والصور والموسيقى بالذكاء الاصطناعي
# نسخة محسّنة v2: قوالب تصميم، دعم عربي صحيح، معرض صور فعلي، قراءة ads.txt
# ==========================================
import io
import os
import tempfile
import asyncio
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ------------------------------------------------------------------
# إصلاح توافق: نسخ Pillow الحديثة (10+) أزالت Image.ANTIALIAS
# ------------------------------------------------------------------
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import edge_tts
from moviepy.editor import (
    ImageClip, AudioFileClip, CompositeVideoClip, concatenate_videoclips, VideoFileClip
)
from moviepy.video.fx.all import crop as mp_crop, loop as mp_loop
from moviepy.audio.AudioClip import concatenate_audioclips, CompositeAudioClip

# دعم عرض النصوص العربية بشكل صحيح (اتجاه واتصال الحروف)
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False

# محاولة استيراد google.generativeai
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

# ==========================================
# إعدادات الخطوط والمسارات العربية أولاً
# ==========================================
FONT_SEARCH_PATHS = [
    "fonts/Cairo-Bold.ttf",
    "fonts/Tajawal-Bold.ttf",
    "fonts/Amiri-Bold.ttf",
    "fonts/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
]

FONT_SEARCH_PATHS_REGULAR = [
    "fonts/Cairo-Regular.ttf",
    "fonts/Tajawal-Regular.ttf",
    "fonts/Amiri-Regular.ttf",
    "fonts/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf",
    "/usr/share/fonts/truetype/kacst/KacstOne.ttf",
]

# تعريف حالة الخط العربي في الأعلى لتجنب خطأ NameError
_ARAB_FONT_STATUS = {"checked": False, "ok": False, "path": None}


def _font_supports_arabic(font_obj) -> bool:
    """اختبار فعلي لرسم كلمة عربية والتأكد من دعم الخط."""
    try:
        test_img = Image.new("RGB", (10, 10))
        draw = ImageDraw.Draw(test_img)
        bbox = draw.textbbox((0, 0), "مرحبا", font=font_obj)
        return (bbox[2] - bbox[0]) > 5
    except Exception:
        return False


def get_font(size, bold=True):
    """تحميل خط عربي حقيقي مع التحقق الفعلي من دعمه للحروف."""
    candidates = FONT_SEARCH_PATHS if bold else FONT_SEARCH_PATHS_REGULAR
    for path in candidates:
        try:
            font_obj = ImageFont.truetype(path, size)
            if _font_supports_arabic(font_obj):
                if not _ARAB_FONT_STATUS["checked"]:
                    _ARAB_FONT_STATUS.update(checked=True, ok=True, path=path)
                return font_obj
        except Exception:
            continue

    if not _ARAB_FONT_STATUS["checked"]:
        _ARAB_FONT_STATUS.update(checked=True, ok=False, path=None)

    fallback_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arial.ttf",
    ]
    for path in fallback_candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


# ==========================================
# إعدادات الصفحة والتصميم
# ==========================================
st.set_page_config(
    page_title="Saeed PostGen - صانع المحتوى بالذكاء الاصطناعي",
    page_icon="🎬",
    layout="wide"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    * { font-family: 'Cairo', sans-serif; }
    .main { background: linear-gradient(145deg, #0b1120, #1a2332); color: #e2e8f0; }
    .title {
        text-align: center; color: #fbbf24; font-size: 2.8rem; font-weight: 700;
        text-shadow: 0 0 20px rgba(251,191,36,0.3); margin-bottom: 10px;
    }
    .subtitle { text-align: center; color: #94a3b8; font-size: 1.2rem; margin-bottom: 30px; }
    .card-box {
        background: rgba(30, 41, 59, 0.7); backdrop-filter: blur(6px); border-radius: 25px;
        padding: 25px; border: 1px solid rgba(251,191,36,0.15); margin-bottom: 25px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }
    .stButton > button {
        background: linear-gradient(90deg, #fbbf24, #f59e0b); color: #0f172a; font-weight: bold;
        border: none; border-radius: 30px; padding: 12px 30px; transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(251,191,36,0.2);
    }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 8px 25px rgba(251,191,36,0.4); }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.05); color: #f8fafc;
        border: 1px solid rgba(251,191,36,0.2); border-radius: 15px;
    }
    .stSelectbox > div > div { background: rgba(255,255,255,0.05); color: #f8fafc; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🎬 Saeed PostGen</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">أنشئ ريلز احترافية وصوراً وموسيقى بالذكاء الاصطناعي بنقرة واحدة</div>', unsafe_allow_html=True)

# =========== التصحيح هنا ===========
# نستخدم _ARAB_FONT_STATUS (بدون I) كما هو معرف أعلاه
_ = get_font(30, bold=True)
if _ARAB_FONT_STATUS["checked"] and not _ARAB_FONT_STATUS["ok"]:
    st.error(
        "⚠️ لا يوجد خط عربي حقيقي مثبّت على الخادم. أضف ملف خط عربي (مثل Cairo-Bold.ttf) "
        "داخل مجلد باسم **fonts** في جذر الريبو (fonts/Cairo-Bold.ttf)."
    )
# ===================================

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

if "gallery" not in st.session_state:
    st.session_state["gallery"] = []
if "last_ad_card" not in st.session_state:
    st.session_state["last_ad_card"] = None

# ==========================================
# قوالب وتصميم البطاقات والدوال المساعدة
# ==========================================
TEMPLATES = {
    "ذهبي فاخر": {"bg": (15, 23, 42), "accent": (251, 191, 36), "text": (255, 255, 255), "sub": (200, 200, 200)},
    "أزرق تقني": {"bg": (10, 20, 40), "accent": (56, 189, 248), "text": (255, 255, 255), "sub": (180, 200, 220)},
    "أخضر عصري": {"bg": (12, 30, 24), "accent": (52, 211, 153), "text": (255, 255, 255), "sub": (190, 220, 205)},
    "أحمر جريء": {"bg": (30, 12, 12), "accent": (248, 113, 113), "text": (255, 255, 255), "sub": (220, 190, 190)},
}


def ar(text):
    if ARABIC_SUPPORT and text:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


def draw_rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def wrap_arabic_text(draw, text, font, max_width):
    words = text.split()
    lines, current = [], []
    for word in words:
        trial = current + [word]
        trial_text = ar(" ".join(trial))
        bbox = draw.textbbox((0, 0), trial_text, font=font)
        if (bbox[2] - bbox[0]) <= max_width or not current:
            current = trial
        else:
            lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def overlay_caption_on_image(base_img: Image.Image, caption: str, accent_color=(251, 191, 36)):
    img = base_img.convert("RGB").copy()
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")
    if not caption:
        return img

    font_size = max(38, int(w * 0.052))
    font = get_font(font_size, bold=True)
    lines = wrap_arabic_text(draw, caption, font, int(w * 0.86))[:4]

    line_height = int(font_size * 1.35)
    block_height = line_height * len(lines) + 50
    band_top = h - block_height - 60
    band_bottom = h - 40

    draw.rectangle([(0, band_top), (w, band_bottom)], fill=(10, 10, 15, 190))
    draw.rectangle([(0, band_top), (w, band_top + 6)], fill=accent_color + (255,))

    y = band_top + 25
    for line in lines:
        display_line = ar(line)
        bbox = draw.textbbox((0, 0), display_line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) / 2
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), display_line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), display_line, font=font, fill=(255, 255, 255, 255))
        y += line_height
    return img


def render_transparent_caption_band(size, caption: str, accent_color=(251, 191, 36)):
    w, h = size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    if not caption:
        return overlay

    draw = ImageDraw.Draw(overlay, "RGBA")
    font_size = max(38, int(w * 0.052))
    font = get_font(font_size, bold=True)
    lines = wrap_arabic_text(draw, caption, font, int(w * 0.86))[:4]

    line_height = int(font_size * 1.35)
    block_height = line_height * len(lines) + 50
    band_top = h - block_height - 60
    band_bottom = h - 40

    draw.rectangle([(0, band_top), (w, band_bottom)], fill=(10, 10, 15, 190))
    draw.rectangle([(0, band_top), (w, band_top + 6)], fill=accent_color + (255,))

    y = band_top + 25
    for line in lines:
        display_line = ar(line)
        bbox = draw.textbbox((0, 0), display_line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) / 2
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), display_line, font=font, fill=(0, 0, 0, 255))
        draw.text((x, y), display_line, font=font, fill=(255, 255, 255, 255))
        y += line_height
    return overlay


def fit_video_to_canvas(video_clip, target_size):
    target_w, target_h = target_size
    clip_w, clip_h = video_clip.w, video_clip.h
    target_ratio = target_w / target_h
    clip_ratio = clip_w / clip_h

    if clip_ratio > target_ratio:
        resized = video_clip.resize(height=target_h)
    else:
        resized = video_clip.resize(width=target_w)

    return mp_crop(
        resized, width=min(target_w, resized.w), height=min(target_h, resized.h),
        x_center=resized.w / 2, y_center=resized.h / 2
    ).resize(newsize=target_size)


def fit_image_to_canvas(image_to_use: Image.Image, target_size):
    image_to_use = image_to_use.convert("RGB")
    if image_to_use.size == target_size:
        return image_to_use.copy()

    if target_size[1] > target_size[0]:
        bg = image_to_use.resize(target_size).filter(ImageFilter.GaussianBlur(20))
        fitted = image_to_use.copy()
        fitted.thumbnail((target_size[0], target_size[0]))
        canvas = bg.copy()
        canvas.paste(fitted, ((target_size[0] - fitted.width) // 2, (target_size[1] - fitted.height) // 2))
        return canvas
    else:
        return image_to_use.resize(target_size)


def build_ad_card(product_name, storage_ram, price, whatsapp, template_name, logo_img=None):
    tpl = TEMPLATES[template_name]
    w, h = 1080, 1080
    card = Image.new("RGB", (w, h), color=tpl["bg"])

    gradient = Image.new("L", (1, h), color=0)
    for y in range(h):
        gradient.putpixel((0, y), int(40 * (y / h)))
    gradient = gradient.resize((w, h))
    overlay = Image.new("RGB", (w, h), tpl["accent"])
    card = Image.composite(overlay, card, gradient.point(lambda p: p // 6))

    draw = ImageDraw.Draw(card, "RGBA")

    # شريط علوي
    draw_rounded_rect(draw, [(60, 55), (w - 60, 135)], 22, tpl["accent"])
    title_font = get_font(44)
    brand_text = ar("SaeedMarketAds  •  عرض حصري")
    bbox = draw.textbbox((0, 0), brand_text, font=title_font)
    draw.text(((w - (bbox[2] - bbox[0])) / 2, 68), brand_text, fill=tpl["bg"], font=title_font)

    # إطار المحتوى
    draw_rounded_rect(draw, [(55, 165), (w - 55, h - 200)], 34, (255, 255, 255, 12))
    content_box = [(85, 195), (w - 85, h - 230)]
    draw.rounded_rectangle(content_box, radius=28, outline=tpl["accent"], width=4)

    font_product = get_font(58)
    font_body = get_font(40, bold=False)
    font_price = get_font(70)
    font_badge = get_font(28)

    y = 250
    product_lines = wrap_arabic_text(draw, f"📱 {product_name}", font_product, w - 260)[:2]
    for line in product_lines:
        display_line = ar(line)
        bbox = draw.textbbox((0, 0), display_line, font=font_product)
        draw.text(((w - (bbox[2] - bbox[0])) / 2, y), display_line, fill=tpl["text"], font=font_product)
        y += 78

    y += 25
    spec_text = ar(f"💾 {storage_ram}")
    bbox = draw.textbbox((0, 0), spec_text, font=font_body)
    draw.text(((w - (bbox[2] - bbox[0])) / 2, y), spec_text, fill=tpl["sub"], font=font_body)
    y += 75

    # السعر
    price_text = ar(f"💰 {price}")
    bbox = draw.textbbox((0, 0), price_text, font=font_price)
    pw, ph = bbox[2] - bbox[0], bbox[3] - bbox[1]
    box_left, box_right = (w - pw) / 2 - 45, (w + pw) / 2 + 45
    box_top, box_bottom = y - 22, y + ph + 42

    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.rounded_rectangle([(box_left - 10, box_top - 10), (box_right + 10, box_bottom + 10)], radius=30, fill=tpl["accent"] + (90,))
    glow = glow.filter(ImageFilter.GaussianBlur(18))
    card.paste(glow, (0, 0), glow)
    draw = ImageDraw.Draw(card, "RGBA")

    draw.rounded_rectangle([(box_left, box_top), (box_right, box_bottom)], radius=22, fill=tpl["accent"])
    draw.text(((w - pw) / 2, y), price_text, fill=tpl["bg"], font=font_price)
    y = box_bottom + 45

    # شارات الثقة
    trust_badges = [ar("✅ ضمان"), ar("💯 أصلي 100%"), ar("🚚 توصيل سريع")]
    badge_gap = 20
    badge_widths = [draw.textbbox((0, 0), b, font=font_badge)[2] - draw.textbbox((0, 0), b, font=font_badge)[0] + 44 for b in trust_badges]
    bx = (w - (sum(badge_widths) + badge_gap * (len(trust_badges) - 1))) / 2
    for b, bw in zip(trust_badges, badge_widths):
        draw.rounded_rectangle([(bx, y), (bx + bw, y + 56)], radius=18, outline=tpl["accent"], width=2)
        bb = draw.textbbox((0, 0), b, font=font_badge)
        draw.text((bx + (bw - (bb[2] - bb[0])) / 2, y + 12), b, fill=tpl["text"], font=font_badge)
        bx += bw + badge_gap
    y += 90

    contact_text = ar(f"📞 {whatsapp}")
    bbox = draw.textbbox((0, 0), contact_text, font=font_body)
    draw.text(((w - (bbox[2] - bbox[0])) / 2, y), contact_text, fill=tpl["text"], font=font_body)

    if logo_img is not None:
        logo = logo_img.convert("RGBA")
        logo.thumbnail((140, 140))
        card.paste(logo, (w - 190, h - 190), logo)

    footer_font = get_font(26, bold=False)
    footer_text = ar("تواصل معنا الآن واحصل على عرضك الخاص قبل نفاد الكمية")
    bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    draw.text(((w - (bbox[2] - bbox[0])) / 2, h - 165), footer_text, fill=tpl["sub"], font=footer_font)

    return card


# ==========================================
# واجهة التبويبات في Streamlit
# ==========================================
tab1, tab2, tab3 = st.tabs(["📱 بطاقة إعلان", "🎥 توليد ريلز", "🖼️ معرض الصور"])

# ------------------------------------------
# التبويب الأول: بطاقة إعلان + قراءة ads.txt
# ------------------------------------------
with tab1:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("إنشاء بطاقة إعلان للمنتج")

    with st.form("ad_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("اسم المنتج", "iPhone 15 Pro Max")
            storage_ram = st.text_input("الذاكرة والرام", "256GB / 8GB RAM")
            template_name = st.selectbox("قالب التصميم", list(TEMPLATES.keys()))
        with col2:
            price = st.text_input("السعر", "$1,200 - 3,900 ريال")
            whatsapp = st.text_input("رقم واتساب", "+966 50 000 0000")
            logo_upload = st.file_uploader("شعار المتجر (اختياري، PNG بخلفية شفافة)", type=["png"])

        submitted = st.form_submit_button("🎨 توليد البطاقة الفردية")

    if submitted:
        logo_img = Image.open(logo_upload) if logo_upload is not None else None
        card = build_ad_card(product_name, storage_ram, price, whatsapp, template_name, logo_img)
        st.session_state["last_ad_card"] = card
        st.session_state["gallery"].append({"image": card, "caption": f"بطاقة: {product_name}"})
        st.image(card, caption="معاينة البطاقة", use_container_width=True)

        buf = io.BytesIO()
        card.save(buf, format="PNG")
        st.download_button("📥 تحميل البطاقة (PNG)", data=buf.getvalue(), file_name="ad_card.png", mime="image/png")

    st.markdown("---")
    st.subheader("📁 التوليد التلقائي من ملف ads.txt")
    st.markdown("يقرأ التطبيق ملف `ads.txt` من الخادم ويولد بطاقات إعلانية لكل المنتجات الموجودة فيه دفعة واحدة.")

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🚀 قراءة وتوليد البطاقات من ملف ads.txt"):
            if os.path.exists('ads.txt'):
                with open('ads.txt', 'r', encoding='utf-8') as file:
                    ads_list = file.readlines()
                
                count = 0
                for line in ads_list:
                    ad_text = line.strip()
                    if ad_text and not ad_text.startswith("#"):
                        card = build_ad_card(
                            product_name=ad_text,
                            storage_ram="256GB / 8GB RAM",
                            price="عرض خاص",
                            whatsapp=whatsapp,
                            template_name=template_name,
                            logo_img=None
                        )
                        st.session_state["gallery"].append({"image": card, "caption": f"من ads.txt: {ad_text}"})
                        count += 1
                st.success(f"✅ تم توليد {count} بطاقة بنجاح وإضافتها إلى معرض الصور!")
            else:
                st.warning("⚠️ ملف `ads.txt` غير موجود. أنشئ الملف أولاً أو اضغط على الزر المجاور.")

    with col_btn2:
        if st.button("📝 إنشاء ملف ads.txt تجريبي"):
            sample_ads = [
                "iPhone 15 Pro Max",
                "Samsung Galaxy S24 Ultra",
                "Xiaomi 14 Pro",
                "Huawei Mate 60 Pro"
            ]
            with open('ads.txt', 'w', encoding='utf-8') as f:
                f.write("\n".join(sample_ads) + "\n")
            st.success("✨ تم إنشاء ملف `ads.txt` تجريبي بنجاح! يمكنك الآن الضغط على زر القراءة أعلاه.")

    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# التبويب الثاني: توليد ريلز
# ------------------------------------------
with tab2:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🎥 توليد ريلز احترافية")
    st.markdown("أنشئ فيديو قصير مع تعليق صوتي فصيح وموسيقى خلفية ونصوص واضحة.")

    VOICES = {
        "رجالي - سعودي (حامد)": "ar-SA-HamedNeural",
        "نسائي - سعودي (زارية)": "ar-SA-ZariyahNeural",
        "رجالي - مصري (شاكر)": "ar-EG-ShakirNeural",
        "نسائي - مصري (سلمى)": "ar-EG-SalmaNeural",
    }

    with st.form("reel_form"):
        script_text = st.text_area(
            "النص التعليقي الكامل (سيُقرأ في الفيديو)",
            "مرحباً بكم في متجرنا، نقدم لكم أفضل العروض على الجوالات الحديثة. تواصلوا معنا الآن واحصلوا على خصم خاص."
        )
        uploaded_video = st.file_uploader("🎬 (اختياري) ارفع فيديو جاهز للمنتج", type=["mp4", "mov", "m4v"])
        uploaded_images = st.file_uploader("أو ارفع صوراً للمنتج (سلايد شو)", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

        col1, col2 = st.columns(2)
        with col1:
            voice_label = st.selectbox("الصوت", list(VOICES.keys()))
            use_generated_image = st.checkbox("استخدام صورة البطاقة الأخيرة إن لم أرفع صوراً")
        with col2:
            aspect = st.selectbox("أبعاد الفيديو", ["عمودي 9:16 (ريلز/ستوري)", "مربع 1:1"])
            add_text_overlay = st.checkbox("إضافة نص واضح فوق الفيديو", value=True)

        background_music = st.file_uploader("ارفع موسيقى خلفية (MP3) - اختياري", type=["mp3"])
        music_volume = st.slider("مستوى صوت الموسيقى", 0.0, 1.0, 0.3)
        duration = st.slider("إجمالي مدة الفيديو (بالثواني)", 5, 60, 14)
        overlay_caption = st.text_input("النص الذي يظهر فوق الفيديو (اتركه فارغاً لاستخدام الجملة الأولى)", "")

        generate_reel = st.form_submit_button("🚀 توليد الريلز الآن")

    if generate_reel:
        if not script_text.strip():
            st.warning("الرجاء كتابة النص التعليقي.")
        else:
            temp_files = []
            try:
                with st.spinner("⏳ جاري تحضير الريلز والصوت بالذكاء الاصطناعي..."):
                    voice = VOICES[voice_label]
                    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                    temp_files.append(temp_audio_path)

                    async def generate_audio():
                        communicate = edge_tts.Communicate(script_text, voice)
                        await communicate.save(temp_audio_path)

                    asyncio.run(generate_audio())

                    audio_clip = AudioFileClip(temp_audio_path)
                    if audio_clip.duration < duration:
                        repeats = int(duration // audio_clip.duration) + 1
                        audio_clip = concatenate_audioclips([audio_clip] * repeats).subclip(0, duration)
                    else:
                        audio_clip = audio_clip.subclip(0, duration)

                    target_size = (1080, 1920) if aspect.startswith("عمودي") else (1080, 1080)
                    caption = overlay_caption.strip() or script_text.strip().split(".")[0][:90]

                    if uploaded_video is not None:
                        temp_src_video_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
                        temp_files.append(temp_src_video_path)
                        with open(temp_src_video_path, "wb") as f:
                            f.write(uploaded_video.read())

                        raw_video_clip = VideoFileClip(temp_src_video_path)
                        if raw_video_clip.duration < duration:
                            raw_video_clip = mp_loop(raw_video_clip, duration=duration)
                        else:
                            raw_video_clip = raw_video_clip.subclip(0, duration)

                        base_video_clip = fit_video_to_canvas(raw_video_clip, target_size).without_audio()

                        if add_text_overlay:
                            text_overlay_img = render_transparent_caption_band(target_size, caption)
                            temp_overlay_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            temp_files.append(temp_overlay_path)
                            text_overlay_img.save(temp_overlay_path)

                            text_clip = ImageClip(temp_overlay_path, transparent=True).set_duration(duration)
                            video_clip = CompositeVideoClip([base_video_clip, text_clip], size=target_size)
                        else:
                            video_clip = base_video_clip
                        video_clip = video_clip.set_duration(duration)
                    else:
                        images_list = []
                        if uploaded_images:
                            for f in uploaded_images:
                                images_list.append(Image.open(f))
                        elif use_generated_image and st.session_state["last_ad_card"] is not None:
                            images_list.append(st.session_state["last_ad_card"])
                        else:
                            images_list.append(Image.new("RGB", (1080, 1080), color=(30, 30, 50)))

                        per_image_duration = duration / len(images_list)
                        video_segments = []
                        for raw_img in images_list:
                            canvas = fit_image_to_canvas(raw_img, target_size)
                            if add_text_overlay:
                                canvas = overlay_caption_on_image(canvas, caption)

                            temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                            temp_files.append(temp_img_path)
                            canvas.save(temp_img_path)

                            video_segments.append(ImageClip(temp_img_path).set_duration(per_image_duration))

                        video_clip = concatenate_videoclips(video_segments, method="compose") if len(video_segments) > 1 else video_segments[0]

                    if background_music is not None:
                        temp_music_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                        temp_files.append(temp_music_path)
                        with open(temp_music_path, "wb") as f:
                            f.write(background_music.read())
                        music_clip = AudioFileClip(temp_music_path).volumex(music_volume)
                        if music_clip.duration < duration:
                            reps = int(duration // music_clip.duration) + 1
                            music_clip = concatenate_audioclips([music_clip] * reps).subclip(0, duration)
                        else:
                            music_clip = music_clip.subclip(0, duration)
                        final_audio = CompositeAudioClip([audio_clip, music_clip])
                    else:
                        final_audio = audio_clip

                    video_clip = video_clip.set_audio(final_audio)
                    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
                    temp_files.append(output_path)
                    video_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', logger=None)

                st.success("✅ تم توليد الريلز بنجاح!")
                st.video(output_path)
                with open(output_path, "rb") as f:
                    st.download_button("📥 تحميل الريلز (MP4)", data=f.read(), file_name="reel.mp4", mime="video/mp4")

            except Exception as e:
                st.error(f"حدث خطأ أثناء توليد الريلز: {e}")
            finally:
                for file in temp_files:
                    if os.path.exists(file):
                        try:
                            os.unlink(file)
                        except OSError:
                            pass
    st.markdown('</div>', unsafe_allow_html=True)

# ------------------------------------------
# التبويب الثالث: معرض الصور
# ------------------------------------------
with tab3:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🖼️ معرض الصور المولدة")

    gallery = st.session_state["gallery"]
    if not gallery:
        st.info("لا توجد صور بعد. أنشئ بطاقات إعلان أو استخدم ملف `ads.txt` لتظهر هنا تلقائياً.")
    else:
        cols = st.columns(3)
        for i, item in enumerate(reversed(gallery)):
            with cols[i % 3]:
                st.image(item["image"], caption=item["caption"], use_container_width=True)
                buf = io.BytesIO()
                item["image"].save(buf, format="PNG")
                st.download_button("📥 تحميل", data=buf.getvalue(), file_name=f"image_{i}.png", mime="image/png", key=f"dl_{i}")

        if st.button("🗑️ مسح المعرض"):
            st.session_state["gallery"] = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# تذييل الصفحة
# ==========================================
st.markdown("---")
st.caption("© 2026 Saeed PostGen - صُنع بحب في اليمن 🇾🇪")
