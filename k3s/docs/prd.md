# PRD: Mini Photo Album on K3S (쿠버네티스 학습용)

> **원문 보관본.** 2026-10-14에 전달받은 PRD v1.1을 내용 수정 없이 옮겼다.
> 구현 중 원문과 달라진 결정(MinIO 이미지 소스 빌드, GHCR 푸시 시점, 터널 포트 등)은 이 파일을 고치지 않고 [plan.md](plan.md)에 기록한다.
> 12장 미결 사항(Q-01~Q-03)의 결정은 plan.md 1.1, 실험 E-01~E-15의 상세는 [experiments/README.md](experiments/README.md)에 있다.

| 항목 | 내용 |
|---|---|
| 문서 버전 | v1.1 |
| 작성일 | 2026-10-14 |
| 상태 | Draft |
| 목적 | 쿠버네티스 핵심 개념 학습 (Pod 분리, 확장, 관측성, 스케일링, CI/CD) |

### 변경 이력

| 버전 | 내용 |
|---|---|
| v1.0 | 초안 작성: 아키텍처, 기능 요구사항, 관측성, 실험 시나리오 E-01~E-10 |
| v1.1 | dev/prod를 별개 VM(독립 K3S 클러스터)으로 분리. CI/CD(GitHub Actions + ArgoCD GitOps) 설계 추가, Sealed Secrets 필수화, 실험 E-11~E-15 추가, 마일스톤과 완료 기준 개정, `X-App-Version` 헤더 추가 |

---

## 1. 개요

### 1.1 목적

이미지를 업로드하면 비동기로 썸네일을 만들어 주는 간단한 사진 앨범 서비스다. 서비스 자체보다는 이 서비스를 만들고 운영하면서 쿠버네티스의 핵심 개념을 직접 익히는 것이 목적이다. 그래서 기능은 최소한으로 두고 다음 항목을 체험할 수 있는 구조로 설계한다.

- **Pod 분리:** 역할별로 워크로드를 나눈다.
- **확장:** 부하에 따라 수평 확장한다.
- **관측:** 메트릭과 대시보드로 상태를 본다.
- **장애 대응:** 셀프 힐링과 롤백을 경험한다.
- **배포 자동화:** GitOps 기반 CI/CD로 환경을 승격한다.

### 1.2 가정 사항

| 항목 | 가정 |
|---|---|
| 클러스터 | dev VM과 prod VM에 각각 독립된 K3S 단일 노드 클러스터. 노드당 4 vCPU / 8GB 이상 (ArgoCD와 모니터링 스택을 고려하면 8GB가 사실상 최소) |
| 네트워크 | 두 VM 모두 사설망에 있고 인바운드는 외부에 열지 않는다. 아웃바운드 인터넷(GitHub, GHCR 접근)만 가능하다 |
| 사용자 | 본인 1인 (인증 없음) |
| 언어 | Python (FastAPI + Pillow). 학습 초점이 K8s이므로 앱 코드는 단순하게 둔다 |
| 배포 도구 | Kustomize (base + dev/prod overlay). 인프라 컴포넌트는 Helm |
| Git / CI | GitHub 저장소, GitHub Actions (GitHub 호스팅 러너) |
| 레지스트리 | GHCR (`ghcr.io/<user>/album-*`) |
| CD | ArgoCD를 클러스터마다 하나씩 설치하는 GitOps(Pull) 방식 |
| 도메인 | 내부망 접근 기준 `album.dev.local`, `album.local` (hosts 파일 또는 nip.io) |
| 로컬 접근 | 작업 PC의 kubeconfig에 `k3s-dev`, `k3s-prod` 두 context를 등록해서 사용 |

### 1.3 범위 밖 (Non-Goals)

- 로그인과 다중 사용자
- 앨범 공유, 태그, 검색
- CDN
- 고가용성 DB 클러스터
- 서비스 메시 (Istio 등)
- 멀티 노드 HA (확장 과제)

---

## 2. 학습 목표와 기능 매핑

| 쿠버네티스 개념 | 서비스에서 적용되는 지점 | 확인 방법 |
|---|---|---|
| Namespace | `album-dev` / `album-prod`, `monitoring`, `argocd` 분리 | `kubectl get all -n ...` |
| Deployment / ReplicaSet | frontend, api, worker | Pod 삭제 후 자동 복구 확인 |
| StatefulSet + PVC | PostgreSQL, MinIO, Redis | Pod 재시작 후에도 데이터가 남는지 확인 |
| Service (ClusterIP) | 컴포넌트 간 내부 통신 | DNS 이름(`api.album-dev.svc`)으로 호출 |
| Ingress (Traefik, K3S 기본) | `/` → frontend, `/api` → api | 경로 기반 라우팅 |
| ConfigMap / Secret | 썸네일 크기, DB 비밀번호, MinIO 키 | 설정 변경 후 롤아웃 |
| Liveness / Readiness Probe | api `/healthz`, `/readyz` | DB를 중단해 readiness 실패 상황 관찰 |
| Resource Requests / Limits | 전체 워크로드 | 메모리 limit 초과 시 OOMKilled 관찰 |
| HPA (CPU 기반) | api | k6 부하 테스트로 replica 증가 관찰 |
| KEDA (큐 길이 기반) | worker | 대량 업로드 시 0→N 확장, 유휴 시 0으로 축소 |
| Rolling Update / Rollback | api 버전 업 | 롤아웃 상태 관찰, Git 기반 롤백 |
| Job / CronJob | DB 마이그레이션 Job, 고아 파일 정리 CronJob | 실행 이력과 로그 확인 |
| PodDisruptionBudget | api (minAvailable: 1) | `kubectl drain` 시 동작 확인 |
| NetworkPolicy | DB는 api/worker에서만 접근 허용 | 다른 Pod에서 접속을 시도해 차단 확인 |
| 관측성 | Prometheus + Grafana (+ Loki 선택) | 커스텀 대시보드 구성 |
| GitOps (ArgoCD) | dev 자동 배포, prod 수동 승격 | 드리프트 자가 복구, Sync 이력 확인 |
| Sealed Secrets | 클러스터별로 Secret 봉인 | 다른 클러스터에서 복호화되지 않는지 확인 |

---

## 3. 시스템 아키텍처

```
                 [Browser]
                     │
            ┌────────▼────────┐
            │ Ingress(Traefik) │
            └───┬─────────┬───┘
         /      │         │  /api
   ┌────────────▼──┐  ┌───▼──────────┐
   │ frontend      │  │ api (FastAPI)│◄── HPA (CPU)
   │ (nginx 정적)  │  └─┬────┬────┬──┘
   └───────────────┘    │    │    │
             ┌──────────┘    │    └──────────┐
       ┌─────▼──────┐ ┌──────▼─────┐  ┌──────▼──────┐
       │PostgreSQL  │ │ Redis      │  │ MinIO       │
       │(StatefulSet)│ │ (Queue)    │  │(원본/썸네일)│
       └─────▲──────┘ └──────┬─────┘  └──────▲──────┘
             │               │               │
             │        ┌──────▼──────┐        │
             └────────┤ worker      ├────────┘
                      │ (Pillow)    │◄── KEDA (Redis list length)
                      └─────────────┘
```

### 3.1 컴포넌트 정의

| 컴포넌트 | 종류 | 역할 | 확장 방식 |
|---|---|---|---|
| frontend | Deployment | 업로드 폼과 갤러리 화면 (정적 HTML/JS) | 고정 replica 2 |
| api | Deployment | 업로드 수신, 원본 MinIO 저장, 메타데이터 DB 기록, 작업 큐 등록, 목록/조회 API 제공 | HPA: CPU 60% |
| worker | Deployment | 큐 소비, 썸네일 생성(small 200px / medium 800px), MinIO 저장, 상태 갱신 | KEDA: 큐 길이 기준 |
| postgres | StatefulSet | 사진 메타데이터 저장 | 1 (확장하지 않음) |
| redis | StatefulSet | 작업 큐 (List, LPUSH/BRPOP) | 1 |
| minio | StatefulSet | 오브젝트 스토리지 (버킷: `originals`, `thumbnails`) | 1 |
| db-migrate | Job (ArgoCD PreSync 훅) | 스키마 생성과 마이그레이션 | 배포마다 1회 |
| smoke-test | Job (ArgoCD PostSync 훅) | 배포 후 동작 검증 | 배포마다 1회 |
| cleanup | CronJob | DB에 없는 고아 객체 삭제, FAILED 상태 재시도 | 매일 03:00 |

worker를 api에서 분리하는 이유는 두 워크로드의 확장 기준이 다르기 때문이다. 업로드 요청 처리는 CPU 부하가 낮고 썸네일 생성은 CPU 부하가 높다. 그래서 api는 HPA(CPU)로, worker는 KEDA(큐 길이)로 확장하며 두 방식을 비교해 볼 수 있다. 환경별 replica 범위는 5.4를 따른다.

---

## 4. 기능 요구사항

### 4.1 사용자 기능

| ID | 기능 | 설명 | 우선순위 |
|---|---|---|---|
| F-01 | 이미지 업로드 | JPG/PNG/WebP, 최대 10MB, 다중 선택 가능 | 필수 |
| F-02 | 처리 상태 표시 | PENDING → PROCESSING → DONE / FAILED | 필수 |
| F-03 | 갤러리 목록 | small 썸네일 그리드, 최신순, 페이지네이션 | 필수 |
| F-04 | 상세 보기 | medium 썸네일 표시, 원본 다운로드 | 필수 |
| F-05 | 삭제 | DB 레코드와 MinIO 객체를 함께 삭제 | 필수 |
| F-06 | 처리 Pod 표시 | 어떤 worker Pod가 썸네일을 만들었는지 표시 (`processed_by`) | 학습용 필수 |

F-06과 아래 응답 헤더는 일반 서비스에는 필요 없지만, 확장과 배포가 실제로 일어나는지 바로 확인할 수 있어서 넣는다.

- `X-Served-By: <pod-name>`: 로드밸런싱 확인용
- `X-App-Version: <image tag>`: 롤링 업데이트와 GitOps 배포 확인용. 빌드 시 환경 변수로 주입한다

### 4.2 API 명세

| Method | Path | 설명 |
|---|---|---|
| POST | `/api/photos` | multipart 업로드. 202 Accepted와 `{id, status}` 반환 |
| GET | `/api/photos?page=&size=` | 목록 조회 |
| GET | `/api/photos/{id}` | 상세 조회 (상태, 썸네일 URL 포함) |
| GET | `/api/photos/{id}/original` | 원본 다운로드 (MinIO presigned URL로 리다이렉트) |
| DELETE | `/api/photos/{id}` | 삭제 |
| GET | `/healthz` | liveness 체크. 프로세스가 살아 있는지만 확인 |
| GET | `/readyz` | readiness 체크. DB, Redis, MinIO 연결 확인 |
| GET | `/metrics` | Prometheus 메트릭 노출 |

worker도 `/healthz`와 `/metrics`를 별도 포트(8001)로 노출한다.

### 4.3 데이터 모델 (photos)

| 컬럼 | 타입 | 설명 |
|---|---|---|
| id | UUID | PK |
| filename | VARCHAR | 원본 파일명 |
| content_type | VARCHAR | MIME 타입 |
| size_bytes | BIGINT | 원본 크기 |
| original_key | VARCHAR | MinIO 객체 키 |
| thumb_small_key / thumb_medium_key | VARCHAR | 썸네일 키 |
| status | ENUM | PENDING / PROCESSING / DONE / FAILED |
| processed_by | VARCHAR | worker Pod 이름 |
| retry_count | INT | 재시도 횟수 |
| created_at / processed_at | TIMESTAMP | 처리 시간 계산용 |

### 4.4 처리 흐름

1. 사용자가 업로드하면 api가 원본을 MinIO `originals/{id}`에 저장한다.
2. api가 DB에 PENDING 상태로 레코드를 만들고, Redis `thumbnail:jobs`에 id를 넣은 뒤 202를 반환한다.
3. worker가 큐에서 id를 꺼내 PROCESSING으로 바꾸고, 원본을 받아 두 가지 크기로 리사이즈한다.
4. worker가 썸네일을 `thumbnails/{id}_s.webp`, `{id}_m.webp`에 저장하고 DONE으로 갱신한다.
5. 처리에 실패하면 retry_count를 올려 다시 큐에 넣고, 3회 실패하면 FAILED로 둔다.

부하 테스트에서 KEDA 확장을 확실히 관찰할 수 있도록, ConfigMap의 `ARTIFICIAL_DELAY_MS` 값으로 worker 처리 시간을 인위적으로 늘릴 수 있게 한다.

---

## 5. 비기능 요구사항

### 5.1 리소스 기준 (초기값, 실험하면서 조정)

| 컴포넌트 | requests (CPU/Mem) | limits (CPU/Mem) |
|---|---|---|
| frontend | 50m / 32Mi | 100m / 64Mi |
| api | 100m / 128Mi | 500m / 256Mi |
| worker | 200m / 256Mi | 1000m / 512Mi |
| postgres | 100m / 256Mi | 500m / 512Mi |
| redis | 50m / 64Mi | 200m / 128Mi |
| minio | 100m / 256Mi | 500m / 512Mi |

### 5.2 스토리지

- K3S 기본 제공인 `local-path` StorageClass를 사용한다.
- PVC 용량: postgres 2Gi, minio 10Gi, redis 1Gi
- 단일 노드라서 노드 장애가 나면 데이터가 보호되지 않는다. 이 한계도 학습 포인트로 문서화한다. 확장 과제로 Longhorn을 다룬다.

### 5.3 보안 (학습 수준)

- **Secret:** DB 비밀번호와 MinIO 키는 Secret으로 관리하고, Git에는 Sealed Secrets로 암호화해서만 올린다 (필수, 11.7 참고).
- **NetworkPolicy:** 기본적으로 모든 트래픽을 차단(default deny)하고 필요한 경로만 허용한다. K3S는 기본 flannel 환경에서도 NetworkPolicy를 지원한다.
- **컨테이너 권한:** 컨테이너는 non-root로 실행하고 `readOnlyRootFilesystem`을 적용한다.
- **CI 권한:** CI에는 클러스터 인증 정보를 두지 않는다.

### 5.4 환경 분리

| 항목 | dev VM | prod VM |
|---|---|---|
| api replica | HPA 1~3 | HPA 2~6 |
| worker | KEDA 0~2 | KEDA 0~5 |
| 이미지 태그 | `sha-<commit>` (main push마다 갱신) | `vX.Y.Z` (git tag 기준, dev와 같은 digest) |
| 배포 트리거 | main merge 시 자동 | Release PR merge 후 수동 Sync |
| ArgoCD 정책 | auto-sync, prune, selfHeal | 수동 Sync, selfHeal |
| 도메인 | `album.dev.local` | `album.local` |
| 로그 레벨 | DEBUG | INFO |
| Grafana | 클러스터마다 따로 설치 (중앙 통합은 확장 과제) | 동일 |

---

## 6. 관측성 (Observability)

### 6.1 스택

- `kube-prometheus-stack` Helm 차트로 Prometheus, Grafana, Alertmanager, node-exporter, kube-state-metrics를 함께 설치한다.
- 앱 메트릭은 ServiceMonitor로 수집한다.
- 로그 수집은 선택 과제로 Loki와 Promtail(또는 Grafana Alloy)을 붙인다.

### 6.2 커스텀 메트릭

| 메트릭 | 타입 | 출처 |
|---|---|---|
| `album_uploads_total{status}` | Counter | api |
| `album_http_request_duration_seconds` | Histogram | api |
| `album_queue_length` | Gauge | api (Redis LLEN) |
| `album_thumbnail_processing_seconds` | Histogram | worker |
| `album_thumbnail_jobs_total{result}` | Counter | worker |

### 6.3 Grafana 대시보드 (직접 제작)

1. **서비스 개요:** 업로드 RPS, 에러율, p95 응답시간
2. **큐와 워커:** 큐 길이와 worker replica 수를 한 그래프에 겹쳐 KEDA 반응 속도를 확인
3. **API 확장:** CPU 사용률과 HPA replica 수를 함께 표시
4. **리소스:** Pod별 CPU/Mem 사용량을 requests/limits 대비로 표시하고, OOMKilled와 재시작 횟수를 표시
5. **썸네일 처리 시간:** p50/p95 분포

대시보드 JSON은 `dashboards/`에 두고, ConfigMap(Grafana sidecar)으로 GitOps 배포한다.

### 6.4 알림 (Alertmanager)

- 큐 길이가 5분 넘게 100을 초과할 때
- api 5xx 비율이 5%를 초과할 때
- Pod가 CrashLoopBackOff 상태일 때

---

## 7. 학습 실험 시나리오 (수용 기준)

### 7.1 쿠버네티스 핵심 (E-01~E-10)

| # | 시나리오 | 수행 방법 | 기대 결과 |
|---|---|---|---|
| E-01 | 셀프 힐링 | api Pod 강제 삭제 | 수초 내 재생성되고 서비스 중단이 없음 |
| E-02 | HPA 확장 | k6로 목록 API에 200 VU 부하 | CPU가 60%를 넘으면 replica가 늘고, 부하가 끝나면 약 5분 뒤 축소됨 |
| E-03 | KEDA 확장 | 이미지 500장 일괄 업로드 스크립트 실행 | worker가 0에서 N으로 늘고, 큐가 비면 0으로 돌아옴 |
| E-04 | 롤링 업데이트 | api v1 → v2 배포 | `X-App-Version`이 무중단으로 전환됨 |
| E-05 | 롤아웃 중단 | readiness가 실패하는 v3 배포 | 롤아웃이 멈추고 기존 Pod가 계속 서비스함 (dev에서 수동 배포 단계에 `rollout undo` 실습) |
| E-06 | OOM | worker 메모리 limit을 64Mi로 낮추고 큰 이미지 처리 | OOMKilled 발생, 재시도 후 FAILED 처리 확인 |
| E-07 | 의존성 장애 | postgres를 replica 0으로 축소 | api readiness가 실패해 트래픽이 끊기고, 복구 시 자동으로 정상화됨 |
| E-08 | 데이터 영속성 | postgres/minio Pod 삭제 | 재기동 후 데이터 유지 |
| E-09 | NetworkPolicy | frontend Pod에서 postgres 접속 시도 | 차단됨 |
| E-10 | 설정 변경 | ConfigMap의 썸네일 크기 변경 | 롤아웃 후 새 크기 적용 |

### 7.2 CI/CD (E-11~E-15)

| # | 시나리오 | 수행 방법 | 기대 결과 |
|---|---|---|---|
| E-11 | GitOps 자동 배포 | api 코드를 한 줄 고쳐 main에 push | 별도 조작 없이 수 분 안에 dev에 새 Pod가 뜨고 `X-App-Version`이 새 sha로 바뀜 |
| E-12 | 드리프트 자가 복구 | dev에서 `kubectl scale deploy/frontend --replicas=5` 실행 | ArgoCD가 감지해서 Git에 정의된 2개로 되돌림 |
| E-13 | 운영 승격 | `git tag v1.1.0` 생성 → PR merge → Sync | prod 이미지 digest가 dev와 같은지 `kubectl get pod -o jsonpath`로 확인 |
| E-14 | GitOps 롤백 | prod에서 `rollout undo`를 먼저 시도한 뒤 `git revert`로 다시 롤백 | 앞의 방법은 ArgoCD가 덮어쓰고, 뒤의 방법은 Git 이력이 남은 채로 롤백됨 |
| E-15 | 배포 게이트 | 마이그레이션이 실패하도록 만든 버전을 배포 | PreSync 훅이 실패해서 기존 버전이 그대로 서비스됨 |

각 실험 결과는 Grafana 스크린샷, 관련 `kubectl` 출력, 관찰 내용과 함께 `k3s/docs/experiments/E-XX.md`에 기록한다.

---

## 8. 저장소 구조

학습용 단일 저장소에서 기존 K3S 프로젝트와 AKS 전환 프로젝트를 디렉터리로 분리한다. K3S 앱 코드와 배포 설정은 `k3s/`, AKS 구현은 `aks/`, 두 프로젝트의 GitHub Actions는 루트 `.github/workflows/`에서 각각 관리한다.

```
kube-study/
├── .github/workflows/             (K3S와 AKS CI/Release 분리)
│   ├── ci.yaml                   (PR/main: 테스트, 빌드, dev 태그 갱신)
│   └── release.yaml              (tag v*: 재태깅, prod PR 생성)
├── AGENTS.md
├── README.md
├── k3s/
│   ├── apps/
│   │   ├── api/                   (FastAPI, Dockerfile)
│   │   ├── worker/                (Pillow, Dockerfile)
│   │   └── frontend/              (정적 파일 + nginx Dockerfile)
│   ├── k8s/
│   │   ├── base/                  (각 컴포넌트 매니페스트)
│   │   └── overlays/
│   │       ├── dev/               ← CI가 이미지 태그를 자동 갱신
│   │       └── prod/              ← Release PR로만 변경
│   ├── argocd/                    (bootstrap, dev/prod Application)
│   ├── infra/                     (Helm values와 Azure VM 설정)
│   ├── scripts/                   (VM 초기화, CI helper, 접근·검증 도구)
│   ├── loadtest/                  (k6와 대량 업로드 스크립트)
│   ├── dashboards/                (Grafana JSON)
│   └── docs/                      (실험 결과와 운영 절차)
└── aks/                           (독립 AKS 전환 프로젝트)
```

---

## 9. 마일스톤

M2부터 M6까지는 일부러 `kubectl apply -k`로 손수 배포한다. 리소스가 어떻게 만들어지는지 직접 겪어 본 다음에 자동화해야, ArgoCD가 대신 해 주는 일이 무엇인지 이해할 수 있기 때문이다.

| 단계 | 내용 | 학습 키워드 | 기간 |
|---|---|---|---|
| M1 | docker-compose로 로컬에서 동작 확인 | 컨테이너화, 멀티스테이지 빌드 | 1주 |
| M2 | dev 클러스터에 전체 수동 배포 | Deployment, Service, StatefulSet, PVC, Ingress, ConfigMap/Secret | 1~2주 |
| M3 | 헬스체크, 리소스, Job/CronJob | Probe, requests/limits, Job | 1주 |
| M4 | 모니터링 구축과 대시보드 제작 | Prometheus, ServiceMonitor, Grafana | 1주 |
| M5 | 오토스케일링과 부하 테스트 (E-02, E-03) | HPA, KEDA, k6 | 1주 |
| M6 | 운영 기능과 실험 (E-01, E-04~E-10) | Rolling update, PDB, NetworkPolicy | 1주 |
| M7 | CI 구축: GitHub Actions, GHCR, Trivy, dev 태그 자동 갱신 | CI, 이미지 태깅 전략 | 1주 |
| M8 | dev에 GitOps 적용: ArgoCD, app-of-apps, Sealed Secrets, 훅 (E-11, E-12, E-15) | GitOps, Sync Wave, Hook | 1~2주 |
| M9 | prod 클러스터 구축과 승격: 빈 VM에서 bootstrap만으로 재현, Release 워크플로 (E-13, E-14) | 환경 승격, 재현성 | 1주 |
| 확장 | Argo Rollouts(카나리 배포), ArgoCD Image Updater, Loki, 두 클러스터 메트릭 통합(Thanos 또는 Grafana 원격 데이터소스), Renovate, Longhorn, cert-manager, 멀티 노드 | - | - |

---

## 10. 완료 기준

1. E-01~E-15를 모두 수행하고, 결과를 `docs/`에 기록한다.
2. prod VM을 초기화한 상태에서 "K3S 설치 → ArgoCD 설치 → root Application apply" 세 단계만으로 서비스 전체(모니터링 포함)가 복구된다.
3. 코드 push부터 prod 반영까지 `kubectl`을 한 번도 직접 실행하지 않는다.
4. 6.3의 대시보드 1~5번이 dev와 prod 양쪽에서 실제 데이터로 동작한다.

---

## 11. CI/CD 설계

### 11.1 배포 방식 결정: Push가 아닌 Pull(GitOps)

GitHub 호스팅 러너는 인터넷에 있고, 두 VM의 K3S API(6443)는 사설망에 있다. 그래서 CI에서 `kubectl apply`를 실행하는 Push 방식을 쓰려면 API를 외부에 노출하거나, VM마다 self-hosted 러너를 따로 두어야 한다.

GitOps 방식은 이 문제를 구조적으로 피한다. CI는 이미지를 빌드해서 Git에 원하는 상태를 커밋하는 데까지만 책임진다. 각 클러스터의 ArgoCD가 바깥으로 나가 Git을 읽어 와서 스스로 반영한다.

| 구분 | Push (CI → kubectl) | Pull (GitOps, 채택) |
|---|---|---|
| 클러스터 API 노출 | 필요 (또는 self-hosted 러너) | 불필요 |
| CI가 갖는 권한 | 클러스터 관리자 권한 | Git 쓰기, 레지스트리 푸시만 |
| 드리프트 감지 | 없음 | 있음 (selfHeal) |
| 롤백 | 파이프라인 재실행 | `git revert` |

### 11.2 전체 흐름

```
 개발자 push (main)
        │
        ▼
 ┌──────────────── GitHub Actions (CI) ────────────────┐
 │ 1. lint / unit test (ruff, pytest)                  │
 │ 2. docker buildx build (변경된 앱만, path filter)   │
 │ 3. 이미지 스캔 (Trivy, HIGH 이상이면 실패)          │
 │ 4. GHCR push  → tag: sha-<7자리>                     │
 │ 5. k3s/k8s/overlays/dev 이미지 태그 갱신 → bot 커밋 │
 └─────────────────────────────────────────────────────┘
        │ (Git 변경)
        ▼
 [dev VM] ArgoCD ── 자동 Sync ──▶ album-dev 배포
        │                          └ PostSync: 스모크 테스트 Job
        │
 개발자: git tag v1.2.0
        │
        ▼
 ┌──────────────── GitHub Actions (Release) ───────────┐
 │ 1. sha-xxxx 이미지를 v1.2.0으로 재태깅 (재빌드 X)    │
 │ 2. k3s/k8s/overlays/prod 태그 갱신 → PR 자동 생성   │
 └─────────────────────────────────────────────────────┘
        │ (본인이 PR 리뷰 후 merge = 운영 승인)
        ▼
 [prod VM] ArgoCD ── 변경 감지 ──▶ OutOfSync 표시
                                   → 수동 Sync → album-prod 배포
```

### 11.3 핵심 원칙

| 원칙 | 내용 |
|---|---|
| Build once, promote many | 운영 이미지는 다시 빌드하지 않는다. dev에서 검증한 이미지 digest에 태그만 추가한다(`docker buildx imagetools create`). dev와 prod가 바이트 단위로 같은 이미지를 쓰도록 보장하기 위해서다. |
| 환경 차이는 overlay에만 | 앱 코드와 이미지는 같고, replica 수, HPA 범위, 로그 레벨, 도메인만 Kustomize overlay로 다르게 둔다. |
| dev는 자동, prod는 사람이 승인 | dev Application은 `automated: {prune: true, selfHeal: true}`로 설정한다. prod는 PR merge와 수동 Sync, 두 단계를 거친다. |
| 무한 루프 방지 | CI의 bot 커밋은 `k8s/**` 경로만 바꾸고, 빌드 워크플로는 `apps/**` 경로 변경에만 반응하도록 path filter를 건다. |

### 11.4 GitHub Actions 워크플로

| 워크플로 | 트리거 | 단계 |
|---|---|---|
| `ci.yaml` | PR, main push (`apps/**`) | PR: lint, 테스트, 빌드(푸시 없음). main: 위 단계에 더해 Trivy, GHCR 푸시, dev overlay 태그 갱신 커밋 |
| `release.yaml` | tag `v*` | 해당 커밋의 `sha-*` 이미지를 `vX.Y.Z`로 재태깅하고, prod overlay 태그를 갱신하는 PR 생성 |

### 11.5 ArgoCD 구성 (app-of-apps)

각 클러스터의 ArgoCD는 자기 환경 디렉터리(`argocd/dev` 또는 `argocd/prod`)만 바라본다. 클러스터 초기 구성 시 손으로 하는 작업은 K3S 설치, ArgoCD Helm 설치, root Application 한 개 apply, 이렇게 세 가지뿐이다.

| Application | 소스 | dev | prod |
|---|---|---|---|
| infra-monitoring | kube-prometheus-stack Helm | 자동 Sync | 자동 Sync |
| infra-keda | KEDA Helm | 자동 Sync | 자동 Sync |
| infra-sealed-secrets | sealed-secrets Helm | 자동 Sync | 자동 Sync |
| album | `k8s/overlays/{env}` | 자동 Sync + selfHeal | 수동 Sync |

설치 순서는 Sync Wave로 보장한다. CRD를 제공하는 컴포넌트(sealed-secrets, KEDA 등)가 wave -1, 앱이 wave 0이다.

### 11.6 배포 훅

| 훅 | Job | 역할 |
|---|---|---|
| PreSync | db-migrate | 새 버전 배포 전에 스키마를 마이그레이션한다. 실패하면 배포가 중단된다. |
| PostSync | smoke-test | `/readyz` 확인, 테스트 이미지 1장 업로드, DONE 상태가 될 때까지 대기(최대 60초). 실패하면 Application이 Degraded로 표시된다. |

### 11.7 Secret 관리 (Sealed Secrets 필수)

GitOps에서는 Git이 진실의 원천이므로 평문 Secret을 Git에 둘 수 없다.

- **클러스터별 봉인:** 각 클러스터의 sealed-secrets 컨트롤러는 자기만의 키 쌍을 가진다. 같은 비밀번호라도 `kubeseal --context k3s-dev`, `--context k3s-prod`로 따로 봉인해서 각 overlay에 둔다. dev용 SealedSecret은 prod에서 복호화되지 않는데, 이 특성도 학습 포인트다.
- **키 백업:** 컨트롤러의 private key는 클러스터를 다시 만들 때 반드시 필요하므로 Git 바깥에 별도로 백업한다. 백업 절차는 `docs/`에 기록한다.
- **CI 쪽 Secret:** GitHub Actions에는 `GITHUB_TOKEN`(GHCR 푸시, bot 커밋, PR 생성용)만 둔다. 클러스터 인증 정보는 CI에 전혀 두지 않는다.
- **이미지 pull:** GHCR 패키지를 private으로 둔다면 클러스터마다 imagePullSecret도 SealedSecret으로 배포한다.

### 11.8 롤백 전략

| 상황 | 방법 |
|---|---|
| 정식 롤백 (권장) | prod overlay 태그를 바꾼 커밋을 `git revert`하고 Sync한다. 이력이 Git에 남는다. |
| 긴급 롤백 | ArgoCD UI에서 History → Rollback을 실행한다. 일시적으로 Git과 상태가 달라지므로 사후에 Git을 맞춰 줘야 한다. |
| 사용 금지 | prod에서 `kubectl rollout undo`는 쓰지 않는다. ArgoCD가 Git 상태로 되돌리기 때문이다 (E-14에서 확인). |

---

## 12. 미결 사항 (Open Questions)

| # | 질문 | 영향 범위 |
|---|---|---|
| Q-01 | Git 호스팅을 GitHub로 할지, GitLab이나 Gitea를 자체 운영할지 | 자체 운영이면 CI가 GitLab CI 또는 Gitea Actions로 바뀌고, Harbor 같은 사설 레지스트리 구축이 필요해서 11장 구성이 달라짐 |
| Q-02 | GHCR 패키지를 public으로 둘지 private으로 둘지 | private이면 imagePullSecret 관리가 추가됨 (11.7) |
| Q-03 | 작업 PC에서 각 VM의 Ingress와 ArgoCD UI에 접근하는 방식 (hosts 파일, nip.io, 내부 DNS) | 도메인 설정과 TLS 적용 여부 |
