import time
from analytics.aggregator import Aggregator


class Reporter:
    def __init__(self, tracker):
        self.tracker = tracker
        self.aggregator = Aggregator()

    def summary_report(self, event_type: str = None) -> dict:
        events = self.tracker.get_events(event_type=event_type)
        return {
            "generated_at": time.time(),
            "total_events": len(events),
            "counts_by_type": self.aggregator.count_by_type(events),
            "top_types": self.aggregator.top_n_types(events, n=5),
        }

    def timeseries_report(self, interval_seconds: int = 60) -> dict:
        events = self.tracker.get_events()
        buckets = self.aggregator.group_by_interval(events, interval_seconds)
        return {
            "interval_seconds": interval_seconds,
            "buckets": {
                str(ts): {
                    "count": len(bucket),
                    "types": self.aggregator.count_by_type(bucket),
                }
                for ts, bucket in buckets.items()
            },
        }

    def payload_summary(self, field: str) -> dict:
        events = self.tracker.get_events()
        return {
            "field": field,
            "sums_by_type": self.aggregator.sum_payload_field(events, field),
            "avgs_by_type": self.aggregator.avg_payload_field(events, field),
        }
