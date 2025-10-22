'use client';

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import Link from 'next/link';
import { SleeperLeague } from '@/types';

export default function DashboardPage() {
  // TODO: Get username from authentication/environment
  const username = process.env.NEXT_PUBLIC_SLEEPER_USERNAME || 'testuser';

  const { data: leagues, isLoading, error } = useQuery({
    queryKey: ['user-leagues', username],
    queryFn: () => apiClient.getUserLeagues(username),
  });

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-4">
        <Skeleton className="h-12 w-64" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-red-500">
          Error loading leagues: {error instanceof Error ? error.message : 'Unknown error'}
        </div>
      </div>
    );
  }

  const leaguesList = (leagues as any)?.leagues || [];

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-4xl font-bold mb-8">Your Leagues</h1>

      {leaguesList.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-muted-foreground">No leagues found for this user.</p>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {leaguesList.map((league: SleeperLeague) => (
            <Link
              key={league.league_id}
              href={`/league/${league.league_id}/lineup`}
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
      )}
    </div>
  );
}
