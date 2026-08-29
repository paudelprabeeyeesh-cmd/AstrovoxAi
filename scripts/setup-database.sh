#!/bin/bash
# Database Setup Automation Script for AstrovoxAI
# This script automates the database migration and setup process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║    ASTRAVOX AI - Database Setup & Migration Tool           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

# Function to print section headers
print_header() {
    echo -e "\n${BLUE}→ ${1}${NC}"
}

# Function to print success messages
print_success() {
    echo -e "${GREEN}✓ ${1}${NC}"
}

# Function to print error messages
print_error() {
    echo -e "${RED}✗ ${1}${NC}"
}

# Function to print warning messages
print_warning() {
    echo -e "${YELLOW}⚠ ${1}${NC}"
}

# Check if .env file exists
if [ ! -f .env ]; then
    print_error "No .env file found!"
    echo "Please create .env by running: cp .env.example .env"
    exit 1
fi

print_success ".env file found"

# Source environment variables
export $(grep -v '^#' .env | xargs)

# Verify required environment variables
print_header "Verifying environment variables"

REQUIRED_VARS=(
    "VITE_SUPABASE_URL"
    "VITE_SUPABASE_ANON_KEY"
)

MISSING_VARS=0
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        print_error "Missing required variable: ${var}"
        MISSING_VARS=$((MISSING_VARS + 1))
    else
        print_success "Found: ${var}"
    fi
done

if [ $MISSING_VARS -gt 0 ]; then
    print_error "Missing ${MISSING_VARS} required environment variables"
    exit 1
fi

# Option to run migrations
print_header "Database Setup Options"
echo "1) Create tables and RLS policies (Schema setup)"
echo "2) Apply migration 0001 (Indexes and triggers)"
echo "3) Apply migration 0002 (Telemetry events)"
echo "4) Run all migrations in order"
echo "5) Reset database (DELETE ALL DATA - use with caution)"
echo "6) Verify database connection"
echo ""
read -p "Select option (1-6): " choice

# Helper function to execute SQL against Supabase
execute_sql() {
    local sql_file=$1
    local description=$2
    
    print_header "Executing: ${description}"
    
    if [ ! -f "$sql_file" ]; then
        print_error "SQL file not found: $sql_file"
        return 1
    fi
    
    # Check if we can use psql
    if command -v psql &> /dev/null; then
        # If DATABASE_URL is set, use it
        if [ ! -z "$DATABASE_URL" ]; then
            print_warning "Using direct database connection via psql"
            psql "$DATABASE_URL" < "$sql_file" && print_success "Migration completed"
        else
            print_warning "DATABASE_URL not set. Skipping direct database execution."
            echo "Manual steps needed:"
            echo "1. Go to your Supabase dashboard: https://app.supabase.com"
            echo "2. Select your project and navigate to SQL Editor"
            echo "3. Create a new query"
            echo "4. Copy and paste the contents of: $sql_file"
            echo "5. Run the query"
        fi
    else
        print_warning "psql not found. Manual database setup required."
        echo ""
        echo "Manual steps:"
        echo "1. Go to your Supabase dashboard: https://app.supabase.com"
        echo "2. Select your project and navigate to SQL Editor"
        echo "3. Create a new query"
        echo "4. Copy and paste the contents of: $sql_file"
        echo "5. Run the query"
        echo ""
        read -p "Press Enter when you have completed the manual setup..."
    fi
}

# Execute selected option
case $choice in
    1)
        execute_sql "database/schemas/supabase_setup.sql" "Database Schema Setup"
        ;;
    2)
        execute_sql "database/migrations/0001_indexes_and_signup_trigger.sql" "Migration 0001"
        ;;
    3)
        execute_sql "database/migrations/0002_telemetry_events.sql" "Migration 0002"
        ;;
    4)
        print_header "Running all migrations in order"
        execute_sql "database/schemas/supabase_setup.sql" "Database Schema Setup"
        echo ""
        execute_sql "database/migrations/0001_indexes_and_signup_trigger.sql" "Migration 0001"
        echo ""
        execute_sql "database/migrations/0002_telemetry_events.sql" "Migration 0002"
        echo ""
        print_success "All migrations completed!"
        ;;
    5)
        print_warning "This will DELETE ALL DATA from your database!"
        read -p "Type 'confirm-reset' to proceed: " confirm
        if [ "$confirm" = "confirm-reset" ]; then
            cat << 'EOF' > /tmp/reset.sql
-- WARNING: This will delete all data!
DROP TABLE IF EXISTS telemetry_events CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
DROP TABLE IF EXISTS memory_entries CASCADE;
DROP TABLE IF EXISTS usage CASCADE;
DROP TABLE IF EXISTS settings CASCADE;
DROP TABLE IF EXISTS users CASCADE;
EOF
            print_header "Resetting database..."
            execute_sql "/tmp/reset.sql" "Database Reset"
            print_success "Database reset complete"
            rm -f /tmp/reset.sql
        else
            print_warning "Reset cancelled"
        fi
        ;;
    6)
        print_header "Verifying database connection"
        if [ ! -z "$DATABASE_URL" ]; then
            if psql "$DATABASE_URL" -c "SELECT version();" > /dev/null 2>&1; then
                print_success "Database connection successful!"
                psql "$DATABASE_URL" -c "SELECT 'AstrovoxAI Database Ready' as status;"
            else
                print_error "Failed to connect to database"
                exit 1
            fi
        else
            print_warning "DATABASE_URL not set in .env"
            echo "Cannot test connection without DATABASE_URL"
            echo "For Supabase, get the connection string from:"
            echo "  Supabase Dashboard → Settings → Database → Connection Pooling"
        fi
        ;;
    *)
        print_error "Invalid option selected"
        exit 1
        ;;
esac

print_header "Database Setup Complete"
echo ""
echo "Next steps:"
echo "1. Verify all migrations completed successfully"
echo "2. Run health check: curl http://localhost:8000/health"
echo "3. Check API docs: http://localhost:8000/docs"
echo "4. View telemetry data: curl http://localhost:8000/telemetry/stats"
echo ""
print_success "AstrovoxAI is ready for deployment!"
