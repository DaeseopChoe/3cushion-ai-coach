# -*- coding: utf-8 -*-
"""
5_half_system_simulator.py — MVP wrapper
- 5_half_system 전용 시뮬레이터/실행기
- track_selector_router.py(run) 호출 → 결과 JSON 출력/저장
"""

import argparse, json, subprocess, sys, os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]  # repo/
ROUTER = REPO_ROOT / "common" / "tools" / "track_selector_router.py"

def run_router(cox, coy, mark, mx, my, out=None, auto_maps=True, force=False,
               co_baseline=50.0, co_gain=0.5, w4=0.0, w5=0.0, w6=0.0, tol=0.05):
    cmd = [
        sys.executable, str(ROUTER), "run",
        "--co", str(cox), str(coy),
        "--mark", mark,
        "--mx", str(mx),
        "--my", str(my),
        "--systems-root", "systems",
        "--system-id", "5_half_system",
        "--co-baseline", str(co_baseline),
        "--co-gain", str(co_gain),
        "--w4", str(w4), "--w5", str(w5), "--w6", str(w6),
        "--tol", str(tol)
    ]
    if auto_maps: cmd.append("--auto-maps")
    if force: cmd.append("--force")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        sys.exit(proc.returncode)

    # track_selector_router.py는 JSON을 stdout으로 출력
    try:
        result = json.loads(proc.stdout)
    except Exception:
        print(proc.stdout)
        raise

    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    return result

def main():
    ap = argparse.ArgumentParser(description="5_half_system simulator (MVP)")
    ap.add_argument("--co", nargs=2, type=float, required=True, metavar=("X_CO","Y_CO"))
    ap.add_argument("--mark", choices=["3C","4C","5C","6C"], required=True)
    ap.add_argument("--mx", type=float, required=True)
    ap.add_argument("--my", type=float, required=True)
    ap.add_argument("--out", type=str, default="")
    ap.add_argument("--no-auto-maps", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--co-baseline", type=float, default=50.0)
    ap.add_argument("--co-gain", type=float, default=0.5)
    ap.add_argument("--w4", type=float, default=0.0)
    ap.add_argument("--w5", type=float, default=0.0)
    ap.add_argument("--w6", type=float, default=0.0)
    ap.add_argument("--tol", type=float, default=0.05)
    args = ap.parse_args()

    res = run_router(
        cox=args.co[0], coy=args.co[1],
        mark=args.mark, mx=args.mx, my=args.my,
        out=args.out,
        auto_maps=not args.no_auto_maps,
        force=args.force,
        co_baseline=args.co_baseline, co_gain=args.co_gain,
        w4=args.w4, w5=args.w5, w6=args.w6, tol=args.tol
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
