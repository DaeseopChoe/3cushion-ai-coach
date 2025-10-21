#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validation_runner.py (universal)

Anchors / Logic / Profile 자동 검증 도구.
시스템 폴더 내의 파일명을 자동 감지하여 Sunrise–Sunset, 5_half_system 등
모든 시스템 이름에 대응한다.
"""

import json
import os
import sys
from pathlib import Path


def load_json(path: str):
    """JSON 파일을 로드하되 주석(//, #) 라인은 무시"""
    lines = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s.startswith("//") or s.startswith("#"):
                continue
            lines.append(line)
    return json.loads("".join(lines))


def find_file(base_path: Path, candidates: list[str]):
    """폴더 내에서 후보 이름 중 존재하는 첫 번째 파일 반환"""
    for name in candidates:
        path = base_path / name
        if path.exists():
            return path
    return None


def check_files(base_path: Path):
    """
    anchors, logic, profile 파일 자동 감지.
    - anchors: anchors.json, *_anchors.json
    - logic: system_logic.json, *_logic.json
    - profile: profile_sunrise_sunset.json, profile_*.json
    """
    anchors_path = find_file(base_path, ["anchors.json"] + [p for p in os.listdir(base_path) if p.endswith("_anchors.json")])
    logic_path = find_file(base_path, ["system_logic.json"] + [p for p in os.listdir(base_path) if p.endswith("_logic.json")])
    profile_path = find_file(base_path, ["profile_sunrise_sunset.json"] + [p for p in os.listdir(base_path) if p.startswith("profile_") and p.endswith(".json")])

    missing = []
    if not anchors_path:
        missing.append("anchors.json or *_anchors.json")
    if not logic_path:
        missing.append("system_logic.json or *_logic.json")
    if not profile_path:
        missing.append("profile_sunrise_sunset.json or profile_*.json")

    if missing:
        print(f"[ERROR] Missing required files: {missing}")
        sys.exit(1)

    print(f"[OK] Found files:\n  - Anchors: {anchors_path.name}\n  - Logic: {logic_path.name}\n  - Profile: {profile_path.name}")
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
    """
    formulae / formulas 구조 모두 지원
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
    """profile 파일의 기본 필드 점검"""
    safety = profile.get("safety", {})
    tip_range = safety.get("tip_range")
    if tip_range:
        print(f"[OK] safety.tip_range: {tip_range}")
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
        print("Usage: python validation_runner.py systems/<system_name>/")
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
