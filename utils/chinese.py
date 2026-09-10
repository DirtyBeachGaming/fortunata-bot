"""
Chinese zodiac (12 animals) + Wu Xing five-element (Wood/Fire/Earth/Metal/
Water) calculation for Fortunata.

Uses the `LunarCalendar` package to convert the Gregorian birthdate to its
lunar year, which correctly handles the Chinese New Year cutoff (a birthday
in, say, late January or early-to-mid February can fall into the *previous*
lunar year). Falls back to a same-year approximation if that lookup fails
for any reason (e.g. a date outside the library's supported 1900-2100
range) so the bot never hard-crashes on an edge-case birthday.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

try:
    from lunarcalendar import Converter, Solar
    _HAS_LUNARCALENDAR = True
except ImportError:  # pragma: no cover - dependency should be installed
    _HAS_LUNARCALENDAR = False


ANIMALS = [
    "Rat", "Ox", "Tiger", "Rabbit", "Dragon", "Snake",
    "Horse", "Goat", "Monkey", "Rooster", "Dog", "Pig",
]

ANIMAL_EMOJI = {
    "Rat": "🐀", "Ox": "🐂", "Tiger": "🐅", "Rabbit": "🐇",
    "Dragon": "🐉", "Snake": "🐍", "Horse": "🐎", "Goat": "🐐",
    "Monkey": "🐒", "Rooster": "🐓", "Dog": "🐕", "Pig": "🐖",
}

ANIMAL_BLURBS = {
    "Rat": "First through the door and first to spot the best seat at "
           "the table. Quick, resourceful, always three steps ahead.",
    "Ox": "The one everyone quietly relies on to keep the whole banquet "
          "from falling apart. Steady, honest, immovable once decided.",
    "Tiger": "Makes an entrance whether they mean to or not. Bold, "
             "magnetic, allergic to being told what to do.",
    "Rabbit": "Smooths over every awkward silence with effortless grace. "
              "Gentle, diplomatic, quietly excellent at getting their way.",
    "Dragon": "The guest of honor energy, even when they weren't invited "
              "as one. Confident, charismatic, larger than the room.",
    "Snake": "Says three words and somehow ends the argument. "
             "Perceptive, elegant, keeping far more in reserve than shown.",
    "Horse": "Already talking about the next party before this one's "
             "over. Free-spirited, energetic, impossible to pin down.",
    "Goat": "Brought flowers nobody asked for and they were exactly "
            "right. Gentle, artistic, quietly the most tasteful in the room.",
    "Monkey": "Doing a bit, running a con, and somehow both are "
              "charming. Clever, playful, never quite tells the whole truth.",
    "Rooster": "Dressed better than the host and will mention it. "
               "Confident, observant, unafraid to say what everyone thinks.",
    "Dog": "Checking in on the guest sitting alone in the corner. "
           "Loyal, honest, the moral compass of every gathering.",
    "Pig": "Enjoying the feast more sincerely than anyone else at the "
           "table. Generous, warm-hearted, trusts easily and gives fully.",
}

# 5 elements, each spanning two consecutive stem years, cycling every 10 yrs
ELEMENTS = ["Wood", "Fire", "Earth", "Metal", "Water"]

ELEMENT_EMOJI = {
    "Wood": "🌳", "Fire": "🔥", "Earth": "🪨", "Metal": "⚙️", "Water": "💧",
}

ELEMENT_BLURBS = {
    "Wood": "Growth-minded and generous, always making room for one "
            "more chair at the table.",
    "Fire": "Bright, passionate, and impossible to ignore — the energy "
            "the whole party ends up orbiting.",
    "Earth": "Grounded and dependable, the steady host energy that "
             "holds the whole evening together.",
    "Metal": "Sharp, disciplined, and precise — knows exactly what "
              "they want and rarely settles for less.",
    "Water": "Intuitive and adaptable, flowing around whatever the "
             "night throws at them without losing their calm.",
}


@dataclass(frozen=True)
class ChineseZodiacResult:
    animal: str
    element: str
    lunar_year: int


def _lunar_year(d: date) -> int:
    if _HAS_LUNARCALENDAR:
        try:
            lunar = Converter.Solar2Lunar(Solar(d.year, d.month, d.day))
            return lunar.year
        except Exception:
            pass
    # Fallback approximation: Chinese New Year almost always falls between
    # Jan 21 and Feb 20. If the birthday is before Feb 4 (a reasonable
    # midpoint) treat it as still belonging to the previous lunar year.
    if (d.month, d.day) < (2, 4):
        return d.year - 1
    return d.year


def get_chinese_zodiac(birth_date: date) -> ChineseZodiacResult:
    lunar_year = _lunar_year(birth_date)
    animal = ANIMALS[(lunar_year - 4) % 12]
    element = ELEMENTS[((lunar_year - 4) % 10) // 2]
    return ChineseZodiacResult(animal=animal, element=element, lunar_year=lunar_year)
