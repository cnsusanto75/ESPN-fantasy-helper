from espn_api.basketball import League

def get_league_info():
    league_id = int(input("Enter your league ID: "))
    year = int(input("Enter the year for the league (e.g., 2023): ")) 
    s2 = input("Enter your espn_s2 cookie value: ") 
    swid = input("Enter your swid cookie value (including curly braces): ") 
    return League(league_id=league_id, year=year, espn_s2 = s2, swid = swid)

league = get_league_info()
print(league.teams)