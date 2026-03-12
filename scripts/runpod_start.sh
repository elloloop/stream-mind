#!/bin/bash
# RunPod startup script: clones repo, installs deps, starts both services
set -e

echo "=== StreamMind RunPod Setup ==="

# Clone the repo
cd /workspace
if [ ! -d "stream-mind" ]; then
    git clone https://github.com/elloloop/stream-mind.git
fi
cd stream-mind

# Install embedding service deps
echo "Installing embedding service dependencies..."
pip install -q -r services/embedding_service/requirements.txt

# Install recommendation service deps
echo "Installing recommendation service dependencies..."
cd services/recommendation_service
pip install -q -e .

# Generate gRPC stubs
echo "Generating gRPC stubs..."
bash generate_protos.sh
cd /workspace/stream-mind

# Generate test data
echo "Generating test data..."
mkdir -p data
python3 scripts/generate_test_data.py

# Start embedding service (background)
echo "Starting embedding service on :8000..."
cd /workspace/stream-mind
DEVICE=cuda PORT=8000 python3 services/embedding_service/main.py &
EMBED_PID=$!

# Wait for embedding service to be ready (model loading takes time)
echo "Waiting for embedding service to load model..."
for i in $(seq 1 120); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Embedding service ready!"
        break
    fi
    sleep 2
done

# Start recommendation service
echo "Starting recommendation service on :8001..."
ARROW_PATH=/workspace/stream-mind/data/movies.arrow \
EMBEDDING_SERVICE_URL=http://localhost:8000 \
HTTP_PORT=8001 \
GRPC_PORT=50051 \
python3 -m streammind_rec.main &
REC_PID=$!

echo ""
echo "=== StreamMind is running ==="
echo "  Embedding:       http://localhost:8000"
echo "  Recommendation:  http://localhost:8001"
echo "  gRPC:            localhost:50051"
echo ""

# Keep the script alive
wait
