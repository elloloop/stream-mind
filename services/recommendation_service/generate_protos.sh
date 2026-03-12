#!/bin/bash
# Generate Python protobuf + grpclib stubs from .proto files
set -e

PROTO_DIR="../../proto"
OUT_DIR="src/streammind_rec/api/grpc/generated"

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR/streammind/v1"

# Generate protobuf messages
python -m grpc_tools.protoc \
    -I "$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpclib_python_out="$OUT_DIR" \
    streammind/v1/service.proto

# Create __init__.py files
touch "$OUT_DIR/__init__.py"
touch "$OUT_DIR/streammind/__init__.py"
touch "$OUT_DIR/streammind/v1/__init__.py"

echo "Proto stubs generated in $OUT_DIR"
