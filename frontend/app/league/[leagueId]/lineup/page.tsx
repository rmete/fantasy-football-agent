'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Select } from '@/components/ui/select';
import { RecommendationCard } from '@/components/recommendation-card';
import { RosterDisplay } from '@/components/roster-display';
import { ChatInterface } from '@/components/chat-interface';
import { Loader2 } from 'lucide-react';
import { useParams } from 'next/navigation';
import { SitStartRecommendation } from '@/types';
import { useAppDispatch, useAppSelector } from '@/store/hooks';
import { setScoringFormat, setSelectedWeek, ScoringFormat } from '@/store/slices/projectionSlice';

export default function LineupOptimizerPage() {
  const params = useParams();
  const leagueId = params.leagueId as string;
  const [recommendations, setRecommendations] = useState<SitStartRecommendation[]>([]);

  const username = process.env.NEXT_PUBLIC_SLEEPER_USERNAME || 'rmete';

  // Redux state
  const dispatch = useAppDispatch();
  const scoringFormat = useAppSelector((state) => state.projection.scoringFormat);
  const selectedWeek = useAppSelector((state) => state.projection.selectedWeek);

  const { data: user } = useQuery({
    queryKey: ['user', username],
    queryFn: () => apiClient.getUser(username),
  });

  const { data: league, isLoading: leagueLoading } = useQuery({
    queryKey: ['league', leagueId],
    queryFn: () => apiClient.getLeague(leagueId),
  });

  const { data: rosters } = useQuery({
    queryKey: ['rosters', leagueId],
    queryFn: () => apiClient.getLeagueRosters(leagueId),
  });

  const { data: players } = useQuery({
    queryKey: ['players'],
    queryFn: () => apiClient.getPlayers(),
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });

  const { data: weekInfo } = useQuery({
    queryKey: ['current-week'],
    queryFn: () => apiClient.getCurrentWeek(),
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });

  const analyzeMutation = useMutation({
    mutationFn: (rosterId: number) =>
      apiClient.runSitStartAnalysis({
        league_id: leagueId,
        roster_id: rosterId,
        week: 1,
      }),
    onSuccess: (data: any) => {
      setRecommendations(data.recommendations || []);
    },
  });

  const handleAnalyze = () => {
    // Get the first roster for now - in production, would identify user's roster
    const rosterId = (rosters as any)?.rosters?.[0]?.roster_id || 1;
    analyzeMutation.mutate(rosterId);
  };

  if (leagueLoading) {
    return (
      <div className="container mx-auto p-6">
        <Loader2 className="h-8 w-8 animate-spin mx-auto" />
      </div>
    );
  }


  const leagueData = (league as any)?.league;

  // Find the user's actual roster by matching owner_id
  const userId = (user as any)?.user_id;
  const userRoster = ((rosters as any) || []).find(
    (r: any) => r.owner_id === userId
  );

  const playersData = players || {};
  const currentWeek = (weekInfo as any)?.current_week || 1;
  const displayWeek = selectedWeek || currentWeek;

  // Generate week options (weeks 1-18)
  const weekOptions = Array.from({ length: 18 }, (_, i) => i + 1);

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-4xl font-bold">Lineup Optimizer</h1>
          <p className="text-muted-foreground">
            {leagueData?.name} • Week {displayWeek}
          </p>
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

      {/* Projection Controls */}
      <div className="flex items-center gap-4 mb-8 p-4 bg-muted/50 rounded-lg">
        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Week:</label>
          <Select
            value={String(displayWeek)}
            onChange={(e) => dispatch(setSelectedWeek(Number(e.target.value)))}
            className="w-24"
          >
            {weekOptions.map((week) => (
              <option key={week} value={week}>
                {week} {week === currentWeek && '(Current)'}
              </option>
            ))}
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm font-medium">Scoring:</label>
          <div className="flex gap-1">
            {(['PPR', 'HALF_PPR', 'STD'] as ScoringFormat[]).map((format) => (
              <Button
                key={format}
                variant={scoringFormat === format ? 'default' : 'outline'}
                size="sm"
                onClick={() => dispatch(setScoringFormat(format))}
              >
                {format === 'HALF_PPR' ? '0.5 PPR' : format}
              </Button>
            ))}
          </div>
        </div>

        <div className="ml-auto">
          <Badge variant="secondary" className="text-xs">
            Projections: Week {displayWeek} • {scoringFormat === 'HALF_PPR' ? '0.5 PPR' : scoringFormat}
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div>
          <RosterDisplay roster={userRoster} players={playersData} />
        </div>
        <div>
          <ChatInterface
            leagueId={leagueId}
            rosterId={userRoster?.roster_id || 1}
            week={currentWeek}
          />
        </div>
      </div>

      {analyzeMutation.isPending && (
        <div className="text-center py-12">
          <Loader2 className="h-12 w-12 animate-spin mx-auto mb-4" />
          <p className="text-lg font-semibold">Analyzing your lineup...</p>
          <p className="text-sm text-muted-foreground">
            This may take 30-60 seconds as we gather data from multiple sources
          </p>
        </div>
      )}

      {analyzeMutation.isError && (
        <div className="text-center py-12">
          <p className="text-red-500">
            Error: {analyzeMutation.error instanceof Error ? analyzeMutation.error.message : 'Unknown error'}
          </p>
        </div>
      )}

      {recommendations.length > 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold mb-4 text-green-600">
              Start Recommendations ({recommendations.filter((r) => r.recommendation === 'START').length})
            </h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {recommendations
                .filter((r) => r.recommendation === 'START')
                .map((rec) => (
                  <RecommendationCard key={rec.player_id} recommendation={rec} />
                ))}
            </div>
          </div>

          <div>
            <h2 className="text-2xl font-semibold mb-4 text-red-600">
              Sit Recommendations ({recommendations.filter((r) => r.recommendation === 'SIT').length})
            </h2>
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
