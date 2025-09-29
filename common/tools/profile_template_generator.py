#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
profile_template_generator.py (v1.3 SSOT)
- 시스템별 profile 템플릿을 공통 규격에 맞춰 생성
- 원칙: 예시 공식 자동 유입 금지 (명시적 승인 없이는 formula 제거)

Usage
-----
python repo/common/tools/profile_template_generator.py \
  --from-preset sunrise_sunset --outfile systems/sunrise_sunset/profile_sunrise_sunset.json
# 또는 스펙 일괄 지정
python repo/common/tools/profile_template_generator.py --spec path/to/spec.json --outfile out.json
# 프리셋 formula 허용 시에만:
python repo/common/tools/profile_template_generator.py --from-preset sunrise_sunset --allow-preset-formula --outfile out.json
"""
from __future__ import annotations
import argparse, json, sys, pathlib
from typing import Any, Dict

REQUIRED_ROOT_KEYS = ["system", "formula", "value_domains", "safety", "space_rule", "mappings"]


def load_json_maybe(path: str | None) -> dict | None:
    if not path:
        return None
    p = pathlib.Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def validate_profile(doc: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_ROOT_KEYS if k not in doc]
    if missing:
        raise SystemExit(f"[FAIL] missing required top-level keys: {missing}")
    if not isinstance(doc["value_domains"], dict):
        raise SystemExit("value_domains must be object")
    if not isinstance(doc["safety"], dict):
        raise SystemExit("safety must be object")
    if not isinstance(doc["space_rule"], dict):
        raise SystemExit("space_rule must be object")
    if not isinstance(doc["mappings"], (dict, type(None))):
        raise SystemExit("mappings must be object or null")


def deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = v
    return out

# -------- Presets (예시) --------
PRESETS = {
    "sunrise_sunset": {
        "system": "Sunrise–Sunset",
        # ⚠️ preset에 formula를 보관하되 기본 주입은 금지 (--allow-preset-formula 필요)
        "formula": "CO_f + 1C_f + 3C_r = HP_n",
        "value_domains": {
            "my_ball_tip": [-5,-4,-3,-2,-1,0,1,2,3,4,5,6],
            "first_cushion_tip": [-4,-3,-2,-1,0,1,2,3,4],
            "third_cushion_tip": [-2,-1,0,1,2,3,4],
            "correction": [0,-1,-1.5,-2]
        },
        "safety": {
            "tip_range": [-4.0, 4.0],
            "correction_only_negative": True,
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
        "meta": {"version": "1.0", "generator": "profile_template_generator.py", "no_preset_autofill": True}
    }
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", help="시스템 이름(출력에 반영)")
    ap.add_argument("--formula", help="공식 문자열")
    ap.add_argument("--domains-json", help="value_domains JSON 경로")
    ap.add_argument("--safety-json", help="safety JSON 경로")
    ap.add_argument("--space-rule-json", help="space_rule JSON 경로")
    ap.add_argument("--mappings-json", help="mappings JSON 경로(없으면 None)")
    ap.add_argument("--spec", help="전체 스펙 JSON(모든 필드를 한번에 지정)")
    ap.add_argument("--from-preset", choices=list(PRESETS.keys()), help="예시 프리셋 사용(선택)")
    ap.add_argument("--allow-preset-formula", action="store_true", help="프리셋 formula 자동 유입 허용")
    ap.add_argument("--outfile", default=None, help="출력 파일 경로 (기본: profile_<system>.json)")
    args = ap.parse_args()

    doc: Dict[str, Any] = {}

    # 1) preset 적용 (선택)
    if args.from_preset:
        doc = deep_merge(doc, PRESETS[args.from_preset])
        if not args.allow_preset_formula:
            # 예시 공식 자동 유입 금지
            doc.pop("formula", None)

    # 2) spec 파일 적용 (선택)
    spec = load_json_maybe(args.spec)
    if spec:
        doc = deep_merge(doc, spec)

    # 3) CLI override
    if args.system:
        doc["system"] = args.system
    if args.formula:
        doc["formula"] = args.formula
    vd = load_json_maybe(args.domains_json)
    if vd is not None:
        doc["value_domains"] = vd
    safety = load_json_maybe(args.safety_json)
    if safety is not None:
        doc["safety"] = safety
    sr = load_json_maybe(args.space_rule_json)
    if sr is not None:
        doc["space_rule"] = sr
    mappings = load_json_maybe(args.mappings_json)
    if args.mappings_json:
        doc["mappings"] = mappings
    elif "mappings" not in doc:
        doc["mappings"] = None

    # 4) meta & 가드
    doc.setdefault("meta", {})
    doc["meta"]["version"] = doc["meta"].get("version", "1.0")
    doc["meta"]["generator"] = "profile_template_generator.py"
    doc["meta"]["no_preset_autofill"] = True

    # 5) 필수 검사
    try:
        validate_profile(doc)
    except SystemExit as e:
        msg = str(e)
        print(msg, file=sys.stderr)
        print("\n[Hint] 다음 중 택1:\n  - --spec <json> 에 모든 필드 정의\n  - 또는 --from-preset <name> 후 필요한 필드 override\n  - 또는 --system/--formula/--domains-json/--safety-json/--space-rule-json/--mappings-json 개별 지정", file=sys.stderr)
        sys.exit(1)

    # 6) 저장
    outname = (doc.get("system") or "unknown").lower().replace(" ", "_")
    outpath = args.outfile or f"profile_{outname}.json"
    pathlib.Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(outpath).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote {outpath}")


if __name__ == "__main__":
    main()
