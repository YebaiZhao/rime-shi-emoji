"""Strict local release gate: skipped tests are not a successful full check."""
import argparse
import os
from pathlib import Path
import sys
import unittest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True, help="Isolated compiled Rime probe directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    profile = args.profile.resolve()
    if not (profile / "build/wanxiang.schema.yaml").exists() or not (profile / ".shi-emoji-probe").is_file():
        parser.error("Expected a marked isolated Wanxiang probe made by prepare_wanxiang_probe.py")
    os.environ["RIME_PROBE_USER"] = str(profile)
    os.chdir(root)
    sys.path.insert(0, str(root / "src"))
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(str(root / "tests")))
    if result.skipped:
        print(f"INCOMPLETE: {len(result.skipped)} skipped tests; not release-verified", file=sys.stderr)
    raise SystemExit(0 if result.wasSuccessful() and not result.skipped else 1)


if __name__ == "__main__":
    main()
