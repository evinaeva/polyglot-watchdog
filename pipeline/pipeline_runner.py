"""Legacy pipeline runner retired in favor of canonical phase execution paths.

TEMP_COMPAT: retained as a bounded shim during PW-BL-001.
Removal condition: delete this module in PW-BL-017 once external callers are migrated.
"""

from __future__ import annotations

import sys


def main() -> None:
    raise SystemExit(
        "pipeline/pipeline_runner.py is retired. Use pipeline/run_phase0.py, "
        "pipeline/run_phase1.py, pipeline/run_phase2.py, pipeline/run_phase3.py, "
        "and pipeline/run_phase6.py via the canonical flow."
    )


if __name__ == "__main__":
    main()
