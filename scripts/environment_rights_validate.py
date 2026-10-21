"""Expose the native Rights manifest validator through a fixed Environment invocation."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
main = import_module("mncs_rights_provenance.cli").main


if __name__ == "__main__":
    main()
