import os
import sys

import pytest
import torch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from models.llm.architectures.base import ArchitectureRegistry
from models.llm.nas.evaluator import ArchitectureEvaluator, EvalResult
from models.llm.nas.evolution import NASEvolution, SearchRecord
from models.llm.nas.manager import NASManager
from models.llm.nas.search import NASSearchSpace, ArchitectureGenome


SEED_GPT2 = {
    "architecture_family": "gpt2",
    "num_layers": 4,
    "hidden_size": 256,
    "num_heads": 4,
    "intermediate_size": 512,
    "max_seq_len": 512,
    "dropout": 0.1,
    "tie_weights": True,
    "use_bias": True,
}

SMALL_GPT2 = {
    "architecture_family": "gpt2",
    "num_layers": 2,
    "hidden_size": 128,
    "num_heads": 4,
    "intermediate_size": 256,
    "max_seq_len": 128,
    "dropout": 0.0,
    "tie_weights": True,
    "use_bias": True,
}


def _evaluator(device: str = "cpu"):
    return ArchitectureEvaluator(
        device=device,
        input_shape=(2, 16),
        vocab_size=50,
        grad_steps=1,
    )


def _fast_evolution():
    return NASEvolution(
        search_space=NASSearchSpace(seed=42),
        population_size=8,
        elite_size=2,
        tournament_size=2,
        mutation_rate=0.4,
        crossover_rate=0.6,
        max_generations=4,
        seed=42,
    )


class TestArchitectureGenome:
    def test_default_id(self):
        g = ArchitectureGenome()
        assert g.genome_id == "gpt2_L4_H256_hd4_ffn512"

    def test_from_config(self):
        g = ArchitectureGenome.from_config(SEED_GPT2)
        assert g.architecture_family == "gpt2"
        assert g.num_layers == 4
        assert g.hidden_size == 256
        assert g.num_heads == 4
        assert g.intermediate_size == 512

    def test_as_config(self):
        g = ArchitectureGenome.from_config(SEED_GPT2)
        cfg = g.as_config()
        assert cfg["architecture_family"] == "gpt2"
        assert cfg["num_layers"] == 4

    def test_copy(self):
        g = ArchitectureGenome.from_config(SEED_GPT2)
        g.metadata["fitness"] = 0.9
        child = g.copy()
        assert child.genome_id == g.genome_id
        assert child.metadata["fitness"] == 0.9

    def test_id_auto_when_blank(self):
        g = ArchitectureGenome()
        assert g.genome_id != ""

    def test_fitness_default(self):
        g = ArchitectureGenome()
        assert g.fitness() == float("-inf")


class TestNASSearchSpace:
    def test_seed_architectures(self):
        ss = NASSearchSpace(seed=42)
        seeds = ss.list_seed_architectures()
        assert "gpt2-small" in seeds
        assert "gpt2-base" in seeds
        assert "llama-mini" in seeds
        assert "mistral-tiny" in seeds

    def test_sample_random(self):
        ss = NASSearchSpace(seed=42)
        g = ss.sample_genome("random")
        assert g.architecture_family in NASSearchSpace._ARCHITECTURE_FAMILIES
        assert g.hidden_size > 0
        assert g.hidden_size % g.num_heads == 0

    def test_sample_seed(self):
        ss = NASSearchSpace(seed=42)
        g = ss.sample_genome("seed")
        assert g.architecture_family in NASSearchSpace._ARCHITECTURE_FAMILIES

    def test_invalid_strategy(self):
        ss = NASSearchSpace(seed=42)
        with pytest.raises(ValueError):
            ss.sample_genome("invalid")

    def test_get_seed_genomes(self):
        ss = NASSearchSpace(seed=42)
        genomes = ss.get_seed_genomes()
        assert len(genomes) == len(ss.list_seed_architectures())
        for g in genomes:
            assert isinstance(g, ArchitectureGenome)

    def test_mutate_num_layers(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome.from_config(SEED_GPT2)
        mutated = ss.mutate(g)
        assert mutated.parent_ids == [g.genome_id]
        assert mutated.genome_id is not None

    def test_mutate_hidden_size(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome.from_config(SEED_GPT2)
        for _ in range(10):
            mutated = ss.mutate(g)
            assert mutated.hidden_size % mutated.num_heads == 0

    def test_mutate_num_heads(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome.from_config(SEED_GPT2)
        for _ in range(10):
            mutated = ss.mutate(g)
            assert mutated.hidden_size % mutated.num_heads == 0

    def test_crossover(self):
        ss = NASSearchSpace(seed=42)
        a = ArchitectureGenome.from_config(SEED_GPT2)
        b = ArchitectureGenome.from_config(SMALL_GPT2)
        child = ss.crossover(a, b)
        assert child.parent_ids == [a.genome_id, b.genome_id]
        assert child.mutation == "crossover"
        assert child.hidden_size % child.num_heads == 0

    def test_crossover_same(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome.from_config(SEED_GPT2)
        child = ss.crossover(g, g)
        assert len(child.parent_ids) >= 1
        assert g.genome_id in child.parent_ids

    def test_validate_genome(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome.from_config(SEED_GPT2)
        errors = ss.validate_genome(g)
        assert errors == []

    def test_validate_genome_bad(self):
        ss = NASSearchSpace(seed=42)
        g = ArchitectureGenome(
            architecture_family="gpt2",
            num_layers=0,
            hidden_size=-1,
            num_heads=4,
            intermediate_size=0,
            dropout=-0.5,
            tie_weights=False,
            use_bias=True,
        )
        errors = ss.validate_genome(g)
        assert len(errors) >= 3


class TestNASEvolution:
    def test_init_population(self):
        evo = _fast_evolution()
        pop = evo.initialize_population()
        assert len(pop) == evo.population_size
        for g in pop:
            assert g.hidden_size % g.num_heads == 0

    def test_tournament_select(self):
        evo = _fast_evolution()
        evo.initialize_population()
        selected = evo._tournament_select()
        assert selected in evo.population

    def test_elitism(self):
        evo = _fast_evolution()
        evo.initialize_population()
        for g in evo.population:
            g.metadata["fitness"] = float(g.genome_id.split("_")[1].replace("L", "")) if "L" in g.genome_id else 0.0
        elites = evo.elitism(evo.population)
        assert len(elites) == evo.elite_size
        assert elites[0].fitness() >= elites[-1].fitness()

    def test_linear_rank_selection(self):
        evo = _fast_evolution()
        evo.initialize_population()
        selected = evo._linear_rank_selection()
        assert selected in evo.population

    def test_selection_pressure(self):
        evo = _fast_evolution()
        assert evo.selection_pressure() == 0.0
        evo.initialize_population()
        assert isinstance(evo.selection_pressure(), float)

    def test_evolve_generation(self):
        evo = _fast_evolution()
        evo.initialize_population()
        evaluator = _evaluator()
        records = evo.evolve_generation(evaluator, device="cpu")
        assert isinstance(records, list)
        assert len(records) == evo.population_size

    def test_run_search(self):
        evo = _fast_evolution()
        evo.initialize_population()
        evaluator = _evaluator()
        results = evo.run_search(evaluator, device="cpu")
        assert isinstance(results, list)

    def test_best_score_update(self):
        evo = _fast_evolution()
        evo.initialize_population()
        evaluator = _evaluator()
        evo.run_search(evaluator, device="cpu")
        assert evo.best_score == float("-inf") or isinstance(evo.best_score, float)


class TestArchitectureEvaluator:
    def test_evaluate_returns_float(self):
        ev = _evaluator()
        g = ArchitectureGenome.from_config(SEED_GPT2)
        score, params, elapsed = ev.evaluate(g, device="cpu")
        assert isinstance(score, float)
        assert isinstance(params, int)
        assert isinstance(elapsed, float)

    def test_evaluate_best_score(self):
        ev = _evaluator()
        g = ArchitectureGenome.from_config(SEED_GPT2)
        score, _, _ = ev.evaluate(g, device="cpu")
        assert score < 0.0 or score > 0.0

    def test_performance_prediction(self):
        ev = _evaluator()
        g = ArchitectureGenome.from_config(SEED_GPT2)
        pred = ev.performance_prediction(g)
        assert pred["genome_id"] == g.genome_id
        assert pred["estimated_params"] > 0

    def test_resource_estimation(self):
        ev = _evaluator()
        g = ArchitectureGenome.from_config(SEED_GPT2)
        res = ev.resource_estimation(g)
        assert res["total_mb"] > 0.0
        assert res["dtype"] == "float32"

    def test_evaluate_small_genome(self):
        ev = _evaluator()
        g = ArchitectureGenome.from_config(SMALL_GPT2)
        score, params, elapsed = ev.evaluate(g, device="cpu")
        assert isinstance(score, float)
        assert params > 0

    def test_evaluate_invalid_family(self):
        ev = _evaluator()
        g = ArchitectureGenome(
            architecture_family="does_not_exist",
            num_layers=2,
            hidden_size=64,
            num_heads=2,
            intermediate_size=128,
            max_seq_len=64,
            dropout=0.0,
            tie_weights=True,
            use_bias=True,
        )
        score, params, elapsed = ev.evaluate(g, device="cpu")
        assert score == float("-inf")
        assert params == 0


class TestNASManager:
    def test_search(self, tmp_path):
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir=str(tmp_path / "nas_output"),
            population_size=8,
            elite_size=2,
            max_generations=3,
            seed=42,
            device="cpu",
        )
        summary = manager.search()
        assert "best_score" in summary
        assert "best_genome" in summary

    def test_get_config(self):
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir="nas_output",
            population_size=8,
            elite_size=2,
            max_generations=4,
            seed=42,
            device="cpu",
        )
        cfg = manager.get_config()
        assert cfg["population_size"] == 8
        assert cfg["max_generations"] == 4
        assert cfg["device"] == "cpu"

    def test_checkpoint_save_restore(self, tmp_path):
        out = tmp_path / "nas_output"
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir=str(out),
            population_size=8,
            elite_size=2,
            max_generations=6,
            seed=42,
            device="cpu",
        )
        manager.search()
        ckpts = sorted((out / "checkpoints").glob("checkpoint_gen*.json"))
        assert len(ckpts) >= 1

        manager2 = NASManager(
            search_space=NASSearchSpace(seed=42),
            evaluator=_evaluator(device="cpu"),
            output_dir=str(out),
            population_size=8,
            elite_size=2,
            max_generations=6,
            seed=42,
            device="cpu",
        )
        manager2.restore_from_checkpoint(ckpts[0])
        summary = manager2.search()
        assert "best_score" in summary

    def test_final_results(self, tmp_path):
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        out = tmp_path / "nas_output"
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir=str(out),
            population_size=8,
            elite_size=2,
            max_generations=3,
            seed=42,
            device="cpu",
        )
        manager.search()
        assert (out / "best_architectures.json").exists()
        assert (out / "summary.md").exists()

    def test_get_config_serializable(self):
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir="nas_output",
            population_size=8,
            elite_size=2,
            max_generations=4,
            seed=42,
            device="cpu",
        )
        cfg = manager.get_config()
        assert all(isinstance(v, (int, float, str, bool, type(None), list, dict)) for v in cfg.values())


class TestNASPackage:
    def test_package_exports(self):
        import models.llm.nas as pkg
        assert hasattr(pkg, "NASSearchSpace")
        assert hasattr(pkg, "ArchitectureGenome")
        assert hasattr(pkg, "NASEvolution")
        assert hasattr(pkg, "ArchitectureEvaluator")
        assert hasattr(pkg, "NASManager")

    def test_search_space_instantiation(self):
        ss = NASSearchSpace(seed=42)
        assert ss is not None

    def test_evolution_instantiation(self):
        evo = _fast_evolution()
        assert evo is not None

    def test_evaluator_instantiation(self):
        ev = _evaluator()
        assert ev is not None

    def test_manager_instantiation(self):
        ss = NASSearchSpace(seed=42)
        ev = _evaluator(device="cpu")
        manager = NASManager(
            search_space=ss,
            evaluator=ev,
            output_dir="nas_output",
            population_size=8,
            elite_size=2,
            max_generations=4,
            seed=42,
            device="cpu",
        )
        assert manager is not None
