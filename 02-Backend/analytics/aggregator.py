from collections import defaultdict


class Aggregator:
    def count_by_type(self, events):
        result = defaultdict(int)
        for event in events:
            result[event["type"]] += 1
        return dict(result)

    def sum_payload_field(self, events, field: str):
        result = defaultdict(float)
        for event in events:
            value = event.get("payload", {}).get(field)
            if value is not None:
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                result[event["type"]] += numeric
        return dict(result)

    def avg_payload_field(self, events, field: str):
        sums = defaultdict(float)
        counts = defaultdict(int)
        for event in events:
            value = event.get("payload", {}).get(field)
            if value is not None:
                try:
                    sums[event["type"]] += float(value)
                    counts[event["type"]] += 1
                except (TypeError, ValueError):
                    pass
        return {
            event_type: sums[event_type] / counts[event_type]
            for event_type in sums
            if counts[event_type] > 0
        }

    def group_by_interval(self, events, interval_seconds: int):
        buckets = defaultdict(list)
        for event in events:
            ts = event["timestamp"]
            bucket_key = int(ts // interval_seconds) * interval_seconds
            buckets[bucket_key].append(event)
        return dict(sorted(buckets.items()))

    def top_n_types(self, events, n: int = 5):
        counts = self.count_by_type(events)
        return sorted(counts.items(), key=lambda item: item[1], reverse=True)[:n]
