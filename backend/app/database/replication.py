from typing import List, Dict


class ReplicationManager:
    def __init__(self, primary_dsn: str, replica_dsns: List[str]):
        self.primary_dsn = primary_dsn
        self.replica_dsns = replica_dsns
        self._replica_index = 0

    def get_read_replica(self) -> str:
        dsn = self.replica_dsns[self._replica_index]
        self._replica_index = (self._replica_index + 1) % len(self.replica_dsns)
        return dsn

    def get_write_dsn(self) -> str:
        return self.primary_dsn

    def replication_lag(self) -> Dict[str, float]:
        return {dsn: 0.0 for dsn in self.replica_dsns}
