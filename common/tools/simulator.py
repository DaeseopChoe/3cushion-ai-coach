
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
simulator.py — sys-only computation + display-space δ correction renderer
Path-robust: resolves dataset.json and system_logic.json relative to THIS FILE.
"""

import json
import math
import os
from dataclasses import dataclass

HERE = os.path.dirname(os.path.abspath(__file__))
DATASET_PATH = os.path.join(HERE, "dataset.json")
SYSTEM_LOGIC_PATH = os.path.join(HERE, "system_logic.json")

@dataclass
class Config:
    offset_fg2rg: float
    delta_contact_mm: float
    delta_min_mm: float
    delta_max_mm: float
    theta_scale_enabled: bool
    theta_min_deg: float
    theta_max_deg: float
    grid_mm: float
    delta_comp_grid: float

def load_configs(dataset_path: str = DATASET_PATH, system_logic_path: str = SYSTEM_LOGIC_PATH) -> Config:
    with open(dataset_path, "r", encoding="utf-8") as f:
        ds = json.load(f)
    with open(system_logic_path, "r", encoding="utf-8") as f:
        sl = json.load(f)

    rr = ds["render_rules"]
    units = ds["units"]
    return Config(
        offset_fg2rg = rr["offset_fg2rg"],
        delta_contact_mm = rr["delta_contact_mm"],
        delta_min_mm = rr.get("delta_min_mm", rr["delta_contact_mm"]),
        delta_max_mm = rr.get("delta_max_mm", rr["delta_contact_mm"]),
        theta_scale_enabled = rr.get("theta_scale_enabled", False),
        theta_min_deg = rr.get("theta_min_deg", 10.0),
        theta_max_deg = rr.get("theta_max_deg", 68.0),
        grid_mm = units["grid_mm"],
        delta_comp_grid = ds.get("calc_rules", {}).get("delta_comp_grid", 0.0)
    )

# ----------------------------
# calc-space (sys-only)
# ----------------------------
def compute_third_cushion_sys(co_f: float, onec_f: float, delta_sys: float) -> float:
    """3C_f = CO_f - 1C_f - Δ_sys"""
    return co_f - onec_f - delta_sys

# ----------------------------
# display-space utilities
# ----------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def deg2rad(d):
    return math.pi * d / 180.0

def mm_to_grid(mm: float, grid_mm: float) -> float:
    return mm / grid_mm

def estimate_theta_proxy_from_sys(co_f: float, onec_f: float) -> float:
    """
    Optional θ proxy from sys values for display-only scaling.
    """
    diff = abs(co_f - onec_f) + 1e-6
    theta_min, theta_max = 10.0, 45.0
    t = clamp((40.0 - min(diff, 40.0)) / 40.0, 0.0, 1.0)
    return theta_min * t + theta_max * (1.0 - t)

def inward_sign(rail: str) -> int:
    if rail in ("BOTTOM", "RIGHT"):
        return +1
    if rail in ("TOP", "LEFT"):
        return -1
    raise ValueError("rail must be one of TOP/BOTTOM/LEFT/RIGHT")

def rail_projection_long(x_fg: float, m: float, cfg: Config, rail: str, theta_deg: float=None) -> float:
    """
    Fg->Rg on long axis: x_rg = x_fg ± (offset/m) − s*δ_contact_grid
    """
    s = inward_sign(rail)
    x_rg = x_fg + s * (cfg.offset_fg2rg / max(abs(m), 1e-6))

    # δ correction (display-space)
    if cfg.theta_scale_enabled:
        if theta_deg is None:
            theta_deg = cfg.theta_min_deg
        theta_deg = clamp(theta_deg, cfg.theta_min_deg, cfg.theta_max_deg)
        sin_th = math.sin(deg2rad(theta_deg))
        r_grid = mm_to_grid(30.75, cfg.grid_mm)  # 61.5mm ball
        delta_geom = r_grid / max(sin_th, 1e-3)
        delta_mm = clamp(delta_geom * cfg.grid_mm, cfg.delta_min_mm, cfg.delta_max_mm)
    else:
        delta_mm = cfg.delta_contact_mm

    delta_grid = mm_to_grid(delta_mm, cfg.grid_mm)
    x_rg -= s * delta_grid
    return x_rg

# ----------------------------
# Example end-to-end
# ----------------------------
def simulate_third_cushion(co_f: float, onec_f: float, *, rail: str="BOTTOM", m: float=1.0,
                           dataset_path: str=DATASET_PATH, system_logic_path: str=SYSTEM_LOGIC_PATH):
    cfg = load_configs(dataset_path, system_logic_path)
    sys_3C = compute_third_cushion_sys(co_f, onec_f, cfg.delta_comp_grid)

    x_fg = sys_3C  # In practice, map sys->(Fg/Rg,axis) via your labels/mappings
    theta = estimate_theta_proxy_from_sys(co_f, onec_f) if cfg.theta_scale_enabled else None
    x_rg = rail_projection_long(x_fg, m, cfg, rail=rail, theta_deg=theta)

    mark_rg = {"space": "Rg", "rail": rail, "axis": "long", "value": x_rg}
    return sys_3C, mark_rg

if __name__ == "__main__":
    co, c1 = 40.0, 40.0
    sys_3C, mark = simulate_third_cushion(co, c1, rail="BOTTOM", m=1.0)
    print(f"[sys] CO={co}, 1C={c1} -> 3C={sys_3C:.3f}")
    print(f"[display] mark Rg = {mark}")
