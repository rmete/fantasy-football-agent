# Phase 6: Frontend Foundation

**Goal**: Build the Next.js frontend with core UI components and pages

**Estimated Time**: 8-10 hours

**Dependencies**: Phases 1-5

## Overview

Create a beautiful, responsive frontend with:
- Dashboard showing league overview
- Lineup optimizer with AI recommendations
- Trade analyzer interface
- Waiver wire suggestions
- Shared component library using Shadcn/ui

## Tasks Breakdown

### Task 6.1: Setup Shadcn/ui Components

```bash
cd frontend
npx shadcn-ui@latest init
```

Install needed components:
```bash
npx shadcn-ui@latest add button card dialog dropdown-menu table tabs badge avatar skeleton
```

### Task 6.2: API Client & Types

#### frontend/lib/api-client.ts

```typescript
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

  // Agent endpoints (to be implemented)
  async runSitStartAnalysis(leagueId: string, rosterId: number) {
    return this.request(`/api/v1/agents/sit-start`, {
      method: 'POST',
      body: JSON.stringify({ league_id: leagueId, roster_id: rosterId }),
    });
  }

  async analyzeTrade(
    leagueId: string,
    myPlayers: string[],
    theirPlayers: string[]
  ) {
    return this.request(`/api/v1/agents/trade-analysis`, {
      method: 'POST',
      body: JSON.stringify({
        league_id: leagueId,
        my_players: myPlayers,
        their_players: theirPlayers,
      }),
    });
  }

  async getAgentTaskStatus(taskId: string) {
    return this.request(`/api/v1/agents/tasks/${taskId}`);
  }
}

export const apiClient = new APIClient();
```

#### frontend/types/index.ts

```typescript
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

export interface AgentTask {
  task_id: string;
  task_type: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress_percentage: number;
  current_step?: string;
  result?: any;
  error_message?: string;
}
```

### Task 6.3: React Query Setup

#### frontend/lib/query-client.ts

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60 * 1000, // 1 minute
      retry: 1,
    },
  },
});
```

#### frontend/app/providers.tsx

```typescript
'use client';

import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '@/lib/query-client';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

### Task 6.4: Shared Components

#### frontend/components/player-card.tsx

```typescript
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Player } from '@/types';

interface PlayerCardProps {
  player: Player;
  showDetails?: boolean;
}

export function PlayerCard({ player, showDetails = false }: PlayerCardProps) {
  const getPositionColor = (position: string) => {
    const colors: Record<string, string> = {
      QB: 'bg-red-500',
      RB: 'bg-green-500',
      WR: 'bg-blue-500',
      TE: 'bg-yellow-500',
      K: 'bg-purple-500',
      DEF: 'bg-gray-500',
    };
    return colors[position] || 'bg-gray-400';
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{player.full_name}</CardTitle>
          <Badge className={getPositionColor(player.position)}>
            {player.position}
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground">{player.team}</p>
      </CardHeader>
      {showDetails && (
        <CardContent>
          {player.injury_status && (
            <Badge variant="destructive" className="mb-2">
              {player.injury_status}
            </Badge>
          )}
          {player.age && (
            <p className="text-sm">Age: {player.age}</p>
          )}
        </CardContent>
      )}
    </Card>
  );
}
```

#### frontend/components/recommendation-card.tsx

```typescript
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { SitStartRecommendation } from '@/types';
import { ThumbsUp, ThumbsDown } from 'lucide-react';

interface RecommendationCardProps {
  recommendation: SitStartRecommendation;
}

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const isStart = recommendation.recommendation === 'START';

  return (
    <Card className={isStart ? 'border-green-500' : 'border-red-500'}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">
            {recommendation.player_name}
          </CardTitle>
          <div className="flex items-center gap-2">
            {isStart ? (
              <ThumbsUp className="text-green-500" />
            ) : (
              <ThumbsDown className="text-red-500" />
            )}
            <Badge variant={isStart ? 'default' : 'destructive'}>
              {recommendation.recommendation}
            </Badge>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          {recommendation.position}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span>Confidence:</span>
            <span className="font-bold">{recommendation.confidence}%</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span>Projection:</span>
            <span>{recommendation.supporting_data.projection.toFixed(1)} pts</span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span>Matchup:</span>
            <span>{recommendation.supporting_data.matchup_rating.toFixed(1)}/10</span>
          </div>
          <div className="mt-4 p-3 bg-muted rounded-md">
            <p className="text-sm">{recommendation.reasoning}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Task 6.5: Dashboard Page

#### frontend/app/dashboard/page.tsx

```typescript
'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import Link from 'next/link';

export default function DashboardPage() {
  const { data: leagues, isLoading } = useQuery({
    queryKey: ['user-leagues'],
    queryFn: () => apiClient.getUserLeagues('YOUR_USERNAME'), // Get from auth
  });

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-4">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-4xl font-bold mb-8">Your Leagues</h1>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {leagues?.leagues?.map((league: any) => (
          <Link
            key={league.league_id}
            href={`/league/${league.league_id}`}
          >
            <Card className="hover:shadow-lg transition-shadow cursor-pointer">
              <CardHeader>
                <CardTitle>{league.name}</CardTitle>
                <p className="text-sm text-muted-foreground">
                  {league.total_rosters} Teams • {league.season}
                </p>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <span className="text-sm">Status:</span>
                  <span className="font-semibold capitalize">
                    {league.status}
                  </span>
                </div>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

### Task 6.6: Lineup Optimizer Page

#### frontend/app/league/[leagueId]/lineup/page.tsx

```typescript
'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { RecommendationCard } from '@/components/recommendation-card';
import { Loader2 } from 'lucide-react';
import { useParams } from 'next/navigation';

export default function LineupOptimizerPage() {
  const params = useParams();
  const leagueId = params.leagueId as string;
  const [recommendations, setRecommendations] = useState<any[]>([]);

  const { data: league, isLoading: leagueLoading } = useQuery({
    queryKey: ['league', leagueId],
    queryFn: () => apiClient.getLeague(leagueId),
  });

  const analyzeMutation = useMutation({
    mutationFn: (rosterId: number) =>
      apiClient.runSitStartAnalysis(leagueId, rosterId),
    onSuccess: (data) => {
      setRecommendations(data.recommendations || []);
    },
  });

  const handleAnalyze = () => {
    // Get roster ID from league data
    const rosterId = 1; // Would come from user's roster in league
    analyzeMutation.mutate(rosterId);
  };

  if (leagueLoading) {
    return <div className="container mx-auto p-6">Loading...</div>;
  }

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold">Lineup Optimizer</h1>
          <p className="text-muted-foreground">{league?.league?.name}</p>
        </div>
        <Button
          onClick={handleAnalyze}
          disabled={analyzeMutation.isPending}
          size="lg"
        >
          {analyzeMutation.isPending && (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          )}
          Analyze Lineup
        </Button>
      </div>

      {analyzeMutation.isPending && (
        <div className="text-center py-12">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4" />
          <p className="text-lg">Analyzing your lineup...</p>
          <p className="text-sm text-muted-foreground">
            This may take 30-60 seconds
          </p>
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold mb-4">Start Recommendations</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recommendations
                .filter((r) => r.recommendation === 'START')
                .map((rec) => (
                  <RecommendationCard key={rec.player_id} recommendation={rec} />
                ))}
            </div>
          </div>

          <div>
            <h2 className="text-2xl font-semibold mb-4">Sit Recommendations</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recommendations
                .filter((r) => r.recommendation === 'SIT')
                .map((rec) => (
                  <RecommendationCard key={rec.player_id} recommendation={rec} />
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### Task 6.7: Navigation Layout

#### frontend/app/layout.tsx

```typescript
import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Navigation } from '@/components/navigation';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'Fantasy Football AI Manager',
  description: 'AI-powered fantasy football team management',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <Providers>
          <Navigation />
          <main>{children}</main>
        </Providers>
      </body>
    </html>
  );
}
```

#### frontend/components/navigation.tsx

```typescript
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';

const routes = [
  { name: 'Dashboard', path: '/dashboard' },
  { name: 'Lineup', path: '/lineup' },
  { name: 'Trades', path: '/trades' },
  { name: 'Waiver Wire', path: '/waiver' },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="border-b">
      <div className="container mx-auto px-6 py-4">
        <div className="flex items-center justify-between">
          <Link href="/" className="text-2xl font-bold">
            Fantasy AI
          </Link>
          <div className="flex gap-6">
            {routes.map((route) => (
              <Link
                key={route.path}
                href={route.path}
                className={cn(
                  'text-sm font-medium transition-colors hover:text-primary',
                  pathname === route.path
                    ? 'text-primary'
                    : 'text-muted-foreground'
                )}
              >
                {route.name}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}
```

## Testing

```bash
# Start frontend development server
cd frontend
npm run dev

# Visit http://localhost:3000
```

## Success Criteria

After Phase 6:

1. ✅ Next.js app running on port 3000
2. ✅ Shadcn/ui components installed and themed
3. ✅ API client connecting to backend
4. ✅ Dashboard showing leagues
5. ✅ Lineup optimizer page functional
6. ✅ Navigation working
7. ✅ React Query managing data fetching

## Next Steps

Proceed to **[Phase 7: Real-time Integration](./phase-7-realtime.md)** to add WebSocket connections.

## Resources

- [Next.js Documentation](https://nextjs.org/docs)
- [Shadcn/ui Documentation](https://ui.shadcn.com/)
- [React Query Documentation](https://tanstack.com/query/latest)
