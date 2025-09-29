# 00_global_rules.md — Global Rules (v1.3, SSOT)

> 목적: **모든 시스템을 동일한 규약으로 계산/표시/검증**하기 위한 전역 규칙.
> 핵심: **계산은 sys 전용**, **표시는 렌더 단계에서만 좌표 변환**, **4트랙 앵커 직접 입력**, **예시 공식 자동 주입 금지**.

---

## 1) 좌표·단위·용어

* **좌표계**: 원점 (0,0) 좌하. Long x: 0→80, Short y: 0→40.
* **프레임(Frame)·레일(Rail)**: 좌표 공간 표기는 **Fg(프레임 그리드)**, **Rg(레일 그리드)**.
* **프레임↔레일 오프셋(법선)**: `offset_fg2rg = 2.25` grid (≈ 80 mm / 35.55 mm), 현장 보정 2.24–2.26 허용.
* **Fg 확장(원천 저장/표시 안전용)**: long: `x_fg ∈ [−2.25 .. 82.25]`, short: `y_fg ∈ [−2.25 .. 42.25]`.
* **중요**: **전역 고정 배율 금지**. 시스템값(sys)과 좌표(Fg/Rg) 사이에 고정 스케일을 가정하지 않는다. 필요 시 `mappings`만 사용(외삽 금지, 보간 시 clamp).

## 2) calc-space (계산)

* **계산은 끝까지 sys만** 사용. 모든 공식/Δ/보간은 **sys 도메인**에서 수행한다.
* 표기: 방정식 내에는 좌표 개념을 쓰지 않고 `_f`/`_r` 태그로 기준만 표시(예: `1C_f = CO_f + 2C_r`).
* **보정(Δ)**: 모든 보정은 **Δ_sys**로 저장·적용(선형 보간, 외삽 금지, 범위 밖 clamp).

## 3) display-space (표시)

* 결과를 그릴 때만 Fg↔Rg 변환.

  * **rail_projection(기본)**

    * long: `x_rg = x_fg ± (offset / m)`
    * short: `y_rg = y_fg ± (m · offset)`
  * **parallel_frame(선택)**: `x_fg == x_rg`, `y_fg == y_rg`.
* **안전 상수**: `m_min = 0.05`, `theta_t_max = 68°`, `no_extrapolation = true`.

## 4) 앵커/라벨 — 4트랙 직접 입력

* 모든 시스템은 **4트랙(B2T_L/R, T2B_L/R)** 앵커를 **직접 입력**한다.
* `anchors.json` 스키마: `trajectories.<track>.anchors[]`(라벨 목록), `lookup_table`(좌표↔sys 테이블, 보간/클램프 근거) — `generated_from`, `ops`는 **옵셔널**.
* **라벨 형식(공통)**: `<ID>_(x,y)_<sys>` (예: `CO_(40,-2.25)_30`, `3C_(20,0)_20`)

  * **상수선 정렬**: Fg 기준 `y = −2.25 / 42.25`, `x = −2.25 / 82.25` (허용오차 ±0.02).
  * **브래킷 메타** `[Fg|Rg, rail, axis]`는 **선택**이며, 상수선 정렬이면 파서가 자동 추론한다.

## 5) 공통 타입 — Mark

```json
{ "space": "Fg|Rg", "rail": "TOP|BOTTOM|LEFT|RIGHT", "axis": "long|short", "value": <number> }
```

* **부호 규칙**: 레일 **내향(unit normal)** 기준 — `TOP/LEFT`는 −, `BOTTOM/RIGHT`는 +.

## 6) Δ/보간 & mappings

* 모든 보간/보정은 **sys-도메인 선형보간 + clamp**.
* `mappings`는 **라벨이 좌표를 제공하지 않을 때에만** 사용(외삽 금지).

## 7) 스냅·허용 범위

* **볼 좌표**: 중심 기준 `x ∈ [0.5 .. 79.5]`, `y ∈ [0.5 .. 39.5]`.
* **Fg 축 필요**: long → `x_fg ∈ [−ext_long .. 80+ext_long]` / short → `y_fg ∈ [−ext_short .. 40+ext_short]`.
* **Rg 축 필요**: long → `x_rg ∈ [0..80]` / short → `y_rg ∈ [0..40]`.

## 8) SSOT — 운영본 6종

1. `dataset.json`  2) `anchors.json`  3) `logic_manual.txt`  4) `simulator.py`  5) `schema.json`  6) `validation_loop.py`

* **중복 사본 금지**, 해시/메타 추적 권장.

---

### 변경 로그 (v1.3)

* (중요) **대칭 생성 규칙 삭제** → 4트랙 앵커는 직접 입력.
* (강화) **전역 고정 배율 금지** 명문화, `mappings` 사용 조건/보간 규칙 명시.
* (정리) 라벨 브래킷 메타는 **선택**, 상수선 정렬 시 자동 추론.
