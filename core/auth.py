# ================================================================
# SAEED POSTGEN 4.6
# AUTHENTICATION ENGINE
# FILE: core/auth.py
# ================================================================

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import streamlit as st

from core.database import execute, fetch_one


# ----------------------------------------------------------------
# PASSWORD SECURITY
# ----------------------------------------------------------------

HASH_ITERATIONS = 200_000


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
    التحقق من كلمة المرور.
    """

    try:
        algorithm, iterations, salt_hex, hash_hex = stored_hash.split("$")

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
    ):
        return False


# ----------------------------------------------------------------
# SESSION
# ----------------------------------------------------------------

def init_auth_session() -> None:
    """
    تهيئة جلسة المصادقة.
    """

    defaults = {
        "authenticated": False,
        "user_id": None,
        "username": "",
        "role": "",
        "full_name": "",
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

    except (TypeError, ValueError):
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


# ----------------------------------------------------------------
# REGISTER
# ----------------------------------------------------------------

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

    username = username.strip()
    full_name = full_name.strip()
    phone = phone.strip()
    email = email.strip()

    if not username:
        return False, "اسم المستخدم مطلوب."

    if len(username) < 3:
        return False, "اسم المستخدم يجب أن يكون 3 أحرف على الأقل."

    if not password:
        return False, "كلمة المرور مطلوبة."

    if len(password) < 6:
        return False, "كلمة المرور يجب أن تكون 6 أحرف على الأقل."

    if role not in {"merchant", "admin"}:
        role = "merchant"

    existing_user = fetch_one(
        """
        SELECT id
        FROM users
        WHERE username = ?
        """,
        (username,),
    )

    if existing_user:
        return False, "اسم المستخدم موجود مسبقًا."

    password_hash = hash_password(password)

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


# ----------------------------------------------------------------
# LOGIN
# ----------------------------------------------------------------

def login_user(
    username: str,
    password: str,
) -> tuple[bool, str]:
    """
    تسجيل دخول المستخدم.
    """

    username = username.strip()

    if not username or not password:
        return False, "أدخل اسم المستخدم وكلمة المرور."

    user = fetch_one(
        """
        SELECT
            id,
            username,
            password_hash,
            role,
            full_name,
            is_active
        FROM users
        WHERE username = ?
        """,
        (username,),
    )

    if not user:
        return False, "بيانات الدخول غير صحيحة."

    if not bool(user["is_active"]):
        return False, "هذا الحساب غير نشط."

    if not verify_password(
        password,
        user["password_hash"],
    ):
        return False, "بيانات الدخول غير صحيحة."

    st.session_state.authenticated = True
    st.session_state.user_id = int(user["id"])
    st.session_state.username = user["username"]
    st.session_state.role = user["role"]
    st.session_state.full_name = user["full_name"] or ""

    return True, "تم تسجيل الدخول بنجاح."


# ----------------------------------------------------------------
# LOGOUT
# ----------------------------------------------------------------

def logout_user() -> None:
    """
    تسجيل الخروج.
    """

    st.session_state.authenticated = False
    st.session_state.user_id = None
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.full_name = ""

    # الاحتفاظ فقط بحالة المصادقة الأساسية.
    st.rerun()


# ----------------------------------------------------------------
# CURRENT USER
# ----------------------------------------------------------------

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
        """,
        (user_id,),
    )


# ----------------------------------------------------------------
# AUTH GUARD
# ----------------------------------------------------------------

def require_login() -> bool:
    """
    التأكد من تسجيل الدخول.
    """

    init_auth_session()

    if is_authenticated():
        return True

    st.warning("🔐 يجب تسجيل الدخول أولًا.")

    return False


def require_admin() -> bool:
    """
    التأكد من أن المستخدم مدير.
    """

    if not require_login():
        return False

    if not is_admin():
        st.error("⛔ هذه الصفحة مخصصة للإدارة.")

        return False

    return True


# ----------------------------------------------------------------
# LOGIN UI
# ----------------------------------------------------------------

def render_login_page() -> None:
    """
    واجهة تسجيل الدخول والتسجيل.
    """

    init_auth_session()

    st.markdown(
        """
        <div style="
            text-align:center;
            padding:20px 0 10px 0;
        ">
            <h1 style="
                color:#D4AF37;
                margin-bottom:5px;
            ">
                Saeed PostGen
            </h1>

            <p style="
                color:#AAAAAA;
                font-size:16px;
            ">
                منصة التصميم والتسويق الذكي
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    login_tab, register_tab = st.tabs(
        [
            "🔐 تسجيل الدخول",
            "👤 إنشاء حساب تاجر",
        ]
    )

    # ============================================================
    # LOGIN
    # ============================================================

    with login_tab:

        st.subheader("تسجيل الدخول")

        username = st.text_input(
            "اسم المستخدم",
            key="login_username",
        )

        password = st.text_input(
            "كلمة المرور",
            type="password",
            key="login_password",
        )

        if st.button(
            "دخول",
            type="primary",
            use_container_width=True,
            key="login_button",
        ):

            success, message = login_user(
                username,
                password,
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

        st.subheader("إنشاء حساب تاجر")

        full_name = st.text_input(
            "اسم التاجر",
            key="register_full_name",
        )

        username = st.text_input(
            "اسم المستخدم",
            key="register_username",
        )

        phone = st.text_input(
            "رقم التواصل",
            key="register_phone",
        )

        email = st.text_input(
            "البريد الإلكتروني",
            key="register_email",
        )

        password = st.text_input(
            "كلمة المرور",
            type="password",
            key="register_password",
        )

        confirm_password = st.text_input(
            "تأكيد كلمة المرور",
            type="password",
            key="register_confirm_password",
        )

        if st.button(
            "إنشاء حساب",
            type="primary",
            use_container_width=True,
            key="register_button",
        ):

            if password != confirm_password:

                st.error(
                    "كلمتا المرور غير متطابقتين."
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

                    st.success(message)

                    st.info(
                        "يمكنك الآن الانتقال إلى تبويب تسجيل الدخول."
                    )

                else:

                    st.error(message)


# ----------------------------------------------------------------
# USER HEADER
# ----------------------------------------------------------------

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
            f"👤 {name}  •  {role_label}"
        )

    with col2:

        if st.button(
            "خروج",
            use_container_width=True,
            key="logout_button",
        ):

            logout_user()
