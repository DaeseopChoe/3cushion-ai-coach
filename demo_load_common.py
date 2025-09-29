@@
-from common_base_loader import CommonBase
+from common_base_loader import CommonBase
@@
-resolver_mod = cb.import_py("common_anchors_anchors_resolver.py", "anchors_resolver")
-guard_mod = cb.import_py("common_anchors_guard_anchors_consistency.py", "anchors_guard")
-sym_mod = cb.import_py("common_anchors_symmetry.py", "symmetry")
+guard_mod = cb.import_py("common_anchors_guard_anchors_consistency.py", "anchors_guard")
@@
-anchors_schema = cb.load_json("anchors_schema.json")
+anchors_schema = cb.load_json("anchors.schema.json")
@@
-# 5) generate_trajectories / validation_loop도 zip 안에서 바로 사용
-gen = cb.import_py("generate_trajectories.py", "gen_traj")
-val = cb.import_py("validation_loop.py", "val_loop")
+val = cb.import_py("validation_loop.py", "val_loop")
@@
-# - 트랙 동기화(기본: 좌표만 대칭 변환, sys 불변)
-# gen.sync(...)
+# - 트랙 동기화 단계 제거(4트랙 직접 입력 정책)