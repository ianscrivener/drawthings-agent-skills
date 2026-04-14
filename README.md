# drawthings-agent-skill

### WIP... planning to make it more robust, better documentation and easier deployment. 


An AI-Agent Skill that lets your Agent (Hermes, Claude Code, Github Copilot... or any compatible agent) generate images using [Draw Things](https://drawthings.ai) on your Mac. Just drop it into your skills folder, ask your agent to make an image, and it handles the rest.

For MacOS & Linux Only. 

## What You Need

- **macOS** or **Linux** with [Draw Things](https://drawthings.ai) application or CLI installed
- **Draw Things API server** enabled: Draw Things → Settings → API Server (default port 7859)
- **Python 3.10+**
- **curl****

## Draw Things API Server Settings

> **Important** — This skill connects to Draw Things via **gRPC** (not HTTP). You must configure the API server in Draw Things to match these settings:
>
> | Setting | Required value |
> |---------|----------------|
> | **Protocol** | gRPC |
> | **Port** | `7859` (default) |
> | **TLS** | On |
> | **Response Compression** | Off |
>
> Open Draw Things → Settings → API Server and make sure all four match.
> <!-- TODO: add screenshot here -->

For `list_assets.py`, these map to CLI flags:
- `--tls true|false`
- `--compression true|false`

Default values are `--tls true --compression false`.

If any of these are wrong the skill won't be able to connect. The most common issue is accidentally selecting HTTP instead of gRPC.

## Installation

Clone or copy this repo into your agent's skills directory. The agent discovers the skill automatically from the `SKILL.md` manifest when you ask it to generate images.

That's it. No manual setup required — the agent will check and bootstrap the Python environment itself the first time it runs.

## What It Can Do

- **Text-to-image**: "Generate a watercolor painting of a cat in a garden"
- **Image-to-image**: "Take this photo and make it look like a pencil sketch"
- **Upscaling**: "Upscale this generation 2x using `4x_ultrasharp_f16.ckpt`"
- **Face restoration**: "Apply face fix with RestoreFormer"
- **Server introspection**: "What models do I have available in Draw Things?"

## How It Works Under the Hood

The agent follows a check → setup → run workflow:

1. Runs `check_env.py` to see if the Python environment is ready
2. If not, runs `setup_env.py` to create the venv and install dependencies via `uv`
3. Runs the appropriate module (`generate.py`, `img2img.py`, `list_assets.py`) using the venv Python

All modules output structured JSON, so the agent always knows what happened.

## Manual Usage (Optional)

You can also run the scripts directly if you want:

```bash
python src/drawthings/setup_env.py

# Then run scripts
.venv/bin/python src/drawthings/list_assets.py --tls true --compression false
.venv/bin/python src/drawthings/generate.py \
  --prompt "a golden retriever on a beach at sunset" \
  --output_dir /tmp
```

## Project Structure

```
├── SKILL.md                      ← Agent skill manifest
├── pyproject.toml
├── README.md
├── src/drawthings/
│   ├── check_env.py              ← Environment check (zero-dependency)
│   ├── setup_env.py              ← Environment setup (zero-dependency)
│   ├── generate.py               ← txt2img CLI
│   ├── img2img.py                ← img2img CLI
│   ├── list_assets.py            ← Server introspection
│   ├── service.py                ← DTService gRPC client
│   ├── config.py                 ← FlatBuffer config builder
│   ├── image_helpers.py          ← DTTensor ↔ PIL Image conversion
│   ├── cred.py                   ← TLS credentials
│   └── generated/                ← Auto-generated (do not edit)
├── assets/
│   ├── references/               ← Config options docs
│   ├── proto/                    ← Source .proto schemas
│   └── fbs/                      ← Source .fbs schemas
└── tests/
```

## Development

```bash
# Setup
python src/drawthings/setup_env.py

# Run tests
pytest

# Regenerate protobuf/flatbuffer code (after changing .proto or .fbs)
./assets/gen_code.sh
```

## License

Apache-2.0
AI Agent Skill for DrawThings


---
### Acknowledgements & Thanks

- Liuliu for creating the most excellent DrawThings
- [draw-things-comfyui](https://github.com/drawthingsai/draw-things-comfyui) — reference for Draw Things workflow/API behavior
- [dt-grpc-ts](https://github.com/kcjerrell/dt-grpc-ts) — primary gRPC/proto/FlatBuffer wire-format reference for this Python port
