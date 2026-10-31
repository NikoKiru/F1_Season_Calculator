from __future__ import annotations

import pytest

from app.services import display


@pytest.mark.parametrize(
    ("rounds", "expected"),
    [
        ([], ""),
        ([7], "7"),
        ([1, 2], "1–2"),
        ([1, 2, 3, 4], "1–4"),
        ([1, 3], "1, 3"),
        ([1, 2, 3, 7, 9, 10, 18], "1–3, 7, 9–10, 18"),
    ],
)
def test_round_ranges(rounds, expected):
    assert display.round_ranges(rounds) == expected
