# 작업 회수와 고아 객체 정리

`album-cleanup` CronJob은 5분마다 API 이미지의 `python -m app.cleanup`을 실행한다.
동시 실행은 금지하고 실패 시 두 번 재시도한다. 완료 Job은 10분 뒤 삭제한다.

- `PROCESSING` 상태가 600초를 넘으면 실패 횟수를 증가시켜 다시 큐에 넣는다.
  3회에 도달하면 `FAILED`로 종료한다.
- 오래된 `PENDING` 사진이 Redis 큐에 없으면 큐 등록을 복구한다.
- 원본/썸네일 중 DB에서 참조하지 않고 24시간 이상 지난 객체만 삭제한다.
  업로드 중인 객체를 보호하기 위해 유예 시간을 둔다.
- worker는 `PENDING` 행을 원자적으로 선점한다. `processing_started_at`과
  처리 Pod를 완료 시 다시 비교하므로 회수된 작업의 이전 실행이 DB 결과를 덮어쓰지 않는다.

`CLEANUP_STALE_SECONDS`(기본 600), `CLEANUP_OBJECT_GRACE_SECONDS`(86400),
`MAX_ATTEMPTS`(3)로 조절한다. 만료 시간은 worker heartbeat timeout(120초),
liveness 실패 감지 시간, termination grace(60초)의 합보다 길게 유지한다.
장시간 이미지 처리를 허용할 때 이 값들을 함께 늘린다.

DB와 Redis 사이에는 분산 트랜잭션이 없다. 큐 등록은 DB 행 잠금을 보유한 동안
수행한다. DB commit 전 소비한 worker는 잠금 해제를 기다린다. 중단으로 인한
누락은 다음 cleanup이 복구하고 중복 전달은 worker의 상태 선점으로 차단한다.

## 검증 (2026-10-15, dev K3S)

- API pytest 12개, worker pytest 7개 통과; 변경 Python 파일의 ruff 통과.
- 실서비스 회귀 시나리오: 만료 lease, 활성 lease, 재시도 소진,
  누락 enqueue, 고아 객체/참조 객체 구분, 재실행 멱등성 확인.
- dev-m3 배포 후 업로드 → DONE → 썸네일 2종 → 원본 → 삭제 smoke 통과.
- CronJob에서 만든 검증 Job 완료, 기존 데이터에서 회수/삭제 대상 0개.

실서비스 시나리오는 기존 데이터와 분리한 schema·queue·bucket을 만들고 삭제한다.
저장소 루트에서 다음과 같이 실행한다.

```bash
ssh kube-dev 'kubectl -n album-dev exec -i deployment/api -- python -' \
  < apps/api/tests/cleanup_scenarios.py
```
