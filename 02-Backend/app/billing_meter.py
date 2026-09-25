import os
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from repositories.database.client import get_db

logger = logging.getLogger(__name__)


@dataclass
class MeterRecord:
    id: str
    tenant_id: str
    user_id: str
    resource_type: str
    quantity: float
    unit: str
    cost: float
    period_start: str
    period_end: str
    created_at: float = field(default_factory=datetime.now(timezone.utc).timestamp)


class BillingMeter:
    def __init__(self):
        self.meters: Dict[str, MeterRecord] = {}

    def record_usage(self, tenant_id: str, user_id: str, resource_type: str, quantity: float, unit: str, cost: float, period_start: str = None, period_end: str = None) -> MeterRecord:
        meter_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        period_start = period_start or now.isoformat()
        period_end = period_end or now.isoformat()

        record = MeterRecord(
            id=meter_id,
            tenant_id=tenant_id,
            user_id=user_id,
            resource_type=resource_type,
            quantity=quantity,
            unit=unit,
            cost=cost,
            period_start=period_start,
            period_end=period_end,
        )
        self.meters[meter_id] = record
        self._persist(record)
        return record

    def _persist(self, record: MeterRecord) -> None:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO billing_meters (id, tenant_id, user_id, resource_type, quantity, unit, cost, period_start, period_end) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record.id,
                    record.tenant_id,
                    record.user_id,
                    record.resource_type,
                    record.quantity,
                    record.unit,
                    record.cost,
                    record.period_start,
                    record.period_end,
                ),
            )
            conn.commit()

    def get_tenant_usage(self, tenant_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            query = "SELECT * FROM billing_meters WHERE tenant_id = ?"
            params = [tenant_id]
            if start_date:
                query += " AND created_at >= ?"
                params.append(start_date)
            if end_date:
                query += " AND created_at <= ?"
                params.append(end_date)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def get_tenant_cost_summary(self, tenant_id: str, period: str = "monthly") -> Dict[str, Any]:
        with get_db() as conn:
            if period == "daily":
                rows = conn.execute(
                    "SELECT date(created_at) as period, SUM(cost) as total_cost, SUM(quantity) as total_quantity FROM billing_meters WHERE tenant_id = ? GROUP BY date(created_at)",
                    (tenant_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT strftime('%Y-%m', created_at) as period, SUM(cost) as total_cost, SUM(quantity) as total_quantity FROM billing_meters WHERE tenant_id = ? GROUP BY strftime('%Y-%m', created_at)",
                    (tenant_id,),
                ).fetchall()
            return {
                "tenant_id": tenant_id,
                "period": period,
                "breakdown": [dict(r) for r in rows],
                "total_cost": sum(r["total_cost"] for r in rows if r["total_cost"]),
            }

    def get_user_usage(self, user_id: str, tenant_id: str = None) -> List[Dict[str, Any]]:
        with get_db() as conn:
            query = "SELECT * FROM billing_meters WHERE user_id = ?"
            params = [user_id]
            if tenant_id:
                query += " AND tenant_id = ?"
                params.append(tenant_id)
            query += " ORDER BY created_at DESC"
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]


billing_meter = BillingMeter()
