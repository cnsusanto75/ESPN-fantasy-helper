from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
from dataclasses import dataclass
from typing import Optional

# Add the algorithm directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from algorithm.league_info import initialize_league_info

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://localhost:3000", "http://localhost:3001"]}})

@dataclass
class ActiveSave:
    id: str
    league_id: int
    year: int
    s2: str
    swid: str

# Global variable to store the current active save
active_save: Optional[ActiveSave] = None

@app.route('/set-active-save', methods=['POST'])
def set_active_save():
    global active_save
    data = request.json
    
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400
    
    try:
        active_save = ActiveSave(
            id=data['saveId'],
            league_id=int(data['leagueId']),
            year=int(data['year']),
            s2=data['s2'],
            swid=data['swid']
        )
        return jsonify({
            'success': True, 
            'activeSave': {
                'id': active_save.id,
                'leagueId': active_save.league_id,
                'year': active_save.year
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

if __name__ == '__main__':
    app.run(port=5000)