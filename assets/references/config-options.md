# Config Options Reference

Full reference for all generation config fields.
Pass these as CLI flags to the scripts, or as dict keys (snake_case) when using the Python library directly.

## Core Generation

| Field | CLI flag | Type | Default | Description |
|-------|----------|------|---------|-------------|
| `model` | `--model` | string | server default | Model filename, e.g. `flux_qwen_srpo_v1.0_f16.ckpt` |
| `width` | `--width` | int | 512 | Image width in pixels. Rounded to nearest 64, minimum 64 |
| `height` | `--height` | int | 512 | Image height in pixels. Rounded to nearest 64, minimum 64 |
| `steps` | `--steps` | int | 20 | Number of diffusion steps. More = higher quality, slower |
| `guidance_scale` | `--guidance` | float | 4.5 | CFG scale. Higher = more prompt adherence. SD: 5–12, Flux: 1–4 |
| `seed` | `--seed` | int | random | Fixed seed for reproducible results. `-1` = random |
| `strength` | `--strength` | float | 1.0 | For img2img: how much to change the source image (0–1) |

## Sampler

| Field | Type | Values |
|-------|------|--------|
| `sampler` | int | `0`=DPMPP2MKarras *(default)*, `1`=EulerA, `2`=DDIM, `3`=PLMS, `4`=DPMPPSDEKarras, `5`=UniPC, `6`=LCM, `7`=EulerASubstep, `8`=DPMPPSDESubstep, `9`=TCD, `10`=EulerATrailing, `11`=DPMPPSDETrailing, `12`=DPMPP2MAYS, `13`=EulerAAYS, `14`=DPMPPSDEAYS, `15`=DPMPP2MTrailing, `16`=DDIMTrailing |
| `seed_mode` | int | `0`=Legacy, `1`=TorchCpuCompatible, `2`=ScaleAlike *(default)*, `3`=NvidiaGpuCompatible |

## Hires Fix / Upscaling

| Field | Type | Description |
|-------|------|-------------|
| `hires_fix` | bool | Enable two-pass hi-res fix |
| `hires_fix_start_width` | int | Low-res pass width |
| `hires_fix_start_height` | int | Low-res pass height |
| `hires_fix_strength` | float | Denoising strength for hires pass |
| `upscaler` | string | Upscaler model filename |
| `upscaler_scale_factor` | int | Scale factor for the upscaler |

## Tiled Diffusion / Decoding

| Field | Type | Description |
|-------|------|-------------|
| `tiled_diffusion` | bool | Enable tiled diffusion (for large images) |
| `diffusion_tile_width` | int | Tile width for diffusion |
| `diffusion_tile_height` | int | Tile height for diffusion |
| `diffusion_tile_overlap` | int | Overlap between tiles |
| `tiled_decoding` | bool | Enable tiled VAE decoding |
| `decoding_tile_width` | int | Tile width for decoding |
| `decoding_tile_height` | int | Tile height for decoding |
| `decoding_tile_overlap` | int | Overlap between decoding tiles |

## Inpainting

| Field | Type | Description |
|-------|------|-------------|
| `mask_blur` | float | Blur radius for mask edges |
| `mask_blur_outset` | int | Outset applied before blurring |
| `preserve_original_after_inpaint` | bool | Keep original pixels outside the mask |

## LoRAs

Pass as `loras` list in config dict:

```python
config = {
    "loras": [
        {"file": "my_style.safetensors", "weight": 0.8},
        {"file": "detail.safetensors", "weight": 0.5},
    ]
}
```

## ControlNets

Pass as `controls` list in config dict:

```python
config = {
    "controls": [{
        "file": "controlnet_depth_1.x_v1.1_f16.ckpt",
        "weight": 1.0,
        "guidance_start": 0,
        "guidance_end": 1,
        "no_prompt": False,
        "global_average_pooling": False,
        "down_sampling_rate": 1,
        "control_mode": 0,   # 0=Balanced, 1=Prompt, 2=Control
        "target_blocks": [],
        "input_override": 0, # see ControlInputType
    }]
}
```

**ControlInputType values:** `0=Unspecified`, `1=Custom`, `2=Depth`, `3=Canny`, `4=Scribble`, `5=Pose`, `6=Normalbae`, `7=Color`, `8=Lineart`, `9=Softedge`, `10=Seg`, `11=Inpaint`, `12=Ip2p`, `13=Shuffle`, `14=Mlsd`, `15=Tile`, `16=Blur`, `17=Lowquality`, `18=Gray`

## Refiner (SDXL)

| Field | Type | Description |
|-------|------|-------------|
| `refiner_model` | string | Refiner model filename |
| `refiner_start` | float | Step ratio at which refiner takes over (0–1) |

## Flux / T5

| Field | Type | Description |
|-------|------|-------------|
| `t5_text_encoder` | bool | Enable T5 text encoder |
| `guidance_embed` | float | Guidance embed value for Flux |
| `speed_up_with_guidance_embed` | bool | Speed optimisation using guidance embed |
| `shift` | float | Flux shift parameter |
| `resolution_dependent_shift` | bool | Auto-adjust shift based on resolution |

## Batch

| Field | Type | Description |
|-------|------|-------------|
| `batch_count` | int | Number of sequential batches |
| `batch_size` | int | Images per batch |

## Misc

| Field | Type | Description |
|-------|------|-------------|
| `clip_skip` | int | Number of CLIP layers to skip |
| `clip_weight` | float | CLIP text encoder weight |
| `face_restoration` | string | Face restoration model |
| `sharpness` | float | Sharpness applied post-generation |
| `zero_negative_prompt` | bool | Use zero tensor instead of encoded negative prompt |
