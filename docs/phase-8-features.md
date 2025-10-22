# Phase 8: Feature Completion

**Goal**: Complete all end-to-end features and integrate everything together

**Estimated Time**: 10-12 hours

**Dependencies**: Phases 1-7

## Overview

This phase brings everything together:
- Complete Waiver Wire agent and UI
- Complete Lineup Manager with ability to update Sleeper
- Implement autonomous mode
- Add human-in-the-loop approval workflows
- Complete Trade Analyzer with proposal generation
- Add monitoring agent for injuries and news

## Tasks Breakdown

### Task 8.1: Waiver Wire Agent

#### backend/app/agents/waiver_agent.py

```python
from typing import Dict, Any, List
from app.agents.config import anthropic_client, SYSTEM_PROMPTS, AGENT_MODELS
from app.tools import (
    sleeper_client,
    projection_tool,
    injury_tool,
    web_search_tool,
    reddit_tool
)
import logging

logger = logging.getLogger(__name__)

class WaiverWireAgent:
    """Agent for analyzing waiver wire opportunities"""

    def __init__(self):
        self.model = AGENT_MODELS["waiver"]
        self.system_prompt = SYSTEM_PROMPTS["waiver"]

    async def analyze_waiver_wire(
        self,
        league_id: str,
        my_roster: Dict[str, Any],
        players_data: Dict[str, Any],
        week: int
    ) -> Dict[str, Any]:
        """Find waiver wire pickups"""

        logger.info(f"Analyzing waiver wire for league {league_id}")

        # Get all rosters to see who's available
        all_rosters = await sleeper_client.get_league_rosters(league_id)

        # Get trending adds
        trending = await sleeper_client.get_trending_players(add_drop="add")

        # Find rostered players
        rostered_player_ids = set()
        for roster in all_rosters:
            rostered_player_ids.update(roster.get("players", []))

        # Identify available players from trending
        available_trending = []
        for trend in trending[:50]:  # Top 50 trending
            player_id = trend.get("player_id")
            if player_id not in rostered_player_ids:
                player_info = players_data.get(player_id, {})
                if player_info:
                    available_trending.append({
                        "player_id": player_id,
                        "player_info": player_info,
                        "count": trend.get("count", 0)
                    })

        # Analyze each available player
        recommendations = []
        for player in available_trending[:10]:  # Analyze top 10
            analysis = await self._analyze_player(
                player["player_id"],
                player["player_info"],
                my_roster,
                players_data,
                week
            )
            recommendations.append(analysis)

        # Sort by priority score
        recommendations.sort(key=lambda x: x["priority_score"], reverse=True)

        # Suggest drop candidates
        drop_candidates = await self._suggest_drops(
            my_roster,
            players_data,
            recommendations
        )

        return {
            "recommendations": recommendations[:5],  # Top 5
            "drop_candidates": drop_candidates,
            "total_analyzed": len(available_trending)
        }

    async def _analyze_player(
        self,
        player_id: str,
        player_info: Dict[str, Any],
        my_roster: Dict[str, Any],
        players_data: Dict[str, Any],
        week: int
    ) -> Dict[str, Any]:
        """Analyze a waiver wire player"""

        player_name = player_info.get("full_name", "Unknown")
        position = player_info.get("position", "")

        # Get recent news
        news = await web_search_tool.search_player_news(
            player_name,
            additional_context="waiver wire breakout"
        )

        # Get sentiment
        sentiment = await reddit_tool.get_player_sentiment(player_name)

        # Get projection
        projection = await projection_tool.get_player_projection(
            player_name, position, week
        )

        # Check injury status
        injury = await injury_tool.check_player_injury_status(
            player_id, player_name
        )

        # Calculate priority score
        priority_score = self._calculate_priority(
            player_info,
            news,
            sentiment,
            projection,
            injury
        )

        # Use Claude for recommendation
        context = f"""
Waiver wire pickup analysis:

Player: {player_name} ({position})
Team: {player_info.get('team')}

Projection: {projection['projected_points']} points
Sentiment: {sentiment['sentiment_score']} ({sentiment['total_mentions']} mentions)
Injury Status: {injury['injury_status']}

Recent News:
{chr(10).join([f"- {n['title']}" for n in news[:3]])}

Should this player be prioritized for waiver pickup? Consider:
1. Breakout potential
2. Opportunity/volume
3. Schedule ahead
4. Roster fit

Provide priority level (HIGH/MEDIUM/LOW) and reasoning.
"""

        try:
            response = anthropic_client.messages.create(
                model=self.model,
                max_tokens=800,
                system=self.system_prompt,
                messages=[{"role": "user", "content": context}]
            )

            recommendation_text = response.content[0].text

            return {
                "player_id": player_id,
                "player_name": player_name,
                "position": position,
                "team": player_info.get("team"),
                "priority_score": priority_score,
                "priority_level": self._extract_priority(recommendation_text),
                "reasoning": recommendation_text,
                "projection": projection["projected_points"],
                "sentiment": sentiment["sentiment_score"],
                "injury_status": injury["injury_status"]
            }

        except Exception as e:
            logger.error(f"Error analyzing player: {e}")
            return {
                "player_id": player_id,
                "player_name": player_name,
                "priority_score": 0,
                "error": str(e)
            }

    def _calculate_priority(
        self,
        player_info: Dict,
        news: List,
        sentiment: Dict,
        projection: Dict,
        injury: Dict
    ) -> float:
        """Calculate priority score (0-100)"""

        score = 50.0  # Base

        # Boost for positive sentiment
        score += sentiment["sentiment_score"] * 10

        # Boost for projected points
        if projection["projected_points"] > 15:
            score += 20
        elif projection["projected_points"] > 10:
            score += 10

        # Penalty for injury
        if injury["severity"] != "none":
            score -= 20

        # Boost for search rank (trending)
        rank = player_info.get("search_rank", 999)
        if rank < 100:
            score += 15

        return max(0, min(100, score))

    def _extract_priority(self, text: str) -> str:
        """Extract priority level from text"""
        text_upper = text.upper()
        if "HIGH" in text_upper:
            return "HIGH"
        elif "LOW" in text_upper:
            return "LOW"
        else:
            return "MEDIUM"

    async def _suggest_drops(
        self,
        my_roster: Dict[str, Any],
        players_data: Dict[str, Any],
        pickups: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Suggest drop candidates"""

        bench_players = []
        starters = set(my_roster.get("starters", []))
        all_players = my_roster.get("players", [])

        for player_id in all_players:
            if player_id not in starters:
                player_info = players_data.get(player_id, {})
                if player_info:
                    bench_players.append({
                        "player_id": player_id,
                        "player_name": player_info.get("full_name"),
                        "position": player_info.get("position"),
                        "search_rank": player_info.get("search_rank", 999)
                    })

        # Sort by search rank (higher = worse)
        bench_players.sort(key=lambda x: x["search_rank"], reverse=True)

        return bench_players[:5]

waiver_agent = WaiverWireAgent()
```

### Task 8.2: Lineup Manager with Sleeper Update

#### backend/app/agents/lineup_agent.py

```python
from typing import Dict, Any, List
from app.agents.config import anthropic_client, SYSTEM_PROMPTS, AGENT_MODELS
from app.tools import sleeper_client, matchup_analyzer
import logging

logger = logging.getLogger(__name__)

class LineupManagerAgent:
    """Agent for managing and updating lineups"""

    def __init__(self):
        self.model = AGENT_MODELS["lineup"]
        self.system_prompt = SYSTEM_PROMPTS["lineup"]

    async def optimize_lineup(
        self,
        roster: Dict[str, Any],
        players_data: Dict[str, Any],
        league_settings: Dict[str, Any],
        week: int
    ) -> Dict[str, Any]:
        """Optimize lineup for maximum points"""

        logger.info("Optimizing lineup")

        roster_positions = league_settings.get("roster_positions", [])
        current_starters = roster.get("starters", [])
        all_players = roster.get("players", [])

        # Analyze all players
        player_analyses = {}
        for player_id in all_players:
            player_info = players_data.get(player_id, {})
            if not player_info:
                continue

            analysis = await matchup_analyzer.analyze_player_matchup(
                player_info.get("full_name", ""),
                player_info.get("team", ""),
                player_info.get("opponent", ""),
                player_info.get("position", ""),
                week
            )
            player_analyses[player_id] = analysis

        # Build optimal lineup based on roster positions
        optimal_starters = self._build_optimal_lineup(
            all_players,
            players_data,
            player_analyses,
            roster_positions
        )

        # Compare with current lineup
        changes = self._calculate_changes(current_starters, optimal_starters)

        return {
            "current_starters": current_starters,
            "optimal_starters": optimal_starters,
            "changes": changes,
            "projected_point_increase": sum(c["point_diff"] for c in changes)
        }

    def _build_optimal_lineup(
        self,
        all_players: List[str],
        players_data: Dict[str, Any],
        analyses: Dict[str, Any],
        roster_positions: List[str]
    ) -> List[str]:
        """Build optimal lineup"""

        # Simplified - in production, use more sophisticated algorithm
        # Group players by position
        players_by_position = {}
        for player_id in all_players:
            player = players_data.get(player_id, {})
            pos = player.get("position", "")
            if pos not in players_by_position:
                players_by_position[pos] = []
            players_by_position[pos].append({
                "id": player_id,
                "matchup_rating": analyses.get(player_id, {}).get("matchup_rating", 5)
            })

        # Sort by matchup rating
        for pos in players_by_position:
            players_by_position[pos].sort(
                key=lambda x: x["matchup_rating"],
                reverse=True
            )

        # Fill roster positions
        optimal = []
        used_players = set()

        for pos_slot in roster_positions:
            if pos_slot == "BN":  # Bench
                continue

            # Handle FLEX positions
            if pos_slot == "FLEX":
                eligible_positions = ["RB", "WR", "TE"]
            elif pos_slot == "SUPER_FLEX":
                eligible_positions = ["QB", "RB", "WR", "TE"]
            else:
                eligible_positions = [pos_slot]

            # Find best available player
            best_player = None
            best_rating = 0

            for pos in eligible_positions:
                for player in players_by_position.get(pos, []):
                    if player["id"] not in used_players:
                        if player["matchup_rating"] > best_rating:
                            best_rating = player["matchup_rating"]
                            best_player = player["id"]

            if best_player:
                optimal.append(best_player)
                used_players.add(best_player)

        return optimal

    def _calculate_changes(
        self,
        current: List[str],
        optimal: List[str]
    ) -> List[Dict[str, Any]]:
        """Calculate lineup changes"""

        changes = []
        current_set = set(current)
        optimal_set = set(optimal)

        # Players being benched
        benched = current_set - optimal_set
        # Players being started
        starting = optimal_set - current_set

        for player_id in benched:
            changes.append({
                "player_id": player_id,
                "action": "bench",
                "point_diff": -2.0  # Estimated
            })

        for player_id in starting:
            changes.append({
                "player_id": player_id,
                "action": "start",
                "point_diff": 2.0  # Estimated
            })

        return changes

    async def update_sleeper_lineup(
        self,
        league_id: str,
        roster_id: int,
        new_starters: List[str]
    ) -> Dict[str, Any]:
        """
        Update lineup on Sleeper
        NOTE: This requires Sleeper OAuth which is complex
        For MVP, we'll return the API call that would need to be made
        """

        # Sleeper doesn't have a simple API to update rosters
        # It requires OAuth and user authorization
        # For MVP, we provide the data for manual update

        return {
            "success": False,
            "message": "Automatic lineup updates require Sleeper OAuth integration",
            "manual_update_data": {
                "league_id": league_id,
                "roster_id": roster_id,
                "new_starters": new_starters
            },
            "instructions": "Log into Sleeper and manually update your lineup with the recommendations"
        }

lineup_agent = LineupManagerAgent()
```

### Task 8.3: Monitoring Agent

#### backend/app/agents/monitoring_agent.py

```python
from typing import Dict, Any, List
from app.tools import (
    sleeper_client,
    injury_tool,
    web_search_tool
)
from app.api.websocket import send_notification
import logging

logger = logging.getLogger(__name__)

class MonitoringAgent:
    """Agent for monitoring injuries, news, and sending alerts"""

    async def monitor_roster_injuries(
        self,
        user_id: str,
        roster: Dict[str, Any],
        players_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Monitor roster for new injuries"""

        logger.info(f"Monitoring injuries for user {user_id}")

        alerts = []
        player_ids = roster.get("players", [])

        injuries = await injury_tool.monitor_roster_injuries(
            player_ids,
            players_data
        )

        for injury in injuries:
            # Send notification
            await send_notification(
                user_id,
                "injury_alert",
                f"Injury Update: {injury['player_name']}",
                f"{injury['player_name']} is {injury['injury_status']} with {injury.get('injury_body_part', 'unknown')} injury",
                injury
            )

            alerts.append(injury)

        return alerts

    async def monitor_breaking_news(
        self,
        user_id: str,
        roster: Dict[str, Any],
        players_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Monitor for breaking news about roster players"""

        news_alerts = []
        player_ids = roster.get("starters", [])[:5]  # Monitor starters

        for player_id in player_ids:
            player_info = players_data.get(player_id, {})
            player_name = player_info.get("full_name", "")

            if not player_name:
                continue

            # Search recent news
            news = await web_search_tool.search_player_news(
                player_name,
                additional_context="breaking news today"
            )

            # Filter for important news (high score)
            important_news = [n for n in news if n.get("score", 0) > 0.7]

            if important_news:
                # Send notification
                await send_notification(
                    user_id,
                    "player_news",
                    f"News: {player_name}",
                    important_news[0]["title"],
                    {
                        "player_id": player_id,
                        "player_name": player_name,
                        "news": important_news[0]
                    }
                )

                news_alerts.append({
                    "player_id": player_id,
                    "player_name": player_name,
                    "news": important_news[0]
                })

        return news_alerts

monitoring_agent = MonitoringAgent()
```

### Task 8.4: Autonomous Mode

#### backend/app/api/autonomous.py

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.user import User
from app.agents.orchestrator import orchestrator
from app.agents.lineup_agent import lineup_agent
from app.agents.waiver_agent import waiver_agent
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/autonomous", tags=["autonomous"])

@router.post("/enable/{user_id}")
async def enable_autonomous_mode(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Enable autonomous management for a user"""

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.autonomous_mode = True
    user.preferences["autonomous_settings"] = {
        "auto_optimize_lineup": True,
        "auto_waiver_pickups": False,  # Requires approval
        "auto_trade_responses": False,  # Requires approval
        "notify_before_action": True
    }

    await db.commit()

    return {
        "success": True,
        "message": "Autonomous mode enabled",
        "settings": user.preferences["autonomous_settings"]
    }

@router.post("/disable/{user_id}")
async def disable_autonomous_mode(
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Disable autonomous mode"""

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        user.autonomous_mode = False
        await db.commit()

    return {"success": True, "message": "Autonomous mode disabled"}
```

### Task 8.5: Waiver Wire UI

#### frontend/app/league/[leagueId]/waiver/page.tsx

```typescript
'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ArrowUpDown, TrendingUp } from 'lucide-react';
import { useParams } from 'next/navigation';

export default function WaiverWirePage() {
  const params = useParams();
  const leagueId = params.leagueId as string;
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [dropCandidates, setDropCandidates] = useState<any[]>([]);

  const analyzeMutation = useMutation({
    mutationFn: () =>
      apiClient.request(`/api/v1/agents/waiver-analysis`, {
        method: 'POST',
        body: JSON.stringify({ league_id: leagueId, roster_id: 1 }),
      }),
    onSuccess: (data) => {
      setRecommendations(data.recommendations || []);
      setDropCandidates(data.drop_candidates || []);
    },
  });

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'HIGH':
        return 'bg-red-500';
      case 'MEDIUM':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-4xl font-bold">Waiver Wire</h1>
        <Button
          onClick={() => analyzeMutation.mutate()}
          disabled={analyzeMutation.isPending}
          size="lg"
        >
          <TrendingUp className="mr-2 h-4 w-4" />
          Analyze Waiver Wire
        </Button>
      </div>

      {recommendations.length > 0 && (
        <div className="space-y-6">
          <div>
            <h2 className="text-2xl font-semibold mb-4">Top Pickups</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {recommendations.map((rec) => (
                <Card key={rec.player_id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle>{rec.player_name}</CardTitle>
                      <Badge className={getPriorityColor(rec.priority_level)}>
                        {rec.priority_level}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {rec.position} • {rec.team}
                    </p>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span>Priority Score:</span>
                        <span className="font-bold">{rec.priority_score}/100</span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span>Projection:</span>
                        <span>{rec.projection.toFixed(1)} pts</span>
                      </div>
                      <p className="mt-4 p-3 bg-muted rounded text-sm">
                        {rec.reasoning}
                      </p>
                      <Button className="w-full mt-4">
                        Add to Waiver Queue
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {dropCandidates.length > 0 && (
            <div>
              <h2 className="text-2xl font-semibold mb-4">Drop Candidates</h2>
              <div className="grid gap-3">
                {dropCandidates.map((player) => (
                  <Card key={player.player_id}>
                    <CardContent className="flex items-center justify-between p-4">
                      <div>
                        <p className="font-semibold">{player.player_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {player.position}
                        </p>
                      </div>
                      <ArrowUpDown className="h-5 w-5 text-muted-foreground" />
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

## Testing

Run complete end-to-end tests:

```bash
# Backend
docker exec -it fantasy-backend python tests/test_complete_flow.py

# Frontend
# Navigate to each page and test functionality
```

## Success Criteria

After Phase 8:

1. ✅ Waiver wire agent finds and ranks pickups
2. ✅ Lineup manager optimizes lineups
3. ✅ Monitoring agent detects injuries and news
4. ✅ Autonomous mode can be enabled/disabled
5. ✅ All UI pages functional
6. ✅ End-to-end workflows complete

## Next Steps

Proceed to **[Phase 9: Testing & Polish](./phase-9-testing.md)** for final testing and refinements.

## Resources

- [Sleeper API Documentation](https://docs.sleeper.com/)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/)
