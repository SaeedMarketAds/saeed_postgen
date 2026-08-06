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
    
    submitted = st.form_submit_button("🎨 توليد وتصميم البطاقة الآن")

if submitted:
    # إنشاء لوحة إعلانية مقاس 1080x1080 مناسبة لمنصات التواصل
    img_width, img_height = 1080, 1080
    card = Image.new("RGB", (img_width, img_height), color=(18, 18, 28))
    draw = ImageDraw.Draw(card)
