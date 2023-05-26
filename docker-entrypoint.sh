#!/bin/bash
set -e

create_tables() {
  exec ./manage.py database create-tables
}

scheduler() {
  echo "Starting RQ scheduler..."
  exec ./manage.py rq scheduler
}

dev_scheduler() {
  echo "Starting dev RQ scheduler..."

  pip install --user watchdog
  exec watchmedo auto-restart \
    --directory=./redash/ \
    --pattern=*.py --recursive -- \
    ./manage.py rq scheduler
}

worker() {
  echo "Starting RQ worker..."

  export WORKERS_COUNT=${WORKERS_COUNT:-2}
  export QUEUES=${QUEUES:-}

  exec supervisord -c ${HOME}/etc/supervisor/worker.conf
}

workers_healthcheck() {
  WORKERS_COUNT=${WORKERS_COUNT}
  echo "Checking active workers count against $WORKERS_COUNT..."
  ACTIVE_WORKERS_COUNT=`echo $(rq info --url $REDASH_REDIS_URL -R | grep workers | grep -oP ^[0-9]+)`
  if [ "$ACTIVE_WORKERS_COUNT" < "$WORKERS_COUNT"  ]; then
    echo "$ACTIVE_WORKERS_COUNT workers are active, Exiting"
    exit 1
  else
    echo "$ACTIVE_WORKERS_COUNT workers are active"
    exit 0
  fi
}

dev_worker() {
  echo "Starting dev RQ worker..."

  pip install --user watchdog
  exec watchmedo auto-restart --directory=./redash/ \
    --pattern=*.py --recursive -- \
    ./manage.py rq worker $QUEUES
}

server() {
  # Recycle gunicorn workers every n-th request.
  # See http://docs.gunicorn.org/en/stable/settings.html#max-requests
  MAX_REQUESTS=${MAX_REQUESTS:-1000}
  MAX_REQUESTS_JITTER=${MAX_REQUESTS_JITTER:-100}
  TIMEOUT=${REDASH_GUNICORN_TIMEOUT:-60}
  exec gunicorn -b 0.0.0.0:5000 --name redash \
    -w${REDASH_WEB_WORKERS:-4} redash.main:app \
    --max-requests $MAX_REQUESTS --max-requests-jitter \
    $MAX_REQUESTS_JITTER --timeout $TIMEOUT
}

help() {
  echo "Redash Docker."
  echo ""
  echo "Usage:"
  echo ""
  echo "manage -- CLI to manage Redash"
  echo "create_tables -- create database tables"
  echo "server -- start Redash server (with gunicorn)"
  echo "worker -- start a single RQ worker"
  echo "scheduler -- start an rq-scheduler instance"
  echo ""
  echo "tests -- run tests"
  echo "shell -- open shell"
  echo "dev_scheduler -- start an rq-scheduler instance with code reloading"
  echo "dev_worker -- start a single RQ worker with code reloading"
  echo "dev_server -- start Flask development server with debugger and auto reload"
  echo "debug -- start Flask development server with remote debugger via ptvsd"
  echo ""
}

tests() {
  if [ $# -eq 0 ]; then
    TEST_ARGS=tests/
  else
    TEST_ARGS=$@
  fi

  exec pytest $TEST_ARGS
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
  worker)
    shift
    worker
    ;;
  workers_healthcheck)
    shift
    workers_healthcheck
    ;;
  server)
    shift
    server
    ;;
  scheduler)
    shift
    scheduler
    ;;
  dev_scheduler)
    shift
    dev_scheduler
    ;;
  dev_worker)
    shift
    dev_worker
    ;;
  dev_server)
    export FLASK_DEBUG=1
    exec ./manage.py runserver --debugger --reload -h 0.0.0.0
    ;;
  debug)
    export FLASK_DEBUG=1
    export REMOTE_DEBUG=1
    exec ./manage.py runserver --debugger --no-reload -h 0.0.0.0
    ;;
  shell)
    exec ./manage.py shell
    ;;
  manage)
    shift
    exec ./manage.py $*
    ;;
  tests)
    shift
    tests $@
    ;;
  help)
    shift
    help
    ;;
  *)
    exec "$@"
    ;;
esac
