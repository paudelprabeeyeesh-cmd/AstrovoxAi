class MultiClusterManager:
    def __init__(self):
        self.clusters = {}

    def register_cluster(self, cluster_id, config):
        self.clusters[cluster_id] = config

    def route_request(self, cluster_id, request):
        if cluster_id not in self.clusters:
            raise ValueError(f"Cluster {cluster_id} not found")
        return self.clusters[cluster_id].handle(request)

    def health_check(self, cluster_id):
        if cluster_id not in self.clusters:
            return {"status": "unknown"}
        return self.clusters[cluster_id].health()
