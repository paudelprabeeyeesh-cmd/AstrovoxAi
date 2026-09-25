from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ..deployment.base_adapter import BaseCloudAdapter, DeploymentConfig


class PermissionEffect(Enum):
    ALLOW = "Allow"
    DENY = "Deny"


class PermissionAction(Enum):
    S3_READ = "s3:GetObject"
    S3_WRITE = "s3:PutObject"
    S3_DELETE = "s3:DeleteObject"
    ECR_PULL = "ecr:GetDownloadUrlForLayer"
    ECR_PUSH = "ecr:PutImage"
    EKS_ACCESS = "eks:AccessKubernetesApi"
    IAM_PASS_ROLE = "iam:PassRole"
    COMPUTE_CREATE = "compute.instances.create"
    COMPUTE_DELETE = "compute.instances.delete"


@dataclass
class IAMPolicyStatement:
    effect: PermissionEffect
    actions: List[PermissionAction]
    resources: List[str]
    conditions: Optional[Dict[str, Any]] = None


@dataclass
class IAMRole:
    role_name: str
    assume_role_policy: Dict[str, Any]
    policies: List[IAMPolicyStatement]
    max_session_duration: int = 3600


class IAMRoleManager:
    def __init__(self, adapter: BaseCloudAdapter):
        self.adapter = adapter
        self.roles: Dict[str, IAMRole] = {}

    def create_role(self, role: IAMRole) -> Dict[str, Any]:
        self.roles[role.role_name] = role
        policy_document = self._build_policy_document(role)
        return self.adapter.setup_iam_roles(role.role_name, policy_document)

    def attach_policy(self, role_name: str, policy: IAMPolicyStatement) -> Dict[str, Any]:
        if role_name not in self.roles:
            raise ValueError(f"Role {role_name} not found")
        self.roles[role_name].policies.append(policy)
        policy_document = self._build_policy_document(self.roles[role_name])
        return self.adapter.setup_iam_roles(role_name, policy_document)

    def _build_policy_document(self, role: IAMRole) -> Dict[str, Any]:
        statements = []
        for statement in role.policies:
            stmt = {
                "Effect": statement.effect.value,
                "Action": [action.value for action in statement.actions],
                "Resource": statement.resources,
            }
            if statement.conditions:
                stmt["Condition"] = statement.conditions
            statements.append(stmt)
        return {
            "Version": "2012-10-17",
            "Statement": statements,
        }

    def generate_least_privilege_policy(
        self,
        role_name: str,
        service: str,
        actions: List[str],
        resource_arns: List[str],
    ) -> Dict[str, Any]:
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": actions,
                    "Resource": resource_arns,
                }
            ],
        }
        return self.adapter.setup_iam_roles(role_name, policy)

    def create_service_role(
        self,
        service_name: str,
        trust_services: List[str],
    ) -> Dict[str, Any]:
        assume_role_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": trust_services},
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        role = IAMRole(
            role_name=f"astrovox-{service_name}-role",
            assume_role_policy=assume_role_policy,
            policies=[],
        )
        return self.create_role(role)
