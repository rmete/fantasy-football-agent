# projection_tool = ProjectionTool()
import asyncio
import httpx
from bs4 import BeautifulSoup  # kept since you already import it (not used here)
from typing import Dict, Any, Optional, List, Tuple
import logging
import time
import unicodedata

logger = logging.getLogger(__name__)

SLEEPER_API = "https://api.sleeper.app"
SLEEPER_V1 = f"{SLEEPER_API}/v1"
SLEEPER_PROJECTIONS_API = "https://api.sleeper.com"  # Projections use .com domain

# Simple in-process caches to avoid re-downloading big player list repeatedly
_player_cache: Dict[str, Dict[str, Any]] = {}
_player_cache_loaded_at: float = 0.0
_player_cache_ttl_sec = 6 * 60 * 60  # 6 hours

def _slug(s: str) -> str:
    """Lowercase, strip accents, trim, collapse spaces."""
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return " ".join(s.lower().strip().split())

def _name_keys(player: Dict[str, Any]) -> List[str]:
    keys = []
    for k in ("full_name", "first_name", "last_name", "last_name", "search_full_name"):
        v = player.get(k)
        if v:
            keys.append(_slug(v))
    # Also common alt name forms: "CeeDee Lamb" => "ceedee lamb", jersey number, etc.
    if player.get("first_name") and player.get("last_name"):
        keys.append(_slug(f"{player['first_name']} {player['last_name']}"))
    if player.get("last_name") and player.get("first_name"):
        keys.append(_slug(f"{player['last_name']}, {player['first_name']}"))
    return list(dict.fromkeys(keys))  # unique, preserve order

def _best_name_match(player_name: str, position: Optional[str], catalog: Dict[str, Dict[str, Any]]) -> Optional[Tuple[str, Dict[str, Any]]]:
    """
    Return (player_id, player_obj) best match by fuzzy-ish normalization + position filter.
    """
    target = _slug(player_name)
    if not target:
        return None

    # Exact match on any key first; constrain by position if provided
    exact_hits = []
    loose_hits = []

    for pid, p in catalog.items():
        if position and p.get("position") and p["position"] != position:
            continue
        keys = _name_keys(p)
        if target in keys:
            exact_hits.append((pid, p))
        else:
            # loose contains: first or last or both as substring
            if any(k in target or target in k for k in keys):
                loose_hits.append((pid, p))

    if exact_hits:
        # Prefer active NFL players, then highest last_modified
        exact_hits.sort(key=lambda t: (t[1].get("status") != "Active", -(t[1].get("last_modified", 0) or 0)))
        return exact_hits[0]
    if loose_hits:
        loose_hits.sort(key=lambda t: (t[1].get("status") != "Active", -(t[1].get("last_modified", 0) or 0)))
        return loose_hits[0]
    return None

class ProjectionTool:
    """Tool for aggregating player projections from Sleeper"""

    def __init__(self, *, timeout: float = 10.0):
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            headers={"User-Agent": "projection-tool/1.0"},
            follow_redirects=True  # Enable redirect following
        )

    async def _get_state(self) -> Dict[str, Any]:
        """Current season/week from Sleeper."""
        resp = await self._client.get(f"{SLEEPER_V1}/state/nfl")
        resp.raise_for_status()
        return resp.json()

    async def _ensure_player_catalog(self) -> Dict[str, Dict[str, Any]]:
        global _player_cache, _player_cache_loaded_at
        now = time.time()
        if _player_cache and (now - _player_cache_loaded_at) < _player_cache_ttl_sec:
            return _player_cache

        logger.info("Fetching Sleeper player catalog…")
        resp = await self._client.get(f"{SLEEPER_V1}/players/nfl")
        resp.raise_for_status()
        data = resp.json()  # huge dict keyed by player_id
        # Keep only reasonable fields to reduce memory (but keep names/position/misc ids)
        pruned = {}
        for pid, p in data.items():
            pruned[pid] = {
                "player_id": pid,
                "full_name": p.get("full_name"),
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "position": p.get("position"),
                "team": p.get("team"),
                "status": p.get("status"),
                "last_modified": p.get("last_modified"),
                "depth_chart_order": p.get("depth_chart_order"),
                "number": p.get("number"),
                "search_full_name": p.get("search_full_name"),
            }
        _player_cache = pruned
        _player_cache_loaded_at = now
        return pruned

    async def _fetch_sleeper_projections(
        self,
        season: int,
        week: int,
        positions: Optional[List[str]] = None,
        season_type: str = "regular",
    ) -> List[Dict[str, Any]]:
        """
        Call Sleeper projections endpoint. Returns a list of projection dicts for players.
        """
        if positions is None:
            positions = ["QB", "RB", "WR", "TE", "K", "DEF", "FLEX"]

        # Projections endpoint uses api.sleeper.com (not .app like v1 endpoints)
        # https://api.sleeper.com/projections/nfl/{season}/{week}?season_type=regular&position[]=QB&position[]=RB&...
        params = [("season_type", season_type)]
        for pos in positions:
            params.append(("position[]", pos))

        url = f"{SLEEPER_PROJECTIONS_API}/projections/nfl/{season}/{week}"
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise ValueError("Unexpected projections payload from Sleeper")
        return data

    @staticmethod
    def _points_from_projection(p: Dict[str, Any], scoring: str) -> Optional[float]:
        # Points are nested in the 'stats' object
        stats = p.get("stats", {})
        scoring = scoring.upper()
        if scoring in ("PPR", "FULL_PPR"):
            return stats.get("pts_ppr")
        if scoring in ("HALF_PPR", "HALFPPR", "0.5PPR"):
            # Some payloads use pts_half_ppr; fall back to ppr if half missing
            return stats.get("pts_half_ppr") if stats.get("pts_half_ppr") is not None else stats.get("pts_ppr")
        if scoring in ("STD", "STANDARD", "NON_PPR"):
            return stats.get("pts_std")
        # Default to PPR if unknown
        return stats.get("pts_ppr")

    def _estimate_floor_ceiling(self, p: Dict[str, Any], scoring: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Sleeper doesn't expose explicit floor/ceiling; derive light bounds
        using volume variance proxies (e.g., target share / carry share are not present),
        so we use a conservative +/- 20% band as a placeholder when abs stats are missing.
        If stat detail exists, widen band for volatile roles (WR3/boom-bust).
        """
        pts = self._points_from_projection(p, scoring)
        if pts is None:
            return None, None

        # Simple heuristic: K and DEF narrower, WR slightly wider
        pos = p.get("position")
        band = 0.2
        if pos in ("K", "DEF"):
            band = 0.12
        elif pos == "WR":
            band = 0.25
        floor = max(0.0, pts * (1 - band))
        ceil = pts * (1 + band)
        return round(floor, 2), round(ceil, 2)

    async def get_player_projection(
        self,
        player_name: str,
        position: str,
        week: Optional[int] = None,
        scoring_format: str = "PPR",
        season: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Get Sleeper projection for a player.
        Returns:
            {
                "player": str,
                "position": str,
                "team": str | None,
                "week": int,
                "season": int,
                "projected_points": float | None,
                "floor": float | None,
                "ceiling": float | None,
                "confidence": str,
                "sources": List[Dict],
                "raw": Dict (raw Sleeper projection row)
            }
        """
        state = await self._get_state()
        season = season or int(state.get("season"))
        current_week = int(state.get("week") or 1)
        target_week = int(week or current_week)

        catalog = await self._ensure_player_catalog()
        match = _best_name_match(player_name, position, catalog)
        if not match:
            return {
                "player": player_name,
                "position": position,
                "team": None,
                "week": target_week,
                "season": season,
                "projected_points": None,
                "floor": None,
                "ceiling": None,
                "confidence": "low",
                "sources": [{"name": "Sleeper", "endpoint": "projections", "status": "not_found"}],
                "note": "Player not found in Sleeper catalog for the given position."
            }

        player_id, player_obj = match

        # Fetch projections for this week and season (once); then pick the player row
        projections = await self._fetch_sleeper_projections(season=season, week=target_week)
        # Projections come as list with fields like player_id, position, team, stats, pts_ppr/pts_std etc.
        row = next((r for r in projections if str(r.get("player_id")) == str(player_id)), None)

        points = self._points_from_projection(row or {}, scoring_format) if row else None
        floor, ceiling = self._estimate_floor_ceiling(row or {}, scoring_format) if row else (None, None)

        confidence = "medium"
        if points is None:
            confidence = "low"

        return {
            "player": player_obj.get("full_name") or player_name,
            "position": player_obj.get("position") or position,
            "team": player_obj.get("team"),
            "week": target_week,
            "season": season,
            "projected_points": round(points, 2) if isinstance(points, (int, float)) else None,
            "floor": floor,
            "ceiling": ceiling,
            "confidence": confidence,
            "sources": [
                {
                    "name": "Sleeper",
                    "season": season,
                    "week": target_week,
                    "scoring": scoring_format.upper(),
                    "endpoint": f"/projections/nfl/{season}/{target_week}",
                }
            ],
            "raw": row or {},
        }

    async def get_weekly_rankings(
        self,
        position: str,
        week: Optional[int] = None,
        scoring_format: str = "PPR",
        season: Optional[int] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return top players at a position for the week based on Sleeper projections.
        """
        state = await self._get_state()
        season = season or int(state.get("season"))
        current_week = int(state.get("week") or 1)
        target_week = int(week or current_week)

        projections = await self._fetch_sleeper_projections(season=season, week=target_week, positions=[position])

        # Build catalog once for nice names/teams
        catalog = await self._ensure_player_catalog()

        rows = []
        for r in projections:
            # Position is nested in player object
            player_pos = r.get("player", {}).get("position")
            if player_pos != position:
                continue
            pid = str(r.get("player_id"))
            p = catalog.get(pid, {})
            pts = self._points_from_projection(r, scoring_format)
            if pts is None:
                continue
            floor, ceil = self._estimate_floor_ceiling(r, scoring_format)
            rows.append({
                "player": p.get("full_name") or pid,
                "player_id": pid,
                "team": p.get("team"),
                "position": position,
                "week": target_week,
                "season": season,
                "projected_points": round(pts, 2),
                "floor": floor,
                "ceiling": ceil,
                "source": "Sleeper",
            })

        rows.sort(key=lambda x: x["projected_points"], reverse=True)
        return rows[:limit]

    async def aclose(self):
        await self._client.aclose()


projection_tool = ProjectionTool()
