#!/bin/bash
set -e

ENVIRONMENT=${ENVIRONMENT:-production}

echo "ENVIRONMENT=${ENVIRONMENT}"

help() {
  echo "Docker entrypoint script."
  echo ""
  echo "Usage:"
  echo ""
  echo "manage -- run CLI to management command"
  echo "healthcheck -- run healthchecks for workers"
  echo ""
  echo "run_scheduler -- start an rq-scheduler instance"
  echo "run_worker -- start a RQ workers with code reloading"
  echo "run_worker -- start a single RQ worker with code reloading"
  echo "run_server -- start Flask / gunicorn server"
  echo ""
  echo "For live code reloading set ENVIRONMENT=development"
  echo ""
  echo "Example:"
  echo ""
  echo "docker <CONTAINER> exec manage database create-tables"
  echo ""
}

healthcheck() {
  WORKERS_COUNT=${WORKERS_COUNT}
  echo "Checking active workers count against $WORKERS_COUNT..."
  ACTIVE_WORKERS_COUNT=`echo $(rq info --url $REDIS_URL -R | grep workers | grep -oP ^[0-9]+)`
  if [ "$ACTIVE_WORKERS_COUNT" < "$WORKERS_COUNT"  ]; then
    echo "$ACTIVE_WORKERS_COUNT workers are active, Exiting"
    exit 1
  else
    echo "$ACTIVE_WORKERS_COUNT workers are active"
    exit 0
  fi
}

run_scheduler() {
  echo "Starting RQ scheduler (${ENVIRONMENT}) ..."
  if [ ${ENVIRONMENT} = "development" ]; then
    exec watchmedo auto-restart -d=./redash/ -d=./dingolytics/ -p=*.py -R -- \
      ./manage.py rq scheduler
  else
    exec ./manage.py rq scheduler
  fi
}

run_worker() {
  echo "Starting RQ worker (${ENVIRONMENT}) ..."
  if [ ${ENVIRONMENT} = "development" ]; then
    exec watchmedo auto-restart -d=./redash/ -d=./dingolytics/ -p=*.py -R -- \
      ./manage.py rq worker $QUEUES
  else
    export WORKERS_COUNT=${WORKERS_COUNT:-2}
    export QUEUES=${QUEUES:-}
    exec supervisord -c ${HOME}/etc/supervisor/worker.conf
  fi
}

run_worker_hy() {
  echo "Starting Huey worker (${ENVIRONMENT}) ..."
  if [ ${ENVIRONMENT} = "development" ]; then
    exec watchmedo auto-restart -d=./redash/ -d=./dingolytics/ -p=*.py -R -- \
      python -m dingolytics.worker default
  else
    exec python -m dingolytics.worker default
  fi
}

run_periodic_hy() {
  echo "Starting Huey periodic worker (${ENVIRONMENT}) ..."
  if [ ${ENVIRONMENT} = "development" ]; then
    exec watchmedo auto-restart -d=./redash/ -d=./dingolytics/ -p=*.py -R -- \
      python -m dingolytics.worker periodic
  else
    exec python -m dingolytics.worker periodic
  fi
}

run_server() {
  echo "Starting application server (${ENVIRONMENT}) ..."
  if [ ${ENVIRONMENT} = "development" ]; then
    export FLASK_DEBUG=1
    exec ./manage.py runserver -h 0.0.0.0
  else
    # Recycle gunicorn workers every n-th request.
    # See http://docs.gunicorn.org/en/stable/settings.html#max-requests
    MAX_REQUESTS=${MAX_REQUESTS:-1000}
    MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}
    TIMEOUT=${GUNICORN_TIMEOUT:-60}
    exec gunicorn -b 0.0.0.0:5000 --name redash \
      -w${GUNICORN_WEB_WORKERS:-4} redash.main:app \
      --max-requests $MAX_REQUESTS --max-requests-jitter \
      $MAX_REQUESTS_JITTER --timeout $TIMEOUT
  fi
}

case "$1" in
  create_db)
    shift
    create_tables
    ;;
  create_tables)
    shift
    create_tables
    ;;
  healthcheck)
    shift
    healthcheck
    ;;
  help)
    shift
    help
    ;;
  manage)
    shift
    exec ./manage.py $*
    ;;
  run_server)
    shift
    run_server
    ;;
  run_scheduler)
    shift
    run_scheduler
    ;;
  run_worker)
    shift
    run_worker
    ;;
  run_worker_hy)
    shift
    run_worker_hy
    ;;
  run_periodic_hy)
    shift
    run_periodic_hy
    ;;
  shell)
    exec ./manage.py shell
    ;;
  *)
    exec "$@"
    ;;
esac
