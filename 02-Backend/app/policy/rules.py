
from typing import Dict, List, Any


class PolicyRules:
    ACCESS_CONTROL_RULES = [
        {
            "rule_id": "org_member_required",
            "name": "Organization Member Required",
            "description": "User must be a member of the organization to access resources",
            "conditions": {"user_is_member": True},
            "effect": "allow",
        },
        {
            "rule_id": "admin_role_required",
            "name": "Admin Role Required",
            "description": "Admin role required for sensitive operations",
            "conditions": {"user_role": "admin"},
            "effect": "allow",
        },
        {
            "rule_id": "owner_role_required",
            "name": "Owner Role Required",
            "description": "Owner role required for destructive operations",
            "conditions": {"user_role": "owner"},
            "effect": "allow",
        },
    ]

    DATA_RETENTION_RULES = [
        {
            "rule_id": "retain_audit_logs",
            "name": "Retain Audit Logs",
            "description": "Audit logs must be retained for 7 years",
            "conditions": {"data_type": "audit_log", "retention_years": 7},
            "effect": "allow",
        },
        {
            "rule_id": "delete_after_retention",
            "name": "Delete After Retention",
            "description": "Delete data after retention period",
            "conditions": {"data_age_days": ">2555"},
            "effect": "deny",
        },
    ]

    USAGE_LIMIT_RULES = [
        {
            "rule_id": "daily_token_limit",
            "name": "Daily Token Limit",
            "description": "Users limited to 1M tokens per day",
            "conditions": {"daily_tokens": "<1000000"},
            "effect": "allow",
        },
        {
            "rule_id": "monthly_cost_limit",
            "name": "Monthly Cost Limit",
            "description": "Users limited to $100 per month",
            "conditions": {"monthly_cost_usd": "<100"},
            "effect": "allow",
        },
    ]

    SSO_RULES = [
        {
            "rule_id": "sso_required_for_enterprise",
            "name": "SSO Required for Enterprise",
            "description": "Enterprise plans must use SSO",
            "conditions": {"plan": "enterprise", "sso_enabled": True},
            "effect": "allow",
        },
        {
            "rule_id": "mfa_required",
            "name": "MFA Required",
            "description": "MFA required for admin and owner roles",
            "conditions": {"user_role": ["admin", "owner"], "mfa_enabled": True},
            "effect": "allow",
        },
    ]

    @classmethod
    def get_all_rules(cls) -> List[Dict[str, Any]]:
        return cls.ACCESS_CONTROL_RULES + cls.DATA_RETENTION_RULES + cls.USAGE_LIMIT_RULES + cls.SSO_RULES
