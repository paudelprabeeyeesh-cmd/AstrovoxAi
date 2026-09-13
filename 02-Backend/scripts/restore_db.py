import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.backup_db import restore_database

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python restore_db.py <backup_file>")
        sys.exit(1)
    
    backup_file = sys.argv[1]
    print(f"Restoring from {backup_file}...")
    success = restore_database(backup_file)
    print(f"Restore: {'Success' if success else 'Failed'}")
