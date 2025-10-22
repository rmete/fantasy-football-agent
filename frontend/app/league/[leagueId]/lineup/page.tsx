'use client';

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { RecommendationCard } from '@/components/recommendation-card';
import { Loader2 } from 'lucide-react';
import { useParams } from 'next/navigation';
import { SitStartRecommendation } from '@/types';

export default function LineupOptimizerPage() {
  const params = useParams();
  const leagueId = params.leagueId as string;
  const [recommendations, setRecommendations] = useState<SitStartRecommendation[]>([]);

  const { data: league, isLoading: leagueLoading } = useQuery({
    queryKey: ['league', leagueId],
    queryFn: () => apiClient.getLeague(leagueId),
  });

  const { data: rosters } = useQuery({
    queryKey: ['rosters', leagueId],
    queryFn: () => apiClient.getLeagueRosters(leagueId),
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

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold">Lineup Optimizer</h1>
          <p className="text-muted-foreground">{leagueData?.name}</p>
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
