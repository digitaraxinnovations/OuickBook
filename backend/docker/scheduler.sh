#!/bin/sh
# Runs the daily job (recurring transactions, late fees, reminders,
# scheduled reports) every DAILY_JOBS_INTERVAL_SECONDS (default: one day).
set -e

INTERVAL="${DAILY_JOBS_INTERVAL_SECONDS:-86400}"

# Give the API a moment to apply migrations on first start.
sleep "${SCHEDULER_START_DELAY_SECONDS:-30}"

while true; do
  echo "$(date -u '+%Y-%m-%d %H:%M:%S') running daily jobs"
  python -m app.scripts.run_daily_jobs || echo "Daily jobs failed - will try again next round."
  sleep "$INTERVAL"
done
