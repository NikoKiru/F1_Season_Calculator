from typing import Tuple, Union, Optional
from flask import (
    Blueprint, render_template, request
)
from .api import (
    get_championship, all_championship_wins, highest_position,
    championship_win_probability, min_races_to_win, driver_position_championships
)
from .models import (
    ROUND_NAMES_2025, DRIVERS, DEFAULT_SEASON,
    get_season_data, get_available_seasons
)

bp = Blueprint('views', __name__, template_folder='templates')


def get_current_season() -> int:
    """Get the current season from query parameter or default."""
    season = request.args.get('season', type=int)
    if season is None:
        season = DEFAULT_SEASON
    return season


def get_template_context(season: Optional[int] = None) -> dict:
    """Get common template context for the given season."""
    if season is None:
        season = get_current_season()

    season_data = get_season_data(season)
    return {
        'season': season,
        'seasons': get_available_seasons(),
        'drivers': season_data.drivers,
        'driver_names': season_data.driver_names,
        'rounds': season_data.round_names,
    }


@bp.route('/')
def index() -> str:
    from db import get_db
    ctx = get_template_context()

    # Fetch the "real life" championship (the one with the largest ID)
    db = get_db()
    row = db.execute("SELECT MAX(championship_id) as max_id FROM championship_results").fetchone()
    if row and row['max_id']:
        response = get_championship(row['max_id'])
        if hasattr(response, 'get_json') and response.status_code == 200:
            ctx['real_life_data'] = response.get_json()
        else:
            ctx['real_life_data'] = None
    else:
        ctx['real_life_data'] = None

    return render_template('index.html', **ctx)


@bp.route('/championship/<int:id>')
def championship_page(id: int) -> Union[str, Tuple[str, int]]:
    ctx = get_template_context()
    response = get_championship(id)
    # Handle both Response object and tuple (response, status) returns
    if isinstance(response, tuple):
        # Error case - API returns (jsonify(response), status)
        data = None
    elif response.status_code != 200:
        data = None
    else:
        data = response.get_json()

    if not data:
        return render_template('championship.html', data=None, error="Championship not found", **ctx), 404

    return render_template('championship.html', data=data, **ctx)


@bp.route('/all_championship_wins')
def all_championship_wins_page() -> str:
    ctx = get_template_context()
    response = all_championship_wins()
    data = response.get_json()
    return render_template('all_championship_wins.html', data=data, **ctx)


@bp.route('/highest_position')
def highest_position_page() -> str:
    ctx = get_template_context()
    response = highest_position()
    data = response.get_json()
    return render_template('highest_position.html', data=data, **ctx)


@bp.route('/driver_positions')
def driver_positions_page() -> str:
    ctx = get_template_context()
    return render_template('driver_positions.html', **ctx)


@bp.route('/head_to_head')
def head_to_head_page() -> str:
    ctx = get_template_context()
    return render_template('head_to_head.html', **ctx)


@bp.route('/min_races_to_win')
def min_races_to_win_page() -> str:
    ctx = get_template_context()
    response = min_races_to_win()
    data = response.get_json()
    return render_template('min_races_to_win.html', data=data, **ctx)


@bp.route('/championship_win_probability')
def championship_win_probability_page() -> str:
    ctx = get_template_context()
    response = championship_win_probability()
    data = response.get_json()
    return render_template('championship_win_probability.html', data=data, **ctx)


@bp.route('/create_championship')
def create_championship_page() -> str:
    ctx = get_template_context()
    return render_template('create_championship.html', **ctx)


@bp.route('/drivers')
def drivers_page() -> str:
    ctx = get_template_context()
    return render_template('drivers.html', **ctx)


@bp.route('/driver/<string:driver_code>')
def driver_page(driver_code: str) -> Union[str, Tuple[str, int]]:
    ctx = get_template_context()
    driver_code = driver_code.upper()
    if driver_code not in ctx['drivers']:
        return render_template('404.html', **ctx), 404
    driver = ctx['drivers'][driver_code]
    return render_template('driver.html', driver_code=driver_code, driver=driver, **ctx)


@bp.route('/driver/<string:driver_code>/position/<int:position>')
def driver_position_detail(driver_code: str, position: int) -> Union[str, Tuple[str, int]]:
    ctx = get_template_context()
    driver_code = driver_code.upper()
    if driver_code not in ctx['drivers']:
        return render_template('404.html', **ctx), 404

    # Pass pagination params to API
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    # Temporarily set request args for the API call
    from flask import current_app
    with current_app.test_request_context(f'/api/driver/{driver_code}/position/{position}?page={page}&per_page={per_page}'):
        response = driver_position_championships(driver_code, position)

    if response.status_code != 200:
        return render_template('404.html', **ctx), 404

    data = response.get_json()
    driver = ctx['drivers'][driver_code]
    return render_template(
        'driver_position_detail.html',
        data=data,
        driver_code=driver_code,
        driver=driver,
        position=position,
        page=data.get('page', 1),
        per_page=data.get('per_page', 100),
        total_pages=data.get('total_pages', 1),
        **ctx
    )
