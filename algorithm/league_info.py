from espn_api.basketball import League
import json

def get_user_team(league):
    for team in league.teams:
        print(f"Team Name: {team.team_name}, Team ID: {team.team_id}")
    return int(input("Enter your Team ID from the above list: "))

def initialize_league_info():
    league_id = int(input("Enter your league ID (e.g., 123456789): "))
    year = int(input("Enter the year for the league (e.g., 2026): ")) 
    s2 = input("Enter your espn_s2 cookie value: ") 
    swid = input("Enter your swid cookie value (including curly braces): ")
    try:
        team_id = get_user_team(League(league_id=league_id, year=year, espn_s2=s2, swid=swid))
        league_info = {
            "league_id": league_id,
            "year": year,
            "espn_s2": s2,
            "swid": swid,
            "user_team_id": team_id
        }
        with open("league_info.json", "w") as f:
            json.dump(league_info, f, indent = 4)
        return League(league_id=league_id, year=year, espn_s2 = s2, swid = swid)
    except Exception as e:
        print(f"An error occurred while fetching league info: {e}")
        return None
 
initialize_league_info()