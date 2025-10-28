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

  async getUserLeagues(username: string, season: string = '2025') {
    return this.request(`/api/v1/sleeper/user/${username}/leagues?season=${season}`);
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

  async sendChatMessage(data: {
    message: string;
    league_id: string;
    roster_id: number;
    week?: number;
    model?: string;
    temperature?: number;
  }) {
    return this.request(`/api/v1/agents/chat`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCurrentWeek() {
    return this.request('/api/v1/agents/week');
  }

  // Projection endpoints
  async getPlayerProjection(
    playerId: string,
    options?: {
      week?: number;
      scoring_format?: 'PPR' | 'HALF_PPR' | 'STD';
      season?: number;
    }
  ) {
    const params = new URLSearchParams();
    if (options?.week) params.append('week', options.week.toString());
    if (options?.scoring_format) params.append('scoring_format', options.scoring_format);
    if (options?.season) params.append('season', options.season.toString());

    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/v1/sleeper/projections/${playerId}${query}`);
  }

  async getBatchProjections(
    playerIds: string[],
    options?: {
      week?: number;
      scoring_format?: 'PPR' | 'HALF_PPR' | 'STD';
      season?: number;
    }
  ) {
    const params = new URLSearchParams();
    if (options?.week) params.append('week', options.week.toString());
    if (options?.scoring_format) params.append('scoring_format', options.scoring_format);
    if (options?.season) params.append('season', options.season.toString());

    const query = params.toString() ? `?${params.toString()}` : '';
    return this.request(`/api/v1/sleeper/projections/batch${query}`, {
      method: 'POST',
      body: JSON.stringify(playerIds),
    });
  }

  // Conversation endpoints
  async getConversations(userId: string = 'default', limit: number = 50, offset: number = 0) {
    const params = new URLSearchParams({
      user_id: userId,
      limit: limit.toString(),
      offset: offset.toString(),
    });
    return this.request(`/api/v1/conversations?${params.toString()}`);
  }

  async getConversation(conversationId: string) {
    return this.request(`/api/v1/conversations/${conversationId}`);
  }

  async deleteConversation(conversationId: string) {
    return this.request(`/api/v1/conversations/${conversationId}`, {
      method: 'DELETE',
    });
  }

  async updateConversationTitle(conversationId: string, title: string) {
    return this.request(`/api/v1/conversations/${conversationId}/title`, {
      method: 'PATCH',
      body: JSON.stringify({ title }),
    });
  }
}

export const apiClient = new APIClient();
