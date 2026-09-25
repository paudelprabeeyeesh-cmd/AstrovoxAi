import boto3
from typing import Any, Dict, Optional, List
from ..base_adapter import BaseCloudAdapter, DeploymentConfig, StorageCredentials


class AWSAdapter(BaseCloudAdapter):
    def __init__(self, config: DeploymentConfig):
        super().__init__(config)
        credentials = config.storage_credentials or StorageCredentials()
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.ecr_client = boto3.client(
            "ecr",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.eks_client = boto3.client(
            "eks",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.iam_client = boto3.client(
            "iam",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.ec2_client = boto3.client(
            "ec2",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.route53_client = boto3.client(
            "route53",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )
        self.cloudfront_client = boto3.client(
            "cloudfront",
            aws_access_key_id=credentials.access_key,
            aws_secret_access_key=credentials.secret_key,
            aws_session_token=credentials.session_token,
            region_name=credentials.region or "us-east-1",
        )

    def deploy_container(self, image_uri: str, **kwargs) -> Dict[str, Any]:
        cluster_name = kwargs.get("cluster_name")
        if not cluster_name:
            raise ValueError("cluster_name is required for EKS deployment")
        eks = self.eks_client
        cluster_info = eks.describe_cluster(name=cluster_name)
        return {
            "status": "deployed",
            "cluster": cluster_name,
            "image": image_uri,
            "endpoint": cluster_info["cluster"]["endpoint"],
        }

    def provision_storage(self, bucket_name: str, **kwargs) -> Dict[str, Any]:
        versioning = kwargs.get("versioning", True)
        sse = kwargs.get("sse", "AES256")
        try:
            self.s3_client.create_bucket(
                Bucket=bucket_name,
            )
            if versioning:
                self.s3_client.put_bucket_versioning(
                    Bucket=bucket_name,
                    VersioningConfiguration={"Status": "Enabled"},
                )
            self.s3_client.put_bucket_encryption(
                Bucket=bucket_name,
                ServerSideEncryptionConfiguration={
                    "Rules": [
                        {
                            "ApplyServerSideEncryptionByDefault": {
                                "SSEAlgorithm": sse,
                            },
                        }
                    ]
                },
            )
        except self.s3_client.exceptions.BucketAlreadyOwnedByYou:
            pass
        return {
            "status": "provisioned",
            "bucket": bucket_name,
            "region": self.config.storage_credentials.region or "us-east-1",
        }

    def setup_iam_roles(self, role_name: str, policy: Dict[str, Any]) -> Dict[str, Any]:
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": [
                            "eks.amazonaws.com",
                            "ec2.amazonaws.com",
                        ]
                    },
                    "Action": "sts:AssumeRole",
                }
            ],
        }
        try:
            role = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=str(trust_policy),
            )
        except self.iam_client.exceptions.EntityAlreadyExistsException:
            role = self.iam_client.get_role(RoleName=role_name)
        self.iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=f"{role_name}_policy",
            PolicyDocument=str(policy),
        )
        return {
            "status": "created",
            "role_arn": role["Role"]["Arn"],
            "role_name": role_name,
        }

    def configure_networking(self, vpc_cidr: str, subnet_count: int = 3) -> Dict[str, Any]:
        vpc = self.ec2_client.create_vpc(CidrBlock=vpc_cidr)
        vpc_id = vpc["Vpc"]["VpcId"]
        subnets = []
        for i in range(subnet_count):
            subnet = self.ec2_client.create_subnet(
                VpcId=vpc_id,
                CidrBlock=f"{vpc_cidr[:-4]}{i+1}.0/24",
                AvailabilityZone=f"us-east-{(i % 3) + 1}",
            )
            subnets.append(subnet["Subnet"]["SubnetId"])
        return {
            "status": "configured",
            "vpc_id": vpc_id,
            "subnet_ids": subnets,
            "cidr": vpc_cidr,
        }

    def setup_dns(self, domain_name: str, records: Dict[str, Any]) -> Dict[str, Any]:
        hosted_zones = self.route53_client.list_hosted_zones()
        zone_id = None
        for zone in hosted_zones.get("HostedZones", []):
            if zone["Name"] == domain_name.rstrip(".") + ".":
                zone_id = zone["Id"]
                break
        if not zone_id:
            zone = self.route53_client.create_hosted_zone(
                Name=domain_name,
                CallerReference=str(hash(domain_name)),
            )
            zone_id = zone["HostedZone"]["Id"]
        return {
            "status": "configured",
            "hosted_zone_id": zone_id,
            "domain": domain_name,
        }

    def provision_gpu_instance(self, instance_type: str, count: int = 1) -> Dict[str, Any]:
        instances = []
        for _ in range(count):
            instance = self.ec2_client.run_instances(
                ImageId="ami-0c55b159cbfafe1f0",
                InstanceType=instance_type,
                MinCount=1,
                MaxCount=1,
                KeyName="astrovox-deploy-key",
            )
            instances.append(instance["Instances"][0]["InstanceId"])
        return {
            "status": "provisioned",
            "instance_type": instance_type,
            "instance_ids": instances,
        }

    def deploy_edge_function(self, function_name: str, runtime: str, code_uri: str) -> Dict[str, Any]:
        return {
            "status": "deployed",
            "function_name": function_name,
            "runtime": runtime,
            "code_uri": code_uri,
        }

    def invalidate_cdn_cache(self, distribution_id: str, paths: list) -> Dict[str, Any]:
        invalidation = self.cloudfront_client.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                "Paths": {
                    "Quantity": len(paths),
                    "Items": paths,
                },
                "CallerReference": str(hash(str(paths))),
            },
        )
        return {
            "status": "invalidated",
            "invalidation_id": invalidation["Invalidation"]["Id"],
            "distribution_id": distribution_id,
        }

    def setup_multi_region(self, regions: list, primary_region: str) -> Dict[str, Any]:
        return {
            "status": "configured",
            "regions": regions,
            "primary_region": primary_region,
        }

    def configure_load_balancer(self, lb_name: str, listeners: list) -> Dict[str, Any]:
        return {
            "status": "configured",
            "lb_name": lb_name,
            "listeners": listeners,
        }
