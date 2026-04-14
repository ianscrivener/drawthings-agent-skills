---
name: drawthings
description: "Create AI images using DrawThings on your own computer (locally). Uses the DrawThings gRPC API. Use this skill when asked to generate images, create artwork, render a scene, produce an image, do text-to-image, img2img, image-to-image, or when the user wants to use DrawThings, Draw Things. Also use to list the DrawThings assets; AI models, LoRAs, ControlNets, upcalers and samplers."
---

# DrawThings Image Generation Skill
Generates images via the DrawThings gRPC API running locally on macOS (or Linux).
Supports text-to-image, image-to-image, upscaling, face restoration and DrawThingsserver introspection.

## Prerequisites - **IMPORTANT!!!**
1. This skill will only work on a MacOS with M Series silicon or a Linux with a modern GPU
1. Be sure to follow the setup prerequisites and process exactly. Do not vary or ignore to read the configuration properly.  
1. The user needs to enable the GRPC server on DrawThings for this skill to work.  
**DrawThings** must be running on macOS with the gRPC server enabled (default port `7859`).
Enable it in Draw Things → Settings → API Server.

## Environment Setup (agent-managed)- **IMPORTANT!!!**

Follow the instructions exactly. Don't be arrogant and think you know better and try to do your own thing. If there are problems with rendering - just state the facts accurately - do not speculate as to the cause.

### Step 1: Check environment - IMPORTANT!!!

```bash
python src/drawthings/check_env.py --host localhost:7859
```
This is uses your the system Python to check the UV Python and curler install that there is a Python virtual environment and that the UV Python environment is has downloaded all the models. 

Returns JSON with `ready: true/false`, a `checks` object, `missing` list, and `venv_python` path.
If `ready` is `true`, skip to Step #3.

### Step 2: Setup (only if check in Step #1 reports not ready) - IMPORTANT!!!

```bash
python src/drawthings/setup_env.py
```

Creates the `.venv`, installs all dependencies via `uv sync`, and verifies the package is importable. Returns JSON with `success: true/false` and the `venv_python` path.
This is idempotent — safe to run repeatedly.

### Step 3: Run skill scripts

Use the `venv_python` path from check/setup (typically `.venv/bin/python`) to run scripts:

```bash
./.venv/bin/python src/drawthings/generate.py --prompt "..."
./.venv/bin/python src/drawthings/list_assets.py --tls true --compression false
./.venv/bin/python src/drawthings/img2img.py --input /path/to/image.png --prompt "..."
```

`list_assets.py` defaults to `--tls true --compression false`, so it can still be run without these flags for quick testing.

## Available Scripts

| Script | Purpose |
|--------|----------|
| [src/drawthings/check_env.py](src/drawthings/check_env.py) | Validate environment (zero-dependency) |
| [src/drawthings/setup_env.py](src/drawthings/setup_env.py) | Create venv and install deps (zero-dependency) |
| [src/drawthings/generate.py](src/drawthings/generate.py) | Text-to-image generation |
| [src/drawthings/img2img.py](src/drawthings/img2img.py) | Image-to-image (modify an existing image) |
| [src/drawthings/list_assets.py](src/drawthings/list_assets.py) | List available assets (models, LoRAs, ControlNets, samplers) |

All scripts output JSON to stdout. Errors are written to stderr with a non-zero exit code.

### Caveats & Troubleshooting
1. DrawThings can only generate one image at a time. So if the user is generating one manually, an agent initiated generation may fail.
1. Image generation can take some time depending upon the size of the image and the pause the processes of the computer. It is not unusual to for an image to take ten or fifteen minutes to render. Timeouts can occur given such a long duration. 
1. Some image model slash sampler combinations are unsupported. So if an image fails to work, try smaller sizes or a different sampler. 
1. Image users should be encouraged to try smaller test images to before embarking on bigger renders. A 128 by 128 pixel image will be quite quick to render.



---

## (1)Procedure: List available models

```bash
./.venv/bin/python src/drawthings/list_assets.py \
  --host localhost:7859 \
  --tls true \
  --compression false
```

`--tls` and `--compression` both accept `true|false`. Defaults are `true` and `false` respectively.

**Output JSON:**
```json
{
  "models": ["flux_qwen_srpo_v1.0_f16.ckpt", "sd_v1.5_f16.ckpt"],
  "loras": ["my_style.safetensors"],
  "control_nets": ["controlnet_depth_1.x_v1.1_f16.ckpt"],
  "upscalers": ["realesrgan_x2plus_f16.ckpt"],
  "textual_inversions": [],
  "samplers": [
    {"id": 5, "name": "UniPC", "api_name": "UniPC"},
    {"id": 15, "name": "DPM++ 2M Trailing", "api_name": "DPMPP2MTrailing"}
  ]
}
```

---

## (2) Procedure: Generate an image from a text prompt

1. Optionally run `list_assets.py` to find an available model name
2. Run `generate.py` with the prompt and model
3. The saved file path is returned in the JSON output as `output`

```bash
./.venv/bin/python src/drawthings/generate.py \
  --prompt "a golden retriever on a beach at sunset" \
  --model "flux_qwen_srpo_v1.0_f16.ckpt" \
  --width 512 --height 512 \
  --output_dir /tmp
```

**All flags for generate.py:**

| Flag | Default | Description |
|------|---------|-------------|
| `--prompt` | *(required)* | Positive prompt text |
| `--negative` | `""` | Negative prompt text |
| `--model` | `z_image_1.0_q8p.ckpt` | Model filename (e.g. `z_image_1.0_q8p.ckpt`) |
| `--width` | `1024` | Image width in pixels (rounded to nearest 64) |
| `--height` | `1024` | Image height in pixels (rounded to nearest 64) |
| `--steps` | `8` | Steps |
| `--guidance` | server default | CFG guidance scale (e.g. `7.5`) |
| `--sampler` | `UniPC` | Sampler name (gRPC `SamplerType`) |
| `--clip_skip` | `1` | Number of CLIP layers to skip |
| `--mask_blur` | `1.5` | Mask blur radius |
| `--sharpness` | `3.5` | Sharpness applied post-generation |
| `--shift` | `2.8` | Shift parameter |
| `--seed` | `-1` | Seed for reproducibility |
| `--upscaler` | disabled | Enable upscaling (optional model name; defaults to `4x_ultrasharp_f16.ckpt`) |
| `--upscale-factor` | `2` | Upscale factor used with `--upscaler` |
| `--facefix` | disabled | Enable face restoration using `RestoreFormer.pth` |
| `--face-restore` | disabled | Alias for `--facefix` |
| `--output_dir` | `/tmp` | Output directory. Image filename is auto-generated as `YYYYDDMM-HHmmss.png` |
| `--host` | `localhost:7859` | Draw Things gRPC server address |

**Output JSON:**
```json
{ "success": true, "output": "/absolute/path/to/output.png" }
```

---

## (3) Procedure: Modify an existing image (img2img)

```bash
./.venv/bin/python src/drawthings/img2img.py \
  --input /path/to/source.png \
  --model z_image_1.0_q8p.ckpt \
  --guidance 1.5 \
  --width 1024 \
  --height 1024 \
  --prompt "same scene but in winter with snow" \
  --strength 0.6 \
  --output_dir /tmp
```

**All flags for img2img.py:**

Same flags as `generate.py`, plus:

| Flag | Default | Description |
|------|---------|-------------|
| `--input` | *(required)* | Path to source image |
| `--strength` | `0.6` | How much to change the image (0=none, 1=full) |

`img2img.py` also supports `--upscaler`, `--upscale-factor`, `--facefix`, and `--face-restore`.

---


## Config Reference

See [assets/references/config-options.md](assets/references/config-options.md) for the full list of generation parameters.

## Troubleshooting

- **Connection refused**: Draw Things is not running, or the API server is not enabled in Settings
- **Module not found**: Run `python src/drawthings/check_env.py` — if not ready, run `python src/drawthings/setup_env.py`
- **Model not found**: Run `list_assets.py` to see available model filenames; use the exact filename including extension
- **Image too dark/bright**: Adjust `--guidance` (typical range 5–12 for SD models, 1–4 for Flux)
