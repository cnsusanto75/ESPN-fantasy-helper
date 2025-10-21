# ESPN Fantasy Sports Helper

Currently only supports basketball, targeted towards points leagues.

An AI model that reads your league information and provides feedback such as players to add or drop.
## Requirements

Install python dependencies using "pip install ." in terminal

Obtain league ID (found in league URL, ex:123456789)
Use season end year (ex: 2025-26 season uses 2026)

For private leagues:
Obtain espn_s2 and swid from cookie information:
1. Open League
2. Right click, inspect element
3. On the top bar, open Application tab (may have to expand using arrows)
4. Under name, look for espn_s2 and swid tabs
5. Copy corresponding values

Alternatively, this chrome extension gives these values: https://chromewebstore.google.com/detail/espn-private-league-setup/bjmalaafoepfooflcnhjejnopgefjgia 