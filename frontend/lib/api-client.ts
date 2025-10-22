const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIClient {
  private baseURL: string;

  constructor() {
    this.baseURL = API_BASE;
  }

  private async request<T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<T> {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Sleeper endpoints
  async getUser(username: string) {
    return this.request(`/api/v1/sleeper/user/${username}`);
  }

  async getUserLeagues(username: string) {
    return this.request(`/api/v1/sleeper/user/${username}/leagues`);
  }

  async getLeague(leagueId: string) {
    return this.request(`/api/v1/sleeper/league/${leagueId}`);
  }

  async getLeagueRosters(leagueId: string) {
    return this.request(`/api/v1/sleeper/league/${leagueId}/rosters`);
  }

  async getPlayers() {
    return this.request('/api/v1/sleeper/players');
  }

  // Agent endpoints
  async runSitStartAnalysis(data: {
    user_id?: string;
    league_id: string;
    roster_id: number;
    week?: number;
  }) {
    return this.request(`/api/v1/agents/sit-start`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async analyzeTrade(data: {
    user_id?: string;
    league_id: string;
    roster_id: number;
    my_players: string[];
    their_players: string[];
  }) {
    return this.request(`/api/v1/agents/trade-analysis`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getAgentHealth() {
    return this.request('/api/v1/agents/health');
  }
}

export const apiClient = new APIClient();
