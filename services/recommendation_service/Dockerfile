FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies first (cache layer)
COPY services/recommendation_service/pyproject.toml ./pyproject.toml
RUN pip install --no-cache-dir . && \
    pip install --no-cache-dir grpcio-tools "grpclib[protobuf]"

# Copy source code
COPY services/recommendation_service/src/ ./src/

# Copy proto definitions and generate stubs
COPY proto/ /proto/
RUN mkdir -p src/streammind_rec/api/grpc/generated/streammind/v1 && \
    python -m grpc_tools.protoc \
        -I /proto \
        --python_out=src/streammind_rec/api/grpc/generated \
        --grpclib_python_out=src/streammind_rec/api/grpc/generated \
        streammind/v1/service.proto && \
    touch src/streammind_rec/api/grpc/generated/__init__.py && \
    touch src/streammind_rec/api/grpc/generated/streammind/__init__.py && \
    touch src/streammind_rec/api/grpc/generated/streammind/v1/__init__.py

# Install the package
RUN pip install --no-cache-dir -e .

EXPOSE 50051 8001

CMD ["python", "-m", "streammind_rec.main"]
