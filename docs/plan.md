# 작업 계획서: Mini Photo Album on K3S

| 항목 | 내용 |
|---|---|
| 작성일 | 2026-10-14 |
| 기준 문서 | PRD v1.1 (Mini Photo Album on K3S, 쿠버네티스 학습용) |
| 저장소 | https://github.com/winty5959/kube-study (public) |
| 상태 | M3 완료 (2026-10-15), M4 진행 중 |

---

## 1. 확정된 결정 사항

### 1.1 PRD 미결 사항(Open Questions) 결정

| # | 질문 | 결정 |
|---|---|---|
| Q-01 | Git 호스팅 | GitHub (`winty5959/kube-study`). CI는 GitHub Actions, 레지스트리는 GHCR |
| Q-02 | GHCR 패키지 공개 여부 | **public**. imagePullSecret 관리 생략 |
| Q-03 | 작업 PC에서 Ingress/ArgoCD UI 접근 방식 | **SSH 터널(A안)**. 아래 1.4 참고 |

### 1.2 저장소 운영

| 항목 | 결정 |
|---|---|
| 구조 | PRD 8장의 디렉터리 구조를 레포 루트에 바로 배치 (`apps/ k8s/ argocd/ infra/ loadtest/ dashboards/ docs/ scripts/ .github/`) |
| 브랜치 | 학습용이므로 `main` 직접 커밋. M7 이후 prod 승격만 Release PR |
| 커밋 | 기능 단위로 분리. 비자명한 결정은 Lore 트레일러 사용. 메시지는 영어 |
| 문서 | 한국어. 실험 결과는 `docs/experiments/E-XX.md` |
| 보안 | 평문 Secret, kubeconfig, sealed-secrets 개인키, `.venv`는 `.gitignore` |
| gh 인증 | `gh auth login` 대신 셸 환경변수 `GITHUB_TOKEN`을 `GH_TOKEN`으로 사용. 토큰 값은 어떤 출력/문서에도 남기지 않음 |
| CI 권한 | GitHub Actions에는 기본 `GITHUB_TOKEN`만 사용. 클러스터 인증 정보는 CI에 두지 않음 |

### 1.3 Azure 인프라

| 항목 | 결정 |
|---|---|
| 테넌트 / 구독 | KT Open Tenant / `AX사업부문-인프라아키텍처팀` |
| 리전 | `koreacentral` |
| 리소스 그룹 | `rg-seonung-kube-study` (신규) |
| VM 크기 | `Standard_B4as_v2` (4 vCPU / 16 GiB, amd64, on-demand) |
| OS / 디스크 | Ubuntu 24.04 LTS, Standard SSD 64 GiB |
| 네트워크 | VNet 1개, dev/prod 서브넷. NSG는 작업 PC 공인 IP → 22만 허용. 공인 IP는 SSH 용도로만 부여 |
| auto-shutdown | 매일 KST 18:00 |
| prod VM | **M9 직전에 생성**. 실험 외 시간에는 `az vm deallocate`로 꺼둠 |
| 재현성 | VM 생성은 `infra/azure/` 스크립트로 두어 prod VM을 같은 방식으로 재현 |

예상 비용(2026-10-14 조회, Linux on-demand 기준):

| 구성 | 시간당 | 월 (8h × 22일) | 월 (24×7) |
|---|---|---|---|
| B4as_v2 VM | $0.187 | 약 $33 | 약 $137 |
| Standard SSD E6 64 GiB | - | 약 $4.8 | 동일 |
| 공인 IP (Standard) | - | 약 $3.6 | 동일 |
| **dev 1대 합계** | - | **약 $41** | 약 $145 |

검토했으나 채택하지 않은 안:

| SKU | 월 (8h × 22일) | 미채택 사유 |
|---|---|---|
| B2as_v2 (2 vCPU / 8 GiB) | 약 $16 | ArgoCD + 모니터링 + 앱 + k6 동시 구동 시 CPU 크레딧 소진 위험. HPA/KEDA 실험 왜곡 가능 |
| D4as_v5 Spot (4 vCPU / 16 GiB) | 약 $7 | 가장 저렴하고 성능도 좋으나 Azure 용량 부족 시 예고 없이 VM이 꺼짐(eviction). 사용자가 중단 가능성을 받아들이지 않아 미채택 |
| D4as_v5 on-demand | 약 $37 | B4as_v2보다 비싸고 학습용으로는 성능 차이가 의미 없음 |

주의: B4as_v2는 Burstable이라 부하 테스트(M5) 중 CPU 크레딧이 소진되면 성능이 떨어져 HPA 실험 결과가 왜곡될 수 있다. 실험 시 `CPU Credits Remaining` 메트릭을 함께 기록한다.

### 1.4 접근 방식 (SSH 터널)

PRD는 "VM은 사설망, 인바운드 미개방"을 가정한다. 작업 PC 브라우저에서 앱(`album.dev.local`), ArgoCD UI, Grafana UI를 보고 `kubectl`로 6443에 접근해야 하므로 다음과 같이 한다.

- NSG에서 작업 PC 공인 IP → 22만 허용
- `scripts/tunnel.sh <env>`로 `ssh -L` 포트 포워딩 (Ingress 80, API 6443. ArgoCD/Grafana UI는 Ingress 호스트 이름으로 같은 포트 사용)
- 작업 PC `/etc/hosts`에 `127.0.0.1 album.dev.local` 등록 → `http://album.dev.local:8080` 접속
- 작업 PC kubeconfig에 `k3s-dev` / `k3s-prod` context 등록, server 주소는 터널 경유 `127.0.0.1:16443` / `26443`
- 상세 절차: [access.md](access.md)
- TLS(cert-manager)는 확장 과제

검토했으나 미채택: Tailscale/VPN(외부 서비스 의존), 80/443 공인 IP 개방(PRD 가정 위배).

### 1.5 작업 위치 (작업 PC vs VM)

작업 PC(맥북)는 디스크 용량이 부족하므로 라이브러리와 이미지는 VM에만 둔다.

| 작업 | 위치 |
|---|---|
| 코드/매니페스트 편집, `git commit/push` | 작업 PC (`kube-study/`) |
| Python venv(`uv sync`), pytest, ruff | VM (작업 PC에 `.venv` 생성 금지) |
| docker build / compose / 이미지 | VM |
| kubectl, helm, k6, kubeseal, argocd CLI | VM (작업 PC는 터널 경유 `kubectl` 조회 정도만) |
| 동기화 | `git push` → VM `git pull`. 빠른 반복용 `scripts/sync.sh`(rsync, `.git`·`.venv` 제외) |

### 1.6 기타

| 항목 | 결정 |
|---|---|
| CPU 아키텍처 | amd64 통일 (VM, GitHub 러너 모두 amd64 → 멀티아키 빌드 불필요) |
| Python 패키지 관리 | uv (`pyproject.toml` + `uv.lock`, Dockerfile에서도 uv 사용) |
| SSH 키 | 프로젝트 전용 `~/.ssh/kube-study` (ed25519) 신규 생성 |
| 오브젝트 스토리지 | MinIO 유지. 공식 이미지 배포 중단·저장소 archive로 마지막 릴리스(`RELEASE.2025-10-15T17-29-55Z`)를 `infra/minio/`에서 소스 빌드해 `ghcr.io/winty5959/album-minio`로 사용 (2026-10-14 사용자 결정). SeaweedFS·RustFS는 미채택 |
| Python 버전 | 3.13 고정 (`.python-version`, Docker 베이스 `python:3.13-slim-bookworm`) |
| DB 마이그레이션 | Alembic 대신 순번 SQL 파일 + `python -m app.migrate` (테이블 1개라 충분, 학습 시 읽기 쉬움) |

---

## 2. 마일스톤

PRD의 M1~M9를 유지하고 앞에 M0(기반 준비)를 추가한다. 각 단계는 "검증" 기준을 통과한 뒤 다음 단계로 넘어간다. M2~M6는 PRD 의도대로 `kubectl apply -k`로 수동 배포한다.

| 단계 | 산출물 | 검증 |
|---|---|---|
| **M0 기반 준비** (완료) | GitHub 레포 생성, 디렉터리 골격, README, Azure dev VM 생성 스크립트 + 실행, K3S 설치, SSH 터널 스크립트, kubeconfig context 등록 | 작업 PC에서 `kubectl --context k3s-dev get nodes` → Ready |
| **M1 로컬 동작** (완료) | `apps/api`(FastAPI, uv), `apps/worker`(Pillow), `apps/frontend`(정적 + nginx), 멀티스테이지 Dockerfile(non-root), `docker-compose.yaml`(postgres/redis/minio 포함), pytest 최소 테스트 | VM에서 compose 기동 → 업로드 → DONE 상태, 썸네일 2종 확인 |
| **M2 수동 배포** (완료) | `k8s/base/` 전 컴포넌트, `k8s/overlays/dev`, Ingress 경로 라우팅, ConfigMap/Secret (이 단계는 평문 Secret을 `.gitignore`로 제외) | `kubectl apply -k k8s/overlays/dev` 후 터널 경유 브라우저에서 업로드 동작 |
| **M3 헬스/리소스/Job** (완료) | liveness/readiness probe, requests/limits, db-migrate Job, cleanup CronJob, `X-Served-By`/`X-App-Version` 헤더 | E-07, E-08 통과 |
| **M4 관측성** | `infra/` kube-prometheus-stack values, ServiceMonitor, 커스텀 메트릭 5종, 대시보드 1~5 JSON + sidecar ConfigMap | 대시보드에 실데이터 표시 |
| **M5 오토스케일링** | HPA(api), KEDA ScaledObject(worker), `loadtest/` k6 스크립트와 대량 업로드 스크립트, `ARTIFICIAL_DELAY_MS` | E-02, E-03 기록 |
| **M6 운영 기능/실험** | PDB, NetworkPolicy(default deny), 롤링 업데이트 전략 | E-01, E-04~E-10 기록 |
| **M7 CI** | `ci.yaml`(ruff/pytest/buildx/Trivy/GHCR push/dev 태그 bot 커밋, path filter), `release.yaml`(imagetools 재태깅 + prod PR) | main push 시 GHCR에 `sha-xxxxxxx` 이미지와 dev overlay 갱신 커밋 생성 |
| **M8 GitOps dev** | ArgoCD Helm 설치, `argocd/bootstrap` app-of-apps, Sync Wave, Sealed Secrets(평문 Secret 대체), PreSync/PostSync 훅, 키 백업 절차 문서 | E-11, E-12, E-15 기록 |
| **M9 prod** | prod VM 생성 → "K3S → ArgoCD → root Application" 3단계로 재현, `k8s/overlays/prod`, Release 워크플로 | E-13, E-14 기록. PRD 완료 기준 2·3 충족 |

### 2.1 M0 세부 작업 순서

모두 완료 (2026-10-14).

1. 레포 생성 → 디렉터리 골격, `.gitignore`(secrets, kubeconfig, `.venv`), README. 결정 사항은 별도 `decisions.md` 없이 이 문서 1장에서 관리
2. SSH 키 생성 → `infra/azure/create-vm.sh` (RG, VNet, NSG, VM, auto-shutdown) 작성·실행 → [azure-vm.md](azure-vm.md)
3. VM 초기화 스크립트 `scripts/vm-setup.sh`: docker, uv, k3s, helm, kubectl, kubeseal, argocd CLI, k6
4. `scripts/tunnel.sh`, `scripts/fetch-kubeconfig.sh` → 작업 PC kubeconfig에 `k3s-dev` context 등록 → [access.md](access.md)
5. `scripts/sync.sh`(rsync) 작성
6. 검증: 작업 PC `kubectl --context k3s-dev get nodes` → Ready 확인

설치된 버전 (dev VM): K3S v1.36.5+k3s1, Docker 29.9.0, Compose v5.6.0, uv 0.13.1, Helm v3.22.0, kubeseal 0.40.0, argocd v3.5.5, k6 v2.3.0

### 2.2 M1 결과

완료 (2026-10-14). 상세 절차와 검증 결과는 [local-compose.md](local-compose.md).

- api(FastAPI), worker(Pillow), frontend(정적 + nginx-unprivileged), MinIO 소스 빌드 이미지, docker-compose(Ingress 역할의 gateway 포함), `scripts/smoke.py`(E2E, PostSync 훅에서 재사용 예정)
- 검증: compose 전체 기동, smoke 통과, 깨진 파일 → FAILED, worker 강제 종료 후 작업 복구, Postgres 중단 시 readyz 503 / healthz 200, 모든 앱 컨테이너 non-root·read-only root FS
- M2 이후로 넘긴 것: PROCESSING에 남은 작업 재시도는 M3 cleanup CronJob

### 2.3 M2 결과

완료 (2026-10-14). 상세 절차와 검증 결과는 [k8s-dev.md](k8s-dev.md).

- `k8s/base`(StatefulSet 3, Deployment 3, Job, Ingress, configMapGenerator) + `k8s/overlays/dev`(namespace, 이미지 태그, DEBUG 로그, secretGenerator, host)
- 이미지 전달: GHCR 대신 VM에서 빌드해 K3S containerd에 직접 import (`scripts/build-images.sh`). GHCR 푸시는 M7(CI)에서 시작. 이미지 이름은 처음부터 GHCR 이름 사용
- Secret: VM에만 있는 `k8s/overlays/dev/secrets.env`(gitignore, `scripts/k8s-secrets.sh`로 생성) → M8에서 SealedSecret으로 교체
- presigned URL을 요청 Host 기준으로 서명하도록 api 변경 (터널 포트와 무관하게 동작)
- 검증: VM 안 Traefik과 작업 PC 터널 양쪽에서 smoke 통과, Pod 삭제 후 자가 복구, StatefulSet 재기동 후 데이터 유지

### 2.4 M3 결과

완료 (2026-10-15). 모든 상주 컨테이너에 probes와 requests/limits를 추가하고
db-migrate Job에 실행 시간 제한과 TTL을 설정했다. cleanup CronJob과 processing lease는
[cleanup.md](cleanup.md)에 설명한다.

- API 12개, worker 7개 pytest와 ruff 통과.
- [E-07](experiments/E-07.md): DB 중단 시 readiness만 실패하고 API restartCount 유지.
- [E-08](experiments/E-08.md): 데이터 서비스 Pod 교체 후 원본·썸네일·메타데이터 유지.
- cleanup의 실서비스 회귀 시나리오 6종과 M3 배포 smoke 통과.

### 2.5 알려진 한계

- MinIO upstream이 archive되어 보안 패치가 없다. M7 Trivy 스캔(HIGH 이상 실패)에서 걸리면 예외 처리할지 다른 S3 구현으로 바꿀지 다시 결정한다.
- 단일 노드라 `kubectl drain`으로 PDB를 검증할 수 없다. `kubectl get pdb`와 eviction API 호출로 대체 검증하고 문서에 한계를 적는다.
- 단일 노드 `local-path` 스토리지는 노드 장애 시 데이터가 보호되지 않는다 (PRD 5.2). Longhorn은 확장 과제.
- Burstable VM의 CPU 크레딧 영향 (1.3 참고).

---

## 3. 완료 기준 (PRD 10장)

1. E-01~E-15를 모두 수행하고 결과를 `docs/experiments/`에 기록한다.
2. prod VM을 초기화한 상태에서 "K3S 설치 → ArgoCD 설치 → root Application apply" 세 단계만으로 서비스 전체(모니터링 포함)가 복구된다.
3. 코드 push부터 prod 반영까지 `kubectl`을 한 번도 직접 실행하지 않는다.
4. Grafana 대시보드 1~5번이 dev와 prod 양쪽에서 실제 데이터로 동작한다.
