from typing import Optional, Dict, Any, List, Tuple
import redis


class RedisCluster:
    def __init__(self, nodes: List[Dict[str, Any]], max_connections: int = 50, decode_responses: bool = True):
        self.nodes = nodes
        self.max_connections = max_connections
        self.decode_responses = decode_responses
        self.clients: Dict[str, redis.Redis] = {}
        for node in nodes:
            client = redis.Redis(host=node['host'], port=node['port'], db=node.get('db', 0), decode_responses=decode_responses, max_connections=max_connections)
            self.clients[node.get('name', f"{node['host']}:{node['port']}")] = client

    def get_client(self, key: str) -> redis.Redis:
        node_idx = hash(key) % len(self.nodes)
        node = self.nodes[node_idx]
        return self.clients[node.get('name', f"{node['host']}:{node['port']}")]

    def get(self, key: str) -> Optional[str]:
        return self.get_client(key).get(key)

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        client = self.get_client(key)
        if ttl:
            client.setex(key, ttl, value)
        else:
            client.set(key, value)

    def delete(self, key: str) -> None:
        self.get_client(key).delete(key)

    def pipeline(self) -> 'RedisClusterPipeline':
        return RedisClusterPipeline(self)

    def flush_all(self) -> None:
        for client in self.clients.values():
            client.flushall()


class RedisClusterPipeline:
    def __init__(self, cluster: RedisCluster):
        self.cluster = cluster
        self.commands: List[Tuple[str, str, Any]] = []

    def get(self, key: str) -> 'RedisClusterPipeline':
        self.commands.append(('get', key, None))
        return self

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> 'RedisClusterPipeline':
        self.commands.append(('set', key, (value, ttl)))
        return self

    def execute(self) -> List[Any]:
        results = []
        for cmd, key, args in self.commands:
            client = self.cluster.get_client(key)
            if cmd == 'get':
                results.append(client.get(key))
            elif cmd == 'set':
                value, ttl = args
                if ttl:
                    results.append(client.setex(key, ttl, value))
                else:
                    results.append(client.set(key, value))
        self.commands.clear()
        return results
