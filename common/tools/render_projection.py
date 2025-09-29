"""
render_utils.py — Common v1.2 (Extended Fg, offset 2.25)
- offset_fg2rg: frame→rail normal offset (Fg to Rg)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


TOP, BOTTOM, LEFT, RIGHT = "TOP", "BOTTOM", "LEFT", "RIGHT"
Rail = Literal["TOP", "BOTTOM", "LEFT", "RIGHT"]
Space = Literal["Fg", "Rg"]


# 전역 상수 (모든 시스템 공용)
OFFSET_FG2RG: float = 2.25 # ≈80 mm / 35.55 mm
THETA_T_MAX_DEG: float = 68.0
M_MIN: float = 0.05
# 확장 Fg 기본값 (dataset.units에서 재정의 가능)
FG_EXT_LONG: float = 2.25
FG_EXT_SHORT: float = 2.25


@dataclass
class Mark:
space: Space
rail: Rail
axis: Literal["long", "short"]
value: float


# parallel frame: 숫자 동일, 위치만 평행 이동


def fg_parallel_from_rg(mark_rg: Mark) -> Mark:
assert mark_rg.space == "Rg"
return Mark(space="Fg", rail=mark_rg.rail, axis=mark_rg.axis, value=float(mark_rg.value))


# rail projection: 궤적과 collinear


def project_fg_to_rg(mark_fg: Mark, m: float, offset: float = OFFSET_FG2RG) -> Mark:
assert mark_fg.space == "Fg"
if abs(m) < M_MIN:
m = M_MIN * (1 if m >= 0 else -1)
if mark_fg.axis == "long":
x_rg = mark_fg.value - offset / m if mark_fg.rail == TOP else mark_fg.value + offset / m
return Mark("Rg", mark_fg.rail, mark_fg.axis, float(x_rg))
else:
y_rg = mark_fg.value - offset * m if mark_fg.rail == LEFT else mark_fg.value + offset * m
return Mark("Rg", mark_fg.rail, mark_fg.axis, float(y_rg))


# 역투영


def project_rg_to_fg(mark_rg: Mark, m: float, offset: float = OFFSET_FG2RG) -> Mark:
assert mark_rg.space == "Rg"
if abs(m) < M_MIN:
m = M_MIN * (1 if m >= 0 else -1)
if mark_rg.axis == "long":
x_fg = mark_rg.value + offset / m if mark_rg.rail == TOP else mark_rg.value - offset / m
return Mark("Fg", mark_rg.rail, mark_rg.axis, float(x_fg))
else:
y_fg = mark_rg.value + offset * m if mark_rg.rail == LEFT else mark_rg.value - offset * m
return Mark("Fg", mark_rg.rail, mark_rg.axis, float(y_fg))