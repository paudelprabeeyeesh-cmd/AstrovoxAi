$env:ENVIRONMENT="development"
$env:JWT_SECRET_KEY="dev-secret-key"
$env:PYTHONPATH="."
& ..\.venv\Scripts\python.exe -m pytest tests/security/test_auth_security_fixes.py --collect-only -q -p no:cacheprovider 2>&1 | Tee-Object -FilePath collect_out3.txt
