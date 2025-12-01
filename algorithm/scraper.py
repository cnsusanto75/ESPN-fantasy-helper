import sqlite3
import os
from espn_api.basketball import League

# Get the absolute path to the database
script_dir = os.path.dirname(os.path.abspath(__file__))
data_folder = os.path.join(script_dir, "player_data")
espn_db_path = os.path.join(data_folder, "espn_league_info.db")


def create_player_stats_table(league):
    espn_db = sqlite3.connect(espn_db_path)
    espn_cursor = espn_db.cursor()
    cats = league.teams[0].roster[0].stats['2026_total']['avg'].keys()
    cat_string = "[NAME], [" +"], [".join([f"{cat}" for cat in cats]) + "]"
    espn_cursor.execute(f"CREATE TABLE IF NOT EXISTS player_stats({cat_string})")
    espn_db.commit()
    espn_db.close()

def update_player_stats(league):
    create_player_stats_table(league)
    # Fetch existing player names to avoid duplicates
    espn_db = sqlite3.connect(espn_db_path)
    espn_cursor = espn_db.cursor()
    # Get the actual column name (might be [NAME] or NAME)
    espn_cursor.execute("PRAGMA table_info(player_stats)")
    columns = [row[1] for row in espn_cursor.fetchall()]
    name_col = None
    for col in columns:
        if col.replace('[', '').replace(']', '').upper() == 'NAME':
            name_col = col
            break
    if not name_col:
        print("Could not find NAME column")
        espn_db.close()
        return
    
    # Query using the correct column name format
    if '[' in name_col or ']' in name_col:
        query = f'SELECT "{name_col}" FROM player_stats'
    else:
        query = f'SELECT {name_col} FROM player_stats'
    espn_cursor.execute(query)
    existing_player_names = [row[0] for row in espn_cursor.fetchall()]
    # Update players on rosters
    for team in league.teams:
        for player in team.roster:
            if player.name in existing_player_names:
                continue  # Skip players already in the database
            try:
                stats = player.stats['2026_total']['avg']
                placeholders = ', '.join(['?'] * (len(stats) + 1))
                columns = "[NAME], [" +"], [".join([f"{cat}" for cat in stats.keys()]) + "]"
                stats = [player.name] + list(stats.values())
                espn_cursor.execute(f"INSERT INTO player_stats ({columns}) VALUES ({placeholders})", stats)
            except Exception as e:
                print(f"Error updating player {player.name}: {e}")
    # Update free agents
    for player in league.free_agents(size = 2000):
        if player.name in existing_player_names:
            continue  # Skip players already in the database
        try:
            stats = player.stats['2026_total']['avg']
            placeholders = ', '.join(['?'] * (len(stats) + 1))
            columns = "[NAME], [" +"], [".join([f"{cat}" for cat in stats.keys()]) + "]"
            stats = [player.name] + list(stats.values())
            espn_cursor.execute(f"INSERT INTO player_stats ({columns}) VALUES ({placeholders})", stats)
        except Exception as e:
            print(f"Error updating free agent {player.name}: {e}")
    espn_db.commit()
    espn_db.close()

def get_player_stats_from_db(player_name):
    """Query the database for a player's stats by name."""
    try:
        if not os.path.exists(espn_db_path):
            print(f"Database not found at: {espn_db_path}")
            return None
            
        espn_db = sqlite3.connect(espn_db_path)
        espn_cursor = espn_db.cursor()
        
        # Get column names first
        espn_cursor.execute("PRAGMA table_info(player_stats)")
        columns = [row[1] for row in espn_cursor.fetchall()]
        
        if not columns:
            print("No columns found in player_stats table")
            espn_db.close()
            return None
        
        # Try both [NAME] and NAME as column names
        name_column = None
        for col in columns:
            # Remove brackets for comparison
            col_clean = col.replace('[', '').replace(']', '').upper()
            if col_clean == 'NAME':
                name_column = col
                break
        
        if not name_column:
            print(f"NAME column not found. Available columns: {columns}")
            espn_db.close()
            return None
        
        # Query player by name - try case-insensitive matching first
        # SQLite handles bracketed column names directly, no need for extra quotes
        # Try exact match first
        query = f'SELECT * FROM player_stats WHERE {name_column} = ?'
        espn_cursor.execute(query, (player_name,))
        row = espn_cursor.fetchone()
        
        # If not found, try case-insensitive match
        if row is None:
            # Use COLLATE NOCASE for case-insensitive comparison
            query = f'SELECT * FROM player_stats WHERE {name_column} = ? COLLATE NOCASE'
            espn_cursor.execute(query, (player_name,))
            row = espn_cursor.fetchone()
        
        # If still not found, try LIKE match (handles partial matches)
        if row is None:
            query = f'SELECT * FROM player_stats WHERE {name_column} LIKE ? COLLATE NOCASE'
            espn_cursor.execute(query, (f'%{player_name}%',))
            row = espn_cursor.fetchone()
        
        espn_db.close()
        
        if row is None:
            print(f"Player '{player_name}' not found in database")
            # Debug: show some sample names from database
            try:
                debug_db = sqlite3.connect(espn_db_path)
                debug_cursor = debug_db.cursor()
                debug_cursor.execute(f'SELECT "{name_column}" FROM player_stats LIMIT 10')
                sample_names = [row[0] for row in debug_cursor.fetchall()]
                print(f"Sample names in database: {sample_names}")
                debug_db.close()
            except:
                pass
            return None
        
        # Convert row to dictionary
        stats = {}
        for i, col in enumerate(columns):
            stats[col] = row[i]
        
        return stats
    except Exception as e:
        print(f"Error querying player stats for {player_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def get_required_cats(League):
    data = League.espn_request.get_league()['settings']['scoringSettings']['scoringItems']
    required_cats = []
    for cat in data:
        if cat['points'] != 0:
            required_cats.append(cat['statId'])
    all_cats = League.teams[0].roster[0].stats['2026_total']['avg'].keys()
    cat_map = {}
    for i, cat in enumerate(all_cats):
        if i in required_cats:
            cat_map[i] = cat
    return cat_map
