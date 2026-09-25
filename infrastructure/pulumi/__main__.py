import pulumi
import pulumi_aws as aws
import pulumi_kubernetes as k8s

config = pulumi.Config()
aws_region = config.require("aws-region")

provider = aws.Provider("aws", region=aws_region)

vpc = aws.ec2.Vpc("astrovox-vpc",
    cidr_block="10.0.0.0/16",
    enable_dns_hostnames=True,
    opts=pulumi.ResourceOptions(provider=provider)
)

cluster = k8s.Provider("k8s-provider")
