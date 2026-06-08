"""Hero strip rendering — bio chips, career tiles, palmarès tiles, fallbacks."""
from __future__ import annotations

# --- driver page ---------------------------------------------------------


def test_driver_hero_renders_bio_chips(client):
    """A driver with nationality/birthdate/debut shows chips for each."""
    r = client.get("/driver/VER")
    assert r.status_code == 200
    html = r.text
    assert 'hero__chips' in html
    assert ">Age<" in html  # chip label
    assert ">Nationality<" in html
    assert "Dutch" in html
    assert ">F1 debut<" in html
    assert "2015" in html


def test_driver_career_tiles_show_numbers_when_career_present(client):
    """Career section shows the numbers + 'Updated' caption when populated."""
    r = client.get("/driver/VER")
    html = r.text
    # Header
    assert 'career-heading' in html
    # All five tiles labels present
    for label in ("Wins", "Podiums", "Poles", "Championships", "Starts"):
        assert f">{label}<" in html
    # Numbers from the seed data
    assert ">60<" in html  # wins
    assert ">110<" in html  # podiums
    assert ">200<" in html  # starts
    # Caption shows
    assert "Updated 2026-05-17" in html


def test_driver_career_tiles_fallback_to_dashes_when_no_career(client):
    """A driver without `career` data renders em-dashes and no caption."""
    r = client.get("/driver/NOR")
    html = r.text
    assert 'career-heading' in html
    # Em-dash fallback in tiles
    assert html.count("—") >= 5  # five career tiles, each "—"
    # No "Updated" caption when career is null
    assert "Updated 20" not in html


# --- constructor page ---------------------------------------------------


def test_constructor_hero_renders_identity_chips(client):
    r = client.get("/constructor/red-bull")
    assert r.status_code == 200
    html = r.text
    assert 'hero__chips' in html
    assert ">Base<" in html
    assert "Austria" in html
    assert ">Founded<" in html
    assert "2005" in html
    assert ">Principal<" in html
    assert "Laurent Mekies" in html
    assert ">Power unit<" in html
    assert "Honda RBPT" in html


def test_constructor_palmares_tiles_show_numbers_when_present(client):
    r = client.get("/constructor/red-bull")
    html = r.text
    assert 'palmares-heading' in html
    for label in ("Constructors' titles", "Race wins", "Podiums", "First race"):
        assert f">{label}<" in html
    assert ">6<" in html  # championships
    assert ">122<" in html  # wins
    assert ">1997<" in html  # first_race_year
    assert "Updated 2026-05-17" in html


def test_constructor_palmares_dashes_when_no_palmares(client):
    """McLaren has identity but palmares=None — tiles show em-dashes."""
    r = client.get("/constructor/mclaren")
    html = r.text
    assert 'palmares-heading' in html
    assert html.count("—") >= 4
    assert "Updated 20" not in html
