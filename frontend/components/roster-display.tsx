'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

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

  const PlayerCard = ({ playerId, isStarter }: { playerId: string; isStarter?: boolean }) => {
    const playerInfo = getPlayerInfo(playerId);

    return (
      <div className="flex items-center gap-3 p-3 rounded-lg border bg-card hover:bg-accent transition-colors">
        <Avatar className="h-10 w-10">
          <AvatarFallback className="text-sm">
            {playerInfo.position}
          </AvatarFallback>
        </Avatar>
        <div className="flex-1 min-w-0">
          <p className="font-medium text-sm truncate">{playerInfo.name}</p>
          <p className="text-xs text-muted-foreground">
            {playerInfo.team} • {playerInfo.position}
          </p>
        </div>
        {isStarter && (
          <Badge variant="default" className="shrink-0">
            Starting
          </Badge>
        )}
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Starting Lineup</span>
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
