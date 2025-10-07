#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_lookup_from_anchors.py (merge version)
- anchors.json 의 라벨( ID_(x,y)_n )에서 lookup_table.symbols.*.points 를 추출해 **병합**합니다.
- 기존 points 는 보존하고, 새로 발견된 pos 는 추가(중복 pos 는 건너뜀), 정렬합니다.

Usage
-----
python common/tools/build_lookup_from_anchors.py systems/sunrise_sunset/anchors.json
python common/tools/build_lookup_from_anchors.py systems/sunrise_sunset/anchors.json --dry-run

Options
-------
--dry-run           : 파일을 수정하지 않고 diff 요약만 출력
--overwrite-meta    : 기존 space/rail/axis 가 비어있을 때만 채우는 기본 동작을, 항상 새 값으로 덮어씌움
--eps 0.000001      : pos 중복 판단 허용 오차
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

LABEL_RX = re.compile(r"^([A-Z0-9]+)_\(([-+]?\d+(?:\.\d+)?),([-+]?\d+(?:\.\d+)?)\)_([-+]?\d+(?:\.\d+)?)$")
TOL = 0.02

# Frame constants (Fg)
FG_Y = (-2.25, 42.25)
FG_X = (-2.25, 82.25)
# Rail constants (Rg)
RG_Y = (0.0, 40.0)
RG_X = (0.0, 80.0)

def near(a: float, b: float, t: float = TOL) -> bool:
    return abs(a - b) <= t


def load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def dump(p: Path, doc: dict) -> None:
    p.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")


def sym_of(label_id: str) -> str | None:
    if label_id.startswith("CO_"): return "CO_f"
    if label_id.startswith("1C_"): return "1C_f"
    if label_id.startswith("3C_"): return "3C_r"
    return None


def axis_space_rail(x: float, y: float):
    # 우선 Fg → 그다음 Rg
    if near(y, FG_Y[0]): return ("long", "Fg", "BOTTOM", x)
    if near(y, FG_Y[1]): return ("long", "Fg", "TOP",    x)
    if near(x, FG_X[0]): return ("short","Fg", "LEFT",   y)
    if near(x, FG_X[1]): return ("short","Fg", "RIGHT",  y)
    if near(y, RG_Y[0]): return ("long", "Rg", "BOTTOM", x)
    if near(y, RG_Y[1]): return ("long", "Rg", "TOP",    x)
    if near(x, RG_X[0]): return ("short","Rg", "LEFT",   y)
    if near(x, RG_X[1]): return ("short","Rg", "RIGHT",  y)
    return None


def uniq_merge(points: list[dict], new_point: dict, *, eps: float) -> bool:
    """pos 중복이 없으면 append 하고 True, 있으면 False"""
    pos = float(new_point["pos"])
    for p in points:
        if abs(float(p["pos"]) - pos) <= eps:
            return False
    points.append({"pos": pos, "sys": float(new_point["sys"])})
    points.sort(key=lambda x: x["pos"])
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("anchors", help="systems/<system>/anchors.json")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite-meta", action="store_true")
    ap.add_argument("--eps", type=float, default=1e-9)
    args = ap.parse_args()

    path = Path(args.anchors)
    doc = load(path)

    tbl = doc.setdefault("lookup_table", {}).setdefault("symbols", {})
    # 초기 심볼 구조 보장
    for key in ("CO_f", "1C_f", "3C_r"):
        tbl.setdefault(key, {"space": None, "rail": None, "axis": None, "points": []})

    added = {k: 0 for k in tbl.keys()}

    for track, block in (doc.get("trajectories") or {}).items():
        for item in (block.get("anchors") or []):
            sid = (item.get("id") or "").strip()
            m = LABEL_RX.match(sid)
            if not m:
                continue
            ID, xs, ys, ns = m.groups()
            x, y, n = float(xs), float(ys), float(ns)
            sym = sym_of(ID)
            if not sym:
                continue
            asr = axis_space_rail(x, y)
            if not asr:
                # 상수선이 아니면 lookup_table 대상 아님
                continue
            axis, space, rail, pos = asr
            entry = tbl.setdefault(sym, {"space": None, "rail": None, "axis": None, "points": []})
            if args.overwrite_meta or entry["space"] is None:
                entry["space"] = space
                entry["rail"]  = rail
                entry["axis"]  = axis
            # 병합
            if uniq_merge(entry["points"], {"pos": pos, "sys": n}, eps=args.eps):
                added[sym] += 1

    if args.dry_run:
        print("[DRY-RUN] would add:")
        for k, v in added.items():
            print(f" - {k}: +{v} points (now total {len(tbl.get(k,{}).get('points',[]))})")
        return

    dump(path, doc)
    for k, v in added.items():
        print(f"[OK] {k}: +{v} points (total {len(tbl.get(k,{}).get('points',[]))})")
    print(f"[OK] wrote {path}")

if __name__ == "__main__":
    main()
