import unittest

from world_model.temporal_reasoning import CausalLink, Event, TemporalReasoner


class TestEvent(unittest.TestCase):
    def test_defaults(self):
        e = Event(id="e1", timestamp=0.0, description="test")
        self.assertEqual(e.id, "e1")
        self.assertEqual(e.entities, [])

    def test_with_properties(self):
        e = Event(id="e1", timestamp=1.0, description="d", entities=["a"], properties={"k": "v"})
        self.assertEqual(e.properties, {"k": "v"})


class TestCausalLink(unittest.TestCase):
    def test_defaults(self):
        link = CausalLink(cause="c", effect="e")
        self.assertEqual(link.cause, "c")
        self.assertEqual(link.effect, "e")
        self.assertEqual(link.strength, 0.5)
        self.assertEqual(link.delay, 0.0)

    def test_custom_values(self):
        link = CausalLink(cause="c", effect="e", strength=0.9, delay=2.0)
        self.assertEqual(link.strength, 0.9)
        self.assertEqual(link.delay, 2.0)


class TestTemporalReasoner(unittest.TestCase):
    def test_add_event_sorted(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e2", timestamp=2.0, description="d2"))
        tr.add_event(Event(id="e1", timestamp=1.0, description="d1"))
        self.assertEqual(tr.events[0].id, "e1")
        self.assertEqual(tr.events[1].id, "e2")

    def test_add_causal_link(self):
        tr = TemporalReasoner()
        tr.add_causal_link("c", "e", strength=0.8, delay=1.0)
        self.assertEqual(len(tr.links), 1)
        self.assertEqual(tr.links[0].cause, "c")
        self.assertEqual(tr.links[0].strength, 0.8)

    def test_sequence(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=1.0, description="d"))
        tr.add_event(Event(id="e2", timestamp=5.0, description="d"))
        result = tr.sequence(2.0, 4.0)
        self.assertEqual(len(result), 0)
        result = tr.sequence(0.0, 5.0)
        self.assertEqual(len(result), 2)

    def test_causality_score(self):
        tr = TemporalReasoner()
        tr.add_causal_link("a", "b", strength=0.7)
        self.assertAlmostEqual(tr.causality_score("a", "b"), 0.7)
        self.assertEqual(tr.causality_score("x", "y"), 0.0)

    def test_predict_next(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=0.0, description="d"))
        predicted = tr.predict_next(window=3)
        self.assertIsNotNone(predicted)
        self.assertAlmostEqual(predicted.timestamp, 1.0)

    def test_predict_next_empty(self):
        tr = TemporalReasoner()
        self.assertIsNone(tr.predict_next())

    def test_build_timeline(self):
        tr = TemporalReasoner()
        tr.add_event(Event(id="e1", timestamp=0.0, description="d"))
        tr.add_causal_link("root", "e1")
        timeline = tr.build_timeline()
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["causes"], ["root"])

    def test_event_similarity(self):
        tr = TemporalReasoner()
        a = Event(id="a", timestamp=0.0, description="d", entities=["x"])
        b = Event(id="b", timestamp=0.0, description="d", entities=["x"])
        sim = tr.event_similarity(a, b)
        self.assertAlmostEqual(sim, 1.0)


if __name__ == "__main__":
    unittest.main()
