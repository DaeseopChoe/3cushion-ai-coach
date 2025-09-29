#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validation_runner.py (v1.0, common)
- 공용 회귀 러너: 스키마 검사 → 케이스 실행(track_selector) → 요약
- 위치: repo/common/tools/validation_runner.py

Usage examples
--------------
python repo/common/tools/validation_runner.py --systems sunrise_sunset 7_system 5_half_system
python repo/common/tools/validation_runner.py               # systems/* 전부 실행
python repo/common/tools/validation_runner.py --skip-schema # 스키마 검사 생략
python repo/common/tools/validation_runner.py --summary-json out/summary.json

Case format (tests/<system>/cases/*.json)
-----------------------------------------
{
  "name": "B2T_L_boundary_y_bottom_tol",
  "input": { "CO": {"x": 40.0, "y": -2.25}, "C1": {"x": 55.0, "y": -2.25}, "C3": {"x": 20.0, "y": 42.25} },
  "expect": {
    "track": "B2T_L",
    "sys": { "HP_n": 30.0, "tol": 0.2 },
    "guards_ok": true
  }
}
"""
from __future__ import annotations
import argparse, json, sys, subprocess
from pathlib import Path

# ---- Paths ----
HERE = Path(__file__).resolve()
ROOT = HERE.parents[2]           # repo/
COMMON = ROOT / "common"
SCHEMA_DIR = COMMON / "schema"
TOOLS_DIR = COMMON / "tools"
SYSTEMS_DIR = ROOT / "systems"
TESTS_DIR = ROOT / "tests"

# ---- IO helpers ----

def jload(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))

# ---- Schema validation ----

def schema_validate(doc: dict, schema_path: Path, *, name: str) -> None:
    try:
        import jsonschema
    except Exception:
        print("[WARN] jsonschema 미설치: 스키마 검증 생략 (pip install jsonschema)", file=sys.stderr)
        return
    try:
        schema = jload(schema_path)
        jsonschema.validate(doc, schema)
        print(f"[PASS] schema: {name}")
    except Exception as e:
        raise SystemExit(f"[FAIL] schema: {name} → {e}")

# ---- Systems discover ----

def iter_systems(selected: list[str] | None) -> list[str]:
    if selected:
        return selected
    return sorted([p.name for p in SYSTEMS_DIR.iterdir() if p.is_dir()])


def find_paths(system: str) -> tuple[Path, Path, Path]:
    sdir = SYSTEMS_DIR / system
    anchors = sdir / "anchors.json"
    logic   = sdir / "system_logic.json"
    profile = sdir / f"profile_{system}.json"
    return anchors, logic, profile

# ---- Runner ----

def run_track_selector(anchors: Path, logic: Path, profile: Path, case_json: dict) -> dict:
    cmd = [sys.executable, str(TOOLS_DIR / "track_selector.py"),
           "--anchors", str(anchors),
           "--logic", str(logic),
           "--profile", str(profile),
           "--input", "-"]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = proc.communicate(json.dumps(case_json, ensure_ascii=False))
    if proc.returncode != 0:
        raise SystemExit(f"[FAIL] track_selector 오류\nCMD: {' '.join(cmd)}\nSTDERR: {err}\nSTDOUT: {out}")
    try:
        return json.loads(out)
    except json.JSONDecodeError as e:
        raise SystemExit(f"[FAIL] track_selector 출력이 JSON 아님: {out}") from e


def compare_expect(got: dict, expect: dict) -> tuple[bool, str]:
    # 1) track
    if "track" in expect:
        if got.get("track") != expect["track"]:
            return False, f"track mismatch: expected={expect['track']} got={got.get('track')}"
    # 2) sys 수치 비교 (tol 허용)
    if isinstance(expect.get("sys"), dict):
        tol = float(expect["sys"].get("tol", 0.0))
        for k, vexp in expect["sys"].items():
            if k == "tol":
                continue
            vgot = got.get("sys", {}).get(k)
            if vgot is None:
                return False, f"missing sys key: {k}"
            try:
                if abs(float(vgot) - float(vexp)) > tol:
                    return False, f"sys[{k}] diff>{tol}: expected={vexp} got={vgot}"
            except Exception:
                return False, f"non-numeric sys[{k}]: got={vgot}"
    # 3) guards_ok
    if "guards_ok" in expect:
        gok = bool(got.get("guards", {}).get("ok"))
        if gok != bool(expect["guards_ok"]):
            return False, f"guards_ok mismatch: expected={expect['guards_ok']} got={gok}"
    return True, ""


def run_cases_for_system(system: str, anchors: Path, logic: Path, profile: Path) -> tuple[int,int,int,list[dict]]:
    cases_dir = TESTS_DIR / system / "cases"
    files = sorted(cases_dir.glob("*.json"))
    passed = failed = 0
    for_total = len(files)
    failures: list[dict] = []

    if not files:
        print(f"[WARN] {system}: 테스트 케이스 없음 ({cases_dir})")
        return 0, 0, 0, []

    for f in files:
        case = jload(f)
        got = run_track_selector(anchors, logic, profile, case)
        ok, reason = compare_expect(got, case.get("expect", {}))
        if ok:
            print(f"[PASS] {system} :: {f.name}")
            passed += 1
        else:
            print(f"[FAIL] {system} :: {f.name} -> {reason}")
            failed += 1
            failures.append({"system": system, "file": f.name, "reason": reason, "got": got, "expect": case.get("expect")})
    return passed, failed, for_total, failures

# ---- main ----

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--systems", nargs="*", help="테스트할 시스템 (기본: systems/* 전부)")
    ap.add_argument("--skip-schema", action="store_true", help="스키마 검증 생략")
    ap.add_argument("--summary-json", help="요약 JSON 저장 경로")
    args = ap.parse_args()

    totals = {"pass": 0, "fail": 0, "total": 0}
    all_failures: list[dict] = []

    for system in iter_systems(args.systems):
        anchors, logic, profile = find_paths(system)
        if not args.skip_schema:
            if anchors.exists(): schema_validate(jload(anchors), SCHEMA_DIR/"anchors.schema.json", name=f"{system}/anchors.json")
            if logic.exists():   schema_validate(jload(logic),   SCHEMA_DIR/"system_logic.schema.json", name=f"{system}/system_logic.json")
            if profile.exists(): schema_validate(jload(profile), SCHEMA_DIR/"profile.schema.json", name=f"{system}/profile_*.json")
        p, f, n, failures = run_cases_for_system(system, anchors, logic, profile)
        totals["pass"] += p; totals["fail"] += f; totals["total"] += n
        all_failures.extend(failures)

    print(f"\n[SUMMARY] pass={totals['pass']} fail={totals['fail']} total={totals['total']}")
    if args.summary_json:
        out = {**totals, "failures": all_failures}
        Path(args.summary_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.summary_json).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    if totals["fail"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
