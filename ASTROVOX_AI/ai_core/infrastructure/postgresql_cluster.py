from typing import Optional, Dict, Any, List
import asyncpg


class PostgreSQLCluster:
    def __init__(self, nodes: List[Dict[str, Any]], pool_size: int = 20):
        self.nodes = nodes
        self.pool_size = pool_size
        self.pools: Dict[str, asyncpg.Pool] = {}
        self.primary_node = next((n for n in nodes if n.get('role') == 'primary'), nodes[0])

    async def connect(self) -> None:
        for node in self.nodes:
            dsn = f"postgresql://{node['user']}:{node['password']}@{node['host']}:{node['port']}/{node['database']}"
            pool = await asyncpg.create_pool(dsn, min_size=5, max_size=self.pool_size)
            self.pools[node.get('name', f"{node['host']}:{node['port']}")] = pool

    async def close(self) -> None:
        for pool in self.pools.values():
            await pool.close()

    async def execute(self, query: str, *args, read_only: bool = False) -> List[Dict[str, Any]]:
        if read_only:
            node = next((n for n in self.nodes if n.get('role') == 'replica'), self.primary_node)
        else:
            node = self.primary_node
        pool = self.pools.get(node.get('name', f"{node['host']}:{node['port']}"))
        if not pool:
            raise ConnectionError('Pool not initialized')
        async with pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(row) for row in rows]

    async def execute_many(self, query: str, args_list: List[tuple]) -> None:
        node = self.primary_node
        pool = self.pools.get(node.get('name', f"{node['host']}:{node['port']}"))
        async with pool.acquire() as conn:
            await conn.executemany(query, args_list)
