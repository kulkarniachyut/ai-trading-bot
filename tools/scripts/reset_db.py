"""
Utility: Reset the database (drop all tables, recreate schema).

Usage:
    python tools/scripts/reset_db.py [--confirm]

WARNING: This deletes all trade journal data. Use with caution.
This script will be functional after db/models.py is built (Step 1).
"""
import sys


def main():
    if "--confirm" not in sys.argv:
        print("⚠️  This will DELETE all data in the trading database.")
        print("Run with --confirm to proceed:")
        print("  python tools/scripts/reset_db.py --confirm")
        sys.exit(1)

    # Will use shared.db.models.init_db() once built
    print("DB reset not yet implemented. Waiting for db/models.py (Step 1).")


if __name__ == "__main__":
    main()
