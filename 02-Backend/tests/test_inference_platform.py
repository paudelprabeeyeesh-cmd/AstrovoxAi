"""Tests for the inference platform."""

from __future__ import annotations

import asyncio
import unittest

from app.inference_platform import (
    ContinuousBatchScheduler,
    GenerationRequest,
    GPUScaler,
    ModelRouter,
    RequestState,
    SpeculativeDecoder,
    StreamingInference,
)


class ContinuousBatchTest(unittest.IsolatedAsyncioTestCase):
    async def test_submit_and_run(self):
        async def fake_executor(batch):
            return [f"output_{r.id}" for r in batch]

        scheduler = ContinuousBatchScheduler(fake_executor, max_batch_size=4, max_wait_ms=10)
        req = GenerationRequest(id="r1", prompt="hello world", max_tokens=10)
        await scheduler.submit(req)
        finished = await scheduler.run_until_empty()
        self.assertEqual(len(finished), 1)
        self.assertEqual(finished[0].output, "output_r1")
        self.assertEqual(finished[0].state, RequestState.FINISHED)

    async def test_batch_multiple(self):
        async def fake_executor(batch):
            return [f"out_{r.id}" for r in batch]

        scheduler = ContinuousBatchScheduler(fake_executor, max_batch_size=10, max_wait_ms=5)
        for i in range(5):
            await scheduler.submit(GenerationRequest(id=f"r{i}", prompt="hi", max_tokens=5))
        finished = await scheduler.run_until_empty()
        self.assertEqual(len(finished), 5)
        self.assertEqual(scheduler.stats()["total_processed"], 5)

    async def test_cancel_pending(self):
        async def fake_executor(batch):
            return [f"out_{r.id}" for r in batch]

        scheduler = ContinuousBatchScheduler(fake_executor, max_wait_ms=5)
        req = GenerationRequest(id="r1", prompt="hi")
        await scheduler.submit(req)
        result = await scheduler.cancel("r1")
        self.assertTrue(result)
        self.assertEqual(req.state, RequestState.CANCELLED)

    async def test_failure_marks_all_failed(self):
        async def failing_executor(batch):
            raise RuntimeError("boom")

        scheduler = ContinuousBatchScheduler(failing_executor, max_wait_ms=5)
        req = GenerationRequest(id="r1", prompt="hi")
        await scheduler.submit(req)
        finished = await scheduler.run_until_empty()
        self.assertEqual(finished[0].state, RequestState.FAILED)


class SpeculativeDecoderTest(unittest.TestCase):
    def test_propose(self):
        decoder = SpeculativeDecoder(
            draft_model=lambda tokens, k: [100, 101, 102, 103, 104][:k],
            target_model=lambda tokens: [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.05],
        )
        proposed = decoder.propose([1, 2, 3])
        self.assertEqual(len(proposed), 5)

    def test_verify_all_accepted(self):
        # All probs > 0.01 so all should be accepted
        decoder = SpeculativeDecoder(
            draft_model=lambda tokens, k: [10, 11, 12],
            target_model=lambda tokens: [0.5] * 20,
        )
        accepted, n = decoder.verify([1, 2], [10, 11, 12])
        self.assertEqual(n, 3)
        self.assertEqual(accepted, [10, 11, 12])

    def test_verify_some_rejected(self):
        # First probs are high, then drop to 0
        decoder = SpeculativeDecoder(
            draft_model=lambda tokens, k: [10, 11, 12],
            target_model=lambda tokens: [0.5, 0.5, 0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        )
        accepted, n = decoder.verify([1, 2], [10, 11, 12])
        # The verify looks at indices len(tokens)+i = 2, 3, 4 of probs (which is 0.5, 0.0, 0.0)
        # So 0 is accepted, 1 and 2 rejected
        self.assertEqual(n, 1)


class ModelRouterTest(unittest.IsolatedAsyncioTestCase):
    async def test_route_cheapest(self):
        router = ModelRouter()
        router.register("expensive", self._exec, cost_per_token=0.01)
        router.register("cheap", self._exec, cost_per_token=0.001)
        request = GenerationRequest(id="r1", prompt="hi")
        chosen = router.route(request=request, prefer_cheapest=True)
        self.assertEqual(chosen, "cheap")

    async def test_route_by_capability(self):
        router = ModelRouter()
        router.register("a", self._exec, capabilities=["chat"])
        router.register("b", self._exec, capabilities=["embedding"])
        request = GenerationRequest(id="r1", prompt="hi")
        chosen = router.route(request=request, preferred_capability="embedding")
        self.assertEqual(chosen, "b")

    async def test_execute_increments_load(self):
        router = ModelRouter()

        async def my_exec(req):
            return f"result_{req.id}"

        router.register("m1", my_exec)
        request = GenerationRequest(id="r1", prompt="hi")
        result = await router.execute("m1", request)
        self.assertEqual(result, "result_r1")
        self.assertEqual(router.stats()["models"]["m1"]["load"], 0)

    @staticmethod
    async def _exec(req):
        return f"result_{req.id}"


class StreamingInferenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_stream_tokens(self):
        async def my_executor(tokens, request):
            for t in ["hello", " ", "world"]:
                yield t
                await asyncio.sleep(0.001)

        request = GenerationRequest(id="r1", prompt="", max_tokens=10)
        si = StreamingInference(my_executor)
        tokens = []
        async for tok in si.stream(request, []):
            tokens.append(tok)
        self.assertEqual("".join(tokens), "hello world")
        self.assertEqual(request.tokens_generated, 3)
        self.assertEqual(request.state, RequestState.FINISHED)

    async def test_cancel_stops_stream(self):
        async def my_executor(tokens, request):
            for t in ["a", "b", "c", "d"]:
                yield t
                await asyncio.sleep(0.001)

        request = GenerationRequest(id="r1", prompt="", max_tokens=10)
        si = StreamingInference(my_executor)
        si.cancel("r1")
        tokens = []
        async for tok in si.stream(request, []):
            tokens.append(tok)
        self.assertEqual(request.state, RequestState.CANCELLED)


class GPUScalerTest(unittest.TestCase):
    def test_scale_up_on_high_load(self):
        scaler = GPUScaler(max_concurrent_per_gpu=10, target_p95_ms=100)
        scaler.observe(load=15, p95_ms=50, replicas=1)
        hint = scaler.recommend()
        self.assertEqual(hint.recommended_replicas, 2)
        self.assertIn("high", hint.reason)

    def test_scale_down_on_low_load(self):
        scaler = GPUScaler(max_concurrent_per_gpu=10, target_p95_ms=100)
        scaler.observe(load=2, p95_ms=50, replicas=3)
        hint = scaler.recommend()
        self.assertEqual(hint.recommended_replicas, 2)
        self.assertIn("low", hint.reason)

    def test_scale_on_high_latency(self):
        scaler = GPUScaler(max_concurrent_per_gpu=10, target_p95_ms=100)
        scaler.observe(load=5, p95_ms=500, replicas=1)
        hint = scaler.recommend()
        self.assertEqual(hint.recommended_replicas, 2)

    def test_stable(self):
        scaler = GPUScaler(max_concurrent_per_gpu=10, target_p95_ms=100)
        scaler.observe(load=5, p95_ms=50, replicas=1)
        hint = scaler.recommend()
        self.assertEqual(hint.recommended_replicas, 1)
        self.assertEqual(hint.reason, "stable")

    def test_cost_estimate(self):
        scaler = GPUScaler(gpu_hourly_cost=3.0, max_concurrent_per_gpu=10)
        scaler.observe(load=25, p95_ms=50, replicas=2)  # utilization 1.25 -> scale to 3
        hint = scaler.recommend()
        self.assertEqual(hint.recommended_replicas, 3)
        self.assertEqual(hint.cost_estimate_per_hour, 9.0)


if __name__ == "__main__":
    unittest.main()
