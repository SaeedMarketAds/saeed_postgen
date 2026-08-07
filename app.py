import io
import streamlit as st
from PIL import Image, ImageDraw

# إعدادات الصفحة
st.set_page_config(page_title="Saeed PostGen", page_icon="⚡", layout="centered")

st.markdown("<h2 style='text-align: center; color: #00FFCC;'>⚡ Saeed PostGen - صانع إعلانات المركز الدولي</h2>", unsafe_allow_html=True)
st.write("أداة مستقلة لتوليد بطاقات إعلانية احترافية للجوالات والأسعار وتجهيزها للنشر الفوري.")

with st.form("postgen_form"):
    st.markdown("### أدخل تفاصيل الإعلان:")
    phone_name = st.text_input("اسم الجوال", "Samsung S23 Ultra")
    storage = st.text_input("الذاكرة والرام", "256 جيجا / 12 رام")
    price = st.text_input("السعر", "$500 - 318,000 ريال")
    whatsapp = st.text_input("رقم الواتساب للتواصل", "+967 777...")
    
    # خيار توليد صورة بالذكاء الاصطناعي
    st.markdown("---")
    use_ai_image = st.checkbox("توليد صورة احترافية للمنتج عبر DALL-E (اختياري)")
    openai_api_key = st.text_input("مفتاح OpenAI API", type="password")
    
    submitted = st.form_submit_button("🎨 توليد وتصميم البطاقة الآن")

if submitted:
    # إنشاء لوحة إعلانية مقاس 1080x1080 مناسبة لمنصات التواصل
    img_width, img_height = 1080, 1080
    card = Image.new("RGB", (img_width, img_height), color=(18, 18, 28))
    draw = ImageDraw.Draw(card)
    
    # رسم النصوص على البطاقة
    draw.text((80, 150), f"Device: {phone_name}", fill=(255, 255, 255))
    draw.text((80, 300), f"Storage: {storage}", fill=(200, 200, 200))
    draw.text((80, 450), f"Price: {price}", fill=(0, 255, 150))
    draw.text((80, 600), f"WhatsApp: {whatsapp}", fill=(255, 255, 255))
    
    # عرض الصورة في واجهة Streamlit
    st.image(card, caption="معاينة بطاقة الإعلان", use_container_width=True)
    
    # تجهيز الصورة للتحميل
    buf = io.BytesIO()
    card.save(buf, format="PNG")
    byte_im = buf.getvalue()
    
    st.download_button(
        label="📥 تحميل البطاقة (PNG)",
        data=byte_im,
        file_name="ad_card.png",
        mime="image/png"
    )
    
    # توليد صورة المنتج بالذكاء الاصطناعي إذا تم تفعيل الخيار وإدخال المفتاح
    if use_ai_image:
        if openai_api_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_api_key)
                with st.spinner("جاري توليد صورة المنتج عبر الذكاء الاصطناعي..."):
                    response = client.images.generate(
                        model="dall-e-3",
                        prompt=f"Professional product photography of {phone_name}, white background, high quality",
                        n=1,
                        size="1024x1024"
                    )
                    image_url = response.data[0].url
                    st.image(image_url, caption="صورة المنتج المولدة بالذكاء الاصطناعي", use_container_width=True)
            except Exception as e:
                st.error(f"حدث خطأ أثناء الاتصال بخدمة الذكاء الاصطناعي: {e}")
        else:
            st.warning("يرجى إدخال مفتاح OpenAI API لتوليد الصورة.")
