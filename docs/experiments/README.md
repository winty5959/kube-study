# 학습 실험 상세 명세 (E-01 ~ E-15)

PRD 7장의 실험 15개를 수행 가능한 형태로 풀어 쓴 문서다. 결과는 실험마다 [TEMPLATE.md](TEMPLATE.md)를 복사해 `docs/experiments/E-XX.md`로 기록한다 (PRD 7.2 마지막 줄, 완료 기준 1).

## 읽는 방법

각 실험은 두 부분으로 나뉜다.

- **PRD 원문:** [prd.md](../prd.md) 7장의 시나리오·수행 방법·기대 결과를 그대로 옮긴 것. 수용 기준은 이 부분이다.
- **보충 (구현 기준):** PRD에 없고 이 저장소의 구현 상태에 맞춰 덧붙인 것. 선행 조건, 구체적인 명령 방향, 관찰할 지표, 주의점. 수용 기준이 아니며 구현이 바뀌면 고친다.

명령은 방향만 적는다. 실제 값(네임스페이스 `album-dev`, 컨텍스트 `k3s-dev`)은 환경에 맞게 바꾸고, 정확한 수행 기록은 `E-XX.md`에 남긴다. 접속 방법은 [server-access.md](../server-access.md)를 본다.

## 한눈에 보기

| # | 시나리오 | 대상 개념 | 환경 | 마일스톤 | 선행 구현 |
|---|---|---|---|---|---|
| E-01 | 셀프 힐링 | Deployment/ReplicaSet | dev | M6 | M2 (미리보기 완료) |
| E-02 | HPA 확장 | HPA, requests | dev | M5 | M3 requests, M4 관측성, M5 HPA, k6 |
| E-03 | KEDA 확장 | KEDA | dev | M5 | M5 KEDA, 대량 업로드 스크립트 |
| E-04 | 롤링 업데이트 | RollingUpdate | dev | M6 | M3 probe |
| E-05 | 롤아웃 중단 | readiness, rollout undo | dev | M6 | M3 probe |
| E-06 | OOM | limits, OOMKilled | dev | M6 | M3 limits, worker 크래시 복구 (M1 완료) |
| E-07 | 의존성 장애 | readiness | dev | M6 | M3 probe |
| E-08 | 데이터 영속성 | StatefulSet, PVC | dev | M6 | M2 (미리보기 완료) |
| E-09 | NetworkPolicy | NetworkPolicy | dev | M6 | M6 default deny |
| E-10 | 설정 변경 | ConfigMap 롤아웃 | dev | M6 | M2 configMapGenerator (완료) |
| E-11 | GitOps 자동 배포 | ArgoCD auto-sync, CI | dev | M8 | M7 CI, M8 ArgoCD |
| E-12 | 드리프트 자가 복구 | selfHeal | dev | M8 | M8 |
| E-13 | 운영 승격 | Build once, promote many | prod | M9 | M7 release.yaml, M9 prod |
| E-14 | GitOps 롤백 | git revert vs rollout undo | prod | M9 | M9 |
| E-15 | 배포 게이트 | PreSync hook | dev | M8 | M8 훅 |

PRD 9장은 E-01을 M6에 배정했다. M2에서 이미 Pod 삭제 후 복구를 미리 확인했지만, 수용 기준용 기록은 M6에서 남긴다.

## 공통 규칙

- **기록 항목:** 수행 일시, 환경, 이미지 태그(`X-App-Version`), 수행한 명령과 출력, Grafana 스크린샷(M4 이후), 기대 결과와 실제 결과, 판정(통과/실패/부분 통과), 관찰 내용과 배운 점.
- **정리:** 실험이 끝나면 원래 상태로 되돌린다(replica, limit, 설정 값, Git 변경). 되돌린 방법도 기록한다.
- **Burstable VM 주의:** dev VM은 B4as_v2라 부하 실험(E-02, E-03) 중 CPU 크레딧이 떨어지면 결과가 왜곡된다. 이 두 실험은 Azure 메트릭 `CPU Credits Remaining`을 시작·종료 시점에 함께 기록한다 ([plan.md](../plan.md) 1.3).
- **민감 정보:** 출력을 붙일 때 Secret 값, 토큰, 공인 IP, kubeconfig 내용은 지우고 붙인다.
- **kubectl 사용 범위:** M6까지는 직접 `kubectl`을 쓴다. E-11~E-15(M8~M9)는 "kubectl을 직접 쓰지 않는다"는 완료 기준 3과 충돌하지 않는 선에서만 쓴다. E-12, E-14처럼 PRD가 `kubectl`을 명시한 경우는 예외다.

---

## 7.1 쿠버네티스 핵심

### E-01 셀프 힐링

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | api Pod 강제 삭제 |
| 기대 결과 | 수초 내 재생성되고 서비스 중단이 없음 |

**보충**

- 선행: api가 HPA 1~3(dev)이면 replica가 2 이상일 때 "서비스 중단 없음"을 볼 수 있다. replica 1이면 새 Pod가 Ready가 되기까지 짧은 단절이 생기는 것이 정상이므로, 이 실험은 replica 2 이상 상태에서 수행하고 1일 때의 결과를 비교로 남기면 좋다.
- 수행: 터미널 하나에서 `/api/photos`를 0.2초 간격으로 호출해 상태 코드와 `X-Served-By`를 기록하는 동안, 다른 터미널에서 `kubectl delete pod -l app.kubernetes.io/name=api`(강제 삭제는 `--grace-period=0 --force`)를 실행한다.
- 관찰: 새 Pod 이름과 생성까지 걸린 시간(`kubectl get pods -w`), 호출 중 non-200 응답 수, `X-Served-By`가 바뀌는 시점, ReplicaSet이 Pod를 다시 만든 이벤트(`kubectl get events`).
- 알아둘 점: readiness probe가 있어야 Ready 전의 새 Pod로 트래픽이 가지 않는다(M3 이후).

### E-02 HPA 확장

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | k6로 목록 API에 200 VU 부하 |
| 기대 결과 | CPU가 60%를 넘으면 replica가 늘고, 부하가 끝나면 약 5분 뒤 축소됨 |

**보충**

- 선행: api에 requests가 있어야 한다(HPA의 CPU 사용률은 requests 대비 비율이다. PRD 5.1 기준 api requests 100m). metrics-server 동작 확인(`kubectl top pods`, K3S 기본 포함), HPA(CPU 60%, dev는 1~3), `loadtest/`의 k6 스크립트, M4 대시보드 3번(CPU와 replica를 한 그래프에).
- 수행: k6는 VM에서 실행한다(작업 PC 금지, [plan.md](../plan.md) 1.5). 목록 API는 사진이 있어야 부하가 의미 있으므로 사전에 일정량의 사진을 준비한다.
- 관찰: HPA의 현재/목표 CPU(`kubectl get hpa -w`), replica 증가 시각, p95 응답시간, 부하 종료 후 축소까지 걸린 시간.
- 알아둘 점: 축소는 HPA 기본 안정화 구간(scaleDown stabilizationWindow 300초) 때문에 약 5분 뒤에 일어난다. 이 값이 PRD의 "약 5분"과 일치하는지 확인한다.
- 주의: 단일 노드에서 api가 3개까지 늘면 같은 4 vCPU를 나눠 쓰므로, 노드 CPU가 포화돼 기대한 만큼 응답시간이 줄지 않을 수 있다. 이것도 관찰 내용이다.

### E-03 KEDA 확장

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | 이미지 500장 일괄 업로드 스크립트 실행 |
| 기대 결과 | worker가 0에서 N으로 늘고, 큐가 비면 0으로 돌아옴 |

**보충**

- 선행: KEDA 설치(M5, 이 시점부터 CRD 필요), worker ScaledObject(dev 0~2, 트리거는 Redis list `thumbnail:jobs` 길이), `ARTIFICIAL_DELAY_MS`로 처리 시간을 늘려 확장을 관찰하기 쉽게 만든다(PRD 4.4), `loadtest/`의 대량 업로드 스크립트, M4 대시보드 2번(큐 길이와 worker replica).
- 관찰: 큐 길이 증가 → worker 0→N 시각(반응 속도), 큐가 비는 시각 → 0으로 돌아오는 시각(KEDA cooldownPeriod 기본 300초), 처리 시간 분포.
- 알아둘 점: worker는 처리 중 작업을 Pod별 목록(`thumbnail:jobs:processing:<pod>`)에 보관한다. KEDA의 큐 길이 지표에는 이 목록이 포함되지 않아야 한다(메인 큐 `thumbnail:jobs`만 본다). 축소로 Pod가 사라지면 그 Pod의 처리 목록이 남을 수 있는데, 이는 cleanup CronJob 대상이다([cleanup.md](../cleanup.md)).
- 주의: 500장 업로드는 api에도 부하다. 업로드 스크립트의 동시성을 정하고 기록한다.

### E-04 롤링 업데이트

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | api v1 → v2 배포 |
| 기대 결과 | `X-App-Version`이 무중단으로 전환됨 |

**보충**

- 선행: 서로 다른 `APP_VERSION`을 가진 이미지 두 개(`scripts/build-images.sh <tag>`로 태그만 다르게 빌드), api replica 2 이상, readiness probe(M3). Deployment 기본 전략은 RollingUpdate(maxSurge 25%, maxUnavailable 25%).
- 수행: 한쪽 터미널에서 `/api/photos`를 계속 호출하며 `X-App-Version`을 기록하고, 다른 쪽에서 overlay의 `newTag`를 v2로 바꿔 `kubectl apply -k`, `kubectl rollout status`로 진행을 본다.
- 관찰: 응답에 v1과 v2가 섞여 나오는 구간, 그 사이의 non-200 응답 수(0이어야 함), ReplicaSet 두 개의 replica 변화(`kubectl get rs -w`), `kubectl rollout history`.
- 알아둘 점: replica 1이면 maxUnavailable 25%가 올림/내림 규칙으로 0이 되어 새 Pod가 Ready가 된 뒤에 기존 Pod가 내려간다. 이 동작을 확인해 기록한다.

### E-05 롤아웃 중단

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | readiness가 실패하는 v3 배포 |
| 기대 결과 | 롤아웃이 멈추고 기존 Pod가 계속 서비스함 (dev에서 수동 배포 단계에 `rollout undo` 실습) |

**보충**

- 선행: E-04와 같다. readiness가 항상 실패하는 v3가 필요하다. 이미지를 따로 만들기보다 v3에서만 `/readyz`가 503을 반환하게 하는 설정 값(예: 존재하지 않는 DB 주소)을 쓰는 편이 간단하다. 어느 방식으로 했는지 기록한다.
- 수행: v3 배포 후 `kubectl rollout status`가 진행되지 않는 것을 확인(타임아웃은 `progressDeadlineSeconds`, 기본 600초)하고, 그 동안 서비스가 계속 응답하는지 호출로 확인한 뒤 `kubectl rollout undo deploy/api`로 되돌린다.
- 관찰: 새 ReplicaSet의 Pod가 `Running`이지만 `0/1 READY`인 상태, 기존 Pod 유지, 롤아웃 중단 시 Deployment 조건(`ProgressDeadlineExceeded`), undo 후 복구 시간.
- 주의: 이 실험은 **수동 배포 단계(M6)** 에서만 `rollout undo`를 쓴다. ArgoCD가 도입된 뒤에는 Git 상태로 덮어쓰이므로 E-14에서 다룬다.

### E-06 OOM

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | worker 메모리 limit을 64Mi로 낮추고 큰 이미지 처리 |
| 기대 결과 | OOMKilled 발생, 재시도 후 FAILED 처리 확인 |

**보충**

- 선행: worker limits(PRD 5.1은 512Mi, 이 실험에서 64Mi로 낮춘다). 큰 이미지: worker는 JPEG draft 모드 없이 전체를 디코딩하므로 메모리가 픽셀 수에 비례해 커진다. 64Mi를 확실히 넘기려면 수천만 화소 이미지를 쓰되 업로드 10MB 제한 안에 들어와야 한다. 단색에 가까운 큰 PNG/WebP는 용량이 작아 이 조건을 만들기 쉽다.
- 관찰: `kubectl describe pod`의 `Last State: Terminated, Reason: OOMKilled, Exit Code: 137`, 컨테이너 RESTARTS 증가, 사진 상태 PROCESSING → (재시작 후) PENDING 재큐 → 3회째 FAILED, `retry_count`와 `error` 컬럼(`worker terminated while processing`), CrashLoopBackOff 간격 증가.
- 알아둘 점: Pod 이름은 컨테이너가 OOMKilled로 재시작돼도 그대로다. 그래서 같은 이름의 처리 목록을 보고 재시작한 컨테이너가 중단된 작업을 되찾아 실패 1회로 계산한다([local-compose.md](../local-compose.md) "worker 신뢰성 큐"). compose에서 SIGKILL로 같은 동작을 확인했지만 실제 Kubernetes OOMKilled는 이 실험이 처음이다.
- 정리: 메모리 limit을 원래 값으로 되돌리고 FAILED 사진을 삭제한다.
- 열린 쟁점: [열린 쟁점](#열린-쟁점-prd에-없어-결정이-필요한-것) 표의 7번(OOMKilled 후 CrashLoopBackOff 대기와 3회 한도의 상호작용, Pod 교체 경로).

### E-07 의존성 장애

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | postgres를 replica 0으로 축소 |
| 기대 결과 | api readiness가 실패해 트래픽이 끊기고, 복구 시 자동으로 정상화됨 |

**보충**

- 선행: api readiness probe가 `/readyz`를 본다(M3). `/healthz`는 의존성을 보지 않으므로 liveness는 유지되어 Pod가 재시작되지 않는 것이 정상 동작이다([prd.md](../prd.md) 4.2).
- 수행: `kubectl scale statefulset postgres --replicas=0` → api가 `NotReady`가 되고 Service endpoint에서 빠지는지 확인 → `--replicas=1`로 복구.
- 관찰: `/readyz` 응답(`{"checks": {"postgres": "error: ..."}}`), api Pod의 `READY 0/1`, Ingress를 통한 요청이 어떻게 실패하는지(Traefik의 응답 코드), **api RESTARTS가 늘지 않음**, 복구 후 자동 정상화까지의 시간, 복구 직후 첫 요청이 500이 아닌지(커넥션 풀 검증 `check_connection`을 넣은 이유).
- 주의: api가 1개뿐이면 모든 api Pod가 NotReady가 되어 서비스 전체가 끊긴다. 이것이 기대 결과("트래픽이 끊기고")다.
- compose에서는 이미 같은 현상(`/readyz` 503, `/healthz` 200 유지, 재기동 후 복구)을 확인했다. 이 실험은 Kubernetes 위에서의 기록이다.

### E-08 데이터 영속성

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | postgres/minio Pod 삭제 |
| 기대 결과 | 재기동 후 데이터 유지 |

**보충**

- 선행: 사진이 몇 장 있고 상태가 DONE인 것. 삭제 전 `/api/photos`의 목록과 썸네일 URL로 받은 파일의 해시를 적어 둔다.
- 수행: `kubectl delete pod postgres-0 minio-0 redis-0`(Redis도 함께 보면 큐 유지까지 확인된다) → 새 Pod가 같은 이름과 같은 PVC로 올라오는지 확인.
- 관찰: Pod 이름이 `postgres-0`으로 유지되는 것(StatefulSet), PVC가 `Bound` 그대로인 것, 재기동 후 목록과 썸네일(해시 일치), 시간.
- 한계로 기록할 것: PV는 노드의 디렉터리(local-path)라 **Pod 삭제에는 견디지만 노드 장애에는 보호되지 않는다**(PRD 5.2). StorageClass의 reclaimPolicy가 `Delete`이므로 **PVC를 지우면 데이터도 사라진다**. 이 차이(Pod 삭제 vs PVC 삭제)를 실험으로 확인해 두면 좋다.
- M2에서 미리보기로 확인했다(postgres/minio/redis Pod 삭제 후 데이터 유지). 수용 기준용 기록은 M6에서 남긴다.

### E-09 NetworkPolicy

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | frontend Pod에서 postgres 접속 시도 |
| 기대 결과 | 차단됨 |

**보충**

- 선행: default deny와 허용 규칙(PRD 5.3: DB는 api/worker에서만 접근). 현재(M2 이후) NetworkPolicy가 하나도 없고, frontend Pod에서 `nc -z postgres 5432`가 성공(exit 0)하는 것을 확인했다. 즉 **적용 전에는 접속되는 것이 기준선**이다.
- 수행: 같은 명령을 NetworkPolicy 적용 전후에 실행해 대비한다. frontend 이미지(busybox nc)에는 `psql`이 없으므로 포트 연결(`nc -z -w 3 postgres 5432`)로 판단한다. 대조군으로 api Pod에서 같은 접속이 **성공**하는지도 확인한다(허용 규칙이 너무 막지 않았는지).
- 관찰: 적용 전 성공 / 적용 후 frontend 실패(타임아웃) / api·worker 성공. 차단은 거부(refused)가 아니라 패킷이 버려져 타임아웃으로 나타난다.
- 주의: default deny는 DNS(kube-dns 53)와 Ingress(Traefik → frontend/api/minio), Prometheus 스크랩 경로까지 막는다. 허용 규칙을 빠뜨리면 앱 전체가 멈추므로 적용은 한 컴포넌트씩 한다. K3S의 네트워크 정책 지원은 기본 포함이지만, 실제로 적용되는지는 이 실험의 "적용 전후 대비"로 확인한다.

### E-10 설정 변경

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | ConfigMap의 썸네일 크기 변경 |
| 기대 결과 | 롤아웃 후 새 크기 적용 |

**보충**

- 선행: M2의 `configMapGenerator`는 내용 해시를 이름에 붙여, 값이 바뀌면 ConfigMap 이름이 바뀌고 이를 참조하는 Deployment가 자동 롤아웃된다. 이 동작이 E-10의 핵심이다.
- 수행: overlay의 `THUMB_MEDIUM_PX`(기본 800)를 바꿔 `kubectl apply -k` → worker가 새 ConfigMap 이름으로 롤아웃 → 새로 업로드한 사진의 medium 썸네일이 새 크기인지 확인(`scripts/smoke.py`가 기대 크기를 검사하므로 기대값을 맞춰 조정).
- 관찰: ConfigMap 이름의 해시 변화(`kubectl get cm`), worker Pod 교체, **기존 사진의 썸네일은 그대로**(새 크기는 새 업로드에만 적용), 이전 ConfigMap이 남는지(`prune` 여부).
- 비교로 남기면 좋은 것: 해시 없는 일반 ConfigMap을 수정했을 때는 Pod가 자동으로 재시작되지 않아 환경 변수가 갱신되지 않는다는 점(envFrom은 Pod 시작 시점에 읽힌다).

---

## 7.2 CI/CD

> E-11~E-15는 M7(CI)과 M8~M9(GitOps)가 구현된 뒤에 수행한다. 아래 보충은 PRD 11장 설계를 기준으로 한 계획이며, 구현 후 달라지면 고친다.

### E-11 GitOps 자동 배포

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | api 코드를 한 줄 고쳐 main에 push |
| 기대 결과 | 별도 조작 없이 수 분 안에 dev에 새 Pod가 뜨고 `X-App-Version`이 새 sha로 바뀜 |

**보충**

- 선행: M7 `ci.yaml`(변경된 앱만 빌드, Trivy, GHCR push, dev overlay 태그 bot 커밋), M8 dev ArgoCD(auto-sync, prune, selfHeal).
- 관찰할 시간 구간: push → Actions 완료 → bot 커밋 → ArgoCD가 변경 감지(기본 reconciliation 약 2~3분 간격) → Pod 교체 → `X-App-Version` 변경. 구간별 소요 시간을 기록하면 "수 분"이 어디서 걸리는지 보인다.
- 확인: `X-App-Version`이 새 `sha-<7자리>`와 일치, ArgoCD Application이 Synced/Healthy, PostSync smoke-test Job 통과, 사람이 `kubectl`을 쓰지 않았음.
- 주의: bot 커밋이 `k8s/**`만 바꾸고 빌드 워크플로는 `apps/**`에만 반응해야 무한 루프가 생기지 않는다(PRD 11.3).

### E-12 드리프트 자가 복구

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | dev에서 `kubectl scale deploy/frontend --replicas=5` 실행 |
| 기대 결과 | ArgoCD가 감지해서 Git에 정의된 2개로 되돌림 |

**보충**

- 선행: dev Application의 `selfHeal: true`. frontend는 Git에서 replica 2로 고정이다(드리프트 대상으로 쓰기 좋게 HPA를 달지 않았다).
- 관찰: replica가 5로 늘었다가 다시 2로 돌아오는 시간(selfHeal은 기본 약 5초 뒤 재동기화), ArgoCD UI에서 OutOfSync가 잠깐 나타났다 사라지는 것, Sync 이력.
- 대조: prod Application(수동 Sync, selfHeal)과 동작이 같은지, auto-sync 없이 selfHeal만 있을 때 어떻게 되는지는 이 실험 후 확인해 기록한다.

### E-13 운영 승격

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | `git tag v1.1.0` 생성 → PR merge → Sync |
| 기대 결과 | prod 이미지 digest가 dev와 같은지 `kubectl get pod -o jsonpath`로 확인 |

**보충**

- 선행: M7 `release.yaml`(해당 커밋의 `sha-*` 이미지를 `imagetools create`로 `vX.Y.Z` 재태깅, 재빌드 없음, prod overlay 태그를 갱신하는 PR 자동 생성), M9 prod 클러스터와 ArgoCD(수동 Sync).
- 수행 순서: 태그 푸시 → Release 워크플로 → prod 태그 PR 생성 → 리뷰 후 merge(= 운영 승인) → prod ArgoCD가 OutOfSync 표시 → 수동 Sync.
- 확인: 두 클러스터의 Pod `imageID`(`sha256:` digest)가 같다. 예: `kubectl --context k3s-dev|k3s-prod get pod -l app.kubernetes.io/name=api -o jsonpath='{.items[0].status.containerStatuses[0].imageID}'`. 태그가 `v1.1.0`으로 바뀌어도 digest가 같아야 "Build once, promote many"가 증명된다.
- 주의: 이 실험은 dev와 prod 두 클러스터를 동시에 조회한다. prod VM은 M9 직전에 만들기로 했으므로 그때까지는 수행할 수 없다.

### E-14 GitOps 롤백

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | prod에서 `rollout undo`를 먼저 시도한 뒤 `git revert`로 다시 롤백 |
| 기대 결과 | 앞의 방법은 ArgoCD가 덮어쓰고, 뒤의 방법은 Git 이력이 남은 채로 롤백됨 |

**보충**

- 선행: E-13으로 prod에 새 버전이 올라가 있는 상태.
- 수행 1: `kubectl rollout undo deploy/api`(prod). 잠시 이전 ReplicaSet으로 돌아가지만 Git은 그대로이므로 Application이 OutOfSync가 된다. 그 뒤 **누가 Git 상태로 되돌리는지가 prod 정책에 달려 있다**: `automated.selfHeal`이 켜져 있으면 ArgoCD가 몇 초 뒤 스스로 덮어쓰고, 순수 수동 Sync면 OutOfSync로 남아 있다가 사람이 Sync할 때 덮어쓴다. 어느 쪽이었는지와 되돌려지는 시점을 기록한다 ([열린 쟁점](#열린-쟁점-prd에-없어-결정이-필요한-것) 13번).
- 수행 2: prod overlay 태그를 바꾼 커밋을 `git revert` → 머지 → Sync. Git 이력에 되돌린 기록이 남는지 확인한다.
- 정리: ArgoCD UI의 History → Rollback(긴급 롤백)은 별도로 시도해 둘 가치가 있다. 일시적으로 Git과 상태가 달라지므로 사후에 Git을 맞춰야 한다(PRD 11.8). 자동 Sync가 켜진 Application에서는 Rollback이 허용되지 않는 점도 같이 확인한다.
- 주의: 이 실험은 PRD가 "prod에서 `kubectl rollout undo`는 쓰지 않는다"고 한 규칙을 **일부러 어겨서** 이유를 확인하는 실험이다. 실험 외에는 쓰지 않는다.

### E-15 배포 게이트

**PRD 원문**

| 항목 | 내용 |
|---|---|
| 수행 방법 | 마이그레이션이 실패하도록 만든 버전을 배포 |
| 기대 결과 | PreSync 훅이 실패해서 기존 버전이 그대로 서비스됨 |

**보충**

- 선행: db-migrate가 ArgoCD PreSync 훅 Job(M8). 실패하는 마이그레이션은 문법 오류가 있는 SQL 파일을 하나 추가하는 식으로 만든다(`python -m app.migrate`는 실패하면 exit 1로 끝난다).
- 확인: PreSync 훅 실패로 Sync가 중단되고 새 Deployment가 적용되지 않는 것, 기존 api Pod가 이전 버전(`X-App-Version`)으로 계속 응답하는 것, Application 상태가 Degraded/OutOfSync로 표시되는 것. 마이그레이션이 한 트랜잭션 안에서 롤백되어 `schema_migrations`에 기록되지 않는 것도 DB에서 확인한다.
- 정리: 잘못된 마이그레이션 파일을 `git revert`로 되돌리고 정상 배포로 돌아오는 과정을 기록한다.

---

## 열린 쟁점 (PRD에 없어 결정이 필요한 것)

PRD 문구만으로는 판정 기준이 모호하거나, 구현 중 확인된 사실과 맞춰 봐야 하는 지점이다. 해당 실험을 수행하기 전에 정하고 `E-XX.md`에 결정 내용을 적는다.

| # | 대상 | 쟁점 | 제안 |
|---|---|---|---|
| 1 | E-01 | "서비스 중단이 없음"의 기준. api replica 1이면 새 Pod가 Ready가 될 때까지 짧은 단절이 불가피 | replica 2 이상에서 수행해 무중단을 판정하고, replica 1 결과는 참고 기록 |
| 2 | E-02 | "CPU가 60%를 넘으면"이 requests 대비 사용률임을 명시하지 않음 | requests 대비로 해석하고 기록 |
| 3 | E-02, E-03 | dev VM이 Burstable이라 부하 중 CPU 크레딧이 소진되면 결과가 왜곡 | 시작·종료 시점의 `CPU Credits Remaining` 기록. 급락하면 재수행 |
| 4 | E-03 | "500장" 업로드 이미지 크기와 업로드 동시성이 미정 | 크기(예: 200KB 내외)와 동시성을 정하고 기록. `ARTIFICIAL_DELAY_MS`도 함께 기록 |
| 5 | E-05 | readiness가 실패하는 v3를 만드는 방법이 미정 | 이미지를 새로 만들기보다 잘못된 DB 주소 같은 설정으로 `/readyz`를 실패시키는 방식 |
| 6 | E-06 | "큰 이미지"의 기준. 10MB 제한 안에서 64Mi를 넘겨야 함 | 단색에 가까운 수천만 화소 PNG/WebP로 용량은 작게, 디코딩 메모리는 크게 |
| 7 | E-06 | OOMKilled 후 CrashLoopBackOff 대기 시간(10초 → 20초 → 40초 …)이 늘어 3회 재시도 완료까지 수 분이 걸릴 수 있음. 또 **재시작이 아니라 Pod가 교체되는 경우**(노드 압박 등)에는 Pod 이름이 바뀌어 처리 중 작업을 되찾지 못하고 cleanup CronJob에 맡겨짐 | 컨테이너 재시작 경로(OOMKilled)로 수행해 3회 후 FAILED를 확인하고, Pod 교체 경로는 cleanup 대상임을 별도로 기록 |
| 8 | E-09 | frontend 이미지에는 `psql`이 없음 | `nc -z` 포트 연결로 판단. 적용 전(성공)·후(타임아웃)와 api 대조군(성공)을 함께 기록 |
| 9 | E-12 | prod Application의 드리프트 처리는 PRD가 dev 기준으로만 서술 | dev에서 수행하고, prod 동작은 E-14에서 함께 관찰 |
| 10 | E-13, E-14 | prod VM은 M9 직전에 만들 예정. 그 전에는 수행 불가 | M9 이후에 수행 |
| 11 | E-14 | PRD 완료 기준 3("kubectl을 한 번도 직접 실행하지 않는다")과 E-12·E-14의 `kubectl`이 충돌하는 것처럼 읽힘 | 완료 기준 3은 "배포 경로"에 대한 기준이고, 실험의 `kubectl`은 의도된 개입(드리프트·롤백 시도)이므로 예외로 해석. 기록에 명시 |
| 12 | 전체 | E-01은 PRD 마일스톤상 M6이지만 M2에서 이미 미리 확인함 | 수용 기준용 기록은 M6에 새로 수행. M2 결과는 참고(`k8s-dev.md`) |
| 13 | E-14 | PRD 5.4가 prod를 "수동 Sync, selfHeal"로 적었지만, ArgoCD에서 `selfHeal`은 `syncPolicy.automated` 안의 옵션이다([공식 문서](https://argo-cd.readthedocs.io/en/stable/user-guide/auto_sync/)). 수동 Sync와 selfHeal은 문자 그대로는 함께 설정할 수 없다. E-14 기대 결과("`rollout undo`는 ArgoCD가 덮어쓴다")는 어느 쪽으로 구현하느냐에 따라 시점이 달라진다 | M9 설계 때 결정해 [plan.md](../plan.md)에 기록. 후보: (a) prod도 `automated: {selfHeal: true}`로 두되 승격 승인은 PR merge로만 통제, (b) 순수 수동 Sync로 두고 `rollout undo`는 OutOfSync로 남다가 다음 Sync에서 덮어쓰이는 것을 관찰. PRD의 "prod는 사람이 승인" 원칙(11.3)에는 (b)가 더 가깝다 |

## 수행 현황

| # | 상태 | 비고 |
|---|---|---|
| E-01 | 미수행 | M2에서 Pod 삭제 후 복구 미리보기 완료 |
| E-02 ~ E-05 | 미수행 | |
| E-06 | 미수행 | M1에서 compose로 worker SIGKILL 후 작업 복구 확인 (실제 OOMKilled 아님) |
| E-07 | 미수행 | M1에서 compose로 postgres 중단 시 `/readyz` 503, `/healthz` 200 확인 |
| E-08 | 미수행 | M2에서 postgres/minio/redis Pod 삭제 후 데이터 유지 미리보기 완료 |
| E-09 | 미수행 | NetworkPolicy 없음, frontend → postgres:5432 연결 성공이 기준선 |
| E-10 | 미수행 | M2 configMapGenerator 구현 완료 |
| E-11 ~ E-15 | 미수행 | M7~M9 이후 |

수행하면 이 표와 [plan.md](../plan.md)의 진행 상태를 함께 갱신한다.
