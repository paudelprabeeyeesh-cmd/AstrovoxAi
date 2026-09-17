import sys
import os
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def restore_database(backup_file: str) -> bool:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL is not set")
        return False

    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        return False

    try:
        if backup_file.endswith(".gz"):
            with open(backup_file, "rb") as f:
                gzip = subprocess.Popen(
                    ["gzip", "-d"],
                    stdin=f,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                sql_data = gzip.stdout.read()
                _, gzip_err = gzip.communicate()
                if gzip.returncode != 0:
                    raise RuntimeError(f"gzip failed: {gzip_err.decode()}")
        else:
            with open(backup_file, "rb") as f:
                sql_data = f.read()

        psql = subprocess.Popen(
            ["psql", "--dbname", database_url],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _, psql_err = psql.communicate(input=sql_data)
        if psql.returncode != 0:
            raise RuntimeError(f"psql failed: {psql_err.decode()}")

        logger.info(f"Restore completed from {backup_file}")
        return True
    except Exception as exc:
        logger.error(f"Restore failed: {exc}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_db.py <backup_file>")
        sys.exit(1)

    backup_file = sys.argv[1]
    success = restore_database(backup_file)
    print(f"Restore: {'Success' if success else 'Failed'}")
    sys.exit(0 if success else 1)
