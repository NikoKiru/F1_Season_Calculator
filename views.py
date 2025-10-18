from flask import (
    Blueprint, render_template
)
from .api import get_championship, all_championship_wins, highest_rounds_won, highest_position, most_common_runner_up

bp = Blueprint('views', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/championship/<int:id>')
def championship_page(id):
    response = get_championship(id)
    data = response.get_json()
    if response.status_code != 200:
        return render_template('championship.html', data=None), 404
    return render_template('championship.html', data=data)

@bp.route('/all_championship_wins')
def all_championship_wins_page():
    response = all_championship_wins()
    data = response.get_json()
    return render_template('all_championship_wins.html', data=data)

@bp.route('/driver_wins')
def driver_wins_page():
    return render_template('driver_wins.html')

@bp.route('/highest_rounds_won')
def highest_rounds_won_page():
    response = highest_rounds_won()
    data = response.get_json()
    return render_template('highest_rounds_won.html', data=data)

@bp.route('/highest_position')
def highest_position_page():
    response = highest_position()
    data = response.get_json()
    return render_template('highest_position.html', data=data)

@bp.route('/most_common_runner_up')
def most_common_runner_up_page():
    response = most_common_runner_up()
    data = response.get_json()
    return render_template('most_common_runner_up.html', data=data)

@bp.route('/head_to_head')
def head_to_head_page():
    return render_template('head_to_head.html')

@bp.route('/min_races_to_win')
def min_races_to_win_page():
    return render_template('min_races_to_win.html')

@bp.route('/largest_championship_wins')
def largest_championship_wins_page():
    return render_template('largest_championship_wins.html')
