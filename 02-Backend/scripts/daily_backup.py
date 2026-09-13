import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from scripts.backup_db import backup_database, restore_database, backup_to_s3

if __name__ == "__main__":
    print("=== Database Backup ===")
    backup_file = backup_database()
    print(f"Local backup: {backup_file}")
    
    print("\n=== S3 Backup ===")
    s3_success = backup_to_s3()
    print(f"S3 upload: {'Success' if s3_success else 'Failed'}")
    
    if backup_file:
        print(f"\nTo restore: python scripts/restore_db.py {backup_file}")
