"""simulator_template.py — Common v1.2 (Extended Fg, offset 2.25)
- 결과 타입: Mark(Fg/Rg)
- 스냅 규칙: Fg와 Rg 범위를 분리, Fg는 확장 허용
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Literal
from render_utils import Mark, TOP, BOTTOM, LEFT, RIGHT, FG_EXT_LONG, FG_EXT_SHORT


Corner = Literal["LEFT", "RIGHT"]


@dataclass
class ShotInput:
x: Optional[float] = None
y: Optional[float] = None
corner: Corner = "LEFT"
display_mode: Literal["rail_projection", "parallel_frame", "both"] = "rail_projection"


@dataclass
class ShotOutput:
result: Mark
anchors: list[Mark]


class Simulator:
def __init__(self, dataset: dict):
self.ds = dataset
units = dataset.get("units", {})
self.ext_long = float(units.get("fg_extension_long", FG_EXT_LONG))
self.ext_short = float(units.get("fg_extension_short", FG_EXT_SHORT))


def snap_fg_long(self, x: float) -> float:
return max(-self.ext_long, min(80.0 + self.ext_long, float(x)))
def snap_fg_short(self, y: float) -> float:
return max(-self.ext_short, min(40.0 + self.ext_short, float(y)))
def snap_rg_long(self, x: float) -> float:
return max(0.0, min(80.0, float(x)))
def snap_rg_short(self, y: float) -> float:
return max(0.0, min(40.0, float(y)))


# 예시: long Fg 결과 반환
def compute_example(self, x: float) -> ShotOutput:
value_fg = self.snap_fg_long(x)
c1 = Mark(space="Fg", rail=TOP, axis="long", value=value_fg)
return ShotOutput(result=c1, anchors=[c1])