#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
track_selector.py (v1.8)
System-agnostic selector + SYS interpolation + formula eval + HP guard
+ tip_policy → 2C/4C 계산(mark_extractor 연동)
"""
from __future__ import annotations
import argparse, json, sys, re
from pathlib import Path
from typing import Dict, Any, Tuple


# ---------- utils ----------
SYMBOL_RX = re.compile(r"\b(?:CO|[1-4]C)_(?:f|r)\b")
TOL = 0.02


def jload(p: str | Path) -> Dict[str, Any]:
return json.loads(Path(p).read_text(encoding="utf-8"))


# ---------- track selection via ruleset ----------


def near(a,b,t=TOL):
try: return abs(float(a)-float(b))<=t
except: return False


def eval_ruleset(ruleset, tol: float, marks: Dict[str, Any]) -> str:
CO = marks.get("CO", {})
C1 = marks.get("C1")
axis = None; side = None
for rule in (ruleset or []):
cond = (rule.get("if") or "").replace(" ", "")
then = rule.get("then")
ok = False
if cond.startswith("CO.y=="):
ok = near(CO.get("y"), float(cond.split("==")[1]))
elif cond.startswith("CO.x=="):
ok = near(CO.get("x"), float(cond.split("==")[1]))
elif cond.startswith("turn(") and cond.endswith(")>0") and C1:
dx = (C1.get("x") or 0) - (CO.get("x") or 0)
ok = dx > 0
if ok:
if then in ("B2T","T2B"): axis = then
elif then in ("L","R"): side = then
if axis and side: return f"{axis}_{side}"
for rule in (ruleset or []):
if rule.get("then") in ("B2T_L","B2T_R","T2B_L","T2B_R"): return rule["then"]
raise SystemExit(json.dumps({"error":"no_track_resolved"}))


# ---------- SYS interpolation via anchors.lookup_table ----------


def interpolate_sys(anchors_doc: Dict[str, Any], marks: Dict[str, Any], formula: str) -> Dict[str, float]:
symbols_tbl = (anchors_doc.get("lookup_table") or {}).get("symbols")
if not isinstance(symbols_tbl, dict):
raise SystemExit(json.dumps({"error":"missing_lookup_table"}))
tokens = list(dict.fromkeys(SYMBOL_RX.findall(formula)))


def mark_name(sym: str) -> str|None:
if sym.startswith("CO"): return "CO"
m = re.match(r"([1-4])C", sym)
return f"C{m.group(1)}" if m else None


def pos_of(mark: Dict[str,Any], axis: str) -> float:
return float(mark.get("x")) if axis=="long" else float(mark.get("y"))


def interp(points, pos: float) -> float:
pts = sorted([{"pos":float(p["pos"]),"sys":float(p["sys"])} for p in points], key=lambda x:x["pos"])
if len(pts)<2: return pts[0]["sys"] if pts else 0.0
if pos<=pts[0]["pos"]: return pts[0]["sys"]
if pos>=pts[-1]["pos"]: return pts[-1]["sys"]
for i in range(len(pts)-1):
p0,p1 = pts[i], pts[i+1]
if p0["pos"]<=pos<=p1["pos"]:
t=(pos-p0["pos"]) / max(1e-12,(p1["pos"]-p0["pos"]))
return p0["sys"] + t*(p1["sys"]-p0["sys"])
return pts[-1]["sys"]


out: Dict[str,float]={}
for sym in tokens:
meta = symbols_tbl.get(sym)
if not meta: raise SystemExit(json.dumps({"error":"symbol_missing_in_lookup","symbol":sym}))
mname = mark_name(sym); mark = marks.get(mname,{})
axis = meta.get("axis"); points = meta.get("points") or []
out[sym] = float(interp(points, pos_of(mark, axis)))
return out


# ---------- formula ----------


def eval_formula(profile: Dict[str, Any], sys_vals: Dict[str, float]):
expr = profile.get("formula") or ""
tokens = SYMBOL_RX.findall(expr)
safe = expr
for t in tokens:
if t not in sys_vals:
raise SystemExit(json.dumps({"error":"symbol_not_provided","symbol":t}))
safe = safe.replace(t, str(sys_vals[t]))
try:
val = eval(safe, {"__builtins__": {}}, {}) if safe else None
except Exception as e:
raise SystemExit(json.dumps({"error":"formula_eval_error","detail":str(e)}))
return (None if val is None else float(val))


# ---------- tip resolution (profile-driven) ----------


def resolve_tips(profile: Dict[str,Any], sys_vals: Dict[str,float], explicit: Dict[str,float]|None=None):
rng = (-4.0, 4.0)
pol = profile.get("tip_policy") or {}
# explicit override
if explicit:
t1 = explicit.get("tip1", pol.get("default",{}).get("tip1",0))
t3 = explicit.get("tip3", pol.get("default",{}).get("tip3",0))
else:
mode = pol.get("mode","fixed")
if mode=="table":
tbl = pol.get("table",{})
main()