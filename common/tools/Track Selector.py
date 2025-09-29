#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
track_selector.py (v1.4, common)
- 공용 트랙 판정 + sys-보간(clamp, TODO: project-specific) + formula 평가
- 입력: --anchors --logic --profile [--input case.json | stdin]
- 출력: { track, sys, guards, debug }

NOTE
----
- interpolate_sys(...)는 각 프로젝트의 lookup_table 포맷에 의존합니다.
  지금은 형상만 점검하고, 실제 보간 규칙은 구현자에게 위임(명확한 실패 메시지 제공).
"""
from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path

SYMBOL_RX = re.compile(r"\b(?:CO|1C|2C|3C|4C)_(?:f|r)\b")

# ---------- IO ----------

def jload(p: str | Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))

# ---------- Guards ----------

def guard_required_marks(required, provided):
    missing = [k for k in required if k not in provided]
    if missing:
        raise SystemExit(json.dumps({"error": "missing_required_marks", "missing": missing}))

# ---------- Track selection (ruleset) ----------

def eval_ruleset(ruleset, tol, marks):
    CO = marks.get("CO", {})
    C1 = marks.get("C1")
    axis = None
    side = None
    def near(a,b): return abs(a-b) <= tol
    for rule in ruleset:
        cond = (rule.get("if") or "").replace(" ", "")
        then = rule.get("then")
        ok = False
        if cond.startswith("CO.y=="):
            ok = near(CO.get("y", 9e9), float(cond.split("==")[1]))
        elif cond.startswith("CO.x=="):
            ok = near(CO.get("x", 9e9), float(cond.split("==")[1]))
        elif cond.startswith("turn(") and cond.endswith(")>0") and C1:
            dx = (C1.get("x") or 0) - (CO.get("x") or 0)
            ok = dx > 0
        if ok:
            if then in ("B2T","T2B"): axis = then
            elif then in ("L","R"): side = then
    if axis and side:
        return f"{axis}_{side}"
    # fallback: explicit track name allowed in rules
    for rule in ruleset:
        if rule.get("then") in ("B2T_L","B2T_R","T2B_L","T2B_R"):
            return rule["then"]
    raise SystemExit(json.dumps({"error": "no_track_resolved"}))

# ---------- Interp (sys domain) ----------

def interpolate_sys(anchors_doc, track: str, marks):
    tr = (anchors_doc.get("trajectories") or {}).get(track)
    if not tr or not tr.get("anchors"):
        raise SystemExit(json.dumps({"error": "no_anchors_for_track", "track": track}))
    # 프로젝트별 포맷이 정해지기 전까지는 명확한 에러로 실패시킵니다.
    if "lookup_table" not in anchors_doc:
        raise SystemExit(json.dumps({"error": "missing_lookup_table", "hint": "anchors.json에 lookup_table(좌표↔sys 보간 근거)을 정의하세요."}))
    # TODO: anchors_doc["lookup_table"][track] 구조에 맞춘 선형보간 + clamp 구현
    raise SystemExit(json.dumps({"error": "interp_not_implemented", "hint": "lookup_table 포맷이 확정되면 보간식을 구현하세요."}))

# ---------- Formula ----------

def eval_formula(profile, sys_vals):
    expr = profile["formula"]["expr"] if isinstance(profile.get("formula"), dict) else profile.get("formula", "")
    if not expr:
        raise SystemExit(json.dumps({"error": "no_formula"}))
    tokens = SYMBOL_RX.findall(expr)
    for t in tokens:
        if t not in sys_vals:
            raise SystemExit(json.dumps({"error": "symbol_not_provided", "symbol": t}))
    safe = expr
    for t in tokens:
        safe = safe.replace(t, str(sys_vals[t]))
    try:
        val = eval(safe, {"__builtins__": {}}, {})
    except Exception as e:
        raise SystemExit(json.dumps({"error": "formula_eval_error", "detail": str(e)}))
    return {"HP_n": float(val)}

# ---------- Main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", required=True)
    ap.add_argument("--logic", required=True)
    ap.add_argument("--profile", required=True)
    ap.add_argument("--input", help="case json path; omit to read stdin")
    args = ap.parse_args()

    anchors = jload(args.anchors)
    logic = jload(args.logic)
    profile = jload(args.profile)
    case = jload(args.input) if args.input else json.loads(sys.stdin.read())

    marks = case.get("input", {})
    required = logic.get("required_marks", [])
    guard_required_marks(required, marks)

    ts = logic.get("track_selection", {})
    tol = ts.get("tolerance", 0.02)
    if ts.get("strategy") == "ruleset":
        track = eval_ruleset(ts.get("ruleset", []), tol, marks)
    else:
        raise SystemExit(json.dumps({"error": "unsupported_strategy"}))

    sys_vals = interpolate_sys(anchors, track, marks)
    out = eval_formula(profile, sys_vals)

    print(json.dumps({"track": track, "sys": out, "guards": {"ok": True}}, ensure_ascii=False))

if __name__ == "__main__":
    main()
