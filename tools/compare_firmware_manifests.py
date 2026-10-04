"""Compare two Sony firmware module manifests and selected binary markers."""

import argparse
import csv
import json
from pathlib import Path

KEY_FILES = (
    "0700_part_image/dev/nflasha3_unpacked_unpacked/av-cam.bin",
    "0700_part_image/dev/nflasha15_unpacked_unpacked/lib/libObj.so",
    "0700_part_image/dev/nflasha15_unpacked_unpacked/lib/libmprctrl.so",
)
MARKERS = (
    "sa_func_DUALREC_BAYER_acquire",
    "sa_func_DUALREC_BAYER_release",
    "sa_func_DUALREC_BAYER_exit",
    "sa_func_DUALREC_BAYER_start",
    "Stage_DualRec.cpp",
    "Stage_DfeRawTrans",
    "Stage_DfeRawTransSnrBranch",
    "RawHsize",
    "RawHofs",
    "YcHsize",
    "YcVsize",
    "PARAMID_RAW_OUTPUT_MODE",
    "PARAMID_MOVIE_RAW_SIZE",
    "VALUEID_MOVIE_RAW_2K",
    "VALUEID_MOVIE_RAW_4K",
    "AllocDfeMemForDfe2Pass",
    "FreeDfeMemForDfe2Pass",
    "SetSyncParamRawBuffering",
    "ringBufferWrapper RawSize==0",
    "RESOURCE_IMAGER0_STORE_RAW",
    "RESOURCE_IMAGER0_TRANS_RAW",
)


def normalize(path: str) -> str:
    path = path.replace("\\", "/")
    if path.startswith("firmware.tar_unpacked/"):
        path = path[len("firmware.tar_unpacked/"):]
    return path


def load_manifest(path: Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    files = {normalize(item["path"]): item for item in data["files"]}
    return data, files


def marker_counts(root: Path, item: dict | None, rel_path: str):
    if not item:
        return {marker: None for marker in MARKERS}
    raw_path = item["path"].replace("\\", "/")
    if raw_path.startswith("firmware.tar_unpacked/"):
        source = root / raw_path
    else:
        source = root / rel_path
    if not source.is_file():
        return {marker: None for marker in MARKERS}
    data = source.read_bytes()
    return {marker: data.count(marker.encode("ascii")) for marker in MARKERS}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("a6300_manifest", type=Path)
    parser.add_argument("a6500_manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--csv-output", type=Path)
    args = parser.parse_args()

    a6300_meta, a6300 = load_manifest(args.a6300_manifest)
    a6500_meta, a6500 = load_manifest(args.a6500_manifest)
    common = sorted(set(a6300) & set(a6500))
    only_a6300 = sorted(set(a6300) - set(a6500))
    only_a6500 = sorted(set(a6500) - set(a6300))
    identical = [path for path in common if a6300[path].get("sha256") == a6500[path].get("sha256")]
    identical_set = set(identical)
    different = [path for path in common if path not in identical_set]

    key_files = {}
    a6300_root = Path(a6300_meta["root"])
    a6500_root = Path(a6500_meta["root"])
    for path in KEY_FILES:
        key_files[path] = {
            "a6300": a6300.get(path),
            "a6500": a6500.get(path),
            "markers": {
                "a6300": marker_counts(a6300_root, a6300.get(path), path),
                "a6500": marker_counts(a6500_root, a6500.get(path), path),
            },
        }

    result = {
        "schema": "sony-firmware-comparison-v1",
        "inputs": {
            "a6300_manifest": str(args.a6300_manifest),
            "a6500_manifest": str(args.a6500_manifest),
        },
        "counts": {
            "a6300_files": len(a6300),
            "a6500_files": len(a6500),
            "common_paths": len(common),
            "identical_sha256": len(identical),
            "different_sha256": len(different),
            "only_a6300": len(only_a6300),
            "only_a6500": len(only_a6500),
        },
        "identical_paths": identical,
        "different_paths": different,
        "only_a6300_paths": only_a6300,
        "only_a6500_paths": only_a6500,
        "key_files": key_files,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.csv_output:
        args.csv_output.parent.mkdir(parents=True, exist_ok=True)
        with args.csv_output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["path", "status", "a6300_size", "a6500_size", "a6300_sha256", "a6500_sha256"])
            for path in common:
                status = "identical" if path in identical_set else "different"
                writer.writerow([
                    path,
                    status,
                    a6300[path].get("size", ""),
                    a6500[path].get("size", ""),
                    a6300[path].get("sha256", ""),
                    a6500[path].get("sha256", ""),
                ])
            for path in only_a6300:
                writer.writerow([path, "only_a6300", a6300[path].get("size", ""), "", a6300[path].get("sha256", ""), ""])
            for path in only_a6500:
                writer.writerow([path, "only_a6500", "", a6500[path].get("size", ""), "", a6500[path].get("sha256", "")])

    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
