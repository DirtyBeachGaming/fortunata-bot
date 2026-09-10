"""
Blood type astrology (ketsuekigata) reference data for Fortunata.

This is the popular Japanese/Korean pop-culture personality typing based on
ABO blood type — presented for fun, same spirit as the sun-sign/Chinese
zodiac features, not a scientific claim.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BloodType:
    key: str
    label: str
    emoji: str
    color: int
    blurb: str
    strengths: str
    watch_for: str


BLOOD_TYPES: dict[str, BloodType] = {
    "a": BloodType(
        key="a", label="Type A", emoji="🅰️", color=0x4C9A2A,
        blurb="Arrived early to help set the table and never quite "
              "stopped organizing the evening from the sidelines.",
        strengths="Careful, cooperative, detail-oriented, a considerate "
                  "and reliable host or guest.",
        watch_for="Can overthink, hold in stress, and take on more "
                  "than their share to keep the peace.",
    ),
    "b": BloodType(
        key="b", label="Type B", emoji="🅱️", color=0xE0402A,
        blurb="Wandered off from the main table to start a far more "
              "interesting conversation by the fountain.",
        strengths="Independent, curious, adaptable, unbothered by what "
                  "the rest of the room thinks of them.",
        watch_for="Can be seen as unpredictable or self-focused when "
                  "everyone else is trying to stick to the plan.",
    ),
    "ab": BloodType(
        key="ab", label="Type AB", emoji="🆎", color=0x8E44AD,
        blurb="Somehow fits in with both the philosophers and the "
              "musicians without ever fully belonging to either group.",
        strengths="Rational yet empathetic, a natural mediator with a "
                  "cool head and a genuinely original point of view.",
        watch_for="Can seem two-faced or aloof while actually just "
                  "holding two valid perspectives at once.",
    ),
    "o": BloodType(
        key="o", label="Type O", emoji="🅾️", color=0xF7A81B,
        blurb="Somehow already knows everyone at the party and is the "
              "reason half of them were invited in the first place.",
        strengths="Confident, generous, a natural leader people "
                  "gravitate toward without quite knowing why.",
        watch_for="Can be stubborn or overly competitive once they've "
                  "decided they're right.",
    ),
}
