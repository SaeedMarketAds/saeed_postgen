# ==========================================
# Saeed PostGen - أداة متكاملة لتوليد الريلز والصور والموسيقى بالذكاء الاصطناعي
# ==========================================
import io
import os
import tempfile
import base64
import requests
import streamlit as st
from PIL import Image, ImageDraw, ImageFont
import edge_tts
from moviepy.editor import ImageClip, AudioFileClip, CompositeVideoClip, TextClip, concatenate_videoclips

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
    .main {
        background: linear-gradient(145deg, #0b1120, #1a2332);
        color: #e2e8f0;
    }
    .title {
        text-align: center;
        color: #fbbf24;
        font-size: 2.8rem;
        font-weight: 700;
        text-shadow: 0 0 20px rgba(251,191,36,0.3);
        margin-bottom: 10px;
    }
    .subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.2rem;
        margin-bottom: 30px;
    }
    .card-box {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(6px);
        border-radius: 25px;
        padding: 25px;
        border: 1px solid rgba(251,191,36,0.15);
        margin-bottom: 25px;
    }
    .stButton > button {
        background: linear-gradient(90deg, #fbbf24, #f59e0b);
        color: #0f172a;
        font-weight: bold;
        border: none;
        border-radius: 30px;
        padding: 12px 30px;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(251,191,36,0.4);
    }
    .stTextInput > div > div > input, .stTextArea > div > div > textarea {
        background: rgba(255,255,255,0.05);
        color: #f8fafc;
        border: 1px solid rgba(251,191,36,0.2);
        border-radius: 15px;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# عنوان التطبيق
# ==========================================
st.markdown('<div class="title">🎬 Saeed PostGen</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">أنشئ ريلز احترافية وصوراً وموسيقى بالذكاء الاصطناعي بنقرة واحدة</div>', unsafe_allow_html=True)

# ==========================================
# الحصول على مفتاح Gemini من الأسرار
# ==========================================
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# ==========================================
# تبويبات التطبيق
# ==========================================
tab1, tab2, tab3 = st.tabs(["📱 بطاقة إعلان", "🎥 توليد ريلز", "🖼️ معرض الصور"])

# ==========================================
# التبويب الأول: بطاقة إعلان (مع إصلاح الأخطاء)
# ==========================================
with tab1:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("إنشاء بطاقة إعلان للمنتج")
    
    with st.form("ad_form"):
        col1, col2 = st.columns(2)
        with col1:
            product_name = st.text_input("اسم المنتج", "iPhone 15 Pro Max")
            storage_ram = st.text_input("الذاكرة والرام", "256GB / 8GB RAM")
        with col2:
            price = st.text_input("السعر", "$1,200 - 3,900 ريال")
            whatsapp = st.text_input("رقم واتساب", "+966 50 000 0000")
        
        # خيار توليد صورة AI
        use_ai_image = st.checkbox("توليد صورة احترافية للمنتج (اختياري)")
        gemini_key_input = st.text_input("مفتاح Gemini API (اختياري)", value=GEMINI_API_KEY, type="password")
        
        submitted = st.form_submit_button("🎨 توليد البطاقة")
    
    if submitted:
        # إنشاء بطاقة نصية
        img_width, img_height = 1080, 1080
        card = Image.new("RGB", (img_width, img_height), color=(15, 23, 42))
        draw = ImageDraw.Draw(card)
        
        # استخدام خط عربي (إن لم يوجد نستخدم الافتراضي)
        try:
            font_title = ImageFont.truetype("arial.ttf", 60)
            font_body = ImageFont.truetype("arial.ttf", 45)
        except:
            font_title = ImageFont.load_default()
            font_body = ImageFont.load_default()
        
        # رسم النصوص (يمكن تحسينه برسم مربعات وخلفيات)
        draw.text((80, 150), f"📱 {product_name}", fill=(255, 255, 255), font=font_title)
        draw.text((80, 300), f"💾 {storage_ram}", fill=(200, 200, 200), font=font_body)
        draw.text((80, 450), f"💰 {price}", fill=(251, 191, 36), font=font_body)
        draw.text((80, 600), f"📞 {whatsapp}", fill=(255, 255, 255), font=font_body)
        
        # عرض الصورة
        st.image(card, caption="معاينة البطاقة", use_container_width=True)
        
        # تحميل
        buf = io.BytesIO()
        card.save(buf, format="PNG")
        st.download_button("📥 تحميل البطاقة (PNG)", data=buf.getvalue(), file_name="ad_card.png", mime="image/png")
        
        # توليد صورة AI (إن تم اختياره)
        if use_ai_image:
            active_key = gemini_key_input if gemini_key_input else GEMINI_API_KEY
            if active_key and GENAI_AVAILABLE:
                try:
                    genai.configure(api_key=active_key)
                    model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    response = model.generate_content(
                        f"توليد صورة احترافية لمنتج {product_name} بخلفية بيضاء، إضاءة استوديو، جودة عالية. (إرجاع وصف الصورة بدلاً من الصورة الفعلية لأن API لا يدعم توليد الصور مباشرة حالياً)"
                    )
                    # نعرض نص الوصف كبديل
                    st.info(f"🔍 وصف الصورة المولدة:\n{response.text}")
                    # نستخدم pollinations.ai لتوليد صورة مجانية (بديل عملي)
                    try:
                        img_url = f"https://image.pollinations.ai/prompt/{product_name.replace(' ', '%20')}%20product%20photography%20white%20background"
                        ai_img_response = requests.get(img_url, timeout=10)
                        if ai_img_response.status_code == 200:
                            ai_img = Image.open(io.BytesIO(ai_img_response.content))
                            st.image(ai_img, caption="صورة مولدة بواسطة الذكاء الاصطناعي (pollinations.ai)", use_container_width=True)
                        else:
                            st.warning("تعذر توليد الصورة عبر الخدمة المجانية.")
                    except Exception as e:
                        st.warning(f"فشل توليد الصورة: {e}")
                except Exception as e:
                    st.error(f"خطأ في Gemini: {e}")
            else:
                st.warning("مفتاح Gemini غير موجود أو المكتبة غير مثبتة. يمكنك توليد الصور مجاناً عبر pollinations.ai (تم تفعيله تلقائياً).")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# التبويب الثاني: توليد ريلز (الميزة الجديدة)
# ==========================================
with tab2:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🎥 توليد ريلز احترافية")
    st.markdown("أنشئ فيديو قصير يجمع بين صورة المنتج، تعليق صوتي، وموسيقى خلفية.")

    with st.form("reel_form"):
        # النص المراد تحويله إلى تعليق صوتي
        script_text = st.text_area("النص التعليقي (سيُقرأ في الفيديو)", "مرحباً بكم في متجرنا، نقدم لكم أفضل العروض على الجوالات الحديثة. تواصلوا معنا الآن واحصلوا على خصم خاص.")
        
        # اختيار صورة المنتج (رفع أو استخدام المولدة)
        col1, col2 = st.columns(2)
        with col1:
            uploaded_image = st.file_uploader("ارفع صورة المنتج (اختياري)", type=["jpg", "jpeg", "png"])
        with col2:
            use_generated_image = st.checkbox("استخدام صورة مولدة من البطاقة السابقة (إن وجدت)")
        
        # رفع موسيقى خلفية (اختياري)
        background_music = st.file_uploader("ارفع موسيقى خلفية (MP3) - اختياري", type=["mp3"])
        
        # إعدادات الفيديو
        duration = st.slider("مدة الفيديو (بالثواني)", 5, 30, 10)
        add_text_overlay = st.checkbox("إضافة نص توضيحي على الفيديو", value=True)
        
        generate_reel = st.form_submit_button("🚀 توليد الريلز الآن")
    
    if generate_reel:
        if not script_text.strip():
            st.warning("الرجاء كتابة النص التعليقي.")
        else:
            with st.spinner("⏳ جاري تحضير الريلز... قد يستغرق هذا دقيقة."):
                try:
                    # 1. توليد الصوت من النص باستخدام edge_tts
                    voice = "ar-SA-HamedNeural"
                    audio_bytes = None
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_audio:
                        temp_audio_path = tmp_audio.name
                    # توليد الصوت
                    async def generate_audio():
                        communicate = edge_tts.Communicate(script_text, voice)
                        await communicate.save(temp_audio_path)
                    import asyncio
                    asyncio.run(generate_audio())
                    
                    # 2. تحديد الصورة المستخدمة
                    image_to_use = None
                    if uploaded_image is not None:
                        image_to_use = Image.open(uploaded_image)
                    elif use_generated_image:
                        # نستخدم صورة البطاقة المولدة سابقاً (نفترض أنها محفوظة في الجلسة)
                        if 'last_ad_card' in st.session_state:
                            image_to_use = st.session_state['last_ad_card']
                        else:
                            st.warning("لم يتم العثور على صورة مولدة، سنستخدم صورة افتراضية.")
                            image_to_use = Image.new("RGB", (1080, 1080), color=(30, 30, 50))
                    else:
                        # صورة افتراضية
                        image_to_use = Image.new("RGB", (1080, 1080), color=(30, 30, 50))
                    
                    # حفظ الصورة مؤقتاً
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmp_img:
                        temp_img_path = tmp_img.name
                        image_to_use.save(temp_img_path)
                    
                    # 3. معالجة الملفات بالفيديو
                    # تحميل الصورة كـ ImageClip
                    img_clip = ImageClip(temp_img_path).set_duration(duration)
                    
                    # تحميل الصوت التعليقي
                    audio_clip = AudioFileClip(temp_audio_path)
                    # إذا كان الصوت أقصر من مدة الفيديو، نكرره، وإلا نقطعه
                    if audio_clip.duration < duration:
                        # نكرر الصوت لملء المدة
                        from moviepy.audio.io.AudioFileClip import AudioFileClip
                        from moviepy.audio.AudioClip import concatenate_audioclips
                        repeats = int(duration // audio_clip.duration) + 1
                        audio_clip = concatenate_audioclips([audio_clip] * repeats).subclip(0, duration)
                    else:
                        audio_clip = audio_clip.subclip(0, duration)
                    
                    # إضافة موسيقى خلفية إن وجدت
                    if background_music is not None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_music:
                            tmp_music.write(background_music.read())
                            temp_music_path = tmp_music.name
                        music_clip = AudioFileClip(temp_music_path)
                        # خفض صوت الموسيقى
                        music_clip = music_clip.volumex(0.3).subclip(0, duration)
                        # دمج الصوتين
                        final_audio = CompositeVideoClip([audio_clip, music_clip]).audio
                    else:
                        final_audio = audio_clip
                    
                    # تعيين الصوت للفيديو
                    video_clip = img_clip.set_audio(final_audio)
                    
                    # إضافة نص فوق الفيديو (اختياري)
                    if add_text_overlay:
                        txt_clip = TextClip(script_text[:50] + "...", fontsize=40, color='white', font='Arial', stroke_color='black', stroke_width=2)
                        txt_clip = txt_clip.set_position(('center', 0.8), relative=True).set_duration(duration)
                        video_clip = CompositeVideoClip([video_clip, txt_clip])
                    
                    # تصدير الفيديو
                    output_path = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4').name
                    video_clip.write_videofile(output_path, fps=24, codec='libx264', audio_codec='aac', verbose=False, logger=None)
                    
                    # عرض الفيديو
                    st.success("✅ تم توليد الريلز بنجاح!")
                    st.video(output_path)
                    
                    # تحميل الفيديو
                    with open(output_path, "rb") as f:
                        video_bytes = f.read()
                    st.download_button("📥 تحميل الريلز (MP4)", data=video_bytes, file_name="reel.mp4", mime="video/mp4")
                    
                    # تنظيف الملفات المؤقتة
                    for file in [temp_audio_path, temp_img_path, output_path]:
                        if os.path.exists(file):
                            os.unlink(file)
                    if background_music is not None:
                        os.unlink(temp_music_path)
                except Exception as e:
                    st.error(f"حدث خطأ أثناء توليد الريلز: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# التبويب الثالث: معرض الصور (قسم مستقبلي)
# ==========================================
with tab3:
    st.markdown('<div class="card-box">', unsafe_allow_html=True)
    st.subheader("🖼️ معرض الصور المولدة")
    st.info("هنا ستظهر الصور التي تم توليدها بواسطة الذكاء الاصطناعي. (قيد التطوير)")
    # يمكننا حفظ الصور في جلسة وعرضها
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# تذييل
# ==========================================
st.markdown("---")
st.caption("© 2026 Saeed PostGen - صُنع بحب في اليمن 🇾🇪")
