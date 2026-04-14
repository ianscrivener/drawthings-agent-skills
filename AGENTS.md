# Project Guidelines — drawthings-agent-skill

## Overview

Python gRPC client and agent skill for the [Draw Things](https://drawthings.ai) image generation server on macOS. Wraps the gRPC + FlatBuffers + DTTensor image format into a simple Python API with CLI scripts that output JSON.

This project is a Python port of [dt-grpc-ts](https://github.com/kcjerrell/dt-grpc-ts), a TypeScript gRPC client library for Draw Things by Kelly Jerrell. The proto/fbs schemas, wire format, tensor encoding, and FlatBuffer config structure are all derived from that reference implementation.

## Architecture

```
DTService (service.py)
  ├── build_config_buffer (config.py)  → FlatBuffer-encoded GenerationConfiguration
  ├── image_helpers.py                 → DTTensor ↔ PIL Image conversion
  ├── cred.py                          → TLS credentials (Draw Things root CA)
  └── generated/                       → Auto-generated protobuf + FlatBuffer code
```

**Request flow:**
1. Config dict → `build_config_buffer()` → FlatBuffer bytes
2. Source image (if img2img) → `convert_image_for_request()` → DTTensor bytes, SHA-256 hashed
3. Protobuf `ImageGenerationRequest` assembled with config, prompt, image hash, contents
4. gRPC streaming response → `convert_response_image()` → PIL Image

**DTTensor wire format** (shared with the TypeScript library):
- 68-byte header: 17 × uint32 (metadata flags at indices 0–5, height at 6, width at 7, channels at 8)
- Payload: float16 pixel data (`width × height × channels × 2` bytes)
- Response decode: `clamp((f16 + 1) × 127, 0, 255)` → uint8
- Request encode: `(uint8 / 127) − 1` → float16
- Images are content-addressed: SHA-256 hash as reference, raw bytes in `contents[]`

## Code Style

- **Python 3.10+**, plain Python — no TypeScript, no frameworks
- **snake_case** for all Python identifiers and config dict keys
- Config keys map to FlatBuffer schema fields: `hires_fix_strength`, `guidance_scale`, `seed_mode`, etc.
- Generated code in `src/drawthings/generated/` — **do not edit manually**; regenerate with `assets/gen_code.sh`
- Imports from generated code use full package paths: `from drawthings.generated import imageService_pb2`

## Build & Test

```bash
# Check environment (JSON: ready true/false, missing list)
python src/drawthings/check_env.py

# Setup if needed (creates .venv, auto-installs uv if missing, installs deps)
python src/drawthings/setup_env.py

# Test
pytest                    # 14 unit tests, all mocked (no Draw Things server needed)

# Run scripts via venv Python (no activation needed)
.venv/bin/python src/drawthings/list_assets.py
.venv/bin/python src/drawthings/generate.py --prompt "test" --output_dir /tmp

# Regenerate proto/fbs code (after changing .proto or .fbs schemas)
./assets/gen_code.sh     # requires grpcio-tools + flatc
```

## Dependencies

- **Runtime**: `grpcio`, `protobuf`, `flatbuffers`, `Pillow`
- **Dev**: `pytest`, `pytest-cov`, `pytest-mock`, `grpcio-tools`
- **System**: `flatc` (via `brew install flatbuffers`) — only needed for code regeneration
- **Package manager**: Always use `uv` — never pip

## Conventions

### CLI Scripts
All scripts in `src/drawthings/` follow the same contract:
- Accept `--host` (default `localhost:7859`) for the gRPC server address
- Output **JSON to stdout** on success: `{"success": true, ...}`
- Output **JSON to stderr** on failure: `{"success": false, "error": "..."}`
- Exit code 0 on success, 1 on error
- Use `argparse` for CLI arguments

### Generated Code
The `gen_code.sh` script handles a known issue: generated protobuf/FlatBuffer files use bare imports (`import imageService_pb2`, `from LoRA import LoRA`) which break when used as a package. The script automatically patches these to use full package paths (`from drawthings.generated import ...`). If you regenerate manually, you must apply these fixes.

### Image Sizes
All pixel dimensions are rounded to the nearest multiple of 64 (minimum 64) before being sent to the server. The FlatBuffer config stores dimensions divided by 64 (`start_width = pixels // 64`).

### TLS
Draw Things uses a self-signed root CA for its gRPC server. The certificate is embedded in `cred.py`. Connections always use TLS via `grpc.ssl_channel_credentials`.

## Skill Integration

The `SKILL.md` file at the repo root is the agent skill manifest. It contains trigger phrases, procedures, and CLI flag references. When this repo is installed into an agent's skills directory, the agent will auto-detect it when users ask to generate images, create artwork, or use Draw Things / Stable Diffusion locally.

### Agent Environment Workflow

The skill uses a **check → setup → run** pattern so the agent manages its own environment:

1. `src/drawthings/check_env.py` — zero-dependency diagnostic; outputs JSON with `ready`, `checks`, `missing`, `venv_python`
2. `src/drawthings/setup_env.py` — zero-dependency setup; creates venv, runs `uv sync`, verifies imports
3. Skill scripts are invoked via `.venv/bin/python src/drawthings/<script>.py` (no shell activation required)

Both check and setup scripts run with the system Python and have no imports from the drawthings package.
Scripts are invoked via `.venv/bin/python` — no shell activation required.

## Reference Implementation

The proto schemas (`assets/proto/imageService.proto`) and FlatBuffer schema (`assets/fbs/config.fbs`) are sourced from [dt-grpc-ts](https://github.com/kcjerrell/dt-grpc-ts). When upstream schemas change, copy the updated `.proto` / `.fbs` files and run `./assets/gen_code.sh` to regenerate.
