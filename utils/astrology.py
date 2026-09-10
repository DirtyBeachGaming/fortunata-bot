"""
Western (tropical) zodiac reference data for Fortunata.

Single source of truth for sign metadata (dates, element, quality, ruling
planet, color, symbol, blurb) so every cog/feature pulls from the same place.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ZodiacSign:
    key: str                 # e.g. "aries" — stable internal id
    name: str                # e.g. "Aries"
    symbol: str              # unicode glyph, e.g. "♈"
    emoji: str                # discord-friendly emoji fallback
    start: tuple[int, int]    # (month, day) inclusive start
    end: tuple[int, int]      # (month, day) inclusive end
    element: str              # Fire / Earth / Air / Water
    quality: str              # Cardinal / Fixed / Mutable
    ruling_planet: str
    color: int                 # discord.Color-compatible int (0xRRGGBB)
    blurb: str
    kerykeion_code: str = ""  # 3-letter code kerykeion returns for .sign


# Ordered Mar 21 -> Mar 20 (traditional zodiac wheel order starting at Aries)
ZODIAC_SIGNS: dict[str, ZodiacSign] = {
    "aries": ZodiacSign(
        key="aries", name="Aries", symbol="♈", emoji="🐏",
        start=(3, 21), end=(4, 19), element="Fire", quality="Cardinal",
        ruling_planet="Mars", color=0xE0402A, kerykeion_code="Ari",
        blurb="First to arrive, first to leave — Aries brings the torch, "
              "the toast, and the occasional overturned couch.",
    ),
    "taurus": ZodiacSign(
        key="taurus", name="Taurus", symbol="♉", emoji="🐂",
        start=(4, 20), end=(5, 20), element="Earth", quality="Fixed",
        ruling_planet="Venus", color=0x4C9A2A, kerykeion_code="Tau",
        blurb="Camped by the best dish on the table and in no hurry to "
              "move. Taurus knows luxury is a full-time commitment.",
    ),
    "gemini": ZodiacSign(
        key="gemini", name="Gemini", symbol="♊", emoji="👯",
        start=(5, 21), end=(6, 20), element="Air", quality="Mutable",
        ruling_planet="Mercury", color=0xF2C230, kerykeion_code="Gem",
        blurb="Two conversations at once, three by dessert. Gemini is the "
              "reason the gossip travels faster than the wine.",
    ),
    "cancer": ZodiacSign(
        key="cancer", name="Cancer", symbol="♋", emoji="🦀",
        start=(6, 21), end=(7, 22), element="Water", quality="Cardinal",
        ruling_planet="Moon", color=0xB6C6E3, kerykeion_code="Can",
        blurb="Quietly making sure everyone's cup stays full. Cancer "
              "hosts the party even when someone else is throwing it.",
    ),
    "leo": ZodiacSign(
        key="leo", name="Leo", symbol="♌", emoji="🦁",
        start=(7, 23), end=(8, 22), element="Fire", quality="Fixed",
        ruling_planet="Sun", color=0xF7A81B, kerykeion_code="Leo",
        blurb="Reclining at the head of the table like it was built for "
              "them — because, honestly, it probably was.",
    ),
    "virgo": ZodiacSign(
        key="virgo", name="Virgo", symbol="♍", emoji="🌾",
        start=(8, 23), end=(9, 22), element="Earth", quality="Mutable",
        ruling_planet="Mercury", color=0x7A8B5A, kerykeion_code="Vir",
        blurb="Already noticed the seating chart is wrong. Virgo will fix "
              "it without anyone realizing a crisis was averted.",
    ),
    "libra": ZodiacSign(
        key="libra", name="Libra", symbol="♎", emoji="⚖️",
        start=(9, 23), end=(10, 22), element="Air", quality="Cardinal",
        ruling_planet="Venus", color=0xE8A0C4, kerykeion_code="Lib",
        blurb="Charming both ends of the table simultaneously. Libra "
              "cannot pick a favorite dish, guest, or exit line.",
    ),
    "scorpio": ZodiacSign(
        key="scorpio", name="Scorpio", symbol="♏", emoji="🦂",
        start=(10, 23), end=(11, 21), element="Water", quality="Fixed",
        ruling_planet="Pluto", color=0x6B1E2B, kerykeion_code="Sco",
        blurb="Knows everyone's secrets by the second course and is "
              "telling no one. Scorpio came for the intrigue.",
    ),
    "sagittarius": ZodiacSign(
        key="sagittarius", name="Sagittarius", symbol="♐", emoji="🏹",
        start=(11, 22), end=(12, 21), element="Fire", quality="Mutable",
        ruling_planet="Jupiter", color=0x8E44AD, kerykeion_code="Sag",
        blurb="Telling a story that started in another country and has "
              "no clear ending. Sagittarius refills their own glass mid-tale.",
    ),
    "capricorn": ZodiacSign(
        key="capricorn", name="Capricorn", symbol="♑", emoji="🐐",
        start=(12, 22), end=(1, 19), element="Earth", quality="Cardinal",
        ruling_planet="Saturn", color=0x3E3E3E, kerykeion_code="Cap",
        blurb="Arrived on time, left having made three new business "
              "contacts. Capricorn treats the banquet as networking.",
    ),
    "aquarius": ZodiacSign(
        key="aquarius", name="Aquarius", symbol="♒", emoji="🏺",
        start=(1, 20), end=(2, 18), element="Air", quality="Fixed",
        ruling_planet="Uranus", color=0x2E9CCA, kerykeion_code="Aqu",
        blurb="Brought a plus-one nobody invited and somehow they're the "
              "life of the party now. Aquarius rewrites the guest list.",
    ),
    "pisces": ZodiacSign(
        key="pisces", name="Pisces", symbol="♓", emoji="🐟",
        start=(2, 19), end=(3, 20), element="Water", quality="Mutable",
        ruling_planet="Neptune", color=0x5FB0A8, kerykeion_code="Pis",
        blurb="Somewhere between the wine and the music, already crying "
              "happy tears. Pisces feels the whole banquet at once.",
    ),
}

# kerykeion 3-letter code -> our internal key
KERYKEION_CODE_TO_KEY: dict[str, str] = {
    s.kerykeion_code: s.key for s in ZODIAC_SIGNS.values()
}

ELEMENT_EMOJI = {
    "Fire": "🔥",
    "Earth": "🌍",
    "Air": "💨",
    "Water": "🌊",
}

SIGN_ORDER = [
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
]


def sign_from_date(month: int, day: int) -> ZodiacSign:
    """Return the ZodiacSign whose date range contains (month, day)."""
    for sign in ZODIAC_SIGNS.values():
        sm, sd = sign.start
        em, ed = sign.end
        if sm <= em:
            # normal range within a single calendar year, e.g. Mar 21 - Apr 19
            if (month, day) >= (sm, sd) and (month, day) <= (em, ed):
                return sign
        else:
            # wraps the new year, e.g. Capricorn Dec 22 - Jan 19
            if (month, day) >= (sm, sd) or (month, day) <= (em, ed):
                return sign
    raise ValueError(f"No zodiac sign matches month={month} day={day}")


def sign_from_kerykeion_code(code: str) -> ZodiacSign | None:
    key = KERYKEION_CODE_TO_KEY.get(code)
    return ZODIAC_SIGNS.get(key) if key else None


def get_sign(key: str) -> ZodiacSign | None:
    return ZODIAC_SIGNS.get(key.lower()) if key else None


def date_range_label(sign: ZodiacSign) -> str:
    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    sm, sd = sign.start
    em, ed = sign.end
    return f"{months[sm - 1]} {sd} – {months[em - 1]} {ed}"
