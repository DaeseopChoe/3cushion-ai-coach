# 7_system_validation_loop.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7_system_validation_loop.py
- 자동 검증 루프 (7_system용)
"""

import json, math, pathlib
from typing import Dict, Any
from 7_system_simulator import compute_mark, load_json

def validation_loop():
    print("=== Validation: 7_system ===")
    anchors = load_json("7_system_anchors.json")

    test_cases = [
        {"CO": 40, "C3": 20, "expected": 21},
        {"CO": 60, "C3": 33.3, "expected": 20}
    ]

    for case in test_cases:
        res = compute_mark(anchors, case["CO"], case["C3"])
        ok = math.isclose(res["1C_sys"], case["expected"], rel_tol=1e-6)
        print(f"CO={case['CO']}, C3={case['C3']} → 1C_sys={res['1C_sys']} ({'OK' if ok else 'ERR'})")

    print("Validation complete.")

if __name__ == "__main__":
    validation_loop()
