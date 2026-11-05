#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compatibility wrapper: single-profile MU1440 test package via build_modular.py.

Equivalent to ``build_modular.py --profiles skoda-mu1440-p4526 --scope single-profile``.
The distribution is the three-profile package; use build_modular.py for it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_modular  # noqa: E402

if __name__ == "__main__":
    build_modular.main(sys.argv[1:], default_profiles=["skoda-mu1440-p4526"],
                       default_scope=build_modular.SCOPE_VALUE)
