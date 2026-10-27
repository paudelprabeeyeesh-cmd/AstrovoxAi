$env:ENVIRONMENT="development"
$env:JWT_SECRET_KEY="dev-secret-key"
$env:PYTHONPATH="02-Backend"
& .\.venv\Scripts\python.exe repro_main3.py 2>&1
