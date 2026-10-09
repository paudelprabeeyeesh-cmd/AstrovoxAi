from system_integration.service_mesh import (
    HealthStatus,
    LoadBalancer,
    ServiceInstance,
    ServiceMesh,
    ServiceRegistry,
)


def test_service_registry_register_discover():
    reg = ServiceRegistry()
    inst = ServiceInstance(name="api", host="h1", port=80)
    reg.register(inst)
    found = reg.discover("api")
    assert len(found) == 1
    assert found[0].host == "h1"


def test_service_registry_unregister():
    reg = ServiceRegistry()
    reg.register(ServiceInstance(name="api", host="h1", port=80))
    reg.unregister("api", "h1", 80)
    assert reg.discover("api") == []


def test_load_balancer_round_robin():
    lb = LoadBalancer(strategy="round_robin")
    lb.register_instance("api")
    insts = [ServiceInstance(name="api", host="h1", port=80), ServiceInstance(name="api", host="h2", port=80)]
    selected = [lb.select("api", insts, None) for _ in range(4)]
    assert selected == [insts[0], insts[1], insts[0], insts[1]]


def test_load_balancer_weighted():
    lb = LoadBalancer(strategy="weighted")
    lb.register_instance("api")
    insts = [ServiceInstance(name="api", host="h1", port=80, load=0.0), ServiceInstance(name="api", host="h2", port=80, load=1.0)]
    picked = lb.select("api", insts, None)
    assert picked.host == "h1"


def test_service_mesh_route():
    mesh = ServiceMesh()
    mesh.register(ServiceInstance(name="api", host="h1", port=80, health=HealthStatus.HEALTHY))
    route = mesh.route("api")
    assert route is not None
    assert route.host == "h1"


def test_service_mesh_health_check():
    mesh = ServiceMesh()
    mesh.register(ServiceInstance(name="api", host="h1", port=80, health=HealthStatus.UNHEALTHY))
    results = mesh.health_check("api")
    assert results[0].status == HealthStatus.UNHEALTHY
