'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Skeleton } from '@/components/ui/skeleton';
import { useAppSelector } from '@/store/hooks';

interface Player {
  player_id: string;
  name: string;
  position: string;
  team?: string;
  isStarter?: boolean;
}

interface RosterDisplayProps {
  roster: any;
  players: Record<string, any>;
}

export function RosterDisplay({ roster, players }: RosterDisplayProps) {
  if (!roster) {
    return (
      <Card>
        <CardContent className="p-6">
          <p className="text-muted-foreground">No roster data available</p>
        </CardContent>
      </Card>
    );
  }

  const starters = roster.starters || [];
  const allPlayers = roster.players || [];
  const bench = allPlayers.filter((p: string) => !starters.includes(p));

  // Get projection settings from Redux
  const scoringFormat = useAppSelector((state) => state.projection.scoringFormat);
  const selectedWeek = useAppSelector((state) => state.projection.selectedWeek);

  // Fetch projections for all players using Redux state
  const { data: projectionsData, isLoading: projectionsLoading } = useQuery({
    queryKey: ['projections', allPlayers, scoringFormat, selectedWeek],
    queryFn: () =>
      apiClient.getBatchProjections(allPlayers, {
        scoring_format: scoringFormat,
        week: selectedWeek || undefined,
      }),
    enabled: allPlayers.length > 0,
    staleTime: 1000 * 60 * 5, // Cache for 5 minutes (reduced since params change)
  });

  const projections = projectionsData?.projections || [];

  const getPlayerInfo = (playerId: string) => {
    const player = players[playerId];
    if (!player) {
      return {
        name: playerId,
        position: 'Unknown',
        team: 'Unknown',
      };
    }
    return {
      name: player.full_name || `${player.first_name} ${player.last_name}`,
      position: player.position || 'N/A',
      team: player.team || 'FA',
    };
  };

  const getInjuryBadgeColor = (status: string) => {
    const normalized = status?.toUpperCase();
    if (normalized === 'OUT' || normalized === 'IR') return 'bg-red-600 text-white';
    if (normalized === 'DOUBTFUL') return 'bg-orange-600 text-white';
    if (normalized === 'QUESTIONABLE') return 'bg-yellow-600 text-white';
    return 'bg-gray-600 text-white';
  };

  const PlayerCard = ({ playerId, isStarter }: { playerId: string; isStarter?: boolean }) => {
    const playerInfo = getPlayerInfo(playerId);
    const projection = projections.find((p: any) => p.player_id === playerId);

    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent transition-colors">
        <Avatar className="h-10 w-10">
          <AvatarFallback className="text-sm">
            {playerInfo.position}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="font-medium text-sm truncate">{playerInfo.name}</p>
            {projection?.is_on_bye && (
              <Badge className="text-xs bg-slate-600 text-white">BYE</Badge>
            )}
            {projection?.injury_status && !projection.is_on_bye && (
              <Badge className={`text-xs ${getInjuryBadgeColor(projection.injury_status)}`}>
                {projection.injury_status}
              </Badge>
            )}
          </div>
          <p className="text-xs text-muted-foreground">
            {playerInfo.team} • {playerInfo.position}
            {projection?.injury_body_part && ` • ${projection.injury_body_part}`}
          </p>
          {projectionsLoading ? (
            <Skeleton className="h-3 w-20 mt-1" />
          ) : projection ? (
            projection.is_on_bye ? (
              <p className="text-xs text-slate-500 mt-1 italic">On bye week</p>
            ) : projection.projected_points ? (
              <p className="text-xs font-semibold text-blue-600 mt-1">
                Proj: {projection.projected_points} pts
              </p>
            ) : projection.injury_status === 'Out' || projection.injury_status === 'IR' ? (
              <p className="text-xs text-red-600 mt-1 italic">Out - No projection</p>
            ) : (
              <p className="text-xs text-muted-foreground mt-1 italic">
                No projection
              </p>
            )
          ) : (
            <p className="text-xs text-red-500 mt-1 italic">
              Not found
            </p>
          )}
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1">
          {isStarter && (
            <Badge variant="default" className="text-xs">
              Starting
            </Badge>
          )}
          {!projectionsLoading && projection?.projected_points && (
            <div className="text-right">
              <p className="text-xs text-muted-foreground">
                {projection.floor} - {projection.ceiling}
              </p>
            </div>
          )}
        </div>
      </div>
    );
  };

  // Calculate total projected points for starters
  const starterProjections = starters
    .map((playerId: string) => projections.find((p: any) => p.player_id === playerId))
    .filter((p: any) => p?.projected_points);

  const totalProjectedPoints = starterProjections.reduce(
    (sum: number, p: any) => sum + (p?.projected_points || 0),
    0
  );

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex flex-col gap-1">
              <span>Starting Lineup</span>
              {!projectionsLoading && totalProjectedPoints > 0 && (
                <span className="text-sm font-normal text-blue-600">
                  Projected: {totalProjectedPoints.toFixed(2)} pts
                </span>
              )}
            </div>
            <Badge variant="outline">{starters.length} Players</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {starters.map((playerId: string) => (
              <PlayerCard key={playerId} playerId={playerId} isStarter />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Bench</span>
            <Badge variant="outline">{bench.length} Players</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2">
            {bench.map((playerId: string) => (
              <PlayerCard key={playerId} playerId={playerId} />
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Team Stats</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Wins</p>
              <p className="text-2xl font-bold">{roster.settings?.wins || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Losses</p>
              <p className="text-2xl font-bold">{roster.settings?.losses || 0}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Points For</p>
              <p className="text-2xl font-bold">
                {roster.settings?.fpts
                  ? Math.round(roster.settings.fpts)
                  : 0}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Points Against</p>
              <p className="text-2xl font-bold">
                {roster.settings?.fpts_against
                  ? Math.round(roster.settings.fpts_against)
                  : 0}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
