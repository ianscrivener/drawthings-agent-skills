#!/usr/bin/env python3
"""list_assets.py — List available assets, samplers, and metadata.

Usage:
    python src/drawthings/list_assets.py
    python src/drawthings/list_assets.py --host localhost:7859
    python src/drawthings/list_assets.py --tls true --compression false
    python src/drawthings/list_assets.py --type models    # upscalers | control_nets | loras | textual_inversions | samplers

Outputs JSON to stdout.
"""

import argparse
import json
import sys

import grpc


VALID_TYPES = ("models", "loras", "control_nets", "upscalers", "textual_inversions", "samplers")

# Samplers excluded due to poor quality / compatibility across models
BLOCKED_SAMPLERS = {"DPMPP2MKarras", "PLMS", "LCM", "DPMPPSDESubstep", "TCD"}


def _parse_bool_arg(value):
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError("expected true|false")


def _item_label(item):
    if isinstance(item, dict):
        for key in ("file", "filename", "name", "api_name", "id"):
            value = item.get(key)
            if value:
                return value
        return item
    return item


def _is_blocked_sampler(item):
    if isinstance(item, dict):
        api_name = item.get("api_name")
        return api_name in BLOCKED_SAMPLERS
    if isinstance(item, str):
        return item in BLOCKED_SAMPLERS
    return False


def _format_rpc_error(exc):
    code = exc.code()
    details = exc.details() or str(exc)
    lowered = details.lower()

    if code == grpc.StatusCode.UNAVAILABLE:
        if "socket closed" in lowered or "endpoint closing" in lowered:
            return (
                "Draw Things responded on the port but rejected the gRPC request. "
                "Check API Server settings and CLI flags: "
                "Protocol=gRPC, --tls true, --compression false. "
                f"Details: {details}"
            )
        if "connection refused" in lowered or "failed to connect" in lowered:
            return (
                "Could not connect to Draw Things gRPC server. "
                "Verify the app is running and --host is correct. "
                f"Details: {details}"
            )

    return f"gRPC {code.name}: {details}"


def main():
    parser = argparse.ArgumentParser(description="List available assets on Draw Things server")
    parser.add_argument("--host", default="localhost:7859", help="gRPC server address")
    parser.add_argument(
        "--tls",
        type=_parse_bool_arg,
        default=True,
        help="Use TLS for gRPC connection (true|false)",
    )
    parser.add_argument(
        "--compression",
        type=_parse_bool_arg,
        default=False,
        help="Enable gRPC gzip compression (true|false)",
    )
    parser.add_argument("--type", default=None, choices=VALID_TYPES,
                        help="Filter to a single asset type")
    args = parser.parse_args()

    try:
        from drawthings.service import DTService

        svc = DTService(
            args.host,
            use_tls=args.tls,
            use_compression=args.compression,
        )
        data = svc.list_assets()

        # Extract just filenames for the summary view
        result = {}
        for key in VALID_TYPES:
            items = data.get(key, [])
            if key == "samplers":
                items = [item for item in items if not _is_blocked_sampler(item)]
            result[key] = [_item_label(item) for item in items]

        if args.type:
            print(json.dumps({"success": True, "type": args.type, "items": result[args.type]}))
        else:
            print(json.dumps({"success": True, **result}))
    except grpc.RpcError as e:
        print(json.dumps({"success": False, "error": _format_rpc_error(e)}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
