import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    print('ERROR: python-dotenv not installed')
    sys.exit(1)

try:
    from sqlalchemy import text, create_engine
except ImportError:
    print('ERROR: sqlalchemy not installed')
    sys.exit(1)


def check_env_vars():
    required = ['DATABASE_URL', 'OPENAI_API_KEY', 'STRIPE_SECRET_KEY']
    missing = [v for v in required if not os.getenv(v)]
    if missing:
        print('FAIL: Missing env vars: ' + ', '.join(missing))
        return False
    print('OK: Required env vars present')
    return True


def check_database():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('FAIL: DATABASE_URL not set')
        return False

    try:
        engine = create_engine(db_url, connect_args={'connect_timeout': 5})
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        print('OK: Database connection successful')
        return True
    except Exception as e:
        print('FAIL: Database connection failed: ' + str(e))
        return False


def main():
    load_dotenv()
    results = [check_env_vars(), check_database()]
    if all(results):
        print('HEALTH CHECK PASSED')
        sys.exit(0)
    else:
        print('HEALTH CHECK FAILED')
        sys.exit(1)


if __name__ == '__main__':
    main()
