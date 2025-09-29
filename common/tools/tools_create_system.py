#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
create_system.py (v1.3 SSOT)
- 새 시스템 스캐폴딩: anchors.json, profile_<system>.json, system_logic.json, README.md
- 정책: 4트랙 직접 입력, lookup_table 공간 제공, profile formula는 REPLACE_ME (예시 자동 유입 금지)

Usage
-----
python repo/common/tools/tools_create_system.py --name 7_system
"""
from __future__ import annotations
import argparse, json, pathlib

INSTRUCTIONS_VERSION = "v1.3"

ANCHORS_TEMPLATE = {
  "lookup_table": {},
  "trajectories": {
    "B2T_L": {"anchors": [], "meta": {}},
    "B2T_R": {"anchors": [], "meta": {}},
    "T2B_R": {"anchors": [], "meta": {}},
    "T2B_L": {"anchors": [], "meta": {}}
  }
}

PROFILE_SKELETON = {
  "system": "REPLACE_ME",
  "formula": "REPLACE_ME",
  "value_domains": {},
  "safety": {
    "offset_fg2rg": 2.25,
    "fg_extension_long": 2.25,
    "fg_extension_short": 2.25,
    "m_min": 0.05,
    "theta_t_max": 68,
    "no_extrapolation": True
  },
  "space_rule": {
    "frame_constants": [-2.25, 42.25, 82.25],
    "tolerance": 0.02,
    "rule": "if x or y matches frame_constants => Fg, else Rg"
  },
  "mappings": None,
  "meta": {"version": "1.0", "generator": "create_system.py", "no_preset_autofill": True}
}

SYSTEM_LOGIC_SKELETON = {
  "track_selection": {"strategy": "ruleset", "tolerance": 0.02, "ruleset": []},
  "required_marks": [],
  "hp_policy": {}
}


def write_text(path: pathlib.Path, content: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding="utf-8")
  print(f"[OK] wrote {path}")


def write_json(path: pathlib.Path, obj) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
  print(f"[OK] wrote {path}")


def main():
  ap = argparse.ArgumentParser()
  ap.add_argument("--name", required=True, help="새 시스템 이름 (예: 7_system)")
  args = ap.parse_args()
  sysname = args.name

  root = pathlib.Path("systems") / sysname
  write_json(root / "anchors.json", ANCHORS_TEMPLATE)
  prof = dict(PROFILE_SKELETON)
  prof["system"] = sysname
  write_json(root / f"profile_{sysname}.json", prof)
  write_json(root / "system_logic.json", SYSTEM_LOGIC_SKELETON)

  readme = f"""# {sysname}\n\n> 스캐폴딩 자동 생성 (규약 {INSTRUCTIONS_VERSION})\n\n## 운영본\n- anchors.json — 4트랙 직접 입력 (lookup_table 포함 권장)\n- system_logic.json — track_selection/required_marks/hp_policy\n- profile_{sysname}.json — formula/value_domains/safety (예시 자동유입 금지)\n\n## 다음 단계\n1) anchors 4트랙 입력 후 `common/tools/anchors_guard.py` 통과\n2) system_logic 규칙/분기 작성\n3) profile 공식을 명시하고 `no_preset_autofill: true` 확인\n4) tests/{sysname}/cases 추가 후 `validation_runner.py` 실행\n"""
  write_text(root / "README.md", readme)

  print(f"\n[DONE] Created boilerplate for system: {sysname}\n - Edit anchors.json (4트랙 직접 입력)\n - Edit system_logic.json (ruleset/required_marks)\n - Edit profile_{sysname}.json (formula/value_domains/safety)\n")


if __name__ == "__main__":
  main()
