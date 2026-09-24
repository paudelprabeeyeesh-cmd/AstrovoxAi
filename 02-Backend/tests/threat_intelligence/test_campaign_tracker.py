from datetime import datetime

import pytest

from threat_intelligence.campaign_tracker import Campaign, CampaignTracker
from threat_intelligence.indicator_manager import Indicator, IndicatorManager
from threat_intelligence.ioc_matcher import IOCMatcher


@pytest.fixture
def tracker():
    manager = IndicatorManager()
    manager.add(Indicator(value="1.2.3.4", type="ip", confidence=0.9))
    manager.add(Indicator(value="malicious.com", type="domain", confidence=0.8))
    return CampaignTracker(IOCMatcher(manager))


def test_add_and_get_campaign(tracker):
    campaign = Campaign(name="OpPhish")
    tracker.add_campaign(campaign)
    assert tracker.get("OpPhish") is campaign
    assert len(tracker) == 1


def test_record_event(tracker):
    tracker.add_campaign(Campaign(name="OpPhish"))
    event = tracker.record_event("OpPhish", "Visit malicious.com from 1.2.3.4", description="Initial access")
    assert len(event.matches) == 2
    campaign = tracker.get("OpPhish")
    assert len(campaign.indicators) == 2
    assert campaign.actors == []


def test_link_actor(tracker):
    tracker.add_campaign(Campaign(name="OpPhish"))
    tracker.link_actor("OpPhish", "APT-X")
    campaign = tracker.get("OpPhish")
    assert campaign.actors == ["APT-X"]


def test_timeline(tracker):
    tracker.add_campaign(Campaign(name="OpPhish"))
    tracker.record_event("OpPhish", "1.2.3.4", description="First seen")
    tracker.record_event("OpPhish", "1.2.3.4", description="Second seen")
    timeline = tracker.timeline("OpPhish")
    assert len(timeline) == 2
    assert timeline[0].description == "First seen"
    assert timeline[1].description == "Second seen"


def test_indicator_history(tracker):
    tracker.add_campaign(Campaign(name="OpPhish"))
    tracker.record_event("OpPhish", "1.2.3.4")
    history = tracker.indicator_history("OpPhish")
    assert len(history) == 1
    assert history[0][1].value == "1.2.3.4"


def test_missing_campaign(tracker):
    assert tracker.timeline("Missing") == []
