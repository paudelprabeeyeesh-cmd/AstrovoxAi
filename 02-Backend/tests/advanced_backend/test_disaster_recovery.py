from advanced_backend.disaster_recovery import DisasterRecoveryManager, Region


def test_failover():
    regions = [
        Region(name="us-east", endpoint="e.example.com"),
        Region(name="us-west", endpoint="w.example.com"),
    ]
    dr = DisasterRecoveryManager(primary_region="us-east", regions=regions)
    result = dr.failover("us-west")
    assert result["new_primary"] == "us-west"
    assert dr.active_region() == "us-west"


def test_health_check():
    regions = [Region(name="r1", endpoint="r1.example.com")]
    dr = DisasterRecoveryManager(primary_region="r1", regions=regions)
    assert dr.health_check("r1") is True


def test_status():
    regions = [Region(name="r1", endpoint="r1.example.com")]
    dr = DisasterRecoveryManager(primary_region="r1", regions=regions)
    status = dr.status()
    assert status["primary"] == "r1"
    assert status["active"] == "r1"
