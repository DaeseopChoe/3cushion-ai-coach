# -*- coding: utf-8 -*-
"""
track_selector_router.py — Final Unified Version (v2.5)
-------------------------------------------------------
✅ 기능 통합:
  • 3C~6C 입력 지원 (sys 변환 자동 매핑)
  • 시스템 자동 탐색 및 히스토리 기반 후보 추천
  • ΔCO 보정, HP 가드, 보간 clamp
  • samples_history.json 자동 기록
  • anchors.json 변경 시 자동 매핑 (--auto-maps)

의존:
  - common/tools/sample_history_manager.py
  - common/tools/track_selector.py
  - common/tools/build_map_from_anchors.py
"""

from __future__ import annotations
import argparse
import json
import os
from glob import glob
from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

# 레거시 유틸
from common.tools.track_selector import (
    snap_direction_candidates,
    load_track_data,
    interp_sys,
    exists_and_loc,
)
# 히스토리 매니저
from common.tools.sample_history_manager import SampleHistoryManager
# 자동 매핑 생성기
from common.tools.build_map_from_anchors import _build_all as build_maps_from_anchors, _save_json


# ------------------------------
# 유틸 함수
# ------------------------------
def _load_json_safe(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


@contextmanager
def chdir(path: str):
    prev = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(prev)


# ------------------------------
# 시스템 탐색 및 로드
# ------------------------------
def discover_systems(systems_root: str = "systems") -> List[dict]:
    out = []
    for sysdir in sorted(glob(os.path.join(systems_root, "*"))):
        if not os.path.isdir(sysdir):
            continue
        anchors = os.path.join(sysdir, "anchors.json")
        logic_candidates = glob(os.path.join(sysdir, "*_logic.json"))
        if os.path.exists(anchors) and logic_candidates:
            sys_id = os.path.basename(sysdir)
            out.append({
                "id": sys_id,
                "dir": sysdir,
                "anchors": anchors,
                "logic": logic_candidates[0],
                "history": os.path.join(sysdir, "samples_history.json"),
                "map_4to3": os.path.join(sysdir, "map_4to3.json"),
                "map_5to3": os.path.join(sysdir, "map_5to3.json"),
                "map_6to3": os.path.join(sysdir, "map_6to3.json"),
            })
    return out


# ------------------------------
# 매핑 로더 & 보간 유틸
# ------------------------------
def _interp_pairs_clamped(pairs: List[List[float]], x: float) -> Optional[float]:
    if not pairs:
        return None
    if x <= pairs[0][0]:
        return pairs[0][1]
    if x >= pairs[-1][0]:
        return pairs[-1][1]
    for i in range(len(pairs) - 1):
        x0, y0 = pairs[i]
        x1, y1 = pairs[i + 1]
        if x0 <= x <= x1:
            t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return None


def _load_map_pairs(path: str) -> dict:
    data = _load_json_safe(path) or {}
    for k, pairs in data.items():
        pairs.sort(key=lambda ab: ab[0])
    return data


class MapBundle:
    def __init__(self, map_4to3: dict, map_5to3: dict, map_6to3: dict):
        self.m43 = map_4to3 or {}
        self.m53 = map_5to3 or {}
        self.m63 = map_6to3 or {}

    def to3(self, track: str, mark_label: str, src_sys: float) -> Optional[float]:
        if mark_label == "3C":
            return src_sys
        if mark_label == "4C":
            return _interp_pairs_clamped(self.m43.get(track, []), src_sys)
        if mark_label == "5C":
            return _interp_pairs_clamped(self.m53.get(track, []), src_sys)
        if mark_label == "6C":
            return _interp_pairs_clamped(self.m63.get(track, []), src_sys)
        return None


def _build_maps_for_system(sysinfo: dict) -> MapBundle:
    m43 = _load_map_pairs(sysinfo["map_4to3"]) if os.path.exists(sysinfo["map_4to3"]) else {}
    m53 = _load_map_pairs(sysinfo["map_5to3"]) if os.path.exists(sysinfo["map_5to3"]) else {}
    m63 = _load_map_pairs(sysinfo["map_6to3"]) if os.path.exists(sysinfo["map_6to3"]) else {}
    return MapBundle(m43, m53, m63)


# ------------------------------
# 핵심: 시스템별 판별/계산
# ------------------------------
def _identify_in_system(
    sysinfo: dict,
    x_co: float, y_co: float,
    x_mk: float, y_mk: float, mark_label: str,
    co_baseline: float = 50.0, co_gain: float = 0.5,
    w4: float = 0.0, w5: float = 0.0, w6: float = 0.0,
    tol: float = 0.05
) -> Optional[Tuple[str, float, float, dict]]:
    maps = _build_maps_for_system(sysinfo)
    mgr = SampleHistoryManager(sysinfo["history"])

    prev = mgr.find_similar(x_co, y_co, x_mk, y_mk, mark_label)
    if prev:
        r = prev["data"]["result"]
        return r["track"], r.get("c1_sys"), None, {"cached": True, **r}

    with chdir(sysinfo["dir"]):
        direction, y_1c, candidates = snap_direction_candidates(y_co, y_mk, mark_label, tol)
        best = None
        for track in candidates:
            td = load_track_data(track)
            co_sys = interp_sys(td, "CO", x_co, y_co)
            mk_sys = interp_sys(td, mark_label, x_mk, y_mk)
            if co_sys is None or mk_sys is None:
                continue
            c3_sys = maps.to3(track, mark_label, mk_sys)
            if c3_sys is None:
                continue

            dCO = co_gain * (co_sys - co_baseline)
            c1_sys = co_sys - (
                c3_sys
                + (w4 * mk_sys if mark_label == "4C" else 0)
                + (w5 * mk_sys if mark_label == "5C" else 0)
                + (w6 * mk_sys if mark_label == "6C" else 0)
                + dCO
            )
            if not (0 <= c1_sys <= 90):
                continue

            ok, _x1, y1 = exists_and_loc(td, "1C", c1_sys)
            if not ok:
                continue
            R = abs(co_sys - (c1_sys + c3_sys + dCO))
            if y1 is not None:
                R += abs(y1 - y_1c) * 0.1

            dbg = {"R": R, "co_sys": co_sys, "mk_sys": mk_sys, "c3_sys": c3_sys, "dCO": dCO}
            if best is None or R < best[3]["R"]:
                best = (track, c1_sys, y_1c, dbg)

    if best:
        result_data = {"system": sysinfo["id"], "track": best[0], "c1_sys": best[1], "score": best[3]["R"]}
        mgr.add_entry(x_co, y_co, x_mk, y_mk, mark_label, result_data)
        mgr.save()
    return best


# ------------------------------
# 히스토리 기반 후보 랭킹
# ------------------------------
def rank_system_candidates_by_history(
    x_co: float, y_co: float, x_mk: float, y_mk: float, mark_label: str,
    systems_root: str = "systems", k: int = 3, max_distance: float = 2.0
) -> List[dict]:
    systems = discover_systems(systems_root)
    ranked = []
    for s in systems:
        hist = _load_json_safe(s["history"]) or []
        bucket = []
        for e in hist:
            i = e.get("input", {})
            if i.get("mark") != mark_label:
                continue
            dx = (x_co - i.get("x_co", 0)) ** 2 + (y_co - i.get("y_co", 0)) ** 2
            dy = (x_mk - i.get("x_mark", 0)) ** 2 + (y_mk - i.get("y_mark", 0)) ** 2
            d = (dx + dy) ** 0.5
            if d <= max_distance:
                bucket.append(d)
        if not bucket:
            continue
        avg_d = sum(bucket) / len(bucket)
        ranked.append({"system_id": s["id"], "score": avg_d, "count": len(bucket)})
    ranked.sort(key=lambda r: r["score"])
    return ranked[:k]


# ------------------------------
# CLI
# ------------------------------
def _parse_args():
    ap = argparse.ArgumentParser(description="Unified Track Selector Router (Auto-Mapping Enabled)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # 추천
    r = sub.add_parser("recommend", help="히스토리 기반 시스템 추천")
    r.add_argument("--co", nargs=2, type=float, required=True)
    r.add_argument("--mark", choices=["3C", "4C", "5C", "6C"], required=True)
    r.add_argument("--mx", type=float, required=True)
    r.add_argument("--my", type=float, required=True)
    r.add_argument("--systems-root", type=str, default="systems")

    # 실행
    run = sub.add_parser("run", help="트랙 판별/계산 + 자동 매핑/기록")
    run.add_argument("--co", nargs=2, type=float, required=True)
    run.add_argument("--mark", choices=["3C", "4C", "5C", "6C"], required=True)
    run.add_argument("--mx", type=float, required=True)
    run.add_argument("--my", type=float, required=True)
    run.add_argument("--systems-root", type=str, default="systems")
    run.add_argument("--system-id", type=str, default="")
    run.add_argument("--co-baseline", type=float, default=50.0)
    run.add_argument("--co-gain", type=float, default=0.5)
    run.add_argument("--w4", type=float, default=0.0)
    run.add_argument("--w5", type=float, default=0.0)
    run.add_argument("--w6", type=float, default=0.0)
    run.add_argument("--tol", type=float, default=0.05)
    run.add_argument("--auto-maps", action="store_true", help="anchors.json에서 매핑 자동 생성")
    run.add_argument("--force", action="store_true", help="기존 매핑 파일 덮어쓰기")

    return ap.parse_args()


def _cmd_recommend(args):
    ranked = rank_system_candidates_by_history(args.co[0], args.co[1], args.mx, args.my, args.mark, args.systems_root)
    print(json.dumps({"ranked_candidates": ranked}, ensure_ascii=False, indent=2))


def _cmd_run(args):
    systems = discover_systems(args.systems_root)
    if args.system_id:
        targets = [s for s in systems if s["id"] == args.system_id]
    else:
        ranked = rank_system_candidates_by_history(args.co[0], args.co[1], args.mx, args.my, args.mark, args.systems_root)
        ranked_ids = [r["system_id"] for r in ranked]
        targets = [s for s in systems if s["id"] in ranked_ids] or systems

    # 자동 매핑
    if args.auto_maps:
        print("[auto-maps] checking anchors and generating mappings...")
        for sysinfo in targets:
            anchors = sysinfo["anchors"]
            if not os.path.exists(anchors):
                continue
            maps = build_maps_from_anchors(anchors)
            for key, data in maps.items():
                out_path = os.path.join(sysinfo["dir"], f"{key}.json")
                if data and (args.force or not os.path.exists(out_path)):
                    _save_json(out_path, data)
                    print(f"[auto-maps] regenerated {out_path}")
        print("[auto-maps] done.\n")

    best = None
    for sysinfo in targets:
        res = _identify_in_system(sysinfo, args.co[0], args.co[1], args.mx, args.my, args.mark,
                                  args.co_baseline, args.co_gain, args.w4, args.w5, args.w6, args.tol)
        if res and (best is None or res[3]["R"] < best[3]["R"]):
            best = (sysinfo["id"], *res)
    if not best:
        print("No valid track found.")
        return
    sys_id, track, c1_sys, y1c, dbg = best
    print(json.dumps({"system_id": sys_id, "track": track, "c1_sys": c1_sys, "debug": dbg}, ensure_ascii=False, indent=2))


def main():
    args = _parse_args()
    if args.cmd == "recommend":
        _cmd_recommend(args)
    elif args.cmd == "run":
        _cmd_run(args)


if __name__ == "__main__":
    main()
