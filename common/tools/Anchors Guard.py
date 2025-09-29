#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchors_guard.py (v1.3)
- anchors.json 정합성 가드 (스키마 + 라벨 상수선 + 기본 규칙)
- 정책 반영: 4트랙 직접 입력, generated_from/ops는 optional, sys-only 계산 원칙

Checks
------
1) JSON Schema 적합성 (있으면 jsonschema 사용)
2) 각 트랙 anchors[].id 라벨 형식 검사: <ID>_(x,y)_<sys>
3) 상수선 정렬 검사(Fg 기준): y ∈ {-2.25, 42.25} 또는 x ∈ {-2.25, 82.25} (tol=0.02)
4) 빈 트랙 금지: trajectories.<track>.anchors 최소 1개
5) lookup_table 존재 시 object 타입 확인(보간 근거용)

Exit codes
----------
0: OK / 1: FAIL
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]  # repo/
SCHEMA = ROOT / "common" / "schema" / "anchors.schema.json"

LABEL_RX = re.compile(r"^([A-Z0-9]+)_\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)_([-+]?\d+(?:\.\d+)?)$")
FG_CONSTS = {-2.25, 42.25, -2.25 + 84.5, 82.25}  # guard: include computed? keep explicit below
TOL = 0.02

FG_Y_CONSTS = (-2.25, 42.25)
FG_X_CONSTS = (-2.25, 82.25)


def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def near(a: float, b: float, tol: float = TOL) -> bool:
    return abs(a - b) <= tol


def validate_schema(doc: dict) -> list[str]:
    try:
        import jsonschema
    except Exception:
        return ["[WARN] jsonschema 미설치: 스키마 검증 생략 (pip install jsonschema)"]
    try:
        schema = jload(SCHEMA)
        jsonschema.validate(doc, schema)
        return ["[PASS] schema: anchors.json"]
    except Exception as e:
        return [f"[FAIL] schema: anchors.json → {e}"]


def parse_label(s: str):
    m = LABEL_RX.match(s.strip())
    if not m:
        raise ValueError(f"bad label: {s}")
    ID, xs, ys, ns = m.groups()
    return ID, float(xs), float(ys), float(ns)


def check_constant_line(x: float, y: float) -> bool:
    # 라벨은 레일 상의 점이어야 하므로 Fg 상수선 중 하나에 근접해야 함
    return any((near(y, c) for c in FG_Y_CONSTS)) or any((near(x, c) for c in FG_X_CONSTS))


def guard(anchors_path: Path) -> int:
    errors: list[str] = []
    warns: list[str] = []

    doc = jload(anchors_path)

    # 1) schema
    warns += validate_schema(doc)

    # 2) structure
    trajs = (doc.get("trajectories") or {})
    for track in ("B2T_L", "B2T_R", "T2B_R", "T2B_L"):
        block = trajs.get(track)
        if not isinstance(block, dict):
            errors.append(f"missing track block: {track}")
            continue
        anchors = block.get("anchors")
        if not isinstance(anchors, list) or len(anchors) == 0:
            errors.append(f"{track}: anchors[] empty")
            continue
        for item in anchors:
            if not isinstance(item, dict) or "id" not in item:
                errors.append(f"{track}: anchor entry must be object with 'id'")
                continue
            try:
                ID, x, y, n = parse_label(item["id"])
            except Exception as e:
                errors.append(f"{track}: {e}")
                continue
            if not check_constant_line(x, y):
                errors.append(f"{track}: label not on frame constant line (x={x}, y={y})")

    # 3) lookup_table (선택)
    if "lookup_table" in doc and not isinstance(doc["lookup_table"], dict):
        errors.append("lookup_table must be an object (mapping table for sys<->coord)")

    # report
    for w in warns:
        print(w, file=sys.stderr if w.startswith("[WARN]") else sys.stdout)
    if errors:
        print("[FAIL] anchors guard")
        for e in errors:
            print(" -", e)
        return 1
    print("[OK] anchors guard passed")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True, help="systems/<system>/anchors.json")
    args = ap.parse_args()
    sys.exit(guard(Path(args.anchors)))

if __name__ == "__main__":
    main()
