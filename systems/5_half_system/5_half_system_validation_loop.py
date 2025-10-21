# -*- coding: utf-8 -*-
"""
5_half_system_validation_loop.py
--------------------------------
MVP 원클릭 검증 루프

순서:
  1) 샘플 템플릿 → lookup 병합 + 테스트 케이스 생성
  2) anchors 백업 후 병합본 적용
  3) 4→3 / 5→3 / 6→3 매핑 자동 생성
  4) 전체 검증(validation_runner.py)

기본 경로는 본 스크립트 위치 기준으로 자동 계산됩니다.
필요시 CLI 옵션으로 덮어쓸 수 있습니다.
"""

from __future__ import annotations
import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"\n$ {' '.join(map(str,cmd))}")
    proc = subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True)
    if proc.returncode != 0:
        raise SystemExit(f"[ERR] command failed with code {proc.returncode}")


def ensure_exists(p: Path, hint: str):
    if not p.exists():
        raise SystemExit(f"[ERR] missing: {p}   ({hint})")


def timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def main():
    # 기본 경로 설정
    here = Path(__file__).resolve().parent                                # systems/5_half_system
    repo = here.parents[2]                                                # repo/
    tools = repo / "common" / "tools"

    default_template = here / "5_half_system_samples_template.txt"
    default_anchors  = here / "5_half_system_anchors.json" if (here / "5_half_system_anchors.json").exists() else (here / "anchors.json")
    out_merged       = here / "anchors.merged.json"
    out_cases        = here / "5_half_system_test_cases.json"

    parser = argparse.ArgumentParser(description="5_half_system MVP validation loop")
    parser.add_argument("--template", type=str, default=str(default_template), help="샘플 템플릿 txt")
    parser.add_argument("--anchors",  type=str, default=str(default_anchors),  help="기준 anchors.json (병합 대상)")
    parser.add_argument("--skip-merge", action="store_true", help="샘플→병합/케이스 생성을 건너뜀")
    parser.add_argument("--skip-apply", action="store_true", help="anchors.merged.json 적용/백업 건너뜀")
    parser.add_argument("--skip-maps",  action="store_true", help="map_4to3/5to3/6to3 생성 건너뜀")
    parser.add_argument("--skip-validate", action="store_true", help="validation_runner 실행 건너뜀")
    parser.add_argument("--force", action="store_true", help="기존 산출물 덮어쓰기")
    args = parser.parse_args()

    template = Path(args.template)
    anchors  = Path(args.anchors)

    # 사전 점검
    ensure_exists(template, "샘플 템플릿이 필요합니다.")
    ensure_exists(anchors,  "기준 앵커가 필요합니다.")

    # 1) 샘플 → lookup 병합 + test_cases
    if not args.skip-merge:
        print("\n=== (1) 샘플 → lookup 병합 + 케이스 생성 ===")
        cmd = [
            sys.executable, str(tools / "compact_samples_to_lookup_and_cases.py"),
            str(template),
            "--anchors", str(anchors),
            "--out-lookup", str(out_merged),
            "--out-cases",  str(out_cases),
        ]
        if args.force:
            cmd.append("--force")
        run(cmd, cwd=repo)
        if not out_merged.exists():
            raise SystemExit("[ERR] anchors.merged.json 생성 실패")

    # 2) anchors 백업 + 병합본 적용
    if not args.skip_apply:
        print("\n=== (2) 앵커 백업 및 적용 ===")
        if not out_merged.exists():
            raise SystemExit("[ERR] anchors.merged.json 이 없습니다. --skip-apply 를 쓰지 않았다면 1단계를 먼저 수행하세요.")
        backup = anchors.with_name(anchors.stem + "_backup_" + timestamp() + anchors.suffix)
        print(f"[info] backup → {backup.name}")
        shutil.copy2(anchors, backup)
        print(f"[info] apply merged → {anchors.name}")
        shutil.move(str(out_merged), str(anchors))

    # 3) 4→3 / 5→3 / 6→3 매핑 생성
    if not args.skip_maps:
        print("\n=== (3) 매핑 생성(4→3 / 5→3 / 6→3) ===")
        cmd = [
            sys.executable, str(tools / "build_map_from_anchors.py"),
            str(anchors)
        ]
        run(cmd, cwd=repo)

    # 4) 전체 검증
    if not args.skip_validate:
        print("\n=== (4) 검증 실행 ===")
        cmd = [
            sys.executable, str(tools / "validation_runner.py"),
            str(here)  # systems/5_half_system/
        ]
        run(cmd, cwd=repo)

    # 요약 출력
    print("\n=== ✅ Validation loop completed ===")
    summary = {
        "template": str(template.relative_to(repo) if template.is_relative_to(repo) else template),
        "anchors":  str(anchors.relative_to(repo)  if anchors.is_relative_to(repo)  else anchors),
        "cases":    str(out_cases.relative_to(repo) if out_cases.exists() and out_cases.is_relative_to(repo) else str(out_cases)),
        "repo":     str(repo),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
