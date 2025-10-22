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
