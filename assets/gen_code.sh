#!/usr/bin/env bash
# Regenerate Python code from proto and flatbuffer schemas.
# Requires: grpcio-tools (pip), flatc (brew install flatbuffers)
set -euo pipefail
cd "$(dirname "$0")/.."

GENERATED=src/drawthings/generated

echo "→ Generating protobuf + gRPC stubs..."
python -m grpc_tools.protoc \
  --proto_path=assets/proto \
  --python_out="$GENERATED" \
  --grpc_python_out="$GENERATED" \
  assets/proto/imageService.proto

# Fix the bare import in the generated gRPC file
sed -i '' 's/^import imageService_pb2/from drawthings.generated import imageService_pb2/' \
  "$GENERATED/imageService_pb2_grpc.py"

echo "→ Generating FlatBuffer Python code..."
flatc --python -o "$GENERATED" assets/fbs/config.fbs

# Fix bare imports in GenerationConfiguration.py
sed -i '' 's/from Control import Control/from drawthings.generated.Control import Control/' \
  "$GENERATED/GenerationConfiguration.py"
sed -i '' 's/from LoRA import LoRA/from drawthings.generated.LoRA import LoRA/' \
  "$GENERATED/GenerationConfiguration.py"

echo "✔ Code generation complete."
