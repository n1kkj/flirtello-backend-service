#!/bin/bash

# Скрипт для очистки зависших транзакций в PostgreSQL
# Добавить в cron: */5 * * * * /path/to/cleanup_idle_transactions.sh
# Использование: ./cleanup_idle_transactions.sh [--dryrun] [--verbose]

# Настройки
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/src/.env"
LOG_FILE="${SCRIPT_DIR}/cleanup_idle_transactions.log"

# Параметры
DRYRUN=false
VERBOSE=false

# Обработка аргументов командной строки
while [[ $# -gt 0 ]]; do
    case $1 in
        --dryrun)
            DRYRUN=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Использование: $0 [--dryrun] [--verbose]"
            echo "  --dryrun    Показать что будет сделано без выполнения"
            echo "  --verbose   Расширенное логирование"
            echo "  -h, --help  Показать эту справку"
            exit 0
            ;;
        *)
            echo "Неизвестный параметр: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Функция логирования
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Функция расширенного логирования
verbose_log() {
    if [ "$VERBOSE" = true ]; then
        log "VERBOSE: $1"
    fi
}

# Функция dryrun логирования
dryrun_log() {
    if [ "$DRYRUN" = true ]; then
        log "DRYRUN: $1"
    fi
}

# Логируем параметры запуска
log "=== Starting cleanup script ==="
log "Script directory: $SCRIPT_DIR"
log "Environment file: $ENV_FILE"
log "Log file: $LOG_FILE"
log "Dryrun mode: $DRYRUN"
log "Verbose mode: $VERBOSE"
log "User: $(whoami)"
log "Working directory: $(pwd)"
log "Shell: $SHELL"
log "PATH: $PATH"

# Проверяем наличие .env файла
verbose_log "Checking for .env file at: $ENV_FILE"
if [ ! -f "$ENV_FILE" ]; then
    log "ERROR: .env file not found at $ENV_FILE"
    verbose_log "Available files in script directory:"
    ls -la "$SCRIPT_DIR" | while read line; do
        verbose_log "  $line"
    done
    exit 1
fi
verbose_log ".env file found"

# Читаем connection string из .env
verbose_log "Reading DB_URL from .env file"
DB_URL=$(grep "^DB_URL=" "$ENV_FILE" | cut -d'=' -f2- | tr -d '"' | tr -d "'")

if [ -z "$DB_URL" ]; then
    log "ERROR: DB_URL not found in .env file"
    verbose_log "Contents of .env file:"
    cat "$ENV_FILE" | while read line; do
        verbose_log "  $line"
    done
    exit 1
fi

verbose_log "DB_URL found (length: ${#DB_URL})"
verbose_log "DB_URL starts with: ${DB_URL:0:20}..."

# Проверяем, что это PostgreSQL URL
if [[ ! "$DB_URL" =~ ^postgresql:// ]]; then
    log "ERROR: DB_URL is not a PostgreSQL connection string"
    verbose_log "DB_URL value: $DB_URL"
    exit 1
fi
verbose_log "DB_URL is valid PostgreSQL connection string"

log "Starting cleanup of idle transactions..."

# Проверяем подключение к базе данных
verbose_log "Testing database connection"
if ! psql "$DB_URL" -c "SELECT 1;" >/dev/null 2>&1; then
    log "ERROR: Cannot connect to database"
    verbose_log "Connection test failed"
    exit 1
fi
verbose_log "Database connection successful"

# Подсчитываем количество зависших транзакций ДО очистки
verbose_log "Counting idle transactions before cleanup"
BEFORE_COUNT=$(psql "$DB_URL" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
AND state_change < NOW() - INTERVAL '5 minutes';
" 2>/dev/null | tr -d ' ')

verbose_log "Raw BEFORE_COUNT result: '$BEFORE_COUNT'"

if [ -z "$BEFORE_COUNT" ] || [ "$BEFORE_COUNT" = "0" ]; then
    log "No idle transactions found to cleanup"
    verbose_log "BEFORE_COUNT is empty or zero"
    exit 0
fi

log "Found $BEFORE_COUNT idle transactions to cleanup"

# В dryrun режиме показываем детали
if [ "$DRYRUN" = true ]; then
    dryrun_log "DRYRUN MODE: Would execute the following query to terminate transactions:"
    dryrun_log "SELECT pid, usename, application_name, client_addr, state, state_change"
    dryrun_log "FROM pg_stat_activity"
    dryrun_log "WHERE state = 'idle in transaction'"
    dryrun_log "AND state_change < NOW() - INTERVAL '5 minutes';"
    
    # Показываем детали транзакций
    verbose_log "Details of idle transactions that would be terminated:"
    psql "$DB_URL" -c "
    SELECT pid, usename, application_name, client_addr, state, state_change
    FROM pg_stat_activity
    WHERE state = 'idle in transaction'
    AND state_change < NOW() - INTERVAL '5 minutes';
    " 2>/dev/null | while read line; do
        dryrun_log "  $line"
    done
    
    log "DRYRUN: Would terminate $BEFORE_COUNT idle transactions"
    exit 0
fi

# Убиваем зависшие транзакции
verbose_log "Executing termination query"
KILLED_COUNT=$(psql "$DB_URL" -t -c "
SELECT count(pg_terminate_backend(pid)) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
AND state_change < NOW() - INTERVAL '5 minutes';
" 2>/dev/null | tr -d ' ')

verbose_log "Raw KILLED_COUNT result: '$KILLED_COUNT'"

if [ -z "$KILLED_COUNT" ]; then
    KILLED_COUNT=0
    verbose_log "KILLED_COUNT was empty, set to 0"
fi

log "Successfully terminated $KILLED_COUNT idle transactions"
verbose_log "Termination operation completed"

# Проверяем результат
verbose_log "Checking result after cleanup"
AFTER_COUNT=$(psql "$DB_URL" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction';
" 2>/dev/null | tr -d ' ')

verbose_log "Raw AFTER_COUNT result: '$AFTER_COUNT'"

if [ -z "$AFTER_COUNT" ]; then
    AFTER_COUNT=0
    verbose_log "AFTER_COUNT was empty, set to 0"
fi

log "Cleanup completed. Idle transactions: $BEFORE_COUNT -> $AFTER_COUNT"

# Дополнительная информация о текущих соединениях
verbose_log "Gathering additional connection statistics"
TOTAL_CONNECTIONS=$(psql "$DB_URL" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE state IS NOT NULL;
" 2>/dev/null | tr -d ' ')

IDLE_TOTAL=$(psql "$DB_URL" -t -c "
SELECT count(*) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction';
" 2>/dev/null | tr -d ' ')

verbose_log "Raw TOTAL_CONNECTIONS result: '$TOTAL_CONNECTIONS'"
verbose_log "Raw IDLE_TOTAL result: '$IDLE_TOTAL'"

if [ -z "$TOTAL_CONNECTIONS" ]; then
    TOTAL_CONNECTIONS=0
fi

if [ -z "$IDLE_TOTAL" ]; then
    IDLE_TOTAL=0
fi

log "Total connections: $TOTAL_CONNECTIONS, Total idle in transaction: $IDLE_TOTAL"

# Если все еще много зависших транзакций, логируем предупреждение
if [ "$IDLE_TOTAL" -gt 20 ]; then
    log "WARNING: High number of idle transactions detected: $IDLE_TOTAL"
    verbose_log "This might indicate a persistent issue with application connections"
fi

# В verbose режиме показываем детали всех активных соединений
if [ "$VERBOSE" = true ]; then
    verbose_log "Current active connections:"
    psql "$DB_URL" -c "
    SELECT pid, usename, application_name, client_addr, state, state_change
    FROM pg_stat_activity
    WHERE state IS NOT NULL
    ORDER BY state_change DESC;
    " 2>/dev/null | while read line; do
        verbose_log "  $line"
    done
fi

log "=== Cleanup script completed ==="
exit 0
