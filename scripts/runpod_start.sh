#!/bin/bash
# RunPod startup script: clones repo, installs deps, generates embeddings, starts services
set -e

echo "=== StreamMind RunPod Setup ==="

# Clone the repo
cd /workspace
if [ ! -d "stream-mind" ]; then
    git clone https://github.com/elloloop/stream-mind.git
fi
cd stream-mind
git pull --ff-only || true

# Install embedding service deps (includes sentence-transformers, torch)
echo "Installing embedding service dependencies..."
pip install -q -r services/embedding_service/requirements.txt

# Install recommendation service deps
echo "Installing recommendation service dependencies..."
cd services/recommendation_service
pip install -q -e .
pip install -q sentence-transformers

# Generate gRPC stubs
echo "Generating gRPC stubs..."
bash generate_protos.sh
cd /workspace/stream-mind

# Generate embeddings for both models if not present
if [ ! -f data/movies_minilm.arrow ] || [ ! -f data/movies_bge.arrow ]; then
    echo "Generating embeddings for both models..."
    mkdir -p data

    if [ -f /workspace/tmdb_movies.jsonl ]; then
        JSONL_PATH=/workspace/tmdb_movies.jsonl
    elif [ -f data/tmdb_movies.jsonl ]; then
        JSONL_PATH=data/tmdb_movies.jsonl
    else
        echo "ERROR: tmdb_movies.jsonl not found. Place it in /workspace/ or data/"
        exit 1
    fi

    python3 scripts/generate_test_data.py "$JSONL_PATH"
else
    echo "Arrow files already exist, skipping embedding generation."
fi

# Start recommendation service (loads both model states)
echo "Starting recommendation service on :8001..."
DATA_DIR=/workspace/stream-mind/data \
EMBEDDING_SERVICE_URL=http://localhost:8000 \
HTTP_PORT=8001 \
GRPC_PORT=50051 \
DEFAULT_MODEL=bge \
python3 -m streammind_rec.main &
REC_PID=$!

# Wait for recommendation service
echo "Waiting for recommendation service..."
for i in $(seq 1 60); do
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "Recommendation service ready!"
        break
    fi
    sleep 2
done

echo ""
echo "=== StreamMind is running ==="
echo "  Recommendation:  http://localhost:8001"
echo "  gRPC:            localhost:50051"
echo ""
echo "Available models:"
curl -s http://localhost:8001/api/models | python3 -m json.tool 2>/dev/null || true
echo ""
echo "Press Ctrl+C to stop"

# Keep alive
wait
