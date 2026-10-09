import unittest

from world_model.event_scheduler import EventScheduler, ScheduledEvent


class TestEventScheduler(unittest.TestCase):
    def test_schedule_and_step(self):
        scheduler = EventScheduler()
        fired = []

        def action(event: ScheduledEvent) -> None:
            fired.append(event.id)

        scheduler.schedule("e1", 1.0, action)
        scheduler.set_time(1.0)
        events = scheduler.step()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].id, "e1")
        self.assertEqual(fired, ["e1"])

    def test_advance(self):
        scheduler = EventScheduler()
        fired = []

        def action(event: ScheduledEvent) -> None:
            fired.append(event.id)

        scheduler.schedule("e1", 2.0, action)
        events = scheduler.advance(3.0)
        self.assertEqual(len(events), 1)
        self.assertEqual(fired, ["e1"])

    def test_cancel(self):
        scheduler = EventScheduler()
        fired = []

        def action(event: ScheduledEvent) -> None:
            fired.append(event.id)

        scheduler.schedule("e1", 1.0, action)
        scheduler.cancel("e1")
        scheduler.set_time(1.0)
        events = scheduler.step()
        self.assertEqual(len(events), 0)
        self.assertEqual(fired, [])

    def test_multiple_events(self):
        scheduler = EventScheduler()
        order = []

        def make_action(eid):
            def action(event: ScheduledEvent) -> None:
                order.append(eid)
            return action

        scheduler.schedule("first", 1.0, make_action("first"))
        scheduler.schedule("second", 2.0, make_action("second"))
        scheduler.set_time(1.0)
        scheduler.step()
        self.assertEqual(order, ["first"])
        scheduler.set_time(2.0)
        scheduler.step()
        self.assertEqual(order, ["first", "second"])

    def test_pending(self):
        scheduler = EventScheduler()
        scheduler.schedule("e1", 1.0, lambda e: None)
        scheduler.schedule("e2", 2.0, lambda e: None)
        self.assertEqual(len(scheduler.pending()), 2)

    def test_clear(self):
        scheduler = EventScheduler()
        scheduler.schedule("e1", 1.0, lambda e: None)
        scheduler.clear()
        self.assertEqual(scheduler.pending(), [])


if __name__ == "__main__":
    unittest.main()
