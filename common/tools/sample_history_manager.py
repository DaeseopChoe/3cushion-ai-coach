"""
3Cushion AI - Sample History Manager
------------------------------------
좌표 기반 시스템 판별/트랙 선택 결과를 자동 저장하고, 
다음 호출 시 동일하거나 유사한 입력을 빠르게 재활용하는 캐시/히스토리 관리 도구.

용도:
    from common.tools.sample_history_manager import SampleHistoryManager

    mgr = SampleHistoryManager("systems/5_half_system/samples_history.json")

    # 1️⃣ 기존 데이터 조회
    prev = mgr.find_similar(x_co=40, y_co=-2.25, x_mk=55, y_mk=0, mark="3C")
    if prev:
        print("[cache hit]", prev)
    else:
        # 2️⃣ 새 계산
        result = {
            "system": "5_half_system",
            "track": "B2T_L",
            "c1_sys": 45.5,
            "score": 1.2
        }
        mgr.add_entry(x_co=40, y_co=-2.25, x_mk=55, y_mk=0, mark="3C", result=result)
        mgr.save()
"""

import json
import math
import os
from datetime import datetime


class SampleHistoryManager:
    def __init__(self, filepath: str, tol: float = 0.05):
        """
        filepath: samples_history.json 파일 경로
        tol: 좌표 유사도 판단 기준(기본 ±0.05)
        """
        self.filepath = filepath
        self.tol = tol
        self.samples = []
        self._load()

    # -------------------------------
    # 내부 유틸
    # -------------------------------
    def _load(self):
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.samples = json.load(f)
            except Exception:
                self.samples = []
        else:
            self.samples = []

    def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(self.samples, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _dist(a, b):
        """단순 유클리드 거리 계산"""
        return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))

    # -------------------------------
    # 공개 API
    # -------------------------------
    def add_entry(self, x_co, y_co, x_mk, y_mk, mark, result: dict):
        """
        새 결과 추가.
        result 예시: {"system": "5_half_system", "track": "B2T_L", "c1_sys": 45.5, "score": 1.2}
        """
        entry = {
            "input": {"x_co": x_co, "y_co": y_co, "x_mark": x_mk, "y_mark": y_mk, "mark": mark},
            "result": result,
            "timestamp": datetime.now().isoformat(timespec="seconds")
        }
        self.samples.append(entry)

    def find_similar(self, x_co, y_co, x_mk, y_mk, mark, max_distance=0.5):
        """
        유사 입력을 검색 (기본 유클리드 거리 <= 0.5)
        mark는 동일해야 함.
        """
        if not self.samples:
            return None

        query_vec = (x_co, y_co, x_mk, y_mk)
        best = None
        best_dist = 9999.0

        for s in self.samples:
            i = s["input"]
            if i["mark"] != mark:
                continue
            vec = (i["x_co"], i["y_co"], i["x_mark"], i["y_mark"])
            d = self._dist(query_vec, vec)
            if d < best_dist:
                best_dist = d
                best = s

        if best and best_dist <= max_distance:
            return {"distance": best_dist, "data": best}
        return None

    def clear(self):
        """히스토리 전체 삭제"""
        self.samples = []
        self.save()
