"""Ergast/Jolpica nationality demonym → flag emoji.

Covers every nationality on the modern grid plus common historical ones.
Unknown demonyms get the checkered flag so scaffolded JSON stays valid and
visibly needs curation.
"""
from __future__ import annotations

_DEMONYM_TO_FLAG = {
    "American": "🇺🇸",
    "Argentine": "🇦🇷",
    "Argentinian": "🇦🇷",
    "Australian": "🇦🇺",
    "Austrian": "🇦🇹",
    "Belgian": "🇧🇪",
    "Brazilian": "🇧🇷",
    "British": "🇬🇧",
    "Canadian": "🇨🇦",
    "Chinese": "🇨🇳",
    "Colombian": "🇨🇴",
    "Danish": "🇩🇰",
    "Dutch": "🇳🇱",
    "Finnish": "🇫🇮",
    "French": "🇫🇷",
    "German": "🇩🇪",
    "Indian": "🇮🇳",
    "Indonesian": "🇮🇩",
    "Irish": "🇮🇪",
    "Italian": "🇮🇹",
    "Japanese": "🇯🇵",
    "Mexican": "🇲🇽",
    "Monegasque": "🇲🇨",
    "Monégasque": "🇲🇨",
    "New Zealander": "🇳🇿",
    "Polish": "🇵🇱",
    "Portuguese": "🇵🇹",
    "Russian": "🇷🇺",
    "Spanish": "🇪🇸",
    "Swedish": "🇸🇪",
    "Swiss": "🇨🇭",
    "Thai": "🇹🇭",
    "Venezuelan": "🇻🇪",
}


def flag_for(nationality: str | None) -> str:
    if not nationality:
        return "🏁"
    return _DEMONYM_TO_FLAG.get(nationality.strip(), "🏁")
