"""
GraphQL resolver functions that wrap existing API logic.
"""
from typing import List, Optional, Dict, Any

try:
    from ..db import get_db
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from db import get_db

try:
    from ..championship.models import DRIVER_NAMES, DRIVERS, ROUND_NAMES_2025
    from ..championship.logic import get_round_points_for_championship
    from ..championship import api as api_module
except ImportError:
    from championship.models import DRIVER_NAMES, DRIVERS, ROUND_NAMES_2025
    from championship.logic import get_round_points_for_championship
    import championship.api as api_module

from .types import (
    Driver, Championship, DriverPointEntry, RoundPointsData,
    PaginatedChampionships, ChampionshipWin, HighestPositionResult,
    HeadToHeadResult, MinRacesToWinResult, DriverPositionCount,
    DriverProbabilityData, ChampionshipWinProbability, DriverStats,
    PositionCount, HeadToHeadRecord, WinProbabilityByLength,
    FindChampionshipResult, ClearCacheResult
)


def get_all_drivers() -> List[Driver]:
    """Get all drivers as GraphQL types."""
    return [
        Driver(
            code=code,
            name=data['name'],
            team=data['team'],
            number=data['number'],
            flag=data['flag'],
            color=data['color']
        )
        for code, data in DRIVERS.items()
    ]


def get_driver_by_code(code: str) -> Optional[Driver]:
    """Get a single driver by code."""
    code = code.upper()
    if code not in DRIVERS:
        return None
    data = DRIVERS[code]
    return Driver(
        code=code,
        name=data['name'],
        team=data['team'],
        number=data['number'],
        flag=data['flag'],
        color=data['color']
    )


def format_championship_to_graphql(row: Any, with_round_points: bool = False) -> Optional[Championship]:
    """Convert a database row to a Championship GraphQL type."""
    if not row:
        return None

    championship_data = dict(row)

    # Parse rounds
    rounds = []
    round_names = []
    if championship_data.get('rounds'):
        rounds = [int(r) for r in championship_data['rounds'].split(',')]
        round_names = [ROUND_NAMES_2025.get(r, 'Unknown') for r in rounds]

    # Parse standings and points
    standings = []
    points = []
    driver_points = []
    if championship_data.get('standings') and championship_data.get('points'):
        standings = championship_data['standings'].split(',')
        points = [int(p) for p in championship_data['points'].split(',')]
        driver_points = [
            DriverPointEntry(
                driver_code=driver,
                points=pts,
                driver_name=DRIVER_NAMES.get(driver, 'Unknown')
            )
            for driver, pts in zip(standings, points)
        ]

    # Get round points data if requested
    round_points_data = None
    if with_round_points and rounds and standings:
        raw_round_points = get_round_points_for_championship(standings, rounds)
        if raw_round_points:
            round_points_data = [
                RoundPointsData(
                    driver_code=driver,
                    round_points=data['round_points'],
                    total_points=data['total_points']
                )
                for driver, data in raw_round_points.items()
            ]

    return Championship(
        championship_id=championship_data['championship_id'],
        num_races=championship_data['num_races'],
        rounds=rounds,
        round_names=round_names,
        standings=standings,
        winner=championship_data.get('winner', ''),
        points=points,
        driver_points=driver_points,
        round_points_data=round_points_data
    )


def get_paginated_championships(page: int = 1, per_page: int = 100) -> PaginatedChampionships:
    """Get paginated list of championships."""
    db = get_db()

    # Get total count
    total_count = db.execute("SELECT COUNT(*) FROM championship_results").fetchone()[0]

    # Calculate offset
    offset = (page - 1) * per_page

    # Fetch paginated data
    rows = db.execute(
        "SELECT * FROM championship_results LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()

    # Convert to GraphQL types
    results = [format_championship_to_graphql(row) for row in rows]
    results = [r for r in results if r is not None]

    total_pages = (total_count + per_page - 1) // per_page

    return PaginatedChampionships(
        total_results=total_count,
        total_pages=total_pages,
        current_page=page,
        per_page=per_page,
        results=results
    )


def get_championship_by_id(id: int, include_round_points: bool = True) -> Optional[Championship]:
    """Get a single championship by ID."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM championship_results WHERE championship_id = ?",
        (id,)
    ).fetchone()

    return format_championship_to_graphql(row, with_round_points=include_round_points)


def get_championship_wins() -> List[ChampionshipWin]:
    """Get championship wins for all drivers."""
    db = get_db()
    query = """
        SELECT winner, COUNT(*) as wins
        FROM championship_results
        GROUP BY winner
        ORDER BY wins DESC
    """
    rows = db.execute(query).fetchall()
    return [
        ChampionshipWin(driver_code=row['winner'], wins=row['wins'])
        for row in rows
    ]


def get_highest_positions(refresh: bool = False) -> List[HighestPositionResult]:
    """Get highest championship position for each driver."""
    # Check cache
    if not refresh and api_module._highest_position_cache is not None:
        return [
            HighestPositionResult(
                driver=item['driver'],
                position=item['position'],
                championship_ids=item['championship_ids']
            )
            for item in api_module._highest_position_cache
        ]

    db = get_db()

    # Get max races
    max_races_row = db.execute("SELECT MAX(num_races) as max_races FROM championship_results").fetchone()
    max_races = max_races_row['max_races']

    # Get all drivers
    sample_row = db.execute("SELECT standings FROM championship_results LIMIT 1").fetchone()
    if not sample_row:
        return []

    all_drivers = [driver.strip() for driver in sample_row['standings'].split(",")]
    drivers_to_find = set(all_drivers)
    highest_positions: Dict[str, Dict] = {}

    # Process championships from max races down
    for num_races in range(max_races, 0, -1):
        if not drivers_to_find:
            break

        query = """
        SELECT championship_id, standings
        FROM championship_results
        WHERE num_races = ?
        ORDER BY championship_id DESC
        LIMIT 10000
        """
        rows = db.execute(query, (num_races,)).fetchall()

        for row in rows:
            championship_id = row['championship_id']
            standings = row['standings']
            drivers_list = [d.strip() for d in standings.split(",")]

            for position, driver in enumerate(drivers_list, start=1):
                if driver not in highest_positions:
                    highest_positions[driver] = {
                        "position": position,
                        "championship_ids": [championship_id]
                    }
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif position < highest_positions[driver]["position"]:
                    highest_positions[driver] = {
                        "position": position,
                        "championship_ids": [championship_id]
                    }
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif position == highest_positions[driver]["position"]:
                    if len(highest_positions[driver]["championship_ids"]) < 5:
                        highest_positions[driver]["championship_ids"].append(championship_id)

    # Sort by position
    sorted_positions = sorted(highest_positions.items(), key=lambda item: item[1]['position'])

    # Cache and return
    cache_data = [
        {'driver': k, 'position': v['position'], 'championship_ids': v['championship_ids']}
        for k, v in sorted_positions
    ]
    api_module._highest_position_cache = cache_data

    return [
        HighestPositionResult(
            driver=item['driver'],
            position=item['position'],
            championship_ids=item['championship_ids']
        )
        for item in cache_data
    ]


def get_head_to_head(driver1: str, driver2: str) -> HeadToHeadResult:
    """Compare two drivers head-to-head."""
    d1_upper = driver1.upper()
    d2_upper = driver2.upper()

    if d1_upper == d2_upper:
        raise ValueError("Cannot compare driver to themselves")

    if d1_upper not in DRIVER_NAMES or d2_upper not in DRIVER_NAMES:
        raise ValueError("Invalid driver abbreviation")

    # Check cache
    cache_key = tuple(sorted([d1_upper, d2_upper]))
    if cache_key in api_module._head_to_head_cache:
        cached = api_module._head_to_head_cache[cache_key]
        return HeadToHeadResult(
            driver1=d1_upper,
            driver1_wins=cached[d1_upper],
            driver2=d2_upper,
            driver2_wins=cached[d2_upper]
        )

    db = get_db()
    query = """
        SELECT
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',')
                < INSTR(',' || standings || ',', ',' || ? || ',')
                THEN 1 ELSE 0 END) as driver1_wins,
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',')
                > INSTR(',' || standings || ',', ',' || ? || ',')
                THEN 1 ELSE 0 END) as driver2_wins
        FROM championship_results
        WHERE INSTR(standings, ?) > 0 AND INSTR(standings, ?) > 0;
    """
    result = db.execute(
        query,
        (d1_upper, d2_upper, d1_upper, d2_upper, d1_upper, d2_upper)
    ).fetchone()

    response_data = {
        d1_upper: result['driver1_wins'],
        d2_upper: result['driver2_wins']
    }

    # Cache
    api_module._head_to_head_cache[cache_key] = response_data

    return HeadToHeadResult(
        driver1=d1_upper,
        driver1_wins=result['driver1_wins'],
        driver2=d2_upper,
        driver2_wins=result['driver2_wins']
    )


def get_min_races_to_win() -> List[MinRacesToWinResult]:
    """Get minimum races needed for each driver to win a championship."""
    db = get_db()
    query = """
        SELECT winner, MIN(num_races) as min_races
        FROM championship_results
        WHERE winner IS NOT NULL
        GROUP BY winner
        ORDER BY min_races ASC
    """
    results = db.execute(query).fetchall()
    return [
        MinRacesToWinResult(driver_code=row['winner'], min_races=row['min_races'])
        for row in results
    ]


def get_driver_positions(position: int) -> List[DriverPositionCount]:
    """Count driver finishes in a specific position."""
    if position < 1:
        raise ValueError("Position must be at least 1")

    # Check cache
    if position in api_module._driver_positions_cache:
        return [
            DriverPositionCount(
                driver=item['driver'],
                count=item['count'],
                percentage=item['percentage']
            )
            for item in api_module._driver_positions_cache[position]
        ]

    db = get_db()
    query = "SELECT standings FROM championship_results"
    rows = db.execute(query).fetchall()

    total_championships = len(rows)
    position_counts: Dict[str, int] = {}

    for row in rows:
        standings = row['standings'].split(',')
        if len(standings) >= position:
            driver = standings[position - 1].strip()
            if driver:
                position_counts[driver] = position_counts.get(driver, 0) + 1

    # Sort by count descending
    sorted_counts = sorted(position_counts.items(), key=lambda item: item[1], reverse=True)

    # Format with percentages
    result_data = []
    for driver, count in sorted_counts:
        percentage = (count / total_championships) * 100 if total_championships > 0 else 0
        result_data.append({
            "driver": driver,
            "count": count,
            "percentage": round(percentage, 2)
        })

    # Cache
    api_module._driver_positions_cache[position] = result_data

    return [
        DriverPositionCount(
            driver=item['driver'],
            count=item['count'],
            percentage=item['percentage']
        )
        for item in result_data
    ]


def get_championship_win_probability() -> ChampionshipWinProbability:
    """Get win probability matrix by season length."""
    db = get_db()

    # Get total wins for each driver
    query_wins = "SELECT winner, COUNT(*) as wins FROM championship_results GROUP BY winner"
    driver_total_wins = {row['winner']: row['wins'] for row in db.execute(query_wins).fetchall()}

    # Get wins per season length for each driver
    query_wins_per_length = "SELECT winner, num_races, COUNT(*) as wins FROM championship_results GROUP BY winner, num_races"
    wins_per_length: Dict[str, Dict[int, int]] = {}
    for row in db.execute(query_wins_per_length).fetchall():
        if row['winner'] not in wins_per_length:
            wins_per_length[row['winner']] = {}
        wins_per_length[row['winner']][row['num_races']] = row['wins']

    # Get total seasons per length
    query_seasons_per_length = "SELECT num_races, COUNT(*) as total FROM championship_results GROUP BY num_races"
    seasons_per_length = {row['num_races']: row['total'] for row in db.execute(query_seasons_per_length).fetchall()}

    season_lengths = sorted(seasons_per_length.keys())
    drivers = sorted(driver_total_wins.keys())

    drivers_data = []
    for driver in drivers:
        wins_list = [wins_per_length.get(driver, {}).get(length, 0) for length in season_lengths]
        percentages = []
        for length in season_lengths:
            wins = wins_per_length.get(driver, {}).get(length, 0)
            total_seasons = seasons_per_length.get(length, 1)
            percentage = (wins / total_seasons) * 100 if total_seasons > 0 else 0
            percentages.append(round(percentage, 2))

        drivers_data.append(DriverProbabilityData(
            driver=driver,
            total_titles=driver_total_wins.get(driver, 0),
            wins_per_length=wins_list,
            percentages=percentages
        ))

    # Sort by percentages from right to left
    if drivers_data and season_lengths:
        drivers_data.sort(key=lambda x: tuple(reversed(x.percentages)) if x.percentages else tuple(), reverse=True)

    return ChampionshipWinProbability(
        season_lengths=season_lengths,
        possible_seasons=[seasons_per_length.get(length, 0) for length in season_lengths],
        drivers_data=drivers_data
    )


def get_driver_stats(driver_code: str) -> Optional[DriverStats]:
    """Get comprehensive statistics for a driver."""
    driver_code = driver_code.upper()

    if driver_code not in DRIVER_NAMES:
        return None

    # Check cache
    if driver_code in api_module._driver_stats_cache:
        cached = api_module._driver_stats_cache[driver_code]
        return _convert_cached_stats_to_graphql(cached)

    db = get_db()

    # Get total wins
    wins_query = "SELECT COUNT(*) as wins FROM championship_results WHERE winner = ?"
    wins_result = db.execute(wins_query, (driver_code,)).fetchone()
    total_wins = wins_result['wins'] if wins_result else 0

    # Get total championships count
    total_query = "SELECT COUNT(*) as total FROM championship_results"
    total_result = db.execute(total_query).fetchone()
    total_championships = total_result['total'] if total_result else 1

    win_percentage = round((total_wins / total_championships) * 100, 2) if total_championships > 0 else 0

    # Get minimum races to win
    min_races_query = "SELECT MIN(num_races) as min_races FROM championship_results WHERE winner = ?"
    min_races_result = db.execute(min_races_query, (driver_code,)).fetchone()
    min_races_to_win = min_races_result['min_races'] if min_races_result and min_races_result['min_races'] else None

    # Compute position distribution, h2h, and best position
    pattern = f"%{driver_code}%"
    position_counts: Dict[int, int] = {}
    h2h_records = {opp: {"wins": 0, "losses": 0} for opp in DRIVER_NAMES.keys() if opp != driver_code}
    highest_pos = 20
    highest_pos_championship = None

    query = "SELECT championship_id, standings FROM championship_results WHERE standings LIKE ?"
    rows = db.execute(query, (pattern,)).fetchall()

    for row in rows:
        standings = row['standings'].split(',')
        try:
            driver_pos = standings.index(driver_code)
            position = driver_pos + 1
            position_counts[position] = position_counts.get(position, 0) + 1

            if position < highest_pos:
                highest_pos = position
                highest_pos_championship = row['championship_id']

            for opponent_code in h2h_records.keys():
                try:
                    opponent_pos = standings.index(opponent_code)
                    if driver_pos < opponent_pos:
                        h2h_records[opponent_code]["wins"] += 1
                    else:
                        h2h_records[opponent_code]["losses"] += 1
                except ValueError:
                    continue
        except ValueError:
            continue

    # Get win probability by season length
    win_prob_by_length: Dict[int, int] = {}
    query = "SELECT num_races, COUNT(*) as wins FROM championship_results WHERE winner = ? GROUP BY num_races"
    for row in db.execute(query, (driver_code,)).fetchall():
        win_prob_by_length[row['num_races']] = row['wins']

    # Get total seasons per length
    seasons_per_length: Dict[int, int] = {}
    for row in db.execute("SELECT num_races, COUNT(*) as total FROM championship_results GROUP BY num_races").fetchall():
        seasons_per_length[row['num_races']] = row['total']

    win_prob_percentages: Dict[int, float] = {}
    for length, wins in win_prob_by_length.items():
        total = seasons_per_length.get(length, 1)
        win_prob_percentages[length] = round((wins / total) * 100, 2)

    # Build response
    response = {
        "driver_code": driver_code,
        "driver_name": DRIVER_NAMES[driver_code],
        "driver_info": DRIVERS[driver_code],
        "total_wins": total_wins,
        "total_championships": total_championships,
        "win_percentage": win_percentage,
        "highest_position": highest_pos,
        "highest_position_championship_id": highest_pos_championship,
        "min_races_to_win": min_races_to_win,
        "position_distribution": position_counts,
        "head_to_head": h2h_records,
        "win_probability_by_length": win_prob_percentages,
        "seasons_per_length": seasons_per_length
    }

    # Cache
    api_module._driver_stats_cache[driver_code] = response

    return _convert_cached_stats_to_graphql(response)


def _convert_cached_stats_to_graphql(cached: Dict) -> DriverStats:
    """Convert cached stats dict to GraphQL DriverStats type."""
    driver_info_data = cached['driver_info']
    driver_info = Driver(
        code=cached['driver_code'],
        name=driver_info_data['name'],
        team=driver_info_data['team'],
        number=driver_info_data['number'],
        flag=driver_info_data['flag'],
        color=driver_info_data['color']
    )

    position_distribution = [
        PositionCount(position=pos, count=count)
        for pos, count in sorted(cached['position_distribution'].items())
    ]

    head_to_head = [
        HeadToHeadRecord(
            opponent_code=opp,
            wins=record['wins'],
            losses=record['losses']
        )
        for opp, record in cached['head_to_head'].items()
    ]

    win_probability_by_length = [
        WinProbabilityByLength(season_length=length, percentage=pct)
        for length, pct in sorted(cached['win_probability_by_length'].items())
    ]

    return DriverStats(
        driver_code=cached['driver_code'],
        driver_name=cached['driver_name'],
        driver_info=driver_info,
        total_wins=cached['total_wins'],
        total_championships=cached['total_championships'],
        win_percentage=cached['win_percentage'],
        highest_position=cached['highest_position'],
        highest_position_championship_id=cached['highest_position_championship_id'],
        min_races_to_win=cached['min_races_to_win'],
        position_distribution=position_distribution,
        head_to_head=head_to_head,
        win_probability_by_length=win_probability_by_length
    )


def find_championship_by_rounds(rounds: List[int]) -> FindChampionshipResult:
    """Find a championship by round numbers."""
    if not rounds:
        return FindChampionshipResult(error="No rounds provided")

    sorted_rounds = sorted(rounds)
    sorted_rounds_str = ','.join(map(str, sorted_rounds))

    db = get_db()
    row = db.execute(
        "SELECT championship_id FROM championship_results WHERE rounds = ?",
        (sorted_rounds_str,),
    ).fetchone()

    if row:
        championship_id = row['championship_id']
        return FindChampionshipResult(url=f"/championship/{championship_id}")
    else:
        return FindChampionshipResult(error="Championship with this combination of rounds not found")


def clear_cache() -> ClearCacheResult:
    """Clear all API caches."""
    api_module._highest_position_cache = None
    api_module._head_to_head_cache = {}
    api_module._driver_positions_cache = {}
    api_module._driver_stats_cache = {}
    return ClearCacheResult(success=True, message="Cache cleared successfully")
