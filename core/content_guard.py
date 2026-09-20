# ================================================================
# SAEED POSTGEN 4.6
# SAEED CONTENT GUARD
# FILE: core/content_guard.py
# ================================================================

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ----------------------------------------------------------------
# CONTENT STATUS
# ----------------------------------------------------------------

class ContentStatus(str, Enum):

    APPROVED = "APPROVED"
    REVIEW = "REVIEW"
    BLOCKED = "BLOCKED"


# ----------------------------------------------------------------
# RESULT
# ----------------------------------------------------------------

@dataclass
class GuardResult:

    status: ContentStatus

    score: float

    reasons: list[str]

    message: str

    requires_human_review: bool = False


# ----------------------------------------------------------------
# BASIC PATTERN GROUPS
# ----------------------------------------------------------------

# هذه ليست قائمة شاملة.
# الهدف منها الفحص الأولي فقط، وليس إصدار حكم نهائي على المستخدم.

BLOCK_PATTERNS = [

    # تهديدات مباشرة
    r"\bاقتل\b",
    r"\bاقتلوا\b",
    r"\bسأقتلك\b",
    r"\bسوف أقتلك\b",

    # دعوات مباشرة للعنف
    r"\bاضربوه\b",
    r"\bهاجموهم\b",
    r"\bفجروهم\b",
    r"\bاحرقوهم\b",

]


REVIEW_PATTERNS = [

    # محتوى عدائي أو تحريضي يحتاج مراجعة بشرية
    r"\bانتقم\b",
    r"\bانتقام\b",
    r"\bحرض\b",
    r"\bتحريض\b",
    r"\bتهديد\b",

]


# ----------------------------------------------------------------
# TEXT NORMALIZATION
# ----------------------------------------------------------------

def normalize_text(text: str) -> str:
    """
    تنظيف وتوحيد النص قبل الفحص.
    """

    if not text:
        return ""

    text = str(text)

    # إزالة HTML
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # توحيد بعض الحروف العربية
    replacements = {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ة": "ه",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new,
        )

    # إزالة التشكيل
    text = re.sub(
        r"[\u064B-\u065F\u0670]",
        "",
        text,
    )

    # إزالة التكرار المفرط للمسافات
    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip().lower()


# ----------------------------------------------------------------
# PATTERN MATCHING
# ----------------------------------------------------------------

def find_matches(
    text: str,
    patterns: list[str],
) -> list[str]:

    matches: list[str] = []

    for pattern in patterns:

        try:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):

                matches.append(pattern)

        except re.error:

            continue

    return matches


# ----------------------------------------------------------------
# CONTENT GUARD
# ----------------------------------------------------------------

def check_content(
    text: str,
) -> GuardResult:
    """
    الفحص الأولي للمحتوى.

    النتائج:

        APPROVED
        REVIEW
        BLOCKED

    ملاحظة:
    هذا النظام فحص أولي وليس نظامًا كاملًا لفهم السياق.
    الحالات الحساسة يمكن تحويلها للمراجعة البشرية.
    """

    normalized = normalize_text(text)

    if not normalized:

        return GuardResult(
            status=ContentStatus.REVIEW,
            score=0.0,
            reasons=[
                "المحتوى فارغ."
            ],
            message="المحتوى يحتاج إلى إدخال نص.",
            requires_human_review=True,
        )

    block_matches = find_matches(
        normalized,
        BLOCK_PATTERNS,
    )

    if block_matches:

        return GuardResult(
            status=ContentStatus.BLOCKED,
            score=0.0,
            reasons=[
                "تم العثور على نمط يحتاج إلى منع النشر مؤقتًا."
            ],
            message=(
                "🔴 BLOCKED — "
                "المحتوى يحتاج إلى مراجعة قبل السماح بالنشر."
            ),
            requires_human_review=True,
        )

    review_matches = find_matches(
        normalized,
        REVIEW_PATTERNS,
    )

    if review_matches:

        return GuardResult(
            status=ContentStatus.REVIEW,
            score=0.5,
            reasons=[
                "تم العثور على محتوى قد يحتاج إلى مراجعة بشرية."
            ],
            message=(
                "🟡 REVIEW — "
                "المحتوى يحتاج إلى مراجعة بشرية."
            ),
            requires_human_review=True,
        )

    return GuardResult(
        status=ContentStatus.APPROVED,
        score=1.0,
        reasons=[],
        message=(
            "🟢 APPROVED — "
            "المحتوى مسموح مبدئيًا."
        ),
        requires_human_review=False,
    )


# ----------------------------------------------------------------
# SHORTCUTS
# ----------------------------------------------------------------

def is_approved(text: str) -> bool:

    result = check_content(text)

    return result.status == ContentStatus.APPROVED


def needs_review(text: str) -> bool:

    result = check_content(text)

    return result.status == ContentStatus.REVIEW


def is_blocked(text: str) -> bool:

    result = check_content(text)

    return result.status == ContentStatus.BLOCKED


# ----------------------------------------------------------------
# DISPLAY HELPERS
# ----------------------------------------------------------------

def status_label(
    status: ContentStatus | str,
) -> str:

    value = (
        status.value
        if isinstance(status, ContentStatus)
        else str(status)
    )

    labels = {

        "APPROVED":
            "🟢 APPROVED — مسموح مبدئيًا",

        "REVIEW":
            "🟡 REVIEW — يحتاج مراجعة بشرية",

        "BLOCKED":
            "🔴 BLOCKED — ممنوع من النشر حتى المراجعة",

    }

    return labels.get(
        value,
        "⚪ UNKNOWN",
    )


# ----------------------------------------------------------------
# CONTENT TYPE HELPER
# ----------------------------------------------------------------

def check_content_package(
    title: str = "",
    description: str = "",
    text: str = "",
) -> GuardResult:
    """
    فحص حزمة محتوى كاملة.
    """

    combined = "\n".join(
        [
            title,
            description,
            text,
        ]
    )

    return check_content(
        combined
  )
