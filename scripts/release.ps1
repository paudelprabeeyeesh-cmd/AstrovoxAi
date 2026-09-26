param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

Write-Host "=== AstrovoxAI Release v$Version ===" -ForegroundColor Cyan

$status = git status --porcelain
if ($status) {
    Write-Host "Error: Uncommitted changes detected" -ForegroundColor Red
    Write-Host $status
    exit 1
}

if (git rev-parse "v$Version" -q) {
    Write-Host "Error: Tag v$Version already exists" -ForegroundColor Red
    exit 1
}

Write-Host "Running tests..." -ForegroundColor Yellow
Set-Location 02-Backend
python -m pytest tests/ -v --tb=short --cov=app --cov-report=term-missing
Set-Location ..

Write-Host "Building Docker images..." -ForegroundColor Yellow
docker build -f Dockerfile.backend -t astrovoxai/backend:v$Version .
docker build -f Dockerfile.frontend -t astrovoxai/frontend:v$Version .

Write-Host "Pushing images..." -ForegroundColor Yellow
docker push astrovoxai/backend:v$Version
docker push astrovoxai/frontend:v$Version

Write-Host "Creating git tag..." -ForegroundColor Yellow
git tag -a "v$Version" -m "Release v$Version"
git push origin "v$Version"

Write-Host "Release v$Version completed successfully!" -ForegroundColor Green
