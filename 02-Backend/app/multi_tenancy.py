class TenantManager:
    def __init__(self):
        self.tenants = {}

    def create_tenant(self, tenant_id, config):
        self.tenants[tenant_id] = config

    def get_tenant(self, tenant_id):
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} not found")
        return self.tenants[tenant_id]

    def list_tenants(self):
        return list(self.tenants.keys())
