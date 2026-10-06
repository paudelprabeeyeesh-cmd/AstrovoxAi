"""Cloud deployment infrastructure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CloudConfig:
    """Cloud deployment config."""
    provider: str = "aws"
    region: str = "us-east-1"
    instance_type: str = "t3.large"


class CloudDeployer:
    """Cloud deployment."""

    def __init__(self, config: CloudConfig | None = None):
        self.config = config or CloudConfig()

    def deploy(self) -> dict:
        return {
            "provider": self.config.provider,
            "region": self.config.region,
            "instance_type": self.config.instance_type,
            "status": "deployed",
        }

    def destroy(self) -> dict:
        return {"status": "destroyed"}

    def plan(self) -> str:
        return f"""plan for {self.config.provider}/{self.config.region}:
  + astrovox-api (t3.large)
  + astrovox-db
  + astrovox-cache
"""

    def outputs(self) -> dict:
        return {"api_url": f"https://astrovox.{self.config.region}.internal",
                "db_endpoint": f"{self.config.region}.astrovox.db"}
