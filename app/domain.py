import re
from dataclasses import dataclass, field
from datetime import date

CURRENCY = re.compile(r"(?:\s*(?:so['’‘ʻ`]?m|uzs|sum)\s*)+$", re.I)
CURRENCY_WORDS = re.compile(r"\b(?:so['’‘ʻ`]?m|uzs|sum)\b", re.I)
AMOUNT_WORDS = re.compile(r"\b(?:ming|million|mln)\b", re.I)

@dataclass
class ParsedEntry:
    kind: str
    amount: int
    category: str
    note: str
    occurred_on: date = field(default_factory=date.today)

class InputError(ValueError): pass

def normalize_category(value: str | None) -> str:
    value = CURRENCY_WORDS.sub("", value or "")
    value = AMOUNT_WORDS.sub("", value)
    value = re.sub(r"\b(?:ga|ka|da|dan|ni|ning|uchun|bez)\b", " ", value, flags=re.I)
    value = re.sub(r"\b\d+\b", "", value).strip(" .,-:")
    return value[:80] or "Boshqa"

AMOUNT_PATTERN = re.compile(
    r"(?<!\w)(?P<number>\d(?:[\d\s.,]*\d)?)(?:\s*(?P<unit>million(?:ga|dan|ni)?|mln(?:ga|dan|ni)?|ming(?:ga|dan|ni)?))?(?!\w)",
    re.I,
)


def infer_category(description: str) -> str:
    text = description.casefold()
    rules = [
        (("benzin", "benzinga", "yoqilg‘i", "yoqilgi", "zapravka", "taksi", "metro", "avtobus"), "Transport"),
        (("video", "videorolik"), "Video xizmati"),
        (("montaj", "montaj"), "Video montaj"),
        (("dizayn", "banner", "logo"), "Dizayn xizmati"),
        (("suv", "ichimlik", "gazli", "sharbat", "kofe", "qahva", "choy"), "Ichimliklar"),
        (("oylik", "maosh", "ish haqi"), "Ish haqi"),
        (("ishlab top", "ishladim", "topdim"), "Mehnat daromadi"),
        (("yo‘l kira", "yo'l kira"), "Transport"),
        (("ovqat", "tushlik", "nonushta", "kechki ovqat", "non", "yegulik", "oziq", "mastava", "sho‘rva", "shorva", "palov", "osh"), "Oziq-ovqat"),
        (("ijara",), "Ijara"),
    ]
    for words, category in rules:
        if any(word in text for word in words):
            return category
    meaningful = CURRENCY_WORDS.sub("", description).strip(" .,-:")
    return normalize_category(meaningful.split(maxsplit=1)[0] if meaningful else "Boshqa")


def infer_transaction_kind(text: str) -> str | None:
    text = text.casefold()
    income_cues = ("ishlab top", "ishladim", "topdim", "daromad", "maosh", "oylik", "ish haqi", "sotdim", "kirim", "pul tush", "haq oldim")
    expense_cues = ("xarajat", "sarfl", "yedim", "yeydim", "jedim", "ichdim", "sotib", "oldim", "mastava", "sho‘rva", "shorva", "palov", "non", "tushlik", "to‘ladim", "to'ladim", "toladim", "ketdi")
    if any(cue in text for cue in income_cues):
        return "income"
    if any(cue in text for cue in expense_cues):
        return "expense"
    return None


def parse_manual_entry(text: str, kind: str) -> ParsedEntry:
    if kind not in {"expense", "income"}:
        raise InputError("Tur noto‘g‘ri")
    match = AMOUNT_PATTERN.search(text)
    if not match:
        raise InputError("Summani kiriting. Masalan: 45000 ovqat tushlik")
    raw = re.sub(r"[\s.,]", "", match.group("number"))
    try:
        amount = int(raw)
    except ValueError as exc:
        raise InputError("Summani raqam bilan kiriting") from exc
    unit = (match.group("unit") or "").casefold()
    if unit.startswith("ming"):
        amount *= 1_000
    elif unit.startswith("million") or unit.startswith("mln"):
        amount *= 1_000_000
    if amount <= 0 or amount > 10**12:
        raise InputError("Summa 0 dan katta va me'yorida bo‘lsin")

    description = (text[:match.start()] + " " + text[match.end():]).strip()
    description = CURRENCY_WORDS.sub("", description)
    description = re.sub(r"\s+", " ", description).strip(" .,-:")
    description = re.sub(r"^(?:ga|ka|da|dan|ni|uchun)\s+", "", description, flags=re.I)
    category = infer_category(description)
    return ParsedEntry(kind, amount, category, description[:300])

def validate_payment(remaining: int, amount: int | None) -> int:
    value = remaining if amount is None else amount
    if value <= 0: raise InputError("To‘lov summasi 0 dan katta bo‘lishi kerak")
    if value > remaining: raise InputError(f"To‘lov qoldiqdan oshdi ({remaining:,} so‘m)")
    return value
