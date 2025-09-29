# -*- coding: utf-8 -*-
"""
label_parser.py — CO/1C..6C 라벨 파서
형식: <ID>_(x,y)_<sys>[grid,rail,axis] // 전역 규칙에 의해 **대괄호는 의무**
예: CO_(60,-2.25)_40[Fg,BOTTOM,long]
1C_(20,42.25)_20[Fg,TOP,long]
3C_(20,0)_20[Rg,BOTTOM,long]
"""


from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional, Literal, Tuple


ID = Literal["CO","1C","2C","3C","4C","5C","6C"]
Space = Literal["Fg","Rg"]
Rail = Literal["TOP","BOTTOM","LEFT","RIGHT"]
Axis = Literal["long","short"]


LABEL_RE = re.compile(r"""
^\s*
(?P<id>CO|[1-6]C)
_\(
\s*(?P<x>[-+]?\d+(?:\.\d+)?)\s*,\s*(?P<y>[-+]?\d+(?:\.\d+)?)\s*
\)
_
(?P<sys>[-+]?\d+(?:\.\d+)?)
(?:\[
\s*(?P<grid>Fg|Rg)\s*,\s*
(?P<rail>TOP|BOTTOM|LEFT|RIGHT)\s*,\s*
(?P<axis>long|short)\s*
\])?
\s*$
""", re.VERBOSE)


EPS = 0.02 # 허용 오차 (현장 보정)
# Fg 상수(프레임선)
FG_Y_TO_RAIL = { -2.25: "BOTTOM", 42.25: "TOP" }
FG_X_TO_RAIL = { -2.25: "LEFT", 82.25: "RIGHT" }
# Rg 상수(레일선)
RG_Y_TO_RAIL = { 0.0: "BOTTOM", 40.0: "TOP" }
RG_X_TO_RAIL = { 0.0: "LEFT", 80.0: "RIGHT" }


STRICT_LABEL_SUFFIX: bool = True # 전역 규칙: 대괄호 메타 의무




def _approx_match(v: float, table: dict[float, str]) -> Optional[Tuple[float, str]]:
for k, name in table.items():
if abs(v - k) <= EPS:
return (k, name)
return None


@dataclass
assert parse_label("3C_(20,0)_20[Rg,BOTTOM,long]").mark == Mark("Rg","BOTTOM","long",20.0)