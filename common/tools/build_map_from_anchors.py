# -*- coding: utf-8 -*-
"""
build_map_from_anchors.py
-------------------------
anchors.json에서 3C 기준의 4C, 5C, 6C 변환 매핑(JSON)을 자동 생성한다.

출력 예:
  systems/5_half_system/map_4to3.json
  systems/5_half_system/map_5to3.json
  systems/5_half_system/map_6to3.json

용도:
  - track_selector_router.py에서 4C/5C/6C 입력 시 3C 등가 sys 변환에 사용
"""

from __future__ import annotations
import argparse
import json
import os
from typing import Dict, List, Tuple


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(path: str, data: dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _extract_track_blocks(anchors: dict) -> Dict[str, dict]:
    """anchors.json에서 B2T_L/R, T2B_L/R 블록만 추출"""
    blocks = {}
    for key, val in anchors.get("trajectories", {}).items():
        if any(t in key for t in ["B2T", "T2B"]):
            blocks[key] = val
    return blocks


def _pair_sys(track_data: dict, label_a: str, label_b: str) -> List[Tuple[float, float]]:
    """
    label_a 기준(예: 4C_sys)과 label_b 기준(예: 3C_sys)을 동일 인덱스 기반으로 묶음.
    ※ sys 목록은 오름차순 정렬, 길이 다르면 짧은 쪽에 맞춤.
    """
    if label_a not in track_data or label_b not in track_data:
        return []

    arr_a = track_data[label_a]
    arr_b = track_data[label_b]

    n = min(len(arr_a), len(arr_b))
    pairs = [(arr_a[i]["sys"], arr_b[i]["sys"]) for i in range(n)]
    pairs.sort(key=lambda ab: ab[0])
    return pairs


def _build_mapping_for_track(track_data: dict) -> Dict[str, List[Tuple[float, float]]]:
    """한 트랙의 (4→3, 5→3, 6→3) 매핑 생성"""
    maps = {}
    for (src, dst) in [("4C", "3C"), ("5C", "3C"), ("6C", "3C")]:
        pairs = _pair_sys(track_data, src, dst)
        if pairs:
            maps[f"{src}_to_{dst}"] = pairs
    return maps


def _build_all(anchors_path: str) -> Dict[str, dict]:
    anchors = _load_json(anchors_path)
    blocks = _extract_track_blocks(anchors)

    all_maps = {"map_4to3": {}, "map_5to3": {}, "map_6to3": {}}

    for track_name, td in blocks.items():
        maps = _build_mapping_for_track(td)
        if "4C_to_3C" in maps:
            all_maps["map_4to3"][track_name] = maps["4C_to_3C"]
        if "5C_to_3C" in maps:
            all_maps["map_5to3"][track_name] = maps["5C_to_3C"]
        if "6C_to_3C" in maps:
            all_maps["map_6to3"][track_name] = maps["6C_to_3C"]

    return all_maps


def main():
    ap = argparse.ArgumentParser(description="Generate 4→3 / 5→3 / 6→3 sys mapping from anchors.json")
    ap.add_argument("anchors", type=str, help="path to anchors.json")
    ap.add_argument("--out-dir", type=str, default="", help="output directory (default: same folder)")
    args = ap.parse_args()

    anchors_path = args.anchors
    out_dir = args.out_dir or os.path.dirname(anchors_path)

    print(f"[info] loading anchors: {anchors_path}")
    maps = _build_all(anchors_path)

    for key, data in maps.items():
        if not data:
            continue
        out_path = os.path.join(out_dir, f"{key}.json")
        _save_json(out_path, data)
        print(f"[ok] saved {out_path} ({len(data)} tracks)")

    print("[done] mapping generation complete.")


if __name__ == "__main__":
    main()
