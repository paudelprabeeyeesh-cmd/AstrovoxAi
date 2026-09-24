from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from threat_intelligence.indicator_manager import Indicator
from threat_intelligence.ioc_matcher import IOCMatcher, Match


@dataclass
class CampaignEvent:
    timestamp: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    actor: Optional[str] = None
    matches: List[Match] = field(default_factory=list)


@dataclass
class Campaign:
    name: str
    first_seen: datetime = field(default_factory=datetime.utcnow)
    last_seen: datetime = field(default_factory=datetime.utcnow)
    actors: List[str] = field(default_factory=list)
    indicators: List[Indicator] = field(default_factory=list)
    events: List[CampaignEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("Campaign name must not be empty")


class CampaignTracker:
    def __init__(self, matcher: IOCMatcher) -> None:
        self.matcher = matcher
        self._campaigns: Dict[str, Campaign] = {}

    def add_campaign(self, campaign: Campaign) -> None:
        self._campaigns[campaign.name] = campaign

    def get(self, name: str) -> Optional[Campaign]:
        return self._campaigns.get(name)

    def record_event(
        self,
        campaign_name: str,
        text: str,
        description: str = "",
        actor: Optional[str] = None,
    ) -> CampaignEvent:
        campaign = self._campaigns.setdefault(campaign_name, Campaign(name=campaign_name))
        event = CampaignEvent(description=description, actor=actor, matches=self.matcher.match_text(text))
        campaign.events.append(event)
        campaign.last_seen = datetime.utcnow()
        for match in event.matches:
            if match.indicator is not None and match.indicator not in campaign.indicators:
                campaign.indicators.append(match.indicator)
        if actor and actor not in campaign.actors:
            campaign.actors.append(actor)
        return event

    def link_actor(self, campaign_name: str, actor: str) -> None:
        campaign = self._campaigns.setdefault(campaign_name, Campaign(name=campaign_name))
        if actor not in campaign.actors:
            campaign.actors.append(actor)
        campaign.last_seen = datetime.utcnow()

    def timeline(self, campaign_name: str) -> List[CampaignEvent]:
        campaign = self._campaigns.get(campaign_name)
        if campaign is None:
            return []
        return sorted(campaign.events, key=lambda e: e.timestamp)

    def indicator_history(self, campaign_name: str) -> List[Tuple[datetime, Indicator]]:
        history: List[Tuple[datetime, Indicator]] = []
        for event in self.timeline(campaign_name):
            for match in event.matches:
                if match.indicator is not None:
                    history.append((event.timestamp, match.indicator))
        return history

    def __len__(self) -> int:
        return len(self._campaigns)
