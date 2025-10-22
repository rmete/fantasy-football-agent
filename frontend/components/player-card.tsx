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
