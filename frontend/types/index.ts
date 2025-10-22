export interface SleeperUser {
  user_id: string;
  username: string;
  display_name: string;
  avatar?: string;
}

export interface SleeperLeague {
  league_id: string;
  name: string;
  season: string;
  sport: string;
  status: string;
  total_rosters: number;
  roster_positions: string[];
  scoring_settings: Record<string, any>;
}

export interface SleeperRoster {
  roster_id: number;
  owner_id: string;
  players: string[];
  starters: string[];
  reserve?: string[];
  wins: number;
  losses: number;
  ties: number;
  fpts: number;
}

export interface Player {
  player_id: string;
  full_name: string;
  first_name?: string;
  last_name?: string;
  position: string;
  team?: string;
  age?: number;
  injury_status?: string;
  search_rank?: number;
}

export interface SitStartRecommendation {
  player_id: string;
  player_name: string;
  position: string;
  recommendation: 'START' | 'SIT';
  confidence: number;
  reasoning: string;
  supporting_data: {
    projection: number;
    matchup_rating: number;
    injury_status: string;
    sentiment_score: number;
  };
}

export interface TradeAnalysis {
  recommendation: 'ACCEPT' | 'REJECT' | 'COUNTER';
  confidence: number;
  reasoning: string;
  value_analysis: {
    my_value: number;
    their_value: number;
    value_difference: number;
  };
  counter_offer?: string;
}

export interface AgentTask {
  task_id: string;
  task_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_percentage: number;
  current_step?: string;
  result?: any;
  error_message?: string;
}
