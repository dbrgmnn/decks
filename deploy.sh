#!/usr/bin/env bash
set -euo pipefail

# Resolve the project root so the script works from any directory.
ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
DATA_DIR="$ROOT_DIR/data"
ACTION="${1:-up}"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or not in PATH."
  exit 1
fi

mkdir -p "$DATA_DIR"
cd "$ROOT_DIR"

run_compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

deploy_now() {
  run_compose up --build -d
}

case "$ACTION" in
  up)
    deploy_now
    ;;
  down)
    run_compose down
    ;;
  restart)
    run_compose down
    deploy_now
    ;;
  logs)
    run_compose logs -f
    ;;
  pull)
    if ! command -v git >/dev/null 2>&1; then
      echo "Git is not installed or not in PATH."
      exit 1
    fi
    echo "Pulling latest code..."
    git pull --ff-only
    deploy_now
    ;;
  *)
    echo "Usage: ./deploy.sh [up|down|restart|logs|pull]"
    exit 1
    ;;
esac
