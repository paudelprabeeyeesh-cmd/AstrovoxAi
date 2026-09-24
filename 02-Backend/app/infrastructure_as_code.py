"""Infrastructure as Code definitions for AstrovoxAI.

Provides Terraform and Pulumi-style IaC templates for cloud deployment.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ResourceDefinition:
    type: str
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TerraformModule:
    source: str
    version: str = ""


@dataclass
class CloudProvider:
    name: str
    region: str
    credentials: Optional[str] = None


class InfrastructureAsCode:
    """Generates IaC templates for Terraform and Pulumi."""

    def __init__(self, provider: str = "aws"):
        self.provider = provider
        self._resources: List[ResourceDefinition] = []
        self._modules: List[TerraformModule] = []

    def add_resource(self, resource: ResourceDefinition) -> None:
        self._resources.append(resource)

    def add_module(self, module: TerraformModule) -> None:
        self._modules.append(module)

    def generate_terraform(self) -> str:
        provider_block = ""
        if self.provider == "aws":
            provider_block = """
provider "aws" {
  region = var.aws_region
}
"""
        elif self.provider == "gcp":
            provider_block = """
provider "google" {
  project = var.gcp_project
  region  = var.gcp_region
}
"""
        elif self.provider == "azure":
            provider_block = """
provider "azurerm" {
  features {}
}
"""
        resources = []
        for resource in self._resources:
            if resource.type == "postgres":
                resources.append(f"""
resource "{self.provider}_db_instance" "{resource.name}" {{
  identifier          = "{resource.name}"
  engine              = "postgres"
  engine_version      = "15.4"
  instance_class      = "{resource.properties.get('instance_class', 'db.t3.micro')}"
  allocated_storage   = {resource.properties.get('allocated_storage', 20)}
  storage_encrypted   = true
  username            = var.db_username
  password            = random_password.db_password.result
  publicly_accessible = false
  skip_final_snapshot = true
  tags                = local.common_tags
}}
""")
            elif resource.type == "redis":
                resources.append(f"""
resource "{self.provider}_elasticache_cluster" "{resource.name}" {{
  cluster_id           = "{resource.name}"
  engine               = "redis"
  node_type            = "{resource.properties.get('node_type', 'cache.t3.micro')}"
  num_cache_nodes      = {resource.properties.get('num_nodes', 1)}
  parameter_group_name = "default.redis7"
  port                 = 6379
  security_group_ids   = [aws_security_group.redis_sg.id]
}}
""")
            elif resource.type == "s3":
                resources.append(f"""
resource "{self.provider}_s3_bucket" "{resource.name}" {{
  bucket = "{resource.name}"
  force_destroy = true
  lifecycle_rule {{
    id      = "log"
    enabled = true
    prefix  = "logs/"
    expiration {{
      days = 30
    }}
  }}
  server_side_encryption_configuration {{
    rule {{
      apply_server_side_encryption_by_default {{
        sse_algorithm = "AES256"
      }}
    }}
  }}
}}
""")
            elif resource.type == "lambda":
                resources.append(f"""
resource "{self.provider}_lambda_function" "{resource.name}" {{
  function_name    = "{resource.name}"
  runtime          = "python3.11"
  handler          = "handler.main"
  filename         = "{resource.properties.get('zip_path', 'lambda.zip')}"
  source_code_hash = filebase64sha256("{resource.properties.get('zip_path', 'lambda.zip')}")
  role             = aws_iam_role.lambda_role.arn
  timeout          = {resource.properties.get('timeout', 30)}
  memory_size      = {resource.properties.get('memory', 128)}
  environment {{
    variables = {{
      REDIS_URL = aws_elasticache_cluster.redis.cache_nodes[0].address
    }}
  }}
}}
""")
            elif resource.type == "ecs_service":
                resources.append(f"""
resource "{self.provider}_ecs_service" "{resource.name}" {{
  name            = "{resource.name}"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.{resource.name}.arn
  desired_count   = {resource.properties.get('desired_count', 1)}
  launch_type     = "FARGATE"
  network_configuration {{
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.ecs_sg.id]
  }}
  load_balancer {{
    target_group_arn = aws_lb_target_group.{resource.name}.arn
    container_name   = "{resource.name}"
    container_port   = {resource.properties.get('port', 8000)}
  }}
}}
""")
        variables = """
variable "aws_region" {
  default = "us-east-1"
}
variable "db_username" {
  default = "astrovox"
}
variable "environment" {
  default = "production"
}
locals {
  common_tags = {
    Project     = "AstrovoxAI"
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
resource "random_password" "db_password" {
  length  = 32
  special = false
}
"""
        return variables + provider_block + "\n".join(resources)

    def generate_pulumi(self) -> str:
        lines = [
            f"from pulumi import Config, Output, ResourceOptions",
            f"from pulumi_aws import ec2, rds, elasticache, s3 as aws_s3, ecs, iam",
            "",
            f"config = Config()",
            f"aws_region = config.require('aws_region')",
            "",
            f"vpc = ec2.get_vpc(default=True)",
            f"subnets = ec2.get_subnets(filters=[{{'Name': 'vpc-id', 'Values': [vpc.id]}}])",
            "",
        ]
        for resource in self._resources:
            if resource.type == "postgres":
                lines.extend([
                    f"db_subnet_group = rds.SubnetGroup('{resource.name}-subnet-group',",
                    f"    subnet_ids=[s.id for s in subnets.ids])",
                    f"db = rds.Instance('{resource.name}',",
                    f"    allocated_storage={resource.properties.get('allocated_storage', 20)},",
                    f"    engine='postgres',",
                    f"    engine_version='15.4',",
                    f"    instance_class='{resource.properties.get('instance_class', 'db.t3.micro')}',",
                    f"    db_subnet_group_name=db_subnet_group.name,",
                    f"    username='astrovox')",
                ])
            elif resource.type == "s3":
                lines.extend([
                    f"bucket = aws_s3.Bucket('{resource.name}',",
                    f"    acl='private',",
                    f"    force_destroy=True)",
                ])
        return "\n".join(lines)

    def generate_docker_compose(self) -> str:
        return """
version: '3.8'
services:
  backend:
    image: astrovoxai/backend:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://astrovox:password@postgres:5432/astrovox
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=astrovox
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=astrovox
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U astrovox"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - backend

volumes:
  postgres_data:
  redis_data:
"""

    def to_json(self) -> str:
        return json.dumps(
            {
                "provider": self.provider,
                "resources": [
                    {
                        "type": r.type,
                        "name": r.name,
                        "properties": r.properties,
                    }
                    for r in self._resources
                ],
            },
            indent=2,
        )


infra = InfrastructureAsCode(provider=os.getenv("CLOUD_PROVIDER", "aws"))
