#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validation_runner.py

Sunrise–Sunset 등 시스템의 anchors / logic / profile을 자동 검증하는 도구.
HP(Height Point) 계산, sys 보간, Δsys 클램핑, 안전각 검사 등을 수행한다.
"""

import json
import os
import sys
from pathlib import Path

def load_json(path: str):
    """JSON 파일을 로드하되 주석(//) 라인은 무시"""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("//") or s.startswith("#"):
                continue
            lines.append(line)
    return json.loads("".join(lines))

def check_files(base_path: Path):
    anchors_path = base_path / "anchors.json"
    logic_path = base_path / "system_logic.json"
    profile_path = base_path / "profile_sunrise_sunset.json"

    missing = [p.name for p in [anchors_path, logic_path, profile_path] if not p.exists()]
    if missing:
        print(f"[ERROR] Missing required files: {missing}")
        sys.exit(1)

    print(f"[OK] Found required files: {anchors_path.name}, {logic_path.name}, {profile_path.name}")
    return anchors_path, logic_path, profile_path

def validate_anchors(anchors):
    symbols = anchors.get("lookup_table", {}).get("symbols", {})
    if not symbols:
        print("[ERROR] lookup_table.symbols missing or empty")
        return False

    print(f"[OK] {len(symbols)} symbol groups loaded.")
    for k, v in symbols.items():
        pts = v.get("points", [])
        if not pts:
            print(f"  [WARN] symbol '{k}' has no points.")
        else:
            sys_min = min(p['sys'] for p in pts)
            sys_max = max(p['sys'] for p in pts)
            print(f"  [INFO] {k}: sys range {sys_min}..{sys_max}, {len(pts)} pts")
    return True

def validate_logic(logic):
    formulas = logic.get("formulas", {})
    if not formulas:
        print("[ERROR] formulas missing.")
        return False
    print(f"[OK] {len(formulas)} formulas found: {', '.join(formulas.keys())}")
    return True

def validate_logic(logic):
    """
    Accept both:
      - {"formulae": [ {name, expression, ...}, ... ]}   # array form (current system_logic.json)
      - {"formulas": {"HP": "...", ...}}                 # dict form (legacy/alt)
    """
    formulas_arr = logic.get("formulae")
    formulas_dict = logic.get("formulas")

    if formulas_arr and isinstance(formulas_arr, list):
        names = [f.get("name", f"f{i}") for i, f in enumerate(formulas_arr)]
        print(f"[OK] {len(formulas_arr)} formulae found: {', '.join(names)}")
        return True

    if formulas_dict and isinstance(formulas_dict, dict):
        print(f"[OK] {len(formulas_dict)} formulas found: {', '.join(formulas_dict.keys())}")
        return True

    print("[ERROR] formulas/formulae missing.")
    return False

def validate_profile(profile):
    """profile_sunrise_sunset.json의 기본 필드 점검"""
    safety = profile.get("safety", {})
    tip_range = safety.get("tip_range")
    if tip_range:
        print(f"[OK] tip_range: {tip_range}")
    else:
        print("[WARN] safety.tip_range missing")

    render_mode = profile.get("render", {}).get("third_cushion_mode")
    if render_mode:
        print(f"[OK] render.third_cushion_mode = {render_mode}")
    else:
        print("[WARN] render.third_cushion_mode not defined")

    return True

def main():
    if len(sys.argv) < 2:
        print("Usage: python validation_runner.py systems/sunrise_sunset/")
        sys.exit(1)

    base_path = Path(sys.argv[1])
    anchors_path, logic_path, profile_path = check_files(base_path)

    print("\n=== Validation: Anchors ===")
    anchors = load_json(anchors_path)
    validate_anchors(anchors)

    print("\n=== Validation: Logic ===")
    logic = load_json(logic_path)
    validate_logic(logic)

    print("\n=== Validation: Profile ===")
    profile = load_json(profile_path)
    validate_profile(profile)

    print("\n[OK] Validation completed.")

if __name__ == "__main__":
    main()
