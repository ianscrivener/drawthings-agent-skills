#!/usr/bin/env python3
"""generate.py — Text-to-image generation via Draw Things gRPC API.

Usage:
    python scripts/generate.py \\
        --prompt "a golden retriever on a beach at sunset" \\
        --model "jibmix_zit_v1.0_fp16_f16" \\
        --output_dir /tmp

Outputs JSON to stdout: { "success": true, "output": "/absolute/path/to/output.png" }
"""

import argparse
from datetime import datetime
import json
import os
import sys


DEFAULT_UPSCALE_MODEL = "4x_ultrasharp_f16.ckpt"
DEFAULT_FACE_RESTORE_MODEL = "RestoreFormer.pth"
_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", "none", "null"}
_SAMPLER_NAME_TO_ID = {
    "DPMPP2MKarras": 0,
    "EulerA": 1,
    "DDIM": 2,
    "PLMS": 3,
    "DPMPPSDEKarras": 4,
    "UniPC": 5,
    "LCM": 6,
    "EulerASubstep": 7,
    "DPMPPSDESubstep": 8,
    "TCD": 9,
    "EulerATrailing": 10,
    "DPMPPSDETrailing": 11,
    "DPMPP2MAYS": 12,
    "EulerAAYS": 13,
    "DPMPPSDEAYS": 14,
    "DPMPP2MTrailing": 15,
    "DDIMTrailing": 16,
}
_SAMPLER_FALLBACKS = {
    "UniPC": ["DPMPP2MTrailing", "DPMPP2MKarras"],
}


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in _TRUE_VALUES:
        return True
    if lowered in _FALSE_VALUES:
        return False
    raise argparse.ArgumentTypeError(
        "expected one of: true/false, yes/no, on/off, 1/0"
    )


def _resolve_upscaler(value):
    if value is None:
        return None
    lowered = str(value).strip().lower()
    if lowered in _FALSE_VALUES:
        return None
    if lowered in _TRUE_VALUES:
        return DEFAULT_UPSCALE_MODEL
    return value


def _build_output_path(output_dir, file_suffix="png"):
    os.makedirs(output_dir, exist_ok=True)
    suffix = str(file_suffix).lstrip(".") or "png"
    timestamp = datetime.now().strftime("%Y%d%m-%H%M%S")
    output_path = os.path.abspath(os.path.join(output_dir, f"{timestamp}.{suffix}"))
    if not os.path.exists(output_path):
        return output_path

    # Rare same-second collision fallback.
    counter = 1
    while True:
        candidate = os.path.abspath(
            os.path.join(output_dir, f"{timestamp}-{counter:02d}.{suffix}")
        )
        if not os.path.exists(candidate):
            return candidate
        counter += 1


def _is_no_final_image_error(exc):
    msg = str(exc)
    return "Draw Things did not return a decodable final image" in msg

def main():
    parser = argparse.ArgumentParser(description="Generate an image from a text prompt")
    parser.add_argument("--prompt", required=True, help="Positive prompt text")
    parser.add_argument("--negative", default="", help="Negative prompt text")
    parser.add_argument("--model", default="jibmix_zit_v1.0_fp16_f16.ckpt", help="Model filename")
    parser.add_argument("--width", type=int, default=1024, help="Image width (rounded to 64)")
    parser.add_argument("--height", type=int, default=1024, help="Image height (rounded to 64)")
    parser.add_argument("--steps", type=int, default=8, help="steps")
    parser.add_argument("--guidance", type=float, default=1.5, help="CFG guidance scale")
    parser.add_argument(
        "--sampler",
        default="UniPC",
        choices=sorted(_SAMPLER_NAME_TO_ID.keys()),
        help="Sampler type name (gRPC SamplerType).",
    )
    parser.add_argument("--clip_skip", type=int, default=1, help="CLIP skip")
    parser.add_argument("--mask_blur", type=float, default=1.5, help="Mask blur")
    parser.add_argument("--sharpness", type=float, default=3.5, help="Post-generation sharpness")
    parser.add_argument("--shift", type=float, default=2.8, help="Shift parameter")
    parser.add_argument("--seed", type=int, default=-1, help="Seed for reproducibility")
    parser.add_argument(
        "--upscaler",
        nargs="?",
        const=DEFAULT_UPSCALE_MODEL,
        default=None,
        help="Enable upscaling. Accepts true/false or a model name (default model: 4x_ultrasharp_f16.ckpt).",
    )
    parser.add_argument(
        "--upscale-factor",
        type=int,
        default=2,
        help="Upscale factor to use with --upscaler (for example, 2).",
    )
    parser.add_argument(
        "--facefix",
        "--face-restore",
        dest="face_restore",
        nargs="?",
        const=True,
        default=False,
        type=_parse_bool,
        help="Enable face restoration using RestoreFormer.pth. Accepts true/false.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="gRPC timeout in seconds (0 disables timeout)",
    )
    parser.add_argument("--output_dir", default="/tmp", help="Directory to save output image")
    parser.add_argument("--host", default="localhost:7859", help="gRPC server address")
    args = parser.parse_args()

    try:
        from drawthings.service import DTService

        def _progress(info):
            print(json.dumps({"progress": info}), file=sys.stderr, flush=True)

        upscaler_model = _resolve_upscaler(args.upscaler)
        face_restore_model = DEFAULT_FACE_RESTORE_MODEL if args.face_restore else None

        config = {
            "width": args.width,
            "height": args.height,
            "steps": args.steps,
            "sampler": _SAMPLER_NAME_TO_ID[args.sampler],
            "clip_skip": args.clip_skip,
            "mask_blur": args.mask_blur,
            "sharpness": args.sharpness,
            "shift": args.shift,
        }
        if args.model:
            config["model"] = args.model
        if args.seed is not None:
            config["seed"] = args.seed
        if args.guidance is not None:
            config["guidance_scale"] = args.guidance

        svc = DTService(args.host)
        timeout = None if args.timeout <= 0 else args.timeout
        try:
            images = svc.generate(args.prompt, args.negative, config=config,
                          progress_callback=_progress,
                          timeout=timeout,
                          upscaler=upscaler_model,
                          upscaler_scale_factor=args.upscale_factor if upscaler_model else 0,
                          face_restoration=face_restore_model)
        except Exception as first_exc:
            fallback_names = _SAMPLER_FALLBACKS.get(args.sampler, [])
            if not fallback_names or not _is_no_final_image_error(first_exc):
                raise

            images = None
            last_exc = first_exc
            for fallback_name in fallback_names:
                try:
                    retry_config = {**config, "sampler": _SAMPLER_NAME_TO_ID[fallback_name]}
                    print(
                        json.dumps(
                            {
                                "warning": {
                                    "sampler_retry": {
                                        "from": args.sampler,
                                        "to": fallback_name,
                                    }
                                }
                            }
                        ),
                        file=sys.stderr,
                        flush=True,
                    )
                    images = svc.generate(
                        args.prompt,
                        args.negative,
                        config=retry_config,
                        progress_callback=_progress,
                        timeout=timeout,
                        upscaler=upscaler_model,
                        upscaler_scale_factor=args.upscale_factor if upscaler_model else 0,
                        face_restoration=face_restore_model,
                    )
                    break
                except Exception as retry_exc:
                    last_exc = retry_exc

            if images is None:
                raise last_exc

        output_path = _build_output_path(args.output_dir)
        if not images:
            raise Exception("DrawThings did not return any images.")
        images[0].save(output_path)

        print(json.dumps({"success": True, "output": output_path}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
