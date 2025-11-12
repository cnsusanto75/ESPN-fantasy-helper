import sqlite3
from espn_api.basketball import League

data_folder = "algorithm/player_data/"
espn_db_path = data_folder + "espn_league_info.db"


def create_player_stats_table(league):
    espn_db = sqlite3.connect(espn_db_path)
    espn_cursor = espn_db.cursor()
    cats = league.teams[0].roster[0].stats['2026_total']['avg'].keys()
    cat_string = "[NAME], [" +"], [".join([f"{cat}" for cat in cats]) + "]"
    espn_cursor.execute(f"CREATE TABLE IF NOT EXISTS player_stats({cat_string})")
    espn_db.commit()
    espn_db.close()

def update_player_stats(league):
    # Fetch existing player names to avoid duplicates
    espn_db = sqlite3.connect(espn_db_path)
    espn_cursor = espn_db.cursor()
    query = "SELECT name FROM player_stats"
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