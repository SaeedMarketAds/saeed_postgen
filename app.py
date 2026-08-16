# ==================================================
# 1. ضبط ترميز النظام شمولياً ليدعم العربية بدون مشاكل
# ==================================================
import os
import sys
import io

os.environ["PYTHONIOENCODING"] = "utf-8"
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
elif hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ===================================================
# 2. إعدادات الصفحة والهوية البصرية
# ===================================================
import streamlit as st

st.set_page_config(
    page_title="Saeed LogiC Pro & AI Studio",
    page_icon="🛍️",
    layout="centered"
)

# ===================================================
# 2.5. تخصيص الألوان المبهجة عبر CSS (أضيف حديثاً)
# ===================================================
st.markdown("""
<style>
    /* خلفية التطبيق العامة - تدرج دافئ */
    .stApp {
        background: linear-gradient(135deg, #fdfcfb 0%, #e2d1c3 100%);
    }
    /* الشريط الجانبي - شفاف مع ظل */
    .css-1d391kg {
        background-color: rgba(255, 255, 255, 0.8);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    /* العناوين الرئيسية - لون برتقالي وردي */
    h1, h2, h3 {
        color: #ff6f61;
        font-weight: bold;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    /* حقول الإدخال والقوائم المنسدلة */
    .stTextInput, .stTextArea, .stSelectbox, .stSlider {
        background-color: #fff9f0;
        border-radius: 12px;
        border: 1px solid #ffb3a0;
    }
    /* الأزرار الرئيسية - تدرج وردي مع تأثير hover */
    .stButton > button {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 30px;
        padding: 0.5rem 2rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 10px rgba(255, 154, 158, 0.4);
    }
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 20px rgba(255, 154, 158, 0.6);
    }
    /* صناديق الدردشة - خلفية شفافة مع ظل */
    .stChatMessage {
        background-color: rgba(255, 255, 255, 0.7);
        border-radius: 20px;
        padding: 10px 15px;
        margin: 5px 0;
        backdrop-filter: blur(5px);
    }
    /* تلوين رسائل المستخدم والمساعد */
    .stChatMessage .user {
        background-color: #d4e9ff;
    }
    .stChatMessage .assistant {
        background-color: #ffe6e6;
    }
    /* الروابط */
    a {
        color: #ff6f61;
    }
    /* عناصر الراديو */
    .stRadio > div {
        background-color: rgba(255, 255, 255, 0.6);
        border-radius: 15px;
        padding: 10px;
    }
    /* شريط التمرير */
    .stSlider > div {
        background-color: #ffd1c1;
    }
    /* رسائل النجاح والخطأ */
    .stSuccess {
        background-color: #d4edda;
        border-color: #c3e6cb;
    }
    .stError {
        background-color: #f8d7da;
        border-color: #f5c6cb;
    }
    /* أزرار التحميل - تدرج أخضر ناعم */
    .stDownloadButton > button {
        background: linear-gradient(135deg, #a8e6cf 0%, #d4edda 100%);
        color: #2d6a4f;
        border: none;
        border-radius: 30px;
        transition: all 0.3s ease;
    }
    .stDownloadButton > button:hover {
        transform: scale(1.05);
    }
</style>
""", unsafe_allow_html=True)

# ===================================================
# 3. جلب المفاتيح من st.secrets بأمان
# ===================================================
def get_secret_val(key_name, default=""):
    try:
        return st.secrets.get(key_name, default)
    except Exception:
        return os.getenv(key_name, default)

GEMINI_MAIN_KEY = get_secret_val("GEMINI_MAIN_KEY")
GEMINI_BACKUP_KEY = get_secret_val("GEMINI_BACKUP_KEY")
ELEVENLABS_API_KEY = get_secret_val("ELEVENLABS_API_KEY")
TELEGRAM_BOT_TOKEN_SAEED_MARKETADS = get_secret_val("TELEGRAM_BOT_TOKEN_SAEED_MARKETADS")
TELEGRAM_BOT_TOKEN_SAEED_PLUS = get_secret_val("TELEGRAM_BOT_TOKEN_SAEED_PLUS")
TELEGRAM_CHANNEL_ID = get_secret_val("TELEGRAM_CHANNEL_ID", "SeenMarket2026")

# ===================================================
# 4. دالة معالجة الردود النصية مع المفاتيح الاحتياطية
# ===================================================
import google.generativeai as genai
from google.generativeai import types

def get_smart_response(messages_history, temperature=0.7, max_tokens=2048):
    keys_to_try = [
        ("الرئيسي", GEMINI_MAIN_KEY),
        ("الاحتياطي", GEMINI_BACKUP_KEY)
    ]
    available_keys = [(name, k) for name, k in keys_to_try if k and k.strip()]
    
    if not available_keys:
        raise ValueError("لم يتم العثور على أي مفتاح Gemini API في إعدادات Secrets!")

    last_exception = None

    for key_name, api_key in available_keys:
        try:
            client = genai.Client(api_key=api_key)
            chat_contents = [
                types.Content(
                    role="user" if m["role"] == "user" else "model",
                    parts=[types.Part.from_text(text=m["content"])]
                ) for m in messages_history
            ]
            
            response = client.models.generate_content(
                 model="gemini-2.5-flash",
                contents=chat_contents,
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                    system_instruction="أنت مساعد التسوق الذكي الخاص بـ Saeed MarketAds. تقدم الإجابات بدقة، واحترافية، وتساعد المستخدمين في العثور على أفضل العروض والمنتجات."
                )
            )
            
            if response and response.text:
                return response.text
                
        except Exception as e:
            last_exception = e
            continue

    raise Exception(f"فشلت الاتصالات بجميع المفاتيح: {last_exception}")

# ===================================================
# 5. القائمة الجانبية (Sidebar) للتنقل والإعدادات
# ===================================================
with st.sidebar:
    st.header("🧭 التنقل في المنصة")
    app_mode = st.radio("اختر القسم:", ["🛍️ مساعد التسوق الذكي", "🎨 استوديو توليد الصور"])
    
    st.markdown("---")
    st.header("⚙️ إعدادات المحرك")
    temp_val = st.slider("مستوى الإبداع (Temperature)", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
    max_tok_val = st.slider("الحد الأقصى للكلمات (Max Tokens)", min_value=256, max_value=8192, value=2048, step=256)
    
    st.markdown("---")
    st.markdown("### 📡 حالة الاتصال")
    st.write(f"**المفتاح الرئيسي:** {'✅ مُفعل' if GEMINI_MAIN_KEY else '❌ غير متاح'}")
    st.write(f"**المفتاح الاحتياطي:** {'✅ مُفعل' if GEMINI_BACKUP_KEY else '❌ غير متاح'}")
    st.write(f"**القناة:** `@{TELEGRAM_CHANNEL_ID}`")

# ===================================================
# 6. واجهة القسم الأول: مساعد التسوق الذكي
# ===================================================
if app_mode == "🛍️ مساعد التسوق الذكي":
    st.title("🛍️ Saeed LogiC Pro")
    st.caption("مساعد التسوق الذكي - Saeed MarketAds")
    st.markdown("---")
    st.markdown("💡 **مرحباً بك يا سعيد!** اكتب استفسارك عن المنتجات أو العروض وسأقوم بمساعدتك فوراً.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_input := st.chat_input("اكتب سؤالك هنا (مثلاً: عروض نون اليوم)..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("جاري البحث عن أفضل العروض وتجهيز الرد..."):
                try:
                    bot_reply = get_smart_response(
                        st.session_state.messages,
                        temperature=temp_val,
                        max_tokens=max_tok_val
                    )
                    st.markdown(bot_reply)
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                except Exception as err:
                    st.error(f"عذراً، حدث خطأ أثناء الاتصال بالخادم: {err}")

# ===================================================
# 7. واجهة القسم الثاني: استوديو توليد الصور التفاعلي
# ===================================================
elif app_mode == "🎨 استوديو توليد الصور":
    st.title("🎨 استوديو سعيد للذكاء الاصطناعي - SaeedMarketAds")
    st.write("صمم صورك وإعلاناتك المبتكرة بالذكاء الاصطناعي وشاركها مع أصدقائك لجذب الزوار للمنصة!")
    st.markdown("---")

    style = st.selectbox(
        "اختر الستايل المطلوب للصورة:",
        [
            "صورة من الثمانينيات (Retro 80s Style)",
            "إعلان منتج احترافي (Product Ad)",
            "شخصية كرتونية ثلاثية الأبعاد (3D Avatar)",
            "فن نيون حديث (Neon Cyberpunk)"
        ]
    )

    user_prompt = st.text_input("صف ما تريد رؤيته في الصورة:", "شخص يرتدي زي كرتوني في مدينة ألعاب")

    if st.button("🚀 توليد الصورة الآن"):
        with st.spinner("جاري تصميم صورتك بالذكاء الاصطناعي..."):
            try:
                full_prompt = f"{user_prompt}, style: {style}, high quality, vibrant colors"
                
                # استخدام المفتاح الرئيسي لتوليد الصور
                active_key = GEMINI_MAIN_KEY if GEMINI_MAIN_KEY else GEMINI_BACKUP_KEY
                client = genai.Client(api_key=active_key)
                
                result = client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=full_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        output_mime_type="image/jpeg",
                        aspect_ratio="1:1",
                    )
                )
                
                for generated_image in result.generated_images:
                    from PIL import Image
                    image = Image.open(io.BytesIO(generated_image.image.image_bytes))
                    st.image(image, caption="تم التصميم بواسطة SaeedMarketAds 🛍️", use_container_width=True)
                    
                    # تحويل الصورة إلى بايتس للتحميل
                    buf = io.BytesIO()
                    image.save(buf, format="JPEG")
                    byte_im = buf.getvalue()

                    st.download_button(
                        label="📥 تحميل الصورة ومشاركتها",
                        data=byte_im,
                        file_name="saeed_ai_design.jpg",
                        mime="image/jpeg"
                    )
                    
                st.balloons()
                st.success("تم التصميم بنجاح! لا تنسَ مشاركتها مع أصدقائك ودعوتهم لاستخدام SaeedMarketAds.")

            except Exception as e:
                st.error(f"حدث خطأ أثناء التوليد: {e}")
