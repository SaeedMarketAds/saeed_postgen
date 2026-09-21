# ================================================================
# SAEED POSTGEN 4.6
# AUTHENTICATION ENGINE
# FILE: core/auth.py
# ================================================================

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any

import streamlit as st

from core.database import execute, fetch_one


# ================================================================
# CONFIG
# ================================================================

HASH_ITERATIONS = 200_000
MIN_PASSWORD_LENGTH = 6
MIN_USERNAME_LENGTH = 3


# ================================================================
# PASSWORD SECURITY
# ================================================================

def hash_password(password: str) -> str:
    """
    تشفير كلمة المرور باستخدام PBKDF2-HMAC-SHA256.
    """

    if not password:
        raise ValueError("كلمة المرور مطلوبة.")

    salt = secrets.token_bytes(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        HASH_ITERATIONS,
    )

    return (
        f"pbkdf2_sha256$"
        f"{HASH_ITERATIONS}$"
        f"{salt.hex()}$"
        f"{password_hash.hex()}"
    )


def verify_password(
    password: str,
    stored_hash: str,
) -> bool:
    """
    التحقق من كلمة المرور المشفرة.
    """

    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")

        if len(parts) != 4:
            return False

        algorithm, iterations, salt_hex, hash_hex = parts

        if algorithm != "pbkdf2_sha256":
            return False

        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )

        return hmac.compare_digest(
            actual_hash,
            expected_hash,
        )

    except (
        ValueError,
        TypeError,
        OverflowError,
    ):
        return False


# ================================================================
# VALIDATION
# ================================================================

def normalize_email(email: str) -> str:
    """
    تنظيف البريد الإلكتروني وتوحيد حالته.
    """

    return str(email or "").strip().lower()


def normalize_username(username: str) -> str:
    """
    تنظيف اسم المستخدم.
    """

    return str(username or "").strip()


def normalize_phone(phone: str) -> str:
    """
    تنظيف رقم الهاتف بدون تغيير محتواه.
    """

    return str(phone or "").strip()


def validate_email(email: str) -> bool:
    """
    تحقق بسيط من صيغة البريد الإلكتروني.
    """

    email = normalize_email(email)

    if not email:
        return False

    pattern = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

    return bool(
        re.match(
            pattern,
            email,
        )
    )


def validate_username(username: str) -> bool:
    """
    التحقق من اسم المستخدم.

    يسمح بالأحرف والأرقام وبعض الرموز الشائعة.
    """

    username = normalize_username(username)

    if len(username) < MIN_USERNAME_LENGTH:
        return False

    pattern = r"^[A-Za-z0-9_.\-]+$"

    return bool(
        re.match(
            pattern,
            username,
        )
    )


# ================================================================
# SESSION
# ================================================================

def init_auth_session() -> None:
    """
    تهيئة جلسة المصادقة.
    """

    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": "",
        "email": "",
        "role": "",
        "full_name": "",
        "remember_me": False,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


def is_authenticated() -> bool:
    """
    هل المستخدم مسجل الدخول؟
    """

    return bool(
        st.session_state.get(
            "authenticated",
            False,
        )
    )


def current_user_id() -> int | None:
    """
    الحصول على ID المستخدم الحالي.
    """

    user_id = st.session_state.get("user_id")

    if user_id is None:
        return None

    try:
        return int(user_id)

    except (
        TypeError,
        ValueError,
    ):
        return None


def current_username() -> str:
    """
    اسم المستخدم الحالي.
    """

    return str(
        st.session_state.get(
            "username",
            "",
        )
    )


def current_email() -> str:
    """
    البريد الإلكتروني للمستخدم الحالي.
    """

    return str(
        st.session_state.get(
            "email",
            "",
        )
    )


def current_role() -> str:
    """
    صلاحية المستخدم الحالي.
    """

    return str(
        st.session_state.get(
            "role",
            "",
        )
    )


def is_admin() -> bool:
    """
    هل المستخدم مدير؟
    """

    return current_role() == "admin"


# ================================================================
# REGISTER
# ================================================================

def register_user(
    username: str,
    password: str,
    full_name: str = "",
    phone: str = "",
    email: str = "",
    role: str = "merchant",
) -> tuple[bool, str]:
    """
    إنشاء حساب مستخدم جديد.
    """

    username = normalize_username(username)
    email = normalize_email(email)
    phone = normalize_phone(phone)
    full_name = str(full_name or "").strip()

    # ------------------------------------------------------------
    # BASIC VALIDATION
    # ------------------------------------------------------------

    if not full_name:
        return False, "الاسم الكامل مطلوب."

    if not email:
        return False, "البريد الإلكتروني مطلوب."

    if not validate_email(email):
        return False, "أدخل بريدًا إلكترونيًا صحيحًا."

    if not username:
        return False, "اسم المستخدم مطلوب."

    if len(username) < MIN_USERNAME_LENGTH:
        return (
            False,
            f"اسم المستخدم يجب أن يكون {MIN_USERNAME_LENGTH} أحرف على الأقل.",
        )

    if not validate_username(username):
        return (
            False,
            "اسم المستخدم يسمح بالأحرف الإنجليزية والأرقام و _ و - و . فقط.",
        )

    if not password:
        return False, "كلمة المرور مطلوبة."

    if len(password) < MIN_PASSWORD_LENGTH:
        return (
            False,
            f"كلمة المرور يجب أن تكون {MIN_PASSWORD_LENGTH} أحرف على الأقل.",
        )

    # ------------------------------------------------------------
    # ROLE
    # ------------------------------------------------------------

    if role not in {
        "merchant",
        "admin",
    }:
        role = "merchant"

    # ------------------------------------------------------------
    # DUPLICATE USERNAME
    # ------------------------------------------------------------

    existing_username = fetch_one(
        """
        SELECT id
        FROM users
        WHERE username = ?
        LIMIT 1
        """,
        (username,),
    )

    if existing_username:
        return False, "اسم المستخدم مستخدم مسبقًا."

    # ------------------------------------------------------------
    # DUPLICATE EMAIL
    # ------------------------------------------------------------

    existing_email = fetch_one(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        LIMIT 1
        """,
        (email,),
    )

    if existing_email:
        return False, "البريد الإلكتروني مستخدم مسبقًا."

    # ------------------------------------------------------------
    # PASSWORD HASH
    # ------------------------------------------------------------

    try:
        password_hash = hash_password(password)

    except ValueError as exc:
        return False, str(exc)

    # ------------------------------------------------------------
    # CREATE USER
    # ------------------------------------------------------------

    user_id = execute(
        """
        INSERT INTO users (
            username,
            password_hash,
            role,
            full_name,
            phone,
            email
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            password_hash,
            role,
            full_name,
            phone,
            email,
        ),
    )

    if not user_id:
        return False, "تعذر إنشاء الحساب."

    return True, "تم إنشاء الحساب بنجاح."


# ================================================================
# LOGIN
# ================================================================

def login_user(
    login_identifier: str,
    password: str,
    remember_me: bool = False,
) -> tuple[bool, str]:
    """
    تسجيل الدخول باستخدام:

    - البريد الإلكتروني
    أو
    - اسم المستخدم
    """

    login_identifier = str(
        login_identifier or ""
    ).strip()

    password = str(
        password or ""
    )

    if not login_identifier:
        return (
            False,
            "أدخل البريد الإلكتروني أو اسم المستخدم.",
        )

    if not password:
        return False, "أدخل كلمة المرور."

    # ------------------------------------------------------------
    # SEARCH BY USERNAME OR EMAIL
    # ------------------------------------------------------------

    user = fetch_one(
        """
        SELECT
            id,
            username,
            password_hash,
            role,
            full_name,
            phone,
            email,
            is_active
        FROM users
        WHERE
            username = ?
            OR LOWER(email) = LOWER(?)
        LIMIT 1
        """,
        (
            login_identifier,
            login_identifier,
        ),
    )

    if not user:
        return False, "بيانات الدخول غير صحيحة."

    # ------------------------------------------------------------
    # ACTIVE CHECK
    # ------------------------------------------------------------

    if not bool(
        user["is_active"]
    ):
        return False, "هذا الحساب غير نشط."

    # ------------------------------------------------------------
    # PASSWORD CHECK
    # ------------------------------------------------------------

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return False, "بيانات الدخول غير صحيحة."

    # ------------------------------------------------------------
    # SESSION
    # ------------------------------------------------------------

    st.session_state.authenticated = True
    st.session_state.user_id = int(
        user["id"]
    )

    st.session_state.username = (
        user["username"] or ""
    )

    st.session_state.email = (
        user["email"] or ""
    )

    st.session_state.role = (
        user["role"] or "merchant"
    )

    st.session_state.full_name = (
        user["full_name"] or ""
    )

    st.session_state.remember_me = bool(
        remember_me
    )

    return True, "تم تسجيل الدخول بنجاح."


# ================================================================
# LOGOUT
# ================================================================

def logout_user() -> None:
    """
    تسجيل الخروج.
    """

    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.email = ""
    st.session_state.role = ""
    st.session_state.full_name = ""
    st.session_state.remember_me = False

    # تنظيف حقول الدخول
    for key in (
        "login_identifier",
        "login_password",
        "login_remember",
    ):
        if key in st.session_state:
            del st.session_state[key]

    st.rerun()


# ================================================================
# CURRENT USER
# ================================================================

def get_current_user() -> dict[str, Any] | None:
    """
    جلب بيانات المستخدم الحالي.
    """

    user_id = current_user_id()

    if user_id is None:
        return None

    return fetch_one(
        """
        SELECT
            id,
            username,
            role,
            full_name,
            phone,
            email,
            is_active,
            created_at
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (user_id,),
    )


# ================================================================
# AUTH GUARD
# ================================================================

def require_login() -> bool:
    """
    التأكد من تسجيل الدخول.
    """

    init_auth_session()

    if is_authenticated():
        return True

    st.warning(
        "🔐 يجب تسجيل الدخول أولًا."
    )

    return False


def require_admin() -> bool:
    """
    التأكد من أن المستخدم مدير.
    """

    if not require_login():
        return False

    if not is_admin():

        st.error(
            "⛔ هذه الصفحة مخصصة للإدارة."
        )

        return False

    return True


# ================================================================
# LOGIN UI
# ================================================================

def render_login_page() -> None:
    """
    واجهة تسجيل الدخول وإنشاء الحساب.
    """

    init_auth_session()

    # ============================================================
    # HEADER
    # ============================================================

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:30px 0 18px 0;
        ">

            <div style="
                font-size:46px;
                margin-bottom:5px;
            ">
                🧠
            </div>

            <h1 style="
                color:#D4AF37;
                margin:0;
                font-size:34px;
                font-weight:800;
            ">
                Saeed PostGen
            </h1>

            <p style="
                color:#AAAAAA;
                font-size:16px;
                margin-top:8px;
            ">
                منصة التصميم والتسويق الذكي
            </p>

            <div style="
                width:90px;
                height:2px;
                margin:18px auto 0 auto;
                background:linear-gradient(
                    90deg,
                    transparent,
                    #D4AF37,
                    transparent
                );
            ">
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    # ============================================================
    # TABS
    # ============================================================

    login_tab, register_tab = st.tabs(
        [
            "🔐 تسجيل الدخول",
            "✨ إنشاء حساب جديد",
        ]
    )

    # ============================================================
    # LOGIN
    # ============================================================

    with login_tab:

        st.markdown(
            "### 🔐 مرحبًا بعودتك"
        )

        st.caption(
            "ادخل بالبريد الإلكتروني أو اسم المستخدم."
        )

        login_identifier = st.text_input(
            "📧 البريد الإلكتروني أو اسم المستخدم",
            placeholder="example@email.com أو username",
            key="login_identifier",
        )

        login_password = st.text_input(
            "🔐 كلمة المرور",
            type="password",
            placeholder="أدخل كلمة المرور",
            key="login_password",
        )

        remember_me = st.checkbox(
            "☑️ تذكرني",
            key="login_remember",
        )

        st.write("")

        if st.button(
            "🚀 دخول إلى Saeed PostGen",
            type="primary",
            use_container_width=True,
            key="login_button",
        ):

            success, message = login_user(
                login_identifier=login_identifier,
                password=login_password,
                remember_me=remember_me,
            )

            if success:

                st.success(message)

                st.rerun()

            else:

                st.error(message)

    # ============================================================
    # REGISTER
    # ============================================================

    with register_tab:

        st.markdown(
            "### ✨ إنشاء حساب جديد"
        )

        st.caption(
            "أنشئ حسابك مرة واحدة ثم استخدم البريد أو اسم المستخدم للدخول."
        )

        # --------------------------------------------------------
        # FULL NAME
        # --------------------------------------------------------

        full_name = st.text_input(
            "👤 الاسم الكامل",
            placeholder="مثال: سعيد المسوري",
            key="register_full_name",
        )

        # --------------------------------------------------------
        # EMAIL
        # --------------------------------------------------------

        email = st.text_input(
            "📧 البريد الإلكتروني",
            placeholder="example@email.com",
            key="register_email",
        )

        # --------------------------------------------------------
        # PHONE
        # --------------------------------------------------------

        phone = st.text_input(
            "📱 رقم الهاتف",
            placeholder="+967xxxxxxxxx",
            key="register_phone",
        )

        # --------------------------------------------------------
        # USERNAME
        # --------------------------------------------------------

        username = st.text_input(
            "🆔 اسم المستخدم",
            placeholder="username",
            help="استخدم الأحرف الإنجليزية والأرقام و _ أو - أو .",
            key="register_username",
        )

        # --------------------------------------------------------
        # PASSWORD
        # --------------------------------------------------------

        password = st.text_input(
            "🔐 كلمة المرور",
            type="password",
            placeholder="أدخل كلمة مرور قوية",
            key="register_password",
        )

        # --------------------------------------------------------
        # CONFIRM PASSWORD
        # --------------------------------------------------------

        confirm_password = st.text_input(
            "🔐 تأكيد كلمة المرور",
            type="password",
            placeholder="أعد كتابة كلمة المرور",
            key="register_confirm_password",
        )

        st.write("")

        if st.button(
            "✨ إنشاء الحساب",
            type="primary",
            use_container_width=True,
            key="register_button",
        ):

            # ----------------------------------------------------
            # PASSWORD MATCH
            # ----------------------------------------------------

            if password != confirm_password:

                st.error(
                    "❌ كلمتا المرور غير متطابقتين."
                )

            else:

                success, message = register_user(
                    username=username,
                    password=password,
                    full_name=full_name,
                    phone=phone,
                    email=email,
                    role="merchant",
                )

                if success:

                    st.success(
                        "✅ تم إنشاء حسابك بنجاح."
                    )

                    st.info(
                        "📧 الآن يمكنك استخدام البريد الإلكتروني "
                        "أو اسم المستخدم مع كلمة المرور لتسجيل الدخول."
                    )

                else:

                    st.error(message)


# ================================================================
# USER HEADER
# ================================================================

def render_user_header() -> None:
    """
    عرض معلومات المستخدم الحالي.
    """

    if not is_authenticated():
        return

    user = get_current_user()

    if not user:
        return

    role_label = (
        "👑 مدير المنصة"
        if user["role"] == "admin"
        else "🏪 تاجر"
    )

    name = (
        user["full_name"]
        or user["username"]
    )

    col1, col2 = st.columns(
        [4, 1]
    )

    with col1:

        st.caption(
            f"👤 {name}  •  "
            f"{role_label}"
        )

    with col2:

        if st.button(
            "🚪 خروج",
            use_container_width=True,
            key="logout_button",
        ):

            logout_user()
