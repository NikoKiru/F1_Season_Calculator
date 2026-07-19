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


# Same demonyms → ISO 3166-1 alpha-2, matching app/static/flags/{iso}.svg.
_DEMONYM_TO_ISO = {
    "American": "us",
    "Argentine": "ar",
    "Argentinian": "ar",
    "Australian": "au",
    "Austrian": "at",
    "Belgian": "be",
    "Brazilian": "br",
    "British": "gb",
    "Canadian": "ca",
    "Chinese": "cn",
    "Colombian": "co",
    "Danish": "dk",
    "Dutch": "nl",
    "Finnish": "fi",
    "French": "fr",
    "German": "de",
    "Indian": "in",
    "Indonesian": "id",
    "Irish": "ie",
    "Italian": "it",
    "Japanese": "jp",
    "Mexican": "mx",
    "Monegasque": "mc",
    "Monégasque": "mc",
    "New Zealander": "nz",
    "Polish": "pl",
    "Portuguese": "pt",
    "Russian": "ru",
    "Spanish": "es",
    "Swedish": "se",
    "Swiss": "ch",
    "Thai": "th",
    "Venezuelan": "ve",
}


def flag_for(nationality: str | None) -> str:
    if not nationality:
        return "🏁"
    return _DEMONYM_TO_FLAG.get(nationality.strip(), "🏁")


def iso_for(nationality: str | None) -> str | None:
    """ISO alpha-2 code for a demonym, or None when there is no SVG flag."""
    if not nationality:
        return None
    return _DEMONYM_TO_ISO.get(nationality.strip())
