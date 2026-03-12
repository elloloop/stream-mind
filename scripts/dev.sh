#!/bin/bash
# Local development: start backend + frontend
# Requires: python3 with deps installed, node via nvm
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Generate test data if not exists
if [ ! -f data/movies.arrow ]; then
    echo "Generating test data..."
    python3 scripts/generate_test_data.py
fi

# Generate gRPC stubs if not exists
GRPC_DIR="services/recommendation_service/src/streammind_rec/api/grpc/generated/streammind/v1"
if [ ! -f "$GRPC_DIR/service_grpc.py" ]; then
    echo "Generating gRPC stubs..."
    cd services/recommendation_service
    bash generate_protos.sh
    cd "$PROJECT_DIR"
fi

echo "Starting recommendation service on :8001 (gRPC on :50051)..."
ARROW_PATH="$PROJECT_DIR/data/movies.arrow" \
EMBEDDING_SERVICE_URL=http://localhost:8000 \
HTTP_PORT=8001 \
GRPC_PORT=50051 \
python3 -m streammind_rec.main &
BACKEND_PID=$!

sleep 2

echo "Starting Next.js frontend..."
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
cd frontend
NEXT_PUBLIC_API_URL=http://localhost:8001 npm run dev &
FRONTEND_PID=$!

echo ""
echo "=== StreamMind is running ==="
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8001"
echo "  gRPC:      localhost:50051"
echo ""
echo "Press Ctrl+C to stop all services"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
