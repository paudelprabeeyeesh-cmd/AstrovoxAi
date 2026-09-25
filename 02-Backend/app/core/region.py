
import os
REGIONS = {"us-east-1": {"country": "US"}, "eu-west-1": {"country": "GB"}, "ap-southeast-1": {"country": "SG"}}
def get_current_region():
    return os.getenv("AWS_REGION", os.getenv("REGION", "us-east-1"))
def nearest_region(lat: float, lon: float) -> str:
    return "us-east-1"
def list_regions():
    return list(REGIONS.keys())
