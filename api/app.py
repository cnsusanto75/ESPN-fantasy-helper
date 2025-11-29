from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from dataclasses import dataclass
from typing import Optional

# Add the algorithm directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from algorithm.league_info import (
    initialize_league_info,
    get_league_teams,
    fetch_league,
    get_team_roster as fetch_team_roster,
    get_top_free_agents as fetch_top_free_agents
)
from algorithm.scraper import update_player_stats

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}})

@dataclass
class ActiveSave:
    id: str
    league_id: int
    year: int
    s2: str
    swid: str
    team_id: Optional[int] = None

# Global variable to store the current active save
active_save: Optional[ActiveSave] = None

@app.route('/set-active-save', methods=['POST'])
def set_active_save():
    global active_save
    data = request.json

    if not data or data.get('saveId') is None:
        active_save = None
        return jsonify({'success': True, 'activeSave': None})

    try:
        if 'teamId' not in data:
            return jsonify({'success': False, 'error': 'Missing teamId'}), 400

        active_save = ActiveSave(
            id=data['saveId'],
            league_id=int(data['leagueId']),
            year=int(data['year']),
            s2=data['s2'],
            swid=data['swid'],
            team_id=int(data['teamId'] - 1) if data['teamId'] is not None else None
        )
        return jsonify({
            'success': True, 
            'activeSave': {
                'id': active_save.id,
                'leagueId': active_save.league_id,
                'year': active_save.year,
                'teamId': active_save.team_id
            }
        })
    except (KeyError, ValueError) as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/get-active-save', methods=['GET'])
def get_active_save():
    if active_save is None:
        return jsonify({'error': 'No active save set'}), 404
    
    return jsonify({
        'id': active_save.id,
        'leagueId': active_save.league_id,
        'year': active_save.year
    })

@app.route('/get-league-teams', methods=['POST'])
def get_league_teams():
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    required_fields = ['leagueId', 'year', 's2', 'swid']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        from algorithm.league_info import get_league_teams
        teams = get_league_teams(
            league_id=int(data['leagueId']),
            year=int(data['year']),
            s2=data['s2'],
            swid=data['swid']
        )
        return jsonify({'teams': teams})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/validate-league', methods=['POST'])
def validate_league():
    data = request.json
    if not data:
        return jsonify({'valid': False, 'error': 'No data provided'}), 400
    
    # Check if all required fields are present
    required_fields = ['leagueId', 'year', 's2', 'swid']
    if not all(field in data for field in required_fields):
        return jsonify({'valid': False, 'error': 'Missing required fields'}), 400
    
    try:
        result = initialize_league_info(
            league_id=int(data['leagueId']),  # Ensure league_id is an integer
            year=int(data['year']),
            s2=data['s2'],
            swid=data['swid']
        )
        return jsonify({'valid': bool(result)})
    except ValueError as e:
        return jsonify({'valid': False, 'error': 'Invalid league ID or year'}), 400
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 400
    
def send_league_teams():
    teams = get_league_teams(
        active_save.league_id,
        active_save.year,
        active_save.s2,
        active_save.swid
    )
    return jsonify({'teams': teams})

def update_stats():
    update_player_stats(fetch_league(
            active_save.league_id,
            year=active_save.year,
            espn_s2=active_save.s2,
            swid=active_save.swid
    ))

def _require_active_save(check_team: bool = False):
    if active_save is None:
        raise ValueError('No active save set')
    if check_team and active_save.team_id is None:
        raise ValueError('No team selected for active save')

def _fetch_active_league():
    _require_active_save()
    return fetch_league(
        active_save.league_id,
        active_save.year,
        active_save.s2,
        active_save.swid
    )

@app.route('/get-team-roster', methods=['GET'])
def get_team_roster_route():
    try:
        _require_active_save(check_team=True)
        league = _fetch_active_league()
        roster = fetch_team_roster(league, active_save.team_id)
        return jsonify({'roster': roster})
    except ValueError as err:
        return jsonify({'error': str(err)}), 400
    except Exception as err:
        return jsonify({'error': str(err)}), 500

@app.route('/get-top-free-agents', methods=['GET'])
def get_top_free_agents_route():
    try:
        league = _fetch_active_league()
        top_free_agents = {
            'OVERALL': fetch_top_free_agents(league),
            'POINT GUARD': fetch_top_free_agents(league, position='PG'),
            'SHOOTING GUARD': fetch_top_free_agents(league, position='SG'),
            'SMALL FORWARD': fetch_top_free_agents(league, position='SF'),
            'POWER FORWARD': fetch_top_free_agents(league, position='PF'),
            'CENTER': fetch_top_free_agents(league, position='C'),
        }
        return jsonify({'top_free_agents': top_free_agents})
    except ValueError as err:
        return jsonify({'error': str(err)}), 400
    except Exception as err:
        return jsonify({'error': str(err)}), 500

if __name__ == '__main__':
    app.run(port=5000)