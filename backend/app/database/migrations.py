import os
import glob
from dataclasses import dataclass
from typing import List


@dataclass
class Migration:
    version: str
    name: str
    sql: str


class MigrationRunner:
    def __init__(self, migrations_dir: str):
        self.migrations_dir = migrations_dir
        self._applied: set = set()

    def load_migrations(self) -> List[Migration]:
        migrations = []
        for path in sorted(glob.glob(os.path.join(self.migrations_dir, "*.sql"))):
            with open(path, "r", encoding="utf-8") as f:
                migrations.append(Migration(
                    version=os.path.basename(path).split("_")[0],
                    name=os.path.basename(path),
                    sql=f.read(),
                ))
        return migrations

    def apply(self, connection) -> None:
        for migration in self.load_migrations():
            if migration.version not in self._applied:
                with connection.cursor() as cur:
                    cur.execute(migration.sql)
                self._applied.add(migration.version)
