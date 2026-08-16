# ==========================================
# Saeed PostGen - أداة متكاملة لتوليد الريلز والصور والموسيقى بالذكاء الاصطناعي
# نسخة محسّنة: قوالب تصميم، دعم عربي صحيح، معرض صور فعلي، إعدادات فيديو أوسع
# ==========================================
import io
import os
import tempfile
import asyncio
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip
from moviepy.audio.AudioClip import concatenate_audioclips

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
# إعدادات الصفحة
# ==========================================
st.set_page_config(
    page_title="Saeed PostGen - صانع المحتوى بالذكاء الاصطناعي",
    page_icon="🎬",
    layout="wide"
)

# ==========================================
# CSS مخصص لتحسين المظهر
# ==========================================
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
    }
    .stButton > button {
        background: linear-gradient(90deg, #fbbf24, #f59e0b); color: #0f172a; font-weight: bold;
        border: none; border-radius: 30px; padding: 12px 30px; transition: all 0.3s;
    }
    .stButton > button:hover { transform: scale(1.02); box-shadow: 0 8px 25px rgba(251,191,36,0.4); }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.05); color: #f8fafc;
        border: 1px solid rgba(251,191,36,0.2); border-radius: 15px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🎬 Saeed PostGen</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">أنشئ ريلز احترافية وصوراً وموسيقى بالذكاء الاصطناعي بنقرة واحدة</div>', unsafe_allow_html=True)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# تهيئة معرض الصور والذاكرة المؤقتة للجلسة
if "gallery" not in st.session_state:
    st.session_state["gallery"] = []  # كل عنصر: {"image": PIL.Image, "caption": str}
if "last_ad_card" not in st.session_state:
    st.session_state["last_ad_card"] = None

# ==========================================
# قوالب تصميم البطاقة
# ==========================================
TEMPLATES = {
    "ذهبي فاخر": {"bg": (15, 23, 42), "accent": (251, 191, 36), "text": (255, 255, 255), "sub": (200, 200, 200)},
    "أزرق تقني": {"bg": (10, 20, 40), "accent": (56, 189, 248), "text": (255, 255, 255), "sub": (180, 200, 220)},
    "أخضر عصري": {"bg": (12, 30, 24), "accent": (52, 211, 153), "text": (255, 255, 255), "sub": (190, 220, 205)},
    "أحمر جريء": {"bg": (30, 12, 12), "accent": (248, 113, 113), "text": (255, 255, 255), "sub": (220, 190, 190)},
}


def get_font(size, bold=True):
    """يحاول تحميل خط عربي مناسب، وإلا يستخدم الخط الافتراضي."""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def ar(text):
    """يهيئ النص العربي للعرض الصحيح (اتصال الحروف + اتجاه من اليمين لليسار)."""
    if ARABIC_SUPPORT and text:
        try:
            reshaped = arabic_reshaper.reshape(text)
            return get_display(reshaped)
        except Exception:
            return text
    return text


def draw_rounded_rect(draw, xy, radius, fill):
    draw.rounded_rectangle(xy, radius=radius, fill=fill)


def build_ad_card(product_name, storage_ram, price, whatsapp, template_name, logo_img=None):
    tpl = TEMPLATES[template_name]
    w, h = 1080, 1080
    card = Image.new("RGB", (w, h), color=tpl["bg"])

    # تدرج خفيف في الخلفية لإضافة عمق
    gradient = Image.new("L", (1, h), color=0)
    for y in range(h):
        gradient.putpixel((0, y), int(40 * (y / h)))
    gradient = gradient.resize((w, h))
    overlay = Image.new("RGB", (w, h), tpl["accent"])
    card = Image.composite(overlay, card, gradient.point(lambda p: p // 6))

    draw = ImageDraw.Draw(card)

    # شريط علوي مميز
    draw_rounded_rect(draw, [(60, 60), (w - 60, 140)], 20, tpl["accent"])
    title_font = get_font(48)
    brand_text = ar("عرض خاص")
    bbox = draw.textbbox((0, 0), brand_text, font=title_font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, 70), brand_text, fill=tpl["bg"], font=title_font)

    # بطاقة المحتوى الرئيسية
    draw_rounded_rect(draw, [(60, 190), (w - 60, h - 220)], 30, (255, 255, 255, 10))
    content_box = [(90, 220), (w - 90, h - 250)]
    draw.rounded_rectangle(content_box, radius=25, outline=tpl["accent"], width=3)

    font_title = get_font(56)
    font_body = get_font(42, bold=False)

    y = 280
    draw.text((130, y), ar(f"📱 {product_name}"), fill=tpl["text"], font=font_title)
    y += 110
    draw.text((130, y), ar(f"💾 {storage_ram}"), fill=tpl["sub"], font=font_body)
    y += 90
    draw.text((130, y), ar(f"💰 {price}"), fill=tpl["accent"], font=font_title)
    y += 110
    draw.text((130, y), ar(f"📞 {whatsapp}"), fill=tpl["text"], font=font_body)

    # شعار اختياري
    if logo_img is not None:
        logo = logo_img.convert("RGBA")
        logo.thumbnail((150, 150))
        card.paste(logo, (w - 200, h - 200), logo)

    # تذييل
    footer_font = get_font(28, bold=False)
    footer_text = ar("تواصل معنا الآن للطلب")
    bbox = draw.textbbox((0, 0), footer_text, font=footer_font)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) / 2, h - 190), footer_text, fill=tpl["sub"], font=footer_font)

    return card


# ==========================================
# تبويبات التطبيق
# ==========================================
tab1, tab2, tab3 = st.tabs(["📱 بطاقة إعلان", "🎥 توليد ريلز", "🖼️ معرض الصور"])

# ==========================================
# التبويب الأول: بطاقة إعلان
# ==========================================
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

        use_ai_image = st.checkbox("توليد صورة احترافية للمنتج (اختياري)")
        gemini_key_input = st.text_input("مفتاح Gemini API (اختياري)", value=GEMINI_API_KEY, type="password")

        submitted = st.form_submit_button("🎨 توليد البطاقة")

    if submitted:
        logo_img = Image.open(logo_upload) if logo_upload is not None else None
        card = build_ad_card(product_name, storage_ram, price, whatsapp, template_name, logo_img)

        # حفظ في الجلسة والمعرض
        st.session_state["last_ad_card"] = card
        st.session_state["gallery"].append({"image": card, "caption": f"بطاقة: {product_name}"})

        st.image(card, caption="معاينة البطاقة", use_container_width=True)

        buf = io.BytesIO()
        card.save(buf, format="PNG")
        st.download_button("📥 تحميل البطاقة (PNG)", data=buf.getvalue(), file_name="ad_card.png", mime="image/png")

        if use_ai_image:
            active_key = gemini_key_input if gemini_key_input else GEMINI_API_KEY
            if active_key and GENAI_AVAILABLE:
                try:
                    genai.configure(api_key=active_key)
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    response = model.generate_content(
                        f"وصف صورة احترافية لمنتج {product_name} بخلفية بيضاء، إضاءة استوديو، جودة عالية."
                    )
                    st.info(f"🔍 وصف الصورة المولدة:\n{response.text}")
                except Exception as e:
                    st.error(f"خطأ في Gemini: {e}")

            try:
                img_url = f"https://image.pollinations.ai/prompt/{product_name.replace(' ', '%20')}%20product%20photography%20white%20background"
                ai_img_response = requests.get(img_url, timeout=15)
                if ai_img_response.status_code == 200:
                    ai_img = Image.open(io.BytesIO(ai_img_response.content))
                    st.image(ai_img, caption="صورة مولدة بواسطة الذكاء الاصطناعي (pollinations.ai)", use_container_width=True)
                    st.session_state["gallery"].append({"image": ai_img, "caption": f"صورة AI: {product_name}"})
                else:
                    st.warning("تعذر توليد الصورة عبر الخدمة المجانية، حاول مرة أخرى.")
            except Exception as e:
                st.warning(f"فشل توليد الصورة: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# التبويب الثاني: توليد ريلز
# ==========================================
with tab2:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🎥 توليد ريلز احترافية")
    st.markdown("أنشئ فيديو قصير يجمع بين صورة المنتج، تعليق صوتي، وموسيقى خلفية.")

    VOICES = {
        "رجالي - سعودي (حامد)": "ar-SA-HamedNeural",
        "نسائي - سعودي (زارية)": "ar-SA-ZariyahNeural",
        "رجالي - مصري (شاكر)": "ar-EG-ShakirNeural",
        "نسائي - مصري (سلمى)": "ar-EG-SalmaNeural",
    }

    with st.form("reel_form"):
        script_text = st.text_area(
            "النص التعليقي (سيُقرأ في الفيديو)",
            "مرحباً بكم في متجرنا، نقدم لكم أفضل العروض على الجوالات الحديثة. تواصلوا معنا الآن واحصلوا على خصم خاص."
        )

        col1, col2 = st.columns(2)
        with col1:
            uploaded_image = st.file_uploader("ارفع صورة المنتج (اختياري)", type=["jpg", "jpeg", "png"])
            voice_label = st.selectbox("الصوت", list(VOICES.keys()))
        with col2:
            use_generated_image = st.checkbox("استخدام صورة مولدة من البطاقة السابقة (إن وجدت)")
            aspect = st.selectbox("أبعاد الفيديو", ["عمودي 9:16 (ريلز/ستوري)", "مربع 1:1"])

        background_music = st.file_uploader("ارفع موسيقى خلفية (MP3) - اختياري", type=["mp3"])
        music_volume = st.slider("مستوى صوت الموسيقى", 0.0, 1.0, 0.3)
        duration = st.slider("مدة الفيديو (بالثواني)", 5, 30, 10)
        add_text_overlay = st.checkbox("إضافة نص توضيحي على الفيديو", value=True)

        generate_reel = st.form_submit_button("🚀 توليد الريلز الآن")

    if generate_reel:
        if not script_text.strip():
            st.warning("الرجاء كتابة النص التعليقي.")
        else:
            temp_files = []
            try:
                with st.spinner("⏳ جاري تحضير الريلز... قد يستغرق هذا دقيقة."):
                    # 1. توليد الصوت
                    voice = VOICES[voice_label]
                    temp_audio_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3').name
                    temp_files.append(temp_audio_path)

                    async def generate_audio():
                        communicate = edge_tts.Communicate(script_text, voice)
                        await communicate.save(temp_audio_path)

                    asyncio.run(generate_audio())

                    # 2. تحديد الصورة وضبط الأبعاد
                    if uploaded_image is not None:
                        image_to_use = Image.open(uploaded_image)
                    elif use_generated_image and st.session_state["last_ad_card"] is not None:
                        image_to_use = st.session_state["last_ad_card"]
                    else:
                        image_to_use = Image.new("RGB", (1080, 1080), color=(30, 30, 50))

                    image_to_use = image_to_use.convert("RGB")
                    if aspect.startswith("عمودي"):
                        target_size = (1080, 1920)
                    else:
                        target_size = (1080, 1080)

                    # يلائم الصورة داخل الإطار المطلوب مع خلفية معتّمة خلفها
                    canvas = image_to_use.resize(target_size) if image_to_use.size != target_size else image_to_use
                    if aspect.startswith("عمودي"):
                        bg = image_to_use.resize(target_size).filter(ImageFilter.GaussianBlur(20))
                        fitted = image_to_use.copy()
                        fitted.thumbnail((target_size[0], target_size[0]))
                        canvas = bg.copy()
                        canvas.paste(fitted, ((target_size[0] - fitted.width) // 2, (target_size[1] - fitted.height) // 2))

                    temp_img_path = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    temp_files.append(temp_img_path)
                    canvas.save(temp_img_path)

                    # 3. بناء الفيديو
                    img_clip = ImageClip(temp_img_path).set_duration(duration)

                    audio_clip = AudioFileClip(temp_audio_path)
                    if audio_clip.duration < duration:
                        repeats = int(duration // audio_clip.duration) + 1
                        audio_clip = concatenate_audioclips([audio_clip] * repeats).subclip(0, duration)
                    else:
                        audio_clip = audio_clip.subclip(0, duration)

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
                        final_audio = CompositeVideoClip([img_clip]).set_audio(audio_clip).audio
                        # دمج الصوتين عبر CompositeAudioClip الصحيح
                        from moviepy.audio.AudioClip import CompositeAudioClip
                        final_audio = CompositeAudioClip([audio_clip, music_clip])
                    else:
                        final_audio = audio_clip

                    video_clip = img_clip.set_audio(final_audio)

                    if add_text_overlay:
                        try:
                            txt_clip = TextClip(
                                script_text[:60] + ("..." if len(script_text) > 60 else ""),
                                fontsize=40, color='white', method='caption',
                                size=(target_size[0] - 120, None), stroke_color='black', stroke_width=2
                            )
                            txt_clip = txt_clip.set_position(('center', 0.85), relative=True).set_duration(duration)
                            video_clip = CompositeVideoClip([video_clip, txt_clip])
                        except Exception:
                            # في حال عدم توفر خط ImageMagick على الخادم، نتجاهل النص بدل فشل كامل العملية
                            st.warning("تعذّر إضافة النص فوق الفيديو (مشكلة خطوط على الخادم)، تم إنشاء الفيديو بدونه.")

                    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
                    temp_files.append(output_path)
                    video_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', logger=None)

                st.success("✅ تم توليد الريلز بنجاح!")
                st.video(output_path)

                with open(output_path, "rb") as f:
                    video_bytes = f.read()
                st.download_button("📥 تحميل الريلز (MP4)", data=video_bytes, file_name="reel.mp4", mime="video/mp4")

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

# ==========================================
# التبويب الثالث: معرض الصور
# ==========================================
with tab3:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🖼️ معرض الصور المولدة")

    gallery = st.session_state["gallery"]
    if not gallery:
        st.info("لا توجد صور بعد. أنشئ بطاقة إعلان من التبويب الأول وستظهر هنا تلقائياً.")
    else:
        cols = st.columns(3)
        for i, item in enumerate(reversed(gallery)):
            with cols[i % 3]:
                st.image(item["image"], caption=item["caption"], use_container_width=True)
                buf = io.BytesIO()
                item["image"].save(buf, format="PNG")
                st.download_button("📥 تحميل", data=buf.getvalue(), file_name=f"image_{i}.png",
                                    mime="image/png", key=f"dl_{i}")

        if st.button("🗑️ مسح المعرض"):
            st.session_state["gallery"] = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# تذييل
# ==========================================
st.markdown("---")
st.caption("© 2026 Saeed PostGen - صُنع بحب في اليمن 🇾🇪")
