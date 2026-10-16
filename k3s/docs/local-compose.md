# M1: docker-compose로 전체 동작 확인

쿠버네티스에 올리기 전에 dev VM에서 docker-compose로 전체 서비스를 띄워 동작을 확인한다. 작업 PC에서는 실행하지 않는다 ([plan.md](plan.md) 1.5).

## 구성

```
브라우저 ──(SSH 터널 :8088)──▶ gateway(nginx) ─┬─ /            → frontend (nginx 정적)
                                               ├─ /api/        → api (FastAPI)
                                               └─ /originals/, /thumbnails/ (GET만) → minio
api ─▶ postgres / redis / minio      worker ─▶ redis(큐) / minio / postgres
migrate: api 이미지로 SQL 마이그레이션을 한 번 실행하고 종료 (K8s에서는 Job → ArgoCD PreSync 훅)
```

`gateway`는 K8s의 Ingress(Traefik) 역할을 흉내 낸다. 썸네일·원본은 api가 만든 **presigned URL**로 브라우저가 MinIO에서 직접 받는데, 서명에 Host가 포함되므로 api는 브라우저가 접속하는 주소(`S3_PUBLIC_ENDPOINT`)로 서명하고 gateway는 Host 헤더를 그대로 넘긴다.

| 서비스 | 이미지 | 실행 UID | 비고 |
|---|---|---|---|
| api | `apps/api` | 10001 | read-only root FS, `/tmp`만 tmpfs |
| worker | `apps/worker` | 10001 | read-only root FS, 메트릭/헬스 :8001 |
| frontend | `apps/frontend` (nginx-unprivileged) | 101 | :8080 |
| minio | `infra/minio` (소스 빌드) | 10001 | 아래 참고 |
| gateway | nginx-unprivileged | 101 | 127.0.0.1:8088에만 바인딩 |

### MinIO 이미지

MinIO 공식 컨테이너 이미지(Docker Hub `minio/minio`, `quay.io/minio/minio`)는 더 이상 받을 수 없고 upstream 저장소도 archive됐다. 그래서 마지막 릴리스 태그 `RELEASE.2025-10-15T17-29-55Z`를 `infra/minio/Dockerfile`로 직접 빌드한다. 앞으로 보안 패치가 나오지 않으므로 M7의 Trivy 스캔에서 이 이미지를 어떻게 처리할지 정해야 한다.

## 실행 (dev VM)

```bash
ssh kube-dev
cd ~/kube-study/k3s             # 작업 PC에서 scripts/sync.sh dev 또는 git pull로 최신화
scripts/compose-env.sh          # 최초 1회: 임의 비밀번호로 .env 생성 (gitignore 대상, 권한 600)
docker compose up -d --build --wait
python3 scripts/smoke.py        # 업로드 → DONE → 썸네일 2종 → 원본 → 삭제
```

작업 PC 브라우저에서 보려면 별도 터널을 연다.

```bash
ssh -N -L 8088:127.0.0.1:8088 kube-dev
open http://localhost:8088
```

정리: `docker compose down` (데이터 유지) / `docker compose down -v` (볼륨까지 삭제).

### 설정 값 (환경 변수)

| 변수 | 기본값 | 설명 |
|---|---|---|
| `THUMB_SMALL_PX` / `THUMB_MEDIUM_PX` | 200 / 800 | 썸네일 긴 변 크기 |
| `ARTIFICIAL_DELAY_MS` | 0 | worker 처리를 일부러 늦춤 (KEDA 실험용) |
| `MAX_ATTEMPTS` | 3 | 이 횟수만큼 실패하면 FAILED |
| `LOG_LEVEL` | DEBUG | compose 기본값 |

예: `ARTIFICIAL_DELAY_MS=3000 docker compose up -d worker`

## 동작 방식에서 알아 둘 점

- **liveness와 readiness 분리:** `/healthz`는 프로세스만 확인하고, `/readyz`는 Postgres·Redis·MinIO 연결을 확인한다. DB가 죽었을 때 Pod를 재시작하는 대신 트래픽만 끊기게 하려는 것이다 (E-07).
- **worker 신뢰성 큐:** worker는 `BLMOVE`로 작업을 자기 전용 처리 목록(`thumbnail:jobs:processing:<pod 이름>`)으로 옮긴 뒤 처리하고, 끝나면 지운다. 처리 중 프로세스가 죽으면(예: OOMKilled) 같은 이름으로 재시작된 컨테이너가 그 목록을 보고 실패 1회로 계산해 다시 큐에 넣는다 (E-06). Pod 자체가 사라져 이름이 바뀐 경우 남은 작업은 M3의 cleanup CronJob이 처리한다.
- **이미지 판별:** 업로드는 Content-Type 헤더가 아니라 파일 앞부분(magic bytes)으로 JPEG/PNG/WebP를 판별한다. 헤더만 그럴듯하고 내용이 깨진 파일은 worker에서 3회 실패 후 FAILED가 된다.
- **메트릭 출처:** `album_uploads_total`, `album_http_request_duration_seconds`, `album_queue_length`는 api `/metrics`, `album_thumbnail_*`는 worker `:8001/metrics`.

## 검증 결과 (2026-10-14, dev VM)

| 항목 | 결과 |
|---|---|
| 전체 기동 | 8개 서비스 정상, migrate exit 0, api/minio/postgres/redis healthy |
| smoke | 업로드 202 → DONE → small 200×100 / medium 800×400 WebP → 원본 다운로드 → 삭제 후 404 |
| 깨진 파일 | 재시도 3회 후 `FAILED`, `retry_count=3`, 에러 메시지 기록 |
| worker 강제 종료 | 처리 중 `SIGKILL` → 재시작 후 "recovered 1 in-flight job" → `DONE`, `retry_count=1` |
| Postgres 중단 | `/readyz` 503 (postgres만 error), `/healthz` 200 유지, 재기동 후 `/readyz` 200 |
| 마이그레이션 재실행 | "0 applied now" (멱등) |
| gateway | `/originals/`·`/thumbnails/` 목록 조회와 PUT은 403 |
| non-root | 모든 앱 컨테이너 UID ≠ 0 |
| 브라우저 | 갤러리 썸네일, 상세 보기, 처리 Pod·버전 표시 확인 |

### 발견한 문제

`scripts/sync.sh`의 `rsync --delete`가 VM에만 있는 `.env`를 지워 compose가 기동되지 않았다. `protect` 필터로 `.env`와 `.venv`를 보호하도록 고쳤다.
