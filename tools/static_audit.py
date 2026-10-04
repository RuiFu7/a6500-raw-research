#!/usr/bin/env python3
"""Build a conservative, reproducible static audit of the alpha6500 RAW path."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path


KEY_NAMES = {
    "avcam": "av-cam.bin",
    "dmm": "dmm.ko",
    "dmac": "dmac.ko",
    "libobj": "libObj.so",
    "libmpr": "libmpr.so",
    "scenario": "CAMERA_SCN_EXTERNAL_RAW_RECORD.so",
    "stream2": "stream2.ko",
}

GHIDRA_FILES = {
    "raw_unit": "ghidra_avcam_rawunit_func.txt",
    "raw_mem": "ghidra_avcam_rawmem_func.txt",
    "dfe_alloc": "ghidra_avcam_dfe_alloc_funcs.txt",
    "dfe_resources": "ghidra_avcam_dfe_res_alloc.txt",
    "dfe_raw_xrefs": "ghidra_dfe_raw_xrefs.tsv",
    "stream2_funcs": "ghidra_mpr_stream2_funcs.txt",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def find_named(root: Path, name: str) -> Path:
    candidates = [p for p in root.rglob(name) if p.is_file()]
    preferred = [p for p in candidates if "ilce6500-v106" in p.as_posix().lower()]
    if preferred:
        return sorted(preferred)[0]
    if not candidates:
        raise FileNotFoundError(name)
    return sorted(candidates)[0]


def parse_ghidra_blocks(path: Path) -> dict[str, dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    starts = list(re.finditer(r"^ADDRESS\s+([0-9a-fA-F]+)\s*$", text, re.M))
    result = {}
    for i, match in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        block = text[match.start():end]
        address = match.group(1).lower()
        fn = re.search(r"^FUNCTION\s+(\S+)\s+entry=([0-9a-fA-F]+)", block, re.M)
        callers = [
            {"from": a.lower(), "to": b.lower(), "type": c.strip()}
            for a, b, c in re.findall(
                r"^\s+From:\s+([0-9a-fA-F]+)\s+To:\s+([0-9a-fA-F]+)\s+Type:\s+([^\n]+)",
                block,
                re.M,
            )
        ]
        calls = [
            value.lower()
            for _, value in re.findall(r"\b(?:bl|blx)\s+(0x)?([0-9a-fA-F]+)", block)
        ]
        result[address] = {
            "address": address,
            "function": fn.group(1) if fn else None,
            "entry": fn.group(2).lower() if fn else address,
            "callers": callers,
            "direct_call_targets": sorted(set(calls)),
            "text": block,
        }
    return result


def get_block(blocks: dict[str, dict], address: str) -> dict:
    key = address.lower().removeprefix("0x")
    if key not in blocks:
        raise KeyError(f"Ghidra block {address} not found")
    return blocks[key]


def marker_counts(path: Path, markers: list[str]) -> dict[str, int]:
    data = path.read_bytes()
    return {marker: data.count(marker.encode("ascii")) for marker in markers}


def static_relation_rows(blocks: dict[str, dict]) -> list[dict]:
    raw_mem = get_block(blocks, "002c2088")
    dfe_alloc = get_block(blocks, "005a2618")
    return [
        {
            "id": "raw-unit-selector",
            "component": "RAW unit selector",
            "statement": "FUN_002c1ab0 branches on param+0x1f0 and returns 0x236, 0x1df, 0x23e, or 0x2b3 under different states.",
            "source": "firmware/manifests/ghidra_avcam_rawunit_func.txt:002c1ab0",
            "evidence": "Thumb listing contains cmp #0xa/#0x1b/#0x9 and movw returns #0x236/#0x1df/#0x23e/#0x2b3.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The function name and unit type do not identify pixel format or producer by themselves.",
        },
        {
            "id": "raw-memory-manager",
            "component": "RAW memory manager",
            "statement": "FUN_002c2088 calls the selector, then DMM allocation helpers 0x006a7d6a or 0x006a7c84, and stores a handle plus unit/extent metadata in the owning object.",
            "source": "firmware/manifests/ghidra_avcam_rawmem_func.txt:002c2088",
            "evidence": "Calls at 002c20ba, 002c2104/002c2118; stores at +0x5208, +0x5594, +0x5598, +0x559c, +0x55a0.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The stored extent is not statically proven to be a sensor pixel plane.",
        },
        {
            "id": "raw-memory-callers",
            "component": "RAW memory manager callers",
            "statement": "The exported Ghidra call graph has three direct callers of FUN_002c2088: 0x006b751c, 0x006b6b86, and 0x002cfb22.",
            "source": "firmware/manifests/ghidra_avcam_rawmem_func.txt:CALLERS",
            "evidence": "; ".join(f"{x['from']} -> {x['to']}" for x in raw_mem["callers"]),
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "Caller names and their complete mode semantics still require function-level exports.",
        },
        {
            "id": "dfe-2pass-request",
            "component": "DFE 2-pass allocation",
            "statement": "FUN_005a2618 conditionally sends a DMM request with literal unit value 0x324 and records a handle/state slot.",
            "source": "firmware/manifests/ghidra_avcam_dfe_alloc_funcs.txt:005a2618",
            "evidence": "005a269c movs r3,#5; 005a269e movs r1,#1; 005a26a0 stores 5; 005a26a2 mov.w r0,#0x324; 005a26aa bl 0x002e7300.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "0x324 is a DMM request value; its actual buffer contents and pixel role are not proven.",
        },
        {
            "id": "dfe-2pass-callers",
            "component": "DFE 2-pass callers",
            "statement": "FUN_005a2618 has direct callers at 0x002718ba, 0x00271964, and 0x002a6d9a.",
            "source": "firmware/manifests/ghidra_avcam_dfe_alloc_funcs.txt:CALLERS",
            "evidence": "; ".join(f"{x['from']} -> {x['to']}" for x in dfe_alloc["callers"]),
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The call sites show resource setup but do not prove continuous movie RAW output.",
        },
        {
            "id": "external-raw-delegation",
            "component": "External RAW scenario",
            "statement": "CAMERA_SCN_EXTERNAL_RAW_RECORD.so creates 0x14-byte OSAL messages and delegates output/acquire/release actions to the AV message system.",
            "source": "scenario/CAMERA_SCN_EXTERNAL_RAW_RECORD.so symbols and disassembly",
            "evidence": "raw_output_on/off/device_acquire/device_release all tail-call raw_output_common; imports are OSAL message functions and memset, with no open/write/ioctl imports.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "Absence of direct file/device imports does not rule out a downstream AV task performing I/O.",
        },
        {
            "id": "stream2-map",
            "component": "stream2 mapping",
            "statement": "libmpr/stream2 contain a physical-range registration plus mmap path using ioctl 0xC0047805 and {phys,size} entries.",
            "source": "firmware/manifests/ghidra_mpr_stream2_funcs.txt; ghidra_mpr_stream2_open.txt",
            "evidence": "FUN_006c7424 calls ioctl then mmap; FUN_006c7e7c opens /dev/stream2; stream2.ko export maps registered extents.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "This is a generic mapping facility; no static proof links it to a RAW pixel producer.",
        },
        {
            "id": "runtime-1df-negative",
            "component": "Runtime candidate 0x1df",
            "statement": "The prior runtime captures establish allocation/readback of a transient 0x1df region but do not establish Bayer pixels; the control captures were fixed or highly patterned.",
            "source": "docs/18_runtime_raw_1df.md; docs/19_runtime_raw_controls.md",
            "evidence": "Multiple 16 MiB captures were byte-identical; another contained a strong 0x5555 pattern; no valid debayered scene was obtained.",
            "level": "confirmed",
            "reproducible": "partial",
            "limits": "This rejects the tested capture interpretation, not every possible RAW buffer or offset.",
        },
        {
            "id": "dfe-stage-descriptor-flow",
            "component": "DFE RAW transfer stage",
            "statement": "FUN_0028d388 consumes the RAW manager context fields +0x5594/+0x5598/+0x559c/+0x55a0, packs them into DAT_000020f0..DAT_000020fc, and calls FUN_006859ec.",
            "source": "analysis_out/ghidra_raw_stage_funcs_full_20260905.txt:0028d388",
            "evidence": "Decompilation shows the four context-field loads and four stores before FUN_006859ec; direct callers are 0x006a43d8 and 0x006a4502.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The field semantics and final DMA/consumer are not identified by this function alone.",
        },    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--output-tsv", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    out_json = args.output_json or root / "analysis_out" / "static_audit_20260906.json"
    out_tsv = args.output_tsv or root / "docs" / "evidence_ledger.tsv"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_tsv.parent.mkdir(parents=True, exist_ok=True)

    paths = {key: find_named(root, name) for key, name in KEY_NAMES.items()}
    manifest_dir = root / "firmware" / "manifests"
    ghidra = {}
    for key, filename in GHIDRA_FILES.items():
        path = manifest_dir / filename
        if path.exists():
            ghidra[key] = {
                "path": rel(path, root),
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }

    blocks = {}
    for key in ("raw_unit", "raw_mem", "dfe_alloc", "dfe_resources"):
        blocks.update(parse_ghidra_blocks(manifest_dir / GHIDRA_FILES[key]))

    markers = [
        "AllocDfeMemForDfe2Pass",
        "SetSyncParamRawBuffering",
        "ringBufferWrapper",
        "RESOURCE_IMAGER0_STORE_RAW",
        "RESOURCE_IMAGER0_TRANS_RAW",
        "Stage_DfeRawTrans",
        "Stage_DfeRawTransSnrBranch",
        "p_raw_out_dmm_info",
        "dmm_info_raw",
        "sa_func_DUALREC_BAYER_start",
        "PARAMID_RAW_OUTPUT_MODE",
        "PARAMID_MOVIE_RAW_SIZE",
    ]
    ledger_rows = static_relation_rows(blocks) + [
        {
            "id": "artifact-avcam",
            "component": "alpha6500 V1.06 artifact",
            "statement": "alpha6500 av-cam.bin is present and hashed for this audit.",
            "source": rel(paths["avcam"], root),
            "evidence": f"size={paths['avcam'].stat().st_size}; sha256={sha256(paths['avcam'])}",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "Hash proves identity, not behavior.",
        },
        {
            "id": "dfe-descriptor-helpers",
            "component": "DFE RAW descriptor helpers",
            "statement": "FUN_006859ec copies descriptor fields, while FUN_006a686a/FUN_006a687e set/get four fields used by the DFE transfer stage.",
            "source": "analysis_out/avcam_descriptor_copy_setters_20260905.txt",
            "evidence": "The copy function moves offsets +0x60/+0x68..+0x78; the setter writes object +0x250/+0x254/+0x258/+0x25c and the getter reads them back.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "These are descriptor operations; no DMA kick or final consumer is identified.",
        },
        {
            "id": "dfe-stage-dispatchers",
            "component": "Stage_DfeRawTrans dispatcher",
            "statement": "FUN_006a4394 reads param+0x23 as an event key; FUN_006a43b2 case 1 and FUN_006a44a0 case 5 both invoke FUN_0028d388.",
            "source": "analysis_out/ghidra_stage_consumer_funcs_20260906.txt; analysis_out/ghidra_dispatch_enum_20260906.txt",
            "evidence": "FUN_006a4394 returns *(param+0x23); dispatcher decompilations contain switch cases that call FUN_0028d388.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The event key has not been mapped to a camera mode or user action.",
        },
        {
            "id": "dfe-buffer-size-calc",
            "component": "DFE buffer size calculation",
            "statement": "FUN_00296884 calls a size getter, scales the returned value by 6 or 8, aligns to 0x80, and stores the result in context+0x5594 or context+0x5584.",
            "source": "analysis_out/avcam_internal_handlers_20260906.txt; analysis_out/avcam_size_helpers_20260906.txt",
            "evidence": "Instructions at 0x00296964 call 0x0068281e, multiply by r7, then call align helper 0x00683038 before storing the aligned result.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The 6/8 multiplier has not been proven to be bit depth, bytes per pixel, channel count, or a frame-size unit.",
        },
        {
            "id": "dfe-descriptor-submission",
            "component": "DFE descriptor submission",
            "statement": "FUN_00298b34 builds a small transfer structure that includes context+0x724, flags, metadata, and a mode value, then calls FUN_00743b52.",
            "source": "analysis_out/avcam_internal_handlers_20260906.txt",
            "evidence": "Assembly writes fields at r5+0x00/+0x04/+0x05/+0x08/+0x0c/+0x10/+0x14 and branches into 0x00743b52.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "Whether 0x00743b52 performs MMIO, DMA kick, DFE command dispatch, or software queuing remains unconfirmed.",
        },
        {
            "id": "dfe-api-boundary",
            "component": "DFE API boundary",
            "statement": "FUN_00743b52 forwards to FUN_00743f54, which builds a 0x30-byte parameter structure and calls high-level helper FUN_001dd460; no direct MMIO or DMA kick appears at this boundary.",
            "source": "analysis_out/avcam_dfe_submit_20260906.txt; analysis_out/avcam_dfe_core_api_20260906.txt; analysis_out/avcam_object_api_20260906.txt",
            "evidence": "00743b52 tail-calls 00743f54; 00743f54 constructs a 0x30-byte stack object and calls 001dd460, which invokes object helpers and performs float ratio calculations.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The final consumer and hardware target remain unconfirmed.",
        },
        {
            "id": "dfe-object-registry",
            "component": "DFE object registry API",
            "statement": "FUN_001df4f4 walks a global object table and calls FUN_00690324 to find a resource; FUN_001dceb0 returns zero-filled runtime slots, reinforcing that the path is object/API-level rather than direct hardware access.",
            "source": "analysis_out/avcam_api_expanded_20260906.txt; analysis_out/avcam_literal_map_20260906.txt",
            "evidence": "FUN_001df4f4 scans 0x5c bytes in 4-byte steps; resolved branch targets in FUN_001dceb0 point to zero-filled BSS/runtime slots.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The downstream handler may still reach hardware through a later callback; this only excludes the immediate layer.",
        },
        {
            "id": "dmm-unit-table",
            "component": "DMM unit table",
            "statement": "dmm.ko uses a 0x188-byte unit table, with handle low 10 bits and fields at +0x618/+0x620/+0x621/+0x623/+0x628/+0x62c; dmm_unit_ctrl_GetUnitInfo and dmm_unit_ctrl_Open expose unit and extent metadata.",
            "source": "analysis_out/dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt; analysis_out/dmm_dmm_unit_ctrl_Open_20260906.txt",
            "evidence": "ET_REL symbol names and disassembly show unit table strides, write offsets, extent loop, and paired output fields.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The paired fields are highly likely physical address and size, but are not proven by symbol names alone.",
        },
        {
            "id": "dmac-hardware-layer",
            "component": "XDMAC hardware layer",
            "statement": "dmac.ko exports XDMAC register/descriptor functions including boss_hw_dmac_start_transfer, boss_hw_dmac_start_wait, and boss_hw_dmac_proc_setbuf_reg_ch.",
            "source": "analysis_out/dmac_start_transfer_20260906.txt; analysis_out/dmac_start_wait_20260906.txt; analysis_out/dmac_setbuf_ch_20260906.txt",
            "evidence": "Disassembly shows six 32-bit writes into a register region, dsb barriers, command 0x11 at +0x1c, and channel register writes.",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "The exact six-register descriptor semantics and whether this path is used by Stage_DfeRawTrans remain unconfirmed.",
        },
        {
            "id": "dmm-dmac-link-unconfirmed",
            "component": "DMM to XDMAC link",
            "statement": "DMM physical extent management and XDMAC hardware programming exist in the same firmware, but no direct call graph connects Stage_DfeRawTrans to dmac_ioctl or boss_hw_dmac_start_transfer.",
            "source": "docs/24_kernel_driver_audit_20260906.md",
            "evidence": "Driver symbol analysis confirms both layers; the application-side Stage entry ends in a soft DFE/object API before a hardware driver call.",
            "level": "unconfirmed",
            "reproducible": "yes",
            "limits": "This is the central unresolved link before claiming a DMA RAW pathway.",
        },
        {
            "id": "artifact-scenario",
            "component": "RAW scenario artifact",
            "statement": "The external RAW scenario is an ARM ELF with named on/off/acquire/release functions.",
            "source": rel(paths["scenario"], root),
            "evidence": f"size={paths['scenario'].stat().st_size}; sha256={sha256(paths['scenario'])}",
            "level": "confirmed",
            "reproducible": "yes",
            "limits": "Named functions do not prove a usable movie RAW stream.",
        },
    ]

    result = {
        "schema": 1,
        "root": str(root),
        "generated": "2026-09-06",
        "artifacts": {
            key: {
                "path": rel(path, root),
                "size": path.stat().st_size,
                "sha256": sha256(path),
            }
            for key, path in paths.items()
        },
        "ghidra_exports": ghidra,
        "analysis_outputs": {
            "stage_xrefs": {
                "path": "analysis_out/ghidra_raw_stage_xrefs_20260905.tsv",
                "sha256": sha256(root / "analysis_out" / "ghidra_raw_stage_xrefs_20260905.tsv") if (root / "analysis_out" / "ghidra_raw_stage_xrefs_20260905.tsv").exists() else None,
            },
            "stage_functions": {
                "path": "analysis_out/ghidra_raw_stage_funcs_full_20260905.txt",
                "sha256": sha256(root / "analysis_out" / "ghidra_raw_stage_funcs_full_20260905.txt") if (root / "analysis_out" / "ghidra_raw_stage_funcs_full_20260905.txt").exists() else None,
            },
            "descriptor_helpers": {
                "path": "analysis_out/avcam_descriptor_copy_setters_20260905.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_descriptor_copy_setters_20260905.txt") if (root / "analysis_out" / "avcam_descriptor_copy_setters_20260905.txt").exists() else None,
            },
            "stage_consumer": {
                "path": "analysis_out/ghidra_stage_consumer_funcs_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "ghidra_stage_consumer_funcs_20260906.txt") if (root / "analysis_out" / "ghidra_stage_consumer_funcs_20260906.txt").exists() else None,
            },
            "dispatch_enum": {
                "path": "analysis_out/ghidra_dispatch_enum_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "ghidra_dispatch_enum_20260906.txt") if (root / "analysis_out" / "ghidra_dispatch_enum_20260906.txt").exists() else None,
            },
            "internal_handlers": {
                "path": "analysis_out/avcam_internal_handlers_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_internal_handlers_20260906.txt") if (root / "analysis_out" / "avcam_internal_handlers_20260906.txt").exists() else None,
            },
            "size_helpers": {
                "path": "analysis_out/avcam_size_helpers_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_size_helpers_20260906.txt") if (root / "analysis_out" / "avcam_size_helpers_20260906.txt").exists() else None,
            },
            "size_getter": {
                "path": "analysis_out/avcam_size_getter_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_size_getter_20260906.txt") if (root / "analysis_out" / "avcam_size_getter_20260906.txt").exists() else None,
            },
            "dfe_submit": {
                "path": "analysis_out/avcam_dfe_submit_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_dfe_submit_20260906.txt") if (root / "analysis_out" / "avcam_dfe_submit_20260906.txt").exists() else None,
            },
            "dfe_core_api": {
                "path": "analysis_out/avcam_dfe_core_api_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_dfe_core_api_20260906.txt") if (root / "analysis_out" / "avcam_dfe_core_api_20260906.txt").exists() else None,
            },
            "object_api": {
                "path": "analysis_out/avcam_object_api_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_object_api_20260906.txt") if (root / "analysis_out" / "avcam_object_api_20260906.txt").exists() else None,
            },
            "api_expanded": {
                "path": "analysis_out/avcam_api_expanded_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_api_expanded_20260906.txt") if (root / "analysis_out" / "avcam_api_expanded_20260906.txt").exists() else None,
            },
            "literal_map": {
                "path": "analysis_out/avcam_literal_map_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "avcam_literal_map_20260906.txt") if (root / "analysis_out" / "avcam_literal_map_20260906.txt").exists() else None,
            },
            "dmm_unit_info": {
                "path": "analysis_out/dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt") if (root / "analysis_out" / "dmm_dmm_unit_ctrl_GetUnitInfo_20260906.txt").exists() else None,
            },
            "dmm_open": {
                "path": "analysis_out/dmm_dmm_unit_ctrl_Open_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "dmm_dmm_unit_ctrl_Open_20260906.txt") if (root / "analysis_out" / "dmm_dmm_unit_ctrl_Open_20260906.txt").exists() else None,
            },
            "dmac_start_transfer": {
                "path": "analysis_out/dmac_start_transfer_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "dmac_start_transfer_20260906.txt") if (root / "analysis_out" / "dmac_start_transfer_20260906.txt").exists() else None,
            },
            "dmac_ioctl": {
                "path": "analysis_out/dmac_ioctl_20260906.txt",
                "sha256": sha256(root / "analysis_out" / "dmac_ioctl_20260906.txt") if (root / "analysis_out" / "dmac_ioctl_20260906.txt").exists() else None,
            },
        },
        "avcam_marker_counts": marker_counts(paths["avcam"], markers),
        "libobj_marker_counts": marker_counts(paths["libobj"], ["PARAMID_RAW_OUTPUT_MODE", "PARAMID_MOVIE_RAW_SIZE", "MSGID_SET_MOVIE_FORMAT"]),
        "raw_unit_selector": get_block(blocks, "002c1ab0"),
        "raw_memory_manager": get_block(blocks, "002c2088"),
        "dfe_2pass_allocator": get_block(blocks, "005a2618"),
        "dmm_request_builder": get_block(blocks, "002e7300"),
        "ledger": ledger_rows,
    }
    for key in ("raw_unit_selector", "raw_memory_manager", "dfe_2pass_allocator", "dmm_request_builder"):
        result[key].pop("text", None)
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["id", "component", "statement", "source", "evidence", "level", "reproducible", "limits"]
    with out_tsv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(ledger_rows)
    print(json.dumps({"json": str(out_json), "tsv": str(out_tsv), "rows": len(ledger_rows)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
