from espn_api.basketball import League
import json

target_folder = "algorithm/league_data/"

def initialize_league_info(league_id, year, s2, swid):
    try:
        league = League(league_id=league_id, year=year, espn_s2=s2, swid=swid)
        return True
    except Exception as e:
        print(f"An error occurred while fetching league info: {e}")
        return False
    
def get_league_teams(league_id, year, s2, swid):
    league = League(league_id=league_id, year=year, espn_s2=s2, swid=swid)
    teams = {}
    for team in league.teams:
        teams[team.team_id] = team.team_name
    return teams

# Only call initialize_league_info when parameters are provided
if __name__ == "__main__":
    # Example usage or testing
    pass