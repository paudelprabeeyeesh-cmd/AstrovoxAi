# Database Setup Automation Script for AstrovoxAI (Windows PowerShell)
# This script automates the database migration and setup process

param(
    [string]$Action = "interactive",
    [string]$MigrationFile = ""
)

# Color functions
function Write-Header {
    param([string]$Message)
    Write-Host ""
    Write-Host "→ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Banner
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║    ASTRAVOX AI - Database Setup & Migration Tool (Windows)  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Error "No .env file found!"
    Write-Host "Please create .env by running: Copy-Item .env.example .env"
    exit 1
}

Write-Success ".env file found"

# Load environment variables from .env
Write-Header "Loading environment variables"
$env_content = Get-Content ".env" | Where-Object { $_ -notmatch "^#" -and $_ -notmatch "^$" }
foreach ($line in $env_content) {
    $parts = $line -split "=", 2
    if ($parts.Count -eq 2) {
        [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
    }
}

# Verify required environment variables
Write-Header "Verifying environment variables"
$required_vars = @("VITE_SUPABASE_URL", "VITE_SUPABASE_ANON_KEY")
$missing_vars = 0

foreach ($var in $required_vars) {
    $value = [Environment]::GetEnvironmentVariable($var, "Process")
    if ([string]::IsNullOrEmpty($value)) {
        Write-Error "Missing required variable: $var"
        $missing_vars++
    }
    else {
        Write-Success "Found: $var"
    }
}

if ($missing_vars -gt 0) {
    Write-Error "Missing $missing_vars required environment variables"
    exit 1
}

# Function to execute SQL
function Execute-SQL {
    param(
        [string]$SqlFile,
        [string]$Description
    )
    
    Write-Header "Executing: $Description"
    
    if (-not (Test-Path $SqlFile)) {
        Write-Error "SQL file not found: $SqlFile"
        return $false
    }
    
    $DATABASE_URL = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
    
    # Check if psql is available
    $psql_available = $null -ne (Get-Command psql -ErrorAction SilentlyContinue)
    
    if ($psql_available -and -not [string]::IsNullOrEmpty($DATABASE_URL)) {
        Write-Warning "Using direct database connection via psql"
        $sql_content = Get-Content $SqlFile -Raw
        $sql_content | psql $DATABASE_URL | Out-Host
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Migration completed"
            return $true
        }
        else {
            Write-Error "Migration failed"
            return $false
        }
    }
    else {
        Write-Warning "Direct database execution not available (psql not found or DATABASE_URL not set)"
        Write-Host ""
        Write-Host "Manual setup required:"
        Write-Host "1. Go to your Supabase dashboard: https://app.supabase.com"
        Write-Host "2. Select your project and navigate to SQL Editor"
        Write-Host "3. Create a new query"
        Write-Host "4. Copy and paste the contents of: $SqlFile"
        Write-Host "5. Run the query"
        Write-Host ""
        Read-Host "Press Enter when you have completed the manual setup"
        return $true
    }
}

# Interactive menu
if ($Action -eq "interactive") {
    Write-Header "Database Setup Options"
    Write-Host "1) Create tables and RLS policies (Schema setup)"
    Write-Host "2) Apply migration 0001 (Indexes and triggers)"
    Write-Host "3) Apply migration 0002 (Telemetry events)"
    Write-Host "4) Run all migrations in order"
    Write-Host "5) Reset database (DELETE ALL DATA - use with caution)"
    Write-Host "6) Verify database connection"
    Write-Host ""
    
    $choice = Read-Host "Select option (1-6)"
    
    switch ($choice) {
        "1" {
            Execute-SQL "database/schemas/supabase_setup.sql" "Database Schema Setup"
        }
        "2" {
            Execute-SQL "database/migrations/0001_indexes_and_signup_trigger.sql" "Migration 0001"
        }
        "3" {
            Execute-SQL "database/migrations/0002_telemetry_events.sql" "Migration 0002"
        }
        "4" {
            Write-Header "Running all migrations in order"
            Execute-SQL "database/schemas/supabase_setup.sql" "Database Schema Setup"
            Write-Host ""
            Execute-SQL "database/migrations/0001_indexes_and_signup_trigger.sql" "Migration 0001"
            Write-Host ""
            Execute-SQL "database/migrations/0002_telemetry_events.sql" "Migration 0002"
            Write-Host ""
            Write-Success "All migrations completed!"
        }
        "5" {
            Write-Warning "This will DELETE ALL DATA from your database!"
            $confirm = Read-Host "Type 'confirm-reset' to proceed"
            if ($confirm -eq "confirm-reset") {
                $reset_sql = @"
-- WARNING: This will delete all data!
DROP TABLE IF EXISTS telemetry_events CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS memory_entries CASCADE;
DROP TABLE IF EXISTS usage CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"@
                Write-Header "Resetting database..."
                $reset_sql | psql ([Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")) | Out-Host
                Write-Success "Database reset complete"
            }
            else {
                Write-Warning "Reset cancelled"
            }
        }
        "6" {
            Write-Header "Verifying database connection"
            $DATABASE_URL = [Environment]::GetEnvironmentVariable("DATABASE_URL", "Process")
            
            $psql_available = $null -ne (Get-Command psql -ErrorAction SilentlyContinue)
            
            if ($psql_available -and -not [string]::IsNullOrEmpty($DATABASE_URL)) {
                try {
                    $result = psql $DATABASE_URL -c "SELECT version();" 2>&1
                    if ($LASTEXITCODE -eq 0) {
                        Write-Success "Database connection successful!"
                        psql $DATABASE_URL -c "SELECT 'AstrovoxAI Database Ready' as status;" | Out-Host
                    }
                    else {
                        Write-Error "Failed to connect to database"
                        exit 1
                    }
                }
                catch {
                    Write-Error "Failed to connect to database: $_"
                    exit 1
                }
            }
            else {
                Write-Warning "DATABASE_URL not set in .env or psql not found"
                Write-Host "Cannot test connection without DATABASE_URL"
                Write-Host "For Supabase, get the connection string from:"
                Write-Host "  Supabase Dashboard → Settings → Database → Connection Pooling"
            }
        }
        default {
            Write-Error "Invalid option selected"
            exit 1
        }
    }
}
else {
    # Programmatic mode
    switch ($Action) {
        "all" { Execute-SQL "database/schemas/supabase_setup.sql" "Database Schema Setup" }
        default { Write-Error "Unknown action: $Action" }
    }
}

Write-Header "Database Setup Complete"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Verify all migrations completed successfully"
Write-Host "2. Run health check: curl http://localhost:8000/health"
Write-Host "3. Check API docs: http://localhost:8000/docs"
Write-Host "4. View telemetry data: curl http://localhost:8000/telemetry/stats"
Write-Host ""
Write-Success "AstrovoxAI is ready for deployment!"
