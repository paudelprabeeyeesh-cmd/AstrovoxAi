import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from models.llm.cloud.hosting import ModelHostingService
from models.llm.cloud.billing import BillingSystem, PricingTier
from models.llm.cloud.autoscaling import Autoscaler, ScalingPolicy


class TestModelHostingService:
    def test_create_api_key(self):
        service = ModelHostingService()
        key = service.create_api_key("dev1", "primary", "secret-key-123")
        assert key.name == "primary"
        assert key.is_active is True

    def test_validate_api_key(self):
        service = ModelHostingService()
        key = service.create_api_key("dev1", "primary", "secret-key-123")
        validated = service.validate_api_key("secret-key-123")
        assert validated is not None
        assert validated.key_id == key.key_id
        assert validated.last_used_at is not None

    def test_revoke_api_key(self):
        service = ModelHostingService()
        key = service.create_api_key("dev1", "primary", "secret-key-123")
        service.revoke_api_key(key.key_id)
        assert service.validate_api_key("secret-key-123") is None

    def test_host_model(self):
        service = ModelHostingService()
        model = service.host_model("TestModel", "user1", "https://api.example.com/test-model")
        assert model.name == "TestModel"
        assert model.replicas == 1

    def test_update_replicas(self):
        service = ModelHostingService()
        model = service.host_model("TestModel", "user1", "https://api.example.com/test-model")
        updated = service.update_replicas(model.model_id, 3)
        assert updated.replicas == 3

    def test_log_request(self):
        service = ModelHostingService()
        model = service.host_model("TestModel", "user1", "https://api.example.com/test-model")
        entry = service.log_request(model.model_id, "dev1", 100, 200, 150.5)
        assert entry["tokens_in"] == 100
        assert entry["tokens_out"] == 200


class TestBillingSystem:
    def test_register_tier_and_record_usage(self):
        billing = BillingSystem()
        tier = PricingTier(
            tier_id="tier-1",
            name="Pro",
            monthly_price=29.0,
            included_tokens=100000,
            overage_rate_per_token=0.00002,
        )
        billing.register_tier(tier)
        billing.record_usage("dev1", tokens_in=50000, tokens_out=30000, model_id="model-1")
        summary = billing.get_usage_summary("dev1")
        assert summary["total_tokens"] == 80000

    def test_generate_invoice_without_overage(self):
        billing = BillingSystem()
        tier = PricingTier(
            tier_id="tier-1",
            name="Pro",
            monthly_price=29.0,
            included_tokens=100000,
            overage_rate_per_token=0.00002,
        )
        billing.register_tier(tier)
        from datetime import datetime, timedelta
        start = datetime.utcnow() - timedelta(days=30)
        end = datetime.utcnow()
        billing.record_usage("dev1", tokens_in=10000, tokens_out=10000)
        invoice = billing.generate_invoice("dev1", "tier-1", start, end)
        assert invoice.total == pytest.approx(29.0)
        assert invoice.status == "draft"

    def test_generate_invoice_with_overage(self):
        billing = BillingSystem()
        tier = PricingTier(
            tier_id="tier-1",
            name="Pro",
            monthly_price=29.0,
            included_tokens=100000,
            overage_rate_per_token=0.00002,
        )
        billing.register_tier(tier)
        from datetime import datetime, timedelta
        start = datetime.utcnow() - timedelta(days=30)
        end = datetime.utcnow()
        billing.record_usage("dev1", tokens_in=80000, tokens_out=50000)
        invoice = billing.generate_invoice("dev1", "tier-1", start, end)
        overage_tokens = 130000 - 100000
        expected_total = 29.0 + overage_tokens * 0.00002
        assert invoice.total == pytest.approx(expected_total)
        assert len(invoice.line_items) == 2

    def test_list_invoices(self):
        billing = BillingSystem()
        tier = PricingTier(
            tier_id="tier-1",
            name="Pro",
            monthly_price=29.0,
            included_tokens=100000,
            overage_rate_per_token=0.00002,
        )
        billing.register_tier(tier)
        from datetime import datetime, timedelta
        start = datetime.utcnow() - timedelta(days=30)
        end = datetime.utcnow()
        billing.generate_invoice("dev1", "tier-1", start, end)
        invoices = billing.list_invoices("dev1")
        assert len(invoices) == 1
        assert invoices[0].developer_id == "dev1"


class TestAutoscaler:
    def test_scale_up_on_high_cpu(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=5, scale_up_cooldown=0))
        result = scaler.evaluate(cpu_usage=90.0, memory_usage=50.0, queue_depth=0, latency_p99_ms=200.0, cost_per_hour=1.0)
        assert result["action"] == "scale_up"
        assert result["replicas"] == 2

    def test_scale_down_on_low_load(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=5, scale_down_cooldown=0))
        scaler._current_replicas = 3
        result = scaler.evaluate(cpu_usage=20.0, memory_usage=30.0, queue_depth=0, latency_p99_ms=100.0, cost_per_hour=1.0)
        assert result["action"] == "scale_down"
        assert result["replicas"] == 2

    def test_no_scale_within_cooldown(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=5, scale_up_cooldown=9999))
        result1 = scaler.evaluate(cpu_usage=90.0, memory_usage=50.0, queue_depth=0, latency_p99_ms=200.0, cost_per_hour=1.0)
        assert result1["action"] == "scale_up"
        result2 = scaler.evaluate(cpu_usage=90.0, memory_usage=50.0, queue_depth=0, latency_p99_ms=200.0, cost_per_hour=1.0)
        assert result2["action"] == "none"

    def test_cost_optimization(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=10))
        scaler._current_replicas = 5
        result = scaler.optimize_cost(current_cost=50.0, target_cost=20.0)
        assert result["action"] == "cost_optimize"
        assert scaler.current_replicas == 2

    def test_scale_up_on_queue_depth(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=10, scale_up_cooldown=0))
        result = scaler.evaluate(cpu_usage=20.0, memory_usage=30.0, queue_depth=50, latency_p99_ms=200.0, cost_per_hour=1.0)
        assert result["action"] == "scale_up"

    def test_cost_optimization_no_action_when_within_budget(self):
        scaler = Autoscaler(policy=ScalingPolicy(min_replicas=1, max_replicas=10))
        scaler._current_replicas = 5
        result = scaler.optimize_cost(current_cost=10.0, target_cost=20.0)
        assert result["action"] == "none"
