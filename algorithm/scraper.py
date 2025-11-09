import sqlite3
from espn_api.basketball import League

data_folder = "algorithm/player_data/"
espn_db_path = data_folder + "espn_league_info.db"
espn_db = sqlite3.connect(espn_db_path)
espn_cursor = espn_db.cursor()
    
def update_player_stats(league):
    cats = league.teams[0].roster[0].stats['2026_total']['avg'].keys()
    cat_string = "[NAME], [" +"], [".join([f"{cat}" for cat in cats]) + "]"
    print(cat_string)
    espn_cursor.execute(f"CREATE TABLE IF NOT EXISTS player_stats({cat_string})")
    #for player in league.players:
        # Update player stats in the database
        #pass

update_player_stats(League(league_id=783667716, year=2026, espn_s2="AEBeJU6gxbT0JUb1kskzDwIdakZzEwMka/9QNop7SujUIrZYiD9U6WMahLbwB69unEuS7uShGWMgJbn3qPDWjHr1fQDpTAeIYBV+qsPNzxZlVZmPAs04GvKxCEdqLZJQn44YyJ3JS5zQpWVtCE7c79DzBwhAcpg+jRStKrThbNPkrTp3AQmVV5Zqpc5RNk+7JeyzMB6alSZlYmdDzXxD7OcVBLXMwAtHvekQ7RGq2cKw2Q8MbWWet/PTl3bWr/TX+q5XWGff00dOCyA42KAsA2SpYV8Ndvj1ZETNSjU5qAPftA==", swid="{3836ABEE-C9FF-4BA8-87B4-DAD5F7FAAB8E}"))