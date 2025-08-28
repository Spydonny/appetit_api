#!/bin/bash
# Docker entrypoint script for APPETIT backend
# handles database initialization and app startup in containerized environments

set -e

# function to log messages with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') [docker-entrypoint] $1"
}

# function to wait for database to be ready
wait_for_db() {
    log "Waiting for database to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        log "Database connection attempt $attempt/$max_attempts"
        
        if python scripts/init_db.py --check-only > /dev/null 2>&1; then
            log "Database is ready!"
            return 0
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            log "ERROR: Database not ready after $max_attempts attempts"
            return 1
        fi
        
        log "Database not ready, waiting 2 seconds..."
        sleep 2
        ((attempt++))
    done
}

# function to init database
init_database() {
    log "Initializing database..."
    
    # run database initialization with optional data seeding
    local seed_flag=""
    if [ "$SEED_INITIAL_DATA" = "true" ]; then
        seed_flag="--seed-data"
        log "Initial data seeding enabled"
    fi
    
    if python scripts/init_db.py $seed_flag; then
        log "Database initialization completed successfully"
        return 0
    else
        log "ERROR: Database initialization failed"
        return 1
    fi
}

# function to run the app
start_application() {
    log "Starting application..."
    
    # default values
    local host=${APP_HOST:-0.0.0.0}
    local port=${APP_PORT:-8000}
    local workers=${UVICORN_WORKERS:-1}
    local log_level=${LOG_LEVEL:-info}
    
    log "Configuration:"
    log "  Host: $host"
    log "  Port: $port" 
    log "  Workers: $workers"
    log "  Log Level: $log_level"
    log "  Environment: ${APP_ENV:-dev}"
    
    # start uvicorn with config
    if [ "$workers" -gt 1 ]; then
        log "Starting with multiple workers"
        exec uvicorn app.main:app \
            --host "$host" \
            --port "$port" \
            --workers "$workers" \
            --log-level "$log_level"
    else
        log "Starting with single worker"
        exec uvicorn app.main:app \
            --host "$host" \
            --port "$port" \
            --log-level "$log_level"
    fi
}

# main execution flow
main() {
    log "=== APPETIT Backend Docker Entrypoint ==="
    log "Environment: ${APP_ENV:-dev}"
    log "Database URL: ${DATABASE_URL:-not-set}"
    
    # handle different commands
    case "${1:-start}" in
        "start")
            log "Starting application with database initialization"
            wait_for_db || exit 1
            init_database || exit 1
            start_application
            ;;
        "init-db")
            log "Database initialization only"
            wait_for_db || exit 1
            init_database || exit 1
            log "Database initialization completed, exiting"
            ;;
        "migrate")
            log "Running migrations only"
            wait_for_db || exit 1
            log "Running Alembic migrations..."
            alembic upgrade head || exit 1
            log "Migrations completed, exiting"
            ;;
        "seed")
            log "Seeding data only"
            wait_for_db || exit 1
            log "Seeding initial data..."
            python scripts/init_db.py --seed-data || exit 1
            log "Data seeding completed, exiting"
            ;;
        "check")
            log "Database connection check only"
            wait_for_db || exit 1
            log "Database connection verified, exiting"
            ;;
        "shell")
            log "Starting interactive shell"
            exec bash
            ;;
        *)
            log "Executing custom command: $*"
            exec "$@"
            ;;
    esac
}

# set up signal handlers for graceful shutdown
handle_signal() {
    log "Received shutdown signal, stopping application..."
    exit 0
}

trap handle_signal SIGTERM SIGINT

# execute main function
main "$@"