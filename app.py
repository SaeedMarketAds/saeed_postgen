# ================================================================
# SAEED POSTGEN 4.6
# UNIFIED STREAMLIT APPLICATION
# FILE: app.py
# ================================================================

from __future__ import annotations

import asyncio
import html
import io
import os
import re
import tempfile
import uuid
from pathlib import Path
from datetime import datetime
from typing import Any

import streamlit as st
from PIL import Image

from core.database import get_connection, fetch_one, fetch_all, execute, DB_PATH
from core.auth import (
    init_auth_session,
    is_authenticated,
    current_user_id,
    current_role,
    get_current_user,
    is_admin,
    logout_user,
    render_login_page,
    render_user_header,
)
from core.content_guard import (
    ContentStatus,
    check_content,
    check_content_package,
    status_label,
)
from core.engines import (
    generate_image,
    generate_post,
    generate_ad_card,
    generate_reel,
    generate_video,
    add_text_overlay,
    fit_image,
)

# Optional AI / voice dependencies are loaded lazily.


# ================================================================
# PATHS
# ================================================================

# الحصول على المسار المطلق للمجلد الذي يوجد فيه app.py
BASE_DIR = Path(__file__).resolve().parent

# المجلد الرئيسي للوسائط
MEDIA_DIR = BASE_DIR / "media"

# المجلدات الفرعية
IMAGE_DIR = MEDIA_DIR / "images"
POST_DIR = MEDIA_DIR / "posts"
AD_DIR = MEDIA_DIR / "ads"
REEL_DIR = MEDIA_DIR / "reels"
VIDEO_DIR = MEDIA_DIR / "videos"

# مجلد الخطوط
FONT_DIR = BASE_DIR / "fonts"


# ================================================================
# SAFE MEDIA DIRECTORY INITIALIZATION
# ================================================================

def ensure_media_directories() -> None:
    """
    إنشاء مجلدات الوسائط بأمان.

    يحل مشكلة FileExistsError التي تحدث عندما يكون:
        media
    ملفًا عاديًا بدل أن يكون مجلدًا.

    كذلك يفحص المجلدات الفرعية في حال وجود ملف بنفس الاسم.
    """

    folders = (
        IMAGE_DIR,
        POST_DIR,
        AD_DIR,
        REEL_DIR,
        VIDEO_DIR,
    )

    # ------------------------------------------------------------
    # 1. إصلاح MEDIA_DIR إذا كان ملفًا
    # ------------------------------------------------------------

    if MEDIA_DIR.exists() and MEDIA_DIR.is_file():
        try:
            MEDIA_DIR.unlink()
        except Exception as exc:
            raise RuntimeError(
                f"تعذر حذف الملف المتعارض مع مجلد media: {MEDIA_DIR}\n"
                f"الخطأ: {exc}"
            ) from exc

    # ------------------------------------------------------------
    # 2. إنشاء المجلد الرئيسي
    # ------------------------------------------------------------

    MEDIA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    # ------------------------------------------------------------
    # 3. إنشاء المجلدات الفرعية بأمان
    # ------------------------------------------------------------

    for folder in folders:

        # إذا كان هناك ملف بنفس اسم المجلد
        if folder.exists() and folder.is_file():
            try:
                folder.unlink()
            except Exception as exc:
                raise RuntimeError(
                    f"تعذر حذف الملف المتعارض مع المجلد:\n"
                    f"{folder}\n"
                    f"الخطأ: {exc}"
                ) from exc

        # إنشاء المجلد
        folder.mkdir(
            parents=True,
            exist_ok=True,
        )

    # ------------------------------------------------------------
    # 4. إنشاء مجلد الخطوط إذا لم يكن موجودًا
    # ------------------------------------------------------------

    if FONT_DIR.exists() and FONT_DIR.is_file():
        try:
            FONT_DIR.unlink()
        except Exception as exc:
            raise RuntimeError(
                f"تعذر حذف الملف المتعارض مع مجلد fonts: {FONT_DIR}\n"
                f"الخطأ: {exc}"
            ) from exc

    FONT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# تنفيذ إنشاء المسارات قبل استخدام أي ملف وسائط
ensure_media_directories()


# ================================================================
# APPLICATION SETTINGS
# ================================================================

APP_NAME = "Saeed PostGen"
VERSION = "4.6"
BRAND = "SaeedMarketAds"

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-2.5-flash",
)

TEMPLATES = [
    "ذهبي فاخر",
    "أزرق تقني",
    "أخضر عصري",
    "أحمر جريء",
]

EDGE_VOICES = {
    "سعودي - Hamed": "ar-SA-HamedNeural",
    "سعودي - Zariyah": "ar-SA-ZariyahNeural",
    "مصري - Shakir": "ar-EG-ShakirNeural",
    "مصري - Salma": "ar-EG-SalmaNeural",
    "إماراتي - Hamdan": "ar-AE-HamdanNeural",
    "إماراتي - Fatima": "ar-AE-FatimaNeural",
    "أردني - Taim": "ar-JO-TaimNeural",
    "أردنية - Sana": "ar-JO-SanaNeural",
}


# ================================================================
# PAGE / STYLE
# ================================================================

st.set_page_config(
    page_title="Saeed PostGen 4.6",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_css() -> None:
    st.markdown(
        """
        <style>

        .stApp {
            background:
                radial-gradient(
                    circle at 20% 0%,
                    rgba(212,175,55,.08),
                    transparent 30%
                ),
                radial-gradient(
                    circle at 90% 20%,
                    rgba(30,80,140,.10),
                    transparent 35%
                ),
                #070b12;

            color: #f4f4f4;
        }

        .block-container {
            max-width: 1450px;
            padding-top: 1.2rem;
        }

        .pg-card {
            background:
                linear-gradient(
                    145deg,
                    rgba(18,24,35,.96),
                    rgba(8,12,19,.96)
                );

            border: 1px solid rgba(212,175,55,.18);
            border-radius: 18px;
            padding: 18px;
            margin-bottom: 14px;
        }

        .pg-gold {
            color: #d4af37;
        }

        .pg-muted {
            color: #9aa4b2;
        }

        .pg-title {
            font-size: 2rem;
            font-weight: 800;
        }

        .pg-subtitle {
            color: #9aa4b2;
            margin-top: -8px;
        }

        .metric-box {
            background: #0d131d;
            border: 1px solid rgba(255,255,255,.07);
            border-radius: 16px;
            padding: 14px;
            text-align: center;
        }

        .metric-value {
            font-size: 1.7rem;
            font-weight: 800;
            color: #d4af37;
        }

        .metric-label {
            color: #aab2bf;
            font-size: .85rem;
        }

        .status-approved {
            color: #48d597;
            font-weight: 700;
        }

        .status-review {
            color: #e7b84b;
            font-weight: 700;
        }

        .status-blocked {
            color: #ff6969;
            font-weight: 700;
        }

        div[data-testid="stSidebar"] {
            background: #080c13;
        }

        .stButton > button {
            border-radius: 10px;
        }

        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css()

init_auth_session()

if not is_authenticated():
    render_login_page()
    st.stop()


# ================================================================
# DATABASE HELPERS
# ================================================================

def db_one(
    query: str,
    params: tuple[Any, ...] = (),
) -> dict[str, Any] | None:

    return fetch_one(
        query,
        params,
    )


def db_all(
    query: str,
    params: tuple[Any, ...] = (),
) -> list[dict[str, Any]]:

    return fetch_all(
        query,
        params,
    )


def now_text() -> str:
    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def user_store() -> dict[str, Any] | None:

    uid = current_user_id()

    if not uid:
        return None

    return db_one(
        """
        SELECT *
        FROM stores
        WHERE user_id=?
        ORDER BY id
        LIMIT 1
        """,
        (uid,),
    )


def ensure_store() -> dict[str, Any] | None:
    store = user_store()

    if store:
        return store

    return None


def save_store(
    data: dict[str, Any],
) -> tuple[bool, str, int]:

    uid = current_user_id()

    if not uid:
        return False, "لا يوجد مستخدم مسجل", 0

    existing = user_store()

    if existing:

        execute(
            """
            UPDATE stores
            SET
                page_name=?,
                slug=?,
                logo_path=?,
                cover_path=?,
                primary_color=?,
                secondary_color=?,
                phone=?,
                description=?,
                business_type=?,
                updated_at=?
            WHERE id=?
            """,
            (
                data.get("page_name", ""),
                data.get("slug", ""),
                data.get("logo_path", ""),
                data.get("cover_path", ""),
                data.get("primary_color", "#D4AF37"),
                data.get("secondary_color", "#0B0F19"),
                data.get("phone", ""),
                data.get("description", ""),
                data.get("business_type", ""),
                now_text(),
                existing["id"],
            ),
        )

        return (
            True,
            "تم تحديث هوية المتجر",
            int(existing["id"]),
        )

    store_id = execute(
        """
        INSERT INTO stores
        (
            user_id,
            page_name,
            slug,
            logo_path,
            cover_path,
            primary_color,
            secondary_color,
            phone,
            description,
            business_type,
            created_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            uid,
            data.get("page_name", ""),
            data.get("slug", ""),
            data.get("logo_path", ""),
            data.get("cover_path", ""),
            data.get("primary_color", "#D4AF37"),
            data.get("secondary_color", "#0B0F19"),
            data.get("phone", ""),
            data.get("description", ""),
            data.get("business_type", ""),
            now_text(),
            now_text(),
        ),
    )

    return (
        True,
        "تم إنشاء هوية المتجر",
        int(store_id),
    )


def save_uploaded_file(
    uploaded: Any,
    directory: Path,
    prefix: str,
) -> str:

    if uploaded is None:
        return ""

    suffix = (
        Path(uploaded.name).suffix.lower()
        or ".png"
    )

    name = (
        f"{prefix}_"
        f"{uuid.uuid4().hex[:10]}"
        f"{suffix}"
    )

    path = directory / name

    path.write_bytes(
        uploaded.getvalue()
    )

    return str(
        path.relative_to(BASE_DIR)
    )


def absolute_path(
    relative_path: str,
) -> Path | None:

    if not relative_path:
        return None

    p = BASE_DIR / relative_path

    return p if p.exists() else None


def store_id_for_user() -> int | None:

    store = user_store()

    if store:
        return int(store["id"])

    return None


def save_product(
    name: str,
    description: str,
    price: str,
    currency: str,
    image_path: str,
    specifications: str,
) -> tuple[bool, str]:

    uid = current_user_id()
    sid = store_id_for_user()

    if not uid or not sid:
        return (
            False,
            "أنشئ هوية المتجر أولاً.",
        )

    try:

        pid = execute(
            """
            INSERT INTO products
            (
                user_id,
                store_id,
                name,
                description,
                price,
                currency,
                image_path,
                specifications,
                is_active,
                created_at
            )
            VALUES (?,?,?,?,?,?,?,?,1,?)
            """,
            (
                uid,
                sid,
                name,
                description,
                price,
                currency,
                image_path,
                specifications,
                now_text(),
            ),
        )

        return (
            True,
            f"تم حفظ المنتج #{pid}",
        )

    except Exception as exc:

        return (
            False,
            f"تعذر حفظ المنتج: {exc}",
        )


def save_content(
    content_type: str,
    title: str,
    description: str,
    file_path: str,
    status: str,
    reason: str,
) -> int:

    uid = current_user_id()
    sid = store_id_for_user()

    if not uid or not sid:
        return 0

    return execute(
        """
        INSERT INTO content
        (
            user_id,
            store_id,
            content_type,
            title,
            description,
            file_path,
            status,
            guard_reason,
            created_at,
            updated_at
        )
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            uid,
            sid,
            content_type,
            title,
            description,
            file_path,
            status,
            reason,
            now_text(),
            now_text(),
        ),
    )


def save_campaign(
    name: str,
    objective: str,
    platform: str,
    budget: str,
    currency: str,
    start_date: str,
    end_date: str,
) -> tuple[bool, str]:

    uid = current_user_id()
    sid = store_id_for_user()

    if not uid or not sid:
        return (
            False,
            "أنشئ هوية المتجر أولاً.",
        )

    try:

        cid = execute(
            """
            INSERT INTO campaigns
            (
                user_id,
                store_id,
                name,
                objective,
                platform,
                budget,
                currency,
                start_date,
                end_date,
                status,
                created_at
            )
            VALUES (?,?,?,?,?,?,?,?,?,'DRAFT',?)
            """,
            (
                uid,
                sid,
                name,
                objective,
                platform,
                budget,
                currency,
                start_date,
                end_date,
                now_text(),
            ),
        )

        return (
            True,
            f"تم حفظ الحملة #{cid} كمسودة",
        )

    except Exception as exc:

        return (
            False,
            f"تعذر حفظ الحملة: {exc}",
        )


def count_rows(
    table: str,
    where: str = "",
    params: tuple[Any, ...] = (),
) -> int:

    allowed = {
        "users",
        "stores",
        "products",
        "content",
        "campaigns",
        "reports",
    }

    if table not in allowed:
        return 0

    row = db_one(
        f"SELECT COUNT(*) AS n FROM {table} {where}",
        params,
    )

    return int(row["n"]) if row else 0


# ================================================================
# GENERAL HELPERS
# ================================================================

def esc(value: Any) -> str:
    return html.escape(
        str(value or "")
    )


def file_bytes(
    relative_path: str,
) -> bytes | None:

    p = absolute_path(
        relative_path
    )

    if not p:
        return None

    try:
        return p.read_bytes()
    except Exception:
        return None


def render_status(
    status: str,
) -> str:

    s = str(
        status or "REVIEW"
    ).upper()

    if s == "APPROVED":
        return "🟢 APPROVED"

    if s == "BLOCKED":
        return "🔴 BLOCKED"

    return "🟡 REVIEW"


def guard_preview(
    title: str,
    description: str,
    text: str = "",
) -> Any:

    return check_content_package(
        title=title,
        description=description,
        text=text,
    )


def save_generated_result(
    result: dict[str, Any],
    content_type: str,
    title: str,
    description: str,
) -> int:

    path = result.get(
        "path",
        "",
    )

    status = str(
        result.get(
            "status",
            "REVIEW",
        )
    )

    message = str(
        result.get(
            "message",
            "",
        )
    )

    return save_content(
        content_type,
        title,
        description,
        path,
        status,
        message,
    )


# ================================================================
# GEMINI
# ================================================================

def gemini_generate(
    prompt: str,
) -> tuple[bool, str]:

    key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not key:

        try:
            key = st.secrets.get(
                "GEMINI_API_KEY",
                "",
            )
        except Exception:
            key = ""

    if not key:
        return (
            False,
            "لم يتم ضبط GEMINI_API_KEY أو GOOGLE_API_KEY.",
        )

    try:

        from google import genai

        client = genai.Client(
            api_key=key
        )

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        text = getattr(
            response,
            "text",
            None,
        )

        if not text:
            return (
                False,
                "Gemini لم يرجع نصًا.",
            )

        return (
            True,
            str(text),
        )

    except Exception as exc:

        return (
            False,
            f"خطأ Gemini: {exc}",
        )


# ================================================================
# TTS
# ================================================================

def clean_tts_text(
    text: str,
) -> str:

    text = re.sub(
        r"https?://\S+",
        "",
        text,
    )

    text = re.sub(
        r"```.*?```",
        "",
        text,
        flags=re.S,
    )

    text = re.sub(
        r"[*_#>`]",
        "",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def create_tts(
    text: str,
    voice: str,
) -> tuple[bool, str, bytes | None]:

    text = clean_tts_text(text)

    if not text:
        return (
            False,
            "النص فارغ.",
            None,
        )

    try:

        import edge_tts

        out = (
            Path(tempfile.gettempdir())
            / f"saeed_postgen_{uuid.uuid4().hex}.mp3"
        )

        async def run() -> None:

            communicate = edge_tts.Communicate(
                text,
                voice,
            )

            await communicate.save(
                str(out)
            )

        asyncio.run(run())

        return (
            True,
            "تم إنشاء الصوت.",
            out.read_bytes(),
        )

    except Exception as edge_exc:

        try:

            from gtts import gTTS

            fp = (
                Path(tempfile.gettempdir())
                / f"saeed_postgen_{uuid.uuid4().hex}.mp3"
            )

            gTTS(
                text=text,
                lang="ar",
            ).save(str(fp))

            return (
                True,
                "تم إنشاء الصوت عبر gTTS.",
                fp.read_bytes(),
            )

        except Exception as gtts_exc:

            return (
                False,
                f"تعذر إنشاء الصوت: {edge_exc} / {gtts_exc}",
                None,
            )


# ================================================================
# HEADER
# ================================================================

def render_header(
    title: str,
    subtitle: str = "",
) -> None:

    st.markdown(
        f"""
        <div class='pg-card' dir='rtl'>

            <div class='pg-title'>
                🎨
                <span class='pg-gold'>
                    {esc(title)}
                </span>
            </div>

            <div class='pg-subtitle'>
                {esc(subtitle)}
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )


# ================================================================
# PAGE — DASHBOARD
# ================================================================

def page_dashboard() -> None:

    render_header(
        "Saeed PostGen 4.6",
        "محرك تصميم وتنفيذ المحتوى التجاري — جاهز للتكامل مع Saeed LogiC",
    )

    uid = current_user_id()
    sid = store_id_for_user()

    cols = st.columns(5)

    metrics = [
        (
            "👤",
            "الحساب",
            1,
        ),
        (
            "🏪",
            "المتجر",
            count_rows(
                "stores",
                "WHERE user_id=?",
                (uid,),
            ) if uid else 0,
        ),
        (
            "📦",
            "المنتجات",
            count_rows(
                "products",
                "WHERE user_id=?",
                (uid,),
            ) if uid else 0,
        ),
        (
            "🎨",
            "المحتوى",
            count_rows(
                "content",
                "WHERE user_id=?",
                (uid,),
            ) if uid else 0,
        ),
        (
            "📢",
            "الحملات",
            count_rows(
                "campaigns",
                "WHERE user_id=?",
                (uid,),
            ) if uid else 0,
        ),
    ]

    for col, (
        icon,
        label,
        value,
    ) in zip(
        cols,
        metrics,
    ):

        with col:

            st.markdown(
                f"""
                <div class='metric-box'>

                    <div>{icon}</div>

                    <div class='metric-value'>
                        {value}
                    </div>

                    <div class='metric-label'>
                        {esc(label)}
                    </div>

                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        "### 🚀 مركز التنفيذ"
    )

    a, b, c, d = st.columns(4)

    with a:
        st.info(
            "🎨 **التصميم**\n\n"
            "صورة، منشور، بطاقة إعلان، Story."
        )

    with b:
        st.info(
            "🎬 **الفيديو**\n\n"
            "Reel Cover ثم MP4 من صورة ثابتة."
        )

    with c:
        st.info(
            "🛡️ **Content Guard**\n\n"
            "APPROVED / REVIEW / BLOCKED."
        )

    with d:
        st.info(
            "🧠 **جاهز لـ LogiC**\n\n"
            "المحركات منفصلة عن الواجهة."
        )

    if sid is None:

        st.warning(
            "ابدأ من صفحة 🏪 هوية المتجر قبل حفظ المنتجات والمحتوى."
        )

    else:

        store = user_store()

        st.success(
            f"المتجر الحالي: {store.get('page_name','')}"
            if store
            else
            "المتجر جاهز"
        )


# ================================================================
# PAGE — STORE
# ================================================================

def page_store() -> None:

    render_header(
        "هوية المتجر",
        "هوية مستقلة لكل تاجر محفوظة في postgen.db",
    )

    store = user_store() or {}

    with st.form("store_form"):

        page_name = st.text_input(
            "اسم الصفحة / المتجر",
            value=store.get(
                "page_name",
                "",
            ),
        )

        slug = st.text_input(
            "Slug",
            value=store.get(
                "slug",
                "",
            ),
        )

        business_type = st.text_input(
            "نوع النشاط",
            value=store.get(
                "business_type",
                "",
            ),
        )

        phone = st.text_input(
            "رقم التواصل",
            value=store.get(
                "phone",
                "",
            ),
        )

        description = st.text_area(
            "وصف النشاط",
            value=store.get(
                "description",
                "",
            ),
            height=100,
        )

        primary = st.color_picker(
            "اللون الأساسي",
            value=store.get(
                "primary_color",
                "#D4AF37",
            ),
        )

        secondary = st.color_picker(
            "اللون الثانوي",
            value=store.get(
                "secondary_color",
                "#0B0F19",
            ),
        )

        logo = st.file_uploader(
            "الشعار",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
            key="store_logo",
        )

        cover = st.file_uploader(
            "الغلاف",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
            key="store_cover",
        )

        submitted = st.form_submit_button(
            "💾 حفظ هوية المتجر",
            use_container_width=True,
        )

    if submitted:

        logo_path = store.get(
            "logo_path",
            "",
        )

        cover_path = store.get(
            "cover_path",
            "",
        )

        if logo:
            logo_path = save_uploaded_file(
                logo,
                IMAGE_DIR,
                "store_logo",
            )

        if cover:
            cover_path = save_uploaded_file(
                cover,
                IMAGE_DIR,
                "store_cover",
            )

        ok, msg, _ = save_store(
            {
                "page_name": page_name,
                "slug": slug,
                "logo_path": logo_path,
                "cover_path": cover_path,
                "primary_color": primary,
                "secondary_color": secondary,
                "phone": phone,
                "description": description,
                "business_type": business_type,
            }
        )

        (
            st.success
            if ok
            else st.error
        )(msg)

        if ok:
            st.rerun()

    current = user_store()

    if current:

        st.markdown(
            "### معاينة الهوية"
        )

        if (
            current.get("cover_path")
            and absolute_path(
                current["cover_path"]
            )
        ):

            st.image(
                str(
                    absolute_path(
                        current["cover_path"]
                    )
                ),
                use_container_width=True,
            )

        x, y = st.columns(
            [1, 3]
        )

        with x:

            if (
                current.get("logo_path")
                and absolute_path(
                    current["logo_path"]
                )
            ):

                st.image(
                    str(
                        absolute_path(
                            current["logo_path"]
                        )
                    ),
                    width=160,
                )

        with y:

            st.subheader(
                current.get(
                    "page_name",
                    "",
                )
            )

            st.write(
                current.get(
                    "description",
                    "",
                )
            )

            st.caption(
                f"{current.get('business_type','')} • "
                f"{current.get('phone','')}"
            )


# ================================================================
# PAGE — PRODUCTS
# ================================================================

def page_products() -> None:

    render_header(
        "المنتجات",
        "كتالوج التاجر الذي يمكن استخدامه لاحقًا كمصدر بيانات لـ Saeed LogiC",
    )

    if not store_id_for_user():

        st.warning(
            "أنشئ هوية المتجر أولاً."
        )

        return

    with st.form("product_form"):

        name = st.text_input(
            "اسم المنتج"
        )

        description = st.text_area(
            "الوصف"
        )

        c1, c2, c3 = st.columns(3)

        with c1:

            price = st.text_input(
                "السعر"
            )

        with c2:

            currency = st.text_input(
                "العملة",
                value="USD",
            )

        with c3:

            image = st.file_uploader(
                "صورة المنتج",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                ],
            )

        specifications = st.text_area(
            "المواصفات"
        )

        submit = st.form_submit_button(
            "📦 حفظ المنتج",
            use_container_width=True,
        )

    if submit:

        if not name.strip():

            st.error(
                "اسم المنتج مطلوب."
            )

        else:

            image_path = (
                save_uploaded_file(
                    image,
                    IMAGE_DIR,
                    "product",
                )
                if image
                else ""
            )

            ok, msg = save_product(
                name,
                description,
                price,
                currency,
                image_path,
                specifications,
            )

            (
                st.success
                if ok
                else st.error
            )(msg)

    rows = db_all(
        """
        SELECT *
        FROM products
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (current_user_id(),),
    )

    st.markdown(
        "### المنتجات المحفوظة"
    )

    for row in rows:

        c1, c2 = st.columns(
            [1, 4]
        )

        with c1:

            p = absolute_path(
                row.get(
                    "image_path",
                    "",
                )
            )

            if p:
                st.image(
                    str(p),
                    width=150,
                )

        with c2:

            st.markdown(
                f"**{esc(row.get('name'))}**",
                unsafe_allow_html=True,
            )

            st.write(
                row.get(
                    "description",
                    "",
                )
            )

            st.caption(
                f"{row.get('price','')} "
                f"{row.get('currency','')} | "
                f"{row.get('specifications','')}"
            )


# ================================================================
# PAGE — DESIGN
# ================================================================

def page_design() -> None:

    render_header(
        "التصميم",
        "PostGen ينفذ التصميم؛ أما فهم القرار التسويقي الذكي فيبقى من اختصاص Saeed LogiC لاحقًا.",
    )

    if not store_id_for_user():

        st.warning(
            "أنشئ هوية المتجر أولاً."
        )

        return

    content_type = st.selectbox(
        "نوع المحتوى",
        [
            "منشور",
            "بطاقة إعلان",
            "Story",
            "Reel",
            "فيديو",
        ],
    )

    products = db_all(
        """
        SELECT *
        FROM products
        WHERE user_id=?
        AND is_active=1
        ORDER BY id DESC
        """,
        (current_user_id(),),
    )

    product_names = [
        p.get(
            "name",
            "",
        )
        for p in products
    ]

    title = st.text_input(
        "العنوان",
        value="",
    )

    prompt = st.text_area(
        "وصف التصميم / Prompt",
        height=120,
        placeholder=(
            "مثال: إعلان فاخر لهاتف ذكي، "
            "خلفية تقنية داكنة، إضاءة احترافية"
        ),
    )

    contact = st.text_input(
        "رقم التواصل",
        value=(
            user_store() or {}
        ).get(
            "phone",
            "",
        ),
    )

    if content_type == "بطاقة إعلان":

        product_name = (
            st.selectbox(
                "المنتج",
                product_names,
            )
            if product_names
            else
            st.text_input(
                "اسم المنتج"
            )
        )

        price = st.text_input(
            "السعر"
        )

        specifications = st.text_area(
            "المواصفات"
        )

        template = st.selectbox(
            "القالب",
            TEMPLATES,
        )

        product_upload = st.file_uploader(
            "صورة المنتج — اختياري",
            type=[
                "png",
                "jpg",
                "jpeg",
                "webp",
            ],
        )

    else:

        product_name = ""
        price = ""
        specifications = ""
        template = TEMPLATES[0]
        product_upload = None

    st.markdown(
        "### 🛡️ الفحص قبل التنفيذ"
    )

    guard = guard_preview(
        title,
        prompt,
        product_name
        if content_type == "بطاقة إعلان"
        else "",
    )

    st.write(
        render_status(
            guard.status.value
        )
    )

    st.caption(
        guard.message
    )

    if guard.reasons:

        st.warning(
            " • ".join(
                guard.reasons
            )
        )

    generate = st.button(
        "✨ توليد المحتوى",
        type="primary",
        use_container_width=True,
    )

    if not generate:
        return

    if guard.status == ContentStatus.BLOCKED:

        st.error(
            "تم إيقاف التنفيذ بواسطة Content Guard."
        )

        return

    if (
        not title.strip()
        and content_type != "بطاقة إعلان"
    ):

        st.error(
            "العنوان مطلوب."
        )

        return

    store = user_store() or {}

    brand = (
        store.get("page_name")
        or BRAND
    )

    try:

        result: dict[str, Any]

        final_type = content_type

        if content_type == "منشور":

            result = generate_post(
                title=title,
                prompt=prompt,
                brand=brand,
                contact=contact,
                filename=(
                    f"post_"
                    f"{uuid.uuid4().hex[:10]}.png"
                ),
            )

        elif content_type == "بطاقة إعلان":

            uploaded_path = (
                save_uploaded_file(
                    product_upload,
                    IMAGE_DIR,
                    "ad_product",
                )
                if product_upload
                else ""
            )

            product_image = (
                absolute_path(
                    uploaded_path
                )
                if uploaded_path
                else None
            )

            result = generate_ad_card(
                product_name=product_name,
                price=price,
                specifications=specifications,
                contact=contact,
                brand=brand,
                template="gold",
                product_image=product_image,
                filename=(
                    f"ad_"
                    f"{uuid.uuid4().hex[:10]}.png"
                ),
            )

            final_type = "بطاقة إعلان"

        elif content_type == "Story":

            raw = generate_image(
                prompt or title,
                width=1080,
                height=1920,
                filename=(
                    f"story_raw_"
                    f"{uuid.uuid4().hex[:10]}.png"
                ),
            )

            if not raw.get("success"):

                result = raw

            else:

                img = raw.get("image")

                if (
                    img is None
                    and raw.get("path")
                ):

                    img = Image.open(
                        raw["path"]
                    )

                final = add_text_overlay(
                    img,
                    title=title,
                    brand=brand,
                    contact=contact,
                    size=(1080, 1920),
                )

                out = (
                    POST_DIR
                    / (
                        f"story_"
                        f"{uuid.uuid4().hex[:10]}.png"
                    )
                )

                final.save(
                    out,
                    format="PNG",
                )

                result = {
                    "success": True,
                    "status": raw.get(
                        "status",
                        "APPROVED",
                    ),
                    "message": "تم إنشاء Story.",
                    "path": str(
                        out.relative_to(
                            BASE_DIR
                        )
                    ),
                    "image": final,
                }

                final_type = "Story"

        elif content_type == "Reel":

            result = generate_reel(
                title=title,
                prompt=prompt,
                brand=brand,
                contact=contact,
                filename=(
                    f"reel_cover_"
                    f"{uuid.uuid4().hex[:10]}.png"
                ),
            )

            final_type = "Reel"

        else:

            source = st.session_state.get(
                "last_generated_path",
                "",
            )

            if not source:

                st.error(
                    "أنشئ صورة أو منشورًا أولاً ثم حوّله إلى فيديو."
                )

                return

            src = absolute_path(
                source
            )

            if not src:

                st.error(
                    "ملف المصدر غير موجود."
                )

                return

            out = (
                VIDEO_DIR
                / (
                    f"video_"
                    f"{uuid.uuid4().hex[:10]}.mp4"
                )
            )

            result = generate_video(
                str(src),
                output_path=str(out),
                duration=10,
                fps=30,
            )

            final_type = "فيديو"

        if result.get("success"):

            st.session_state.last_generated_path = (
                result.get(
                    "path",
                    "",
                )
            )

            st.session_state.last_generated_result = result

            cid = save_generated_result(
                result,
                final_type,
                title or product_name,
                prompt or specifications,
            )

            st.success(
                f"تم التنفيذ والحفظ. Content ID: {cid}"
            )

        else:

            st.error(
                result.get(
                    "message",
                    "تعذر التنفيذ.",
                )
            )

    except Exception as exc:

        st.exception(exc)

    result = st.session_state.get(
        "last_generated_result"
    )

    if result and result.get("path"):

        st.markdown(
            "### النتيجة"
        )

        p = absolute_path(
            result["path"]
        )

        if (
            p
            and p.suffix.lower()
            in {
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
            }
        ):

            st.image(
                str(p),
                use_container_width=True,
            )

        elif (
            p
            and p.suffix.lower()
            == ".mp4"
        ):

            st.video(
                str(p)
            )

        data = file_bytes(
            result["path"]
        )

        if data:

            mime = (
                "video/mp4"
                if p
                and p.suffix.lower()
                == ".mp4"
                else
                "image/png"
            )

            st.download_button(
                "📥 تنزيل الملف",
                data=data,
                file_name=(
                    p.name
                    if p
                    else
                    "output"
                ),
                mime=mime,
            )


# ================================================================
# PAGE — AI
# ================================================================

def page_ai() -> None:

    render_header(
        "Saeed AI Assistant",
        "مساعد نصي للتجربة فقط؛ لا يمثل عقل Saeed LogiC النهائي.",
    )

    if "ai_messages" not in st.session_state:

        st.session_state.ai_messages = []

    for msg in st.session_state.ai_messages:

        with st.chat_message(
            msg["role"]
        ):

            st.markdown(
                msg["content"]
            )

    prompt = st.chat_input(
        "اكتب طلبك التسويقي أو فكرة التصميم..."
    )

    if prompt:

        st.session_state.ai_messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        ok, answer = gemini_generate(
            "أنت مساعد تسويق عربي لمنصة Saeed PostGen. "
            "حلل الطلب واقترح نوع المحتوى والعنوان والوصف والتصميم "
            "دون الادعاء أنك نفذت التصميم.\n\n"
            + prompt
        )

        if not ok:

            answer = (
                answer
                + "\n\n"
                "يمكنك استخدام صفحة التصميم مباشرة لتنفيذ المحتوى يدويًا."
            )

        st.session_state.ai_messages.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        st.rerun()


# ================================================================
# PAGE — VOICE
# ================================================================

def page_voice() -> None:

    render_header(
        "الصوت",
        "تحويل النص إلى صوت — يعمل من الكتابة ولا يتطلب ميكروفونًا.",
    )

    text = st.text_area(
        "النص",
        height=180,
    )

    voice_name = st.selectbox(
        "الصوت",
        list(
            EDGE_VOICES.keys()
        ),
    )

    if st.button(
        "🎙️ إنشاء الصوت",
        type="primary",
        use_container_width=True,
    ):

        ok, msg, data = create_tts(
            text,
            EDGE_VOICES[
                voice_name
            ],
        )

        (
            st.success
            if ok
            else st.error
        )(msg)

        if data:

            st.audio(
                data,
                format="audio/mp3",
            )

            st.download_button(
                "📥 تنزيل الصوت",
                data=data,
                file_name=(
                    "saeed_postgen_voice.mp3"
                ),
                mime="audio/mpeg",
            )


# ================================================================
# PAGE — CAMPAIGNS
# ================================================================

def page_campaigns() -> None:

    render_header(
        "الحملات المدفوعة",
        "إدارة بيانات الحملة داخل PostGen. النشر الفعلي على المنصات الخارجية يحتاج تكامل APIs/OAuth لاحقًا.",
    )

    if not store_id_for_user():

        st.warning(
            "أنشئ هوية المتجر أولاً."
        )

        return

    with st.form("campaign_form"):

        name = st.text_input(
            "اسم الحملة"
        )

        objective = st.text_input(
            "الهدف"
        )

        platform = st.selectbox(
            "المنصة",
            [
                "Facebook",
                "Instagram",
                "TikTok",
                "YouTube",
                "Google",
                "أخرى",
            ],
        )

        c1, c2 = st.columns(2)

        with c1:

            budget = st.text_input(
                "الميزانية"
            )

            currency = st.text_input(
                "العملة",
                value="USD",
            )

        with c2:

            start = st.date_input(
                "تاريخ البداية"
            )

            end = st.date_input(
                "تاريخ النهاية"
            )

        submit = st.form_submit_button(
            "📢 حفظ الحملة",
            use_container_width=True,
        )

    if submit:

        if not name.strip():

            st.error(
                "اسم الحملة مطلوب."
            )

        else:

            ok, msg = save_campaign(
                name,
                objective,
                platform,
                budget,
                currency,
                str(start),
                str(end),
            )

            (
                st.success
                if ok
                else st.error
            )(msg)

    rows = db_all(
        """
        SELECT *
        FROM campaigns
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (current_user_id(),),
    )

    for row in rows:

        with st.container(
            border=True
        ):

            st.markdown(
                f"**{esc(row.get('name'))}**",
                unsafe_allow_html=True,
            )

            st.write(
                f"الهدف: {row.get('objective','')} | "
                f"المنصة: {row.get('platform','')}"
            )

            st.caption(
                f"{row.get('budget','')} "
                f"{row.get('currency','')} • "
                f"{row.get('start_date','')} → "
                f"{row.get('end_date','')} • "
                f"{row.get('status','DRAFT')}"
            )


# ================================================================
# PAGE — GALLERY
# ================================================================

def page_gallery() -> None:

    render_header(
        "معرض التاجر",
        "المعرض الدائم من postgen.db + الملفات المحفوظة داخل media/",
    )

    rows = db_all(
        """
        SELECT *
        FROM content
        WHERE user_id=?
        ORDER BY id DESC
        """,
        (current_user_id(),),
    )

    if not rows:

        st.info(
            "لا يوجد محتوى محفوظ حتى الآن."
        )

        return

    for row in rows:

        path = row.get(
            "file_path",
            "",
        )

        p = absolute_path(
            path
        )

        with st.container(
            border=True
        ):

            c1, c2 = st.columns(
                [1.2, 2]
            )

            with c1:

                if (
                    p
                    and p.suffix.lower()
                    in {
                        ".png",
                        ".jpg",
                        ".jpeg",
                        ".webp",
                    }
                ):

                    st.image(
                        str(p),
                        use_container_width=True,
                    )

                elif (
                    p
                    and p.suffix.lower()
                    == ".mp4"
                ):

                    st.video(
                        str(p)
                    )

                else:

                    st.caption(
                        "الملف غير موجود"
                    )

            with c2:

                st.subheader(
                    row.get(
                        "title"
                    )
                    or
                    "بدون عنوان"
                )

                st.write(
                    row.get(
                        "description",
                        "",
                    )
                )

                st.write(
                    render_status(
                        row.get(
                            "status",
                            "REVIEW",
                        )
                    )
                )

                st.caption(
                    f"النوع: "
                    f"{row.get('content_type','')} "
                    f"• ID: "
                    f"{row.get('id')}"
                )

                if p and p.exists():

                    data = p.read_bytes()

                    mime = (
                        "video/mp4"
                        if p.suffix.lower()
                        == ".mp4"
                        else
                        "image/png"
                    )

                    st.download_button(
                        "📥 تنزيل",
                        data=data,
                        file_name=p.name,
                        mime=mime,
                        key=(
                            f"download_{row['id']}"
                        ),
                    )


# ================================================================
# PAGE — REPORTS
# ================================================================

def page_reports() -> None:

    render_header(
        "التقارير والمراجعة",
        "Content Guard يسجل حالة المحتوى؛ يمكن للتاجر الإبلاغ عن محتوى يحتاج مراجعة.",
    )

    rows = db_all(
        """
        SELECT
            c.*,
            r.id AS report_id,
            r.reason AS report_reason,
            r.status AS report_status
        FROM content c
        LEFT JOIN reports r
            ON r.content_id=c.id
        WHERE c.user_id=?
        ORDER BY c.id DESC
        """,
        (current_user_id(),),
    )

    for row in rows:
        with st.container(
            border=True
        ):
            st.write(
                f"**{row.get('title') or 'بدون عنوان'}** — "
                f"{render_status(row.get('status'))}"
            )

            if row.get("report_id"):
                st.caption(
                    f"بلاغ #{row.get('report_id')} • "
                    f"{row.get('report_reason', '')} • "
                    f"{row.get('report_status', 'OPEN')}"
                )
