$env:ENVIRONMENT="development"
$env:JWT_SECRET_KEY="dev-secret-key"
$env:PYTHONPATH="02-Backend"
& .\.venv\Scripts\python.exe repro_main2.py 2>&1
