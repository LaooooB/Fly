from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys

from scipy.sparse import load_npz

EXPECTED_N = 166_700
EXPECTED_NNZ = 25_582_938


def find_weights(root: Path) -> Path:
    direct = root / "weights.npz"
    if direct.exists():
        return direct
    matches = list(root.rglob("weights.npz"))
    if not matches:
        raise FileNotFoundError(f"weights.npz not found under {root}")
    return matches[0]


def main() -> int:
    root = Path(os.environ.get("FLY_DATA", r"J:\FLY\male_cns_data"))
    raw_dir = root / "raw"
    required_raw = {
        "connectome-weights-male-cns-v1.0-minconf-0.5.feather": 1_000_000_000,
        "body-annotations-male-cns-v1.0-minconf-0.5.feather": 10_000_000,
        "body-neurotransmitters-male-cns-v1.0.feather": 40_000_000,
    }
    raw_sizes = {}
    for name, minimum in required_raw.items():
        path = raw_dir / name
        if not path.exists():
            raise FileNotFoundError(f"Official MaleCNS raw source missing: {path}")
        size = path.stat().st_size
        if size < minimum:
            raise RuntimeError(f"Raw source looks incomplete: {path} ({size} bytes)")
        raw_sizes[name] = size

    weights_path = find_weights(root)
    print(f"Verifying: {weights_path}")
    matrix = load_npz(weights_path)
    if matrix.shape != (EXPECTED_N, EXPECTED_N):
        raise RuntimeError(f"Unexpected MaleCNS matrix shape: {matrix.shape}, expected {(EXPECTED_N, EXPECTED_N)}")
    if int(matrix.nnz) != EXPECTED_NNZ:
        raise RuntimeError(f"Unexpected MaleCNS connection count: {matrix.nnz}, expected {EXPECTED_NNZ}")

    marker = {
        "dataset": "MaleCNS v1.0",
        "neuprint_dataset": "male-cns:v1.0",
        "neurons": EXPECTED_N,
        "derived_connections": EXPECTED_NNZ,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
        "build_method": "flybrain 0.1.0 `flybrain build` from official MaleCNS v1.0 release",
        "official_download_page": "https://male-cns.janelia.org/download/",
        "official_bucket": "gs://flyem-male-cns/v1.0/connectome-data/flat-connectome/",
        "weights_file": str(weights_path),
        "official_raw_files": raw_sizes,
    }
    marker_path = root / "OFFICIAL_MALECNS_BUILD_OK.json"
    marker_path.write_text(json.dumps(marker, indent=2), encoding="utf-8")
    print(f"OK: {EXPECTED_N:,} neurons / {EXPECTED_NNZ:,} derived connections")
    print(f"Marker: {marker_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"MaleCNS verification FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
