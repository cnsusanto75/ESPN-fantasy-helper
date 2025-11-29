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


def get_team_roster(league, user_team_id):
    roster = []
    for player in league.teams[user_team_id].roster:
        roster.append(player.name)
    return roster

def get_top_free_agents(league, position = None):
    if position is None:
        free_agents = league.free_agents(size = 10)
    else:
        free_agents = league.free_agents(position = position, size = 10)
    free_agents_list = []
    for agent in free_agents:
        free_agents_list.append(agent.name)
    return free_agents_list

def fetch_league(league_id, year, s2, swid):
    league = League(league_id=league_id, year=year, espn_s2=s2, swid=swid)
    return league

# Only call initialize_league_info when parameters are provided
if __name__ == "__main__":
    pass