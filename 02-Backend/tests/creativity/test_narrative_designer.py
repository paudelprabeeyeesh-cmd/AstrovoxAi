from creativity.narrative_designer import NarrativeDesigner, Plot


class TestNarrativeDesigner:
    def test_design_returns_plot(self):
        designer = NarrativeDesigner()
        plot = designer.design("redemption", characters=3)
        assert isinstance(plot, Plot)
        assert plot.title
        assert plot.structure
        assert len(plot.stages) > 0

    def test_coherence_in_range(self):
        designer = NarrativeDesigner()
        plot = designer.design("betrayal", characters=2)
        assert 0.0 <= plot.coherence <= 1.0

    def test_characters_count(self):
        designer = NarrativeDesigner()
        plot = designer.design("journey", characters=4)
        stage_text = " ".join(plot.stages)
        names = ["Aria", "Orion", "Lyra", "Zara", "Kael", "Nova", "Riven", "Sable"]
        found = sum(name in stage_text for name in names)
        assert found >= 2

    def test_structure_variations(self):
        designer = NarrativeDesigner(seed=1)
        plots = [designer.design("hope", characters=2, structure=s) for s in ["three_act", "hero_journey", "kishotenketsu"]]
        assert len({p.structure for p in plots}) == 3

    def test_title_contains_theme(self):
        designer = NarrativeDesigner()
        plot = designer.design("silence")
        assert "silence" in plot.title.lower()

    def test_deterministic_with_seed(self):
        designer_a = NarrativeDesigner(seed=11)
        designer_b = NarrativeDesigner(seed=11)
        p_a = designer_a.design("light", characters=2)
        p_b = designer_b.design("light", characters=2)
        assert p_a.title == p_b.title
        assert p_a.stages == p_b.stages

    def test_specific_structure_stages(self):
        designer = NarrativeDesigner(seed=2)
        plot = designer.design("redemption", characters=2, structure="three_act")
        assert plot.stages == ["setup", "confrontation", "resolution"]

    def test_stages_contain_theme(self):
        designer = NarrativeDesigner(seed=3)
        plot = designer.design("courage", characters=3)
        combined = " ".join(plot.stages).lower()
        assert "courage" in combined

    def test_archetypes_assigned_sequentially(self):
        designer = NarrativeDesigner(seed=4)
        plot = designer.design("journey", characters=4)
        expected = ["hero", "mentor", "trickster", "shadow"]
        found = [archetype for archetype in expected if archetype in " ".join(plot.stages)]
        assert len(found) >= 2
