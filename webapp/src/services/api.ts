import type { Save, LeagueConfig } from '../types';

interface LeagueTeams {
  [key: string]: string;  // team_id -> team_name mapping
}

export class APIService {
  private readonly API_URL = 'http://localhost:5000';

  async validateLeague(credentials: LeagueConfig): Promise<boolean> {
    try {
      const response = await fetch(`${this.API_URL}/validate-league`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials)
      });
      
      const data = await response.json();
      return data.valid;
    } catch (error) {
      console.error('Error validating league:', error);
      return false;
    }
  }

  async getLeagueTeams(credentials: LeagueConfig): Promise<LeagueTeams | null> {
    try {
      const response = await fetch(`${this.API_URL}/get-league-teams`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials)
      });
      
      const data = await response.json();
      if ('error' in data) {
        throw new Error(data.error);
      }
      
      return data.teams;
    } catch (error) {
      console.error('Error getting league teams:', error);
      return null;
    }
  }

  async setActiveSave(save: Save): Promise<boolean> {
    try {
      const response = await fetch(`${this.API_URL}/set-active-save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          saveId: save.id,
          leagueId: save.leagueId,
          year: save.year,
          s2: save.s2,
          swid: save.swid,
          teamId: save.teamId
        })
      });
      
      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Error setting active save:', error);
      return false;
    }
  }

  async clearActiveSave(): Promise<boolean> {
    try {
      const response = await fetch(`${this.API_URL}/set-active-save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(null)
      });
      
      const data = await response.json();
      return data.success;
    } catch (error) {
      console.error('Error clearing active save:', error);
      return false;
    }
  }
}