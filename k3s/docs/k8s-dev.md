# M2: dev 클러스터 수동 배포

M2~M6는 일부러 `kubectl apply -k`로 손수 배포한다 (PRD 9장). ArgoCD가 나중에 대신 해 줄 일을 먼저 직접 겪어 보기 위해서다.

## 리소스 구성 (`album-dev` 네임스페이스)

| 리소스 | 종류 | 포인트 |
|---|---|---|
| postgres, redis, minio | StatefulSet + headless Service + PVC(local-path) | Pod 이름이 `postgres-0`처럼 고정되고, 재생성돼도 같은 PVC를 다시 붙인다 |
| api, worker, frontend | Deployment + ClusterIP Service | frontend는 replica 2 고정 |
| db-migrate | Job | api 이미지로 `python -m app.migrate` 실행 |
| album | Ingress (Traefik) | `album.dev.local`: `/api/` → api, `/originals/`·`/thumbnails/` → minio, `/` → frontend |
| album-config-<hash> | ConfigMap (configMapGenerator) | 값이 바뀌면 이름의 해시가 바뀌어 참조하는 Deployment가 자동 롤아웃된다 (E-10) |
| album-secrets-<hash> | Secret (secretGenerator) | VM에만 있는 `secrets.env`에서 생성. M8에서 SealedSecret으로 교체 |

모든 Pod는 non-root, `readOnlyRootFilesystem`, `capabilities: drop ALL`, `seccompProfile: RuntimeDefault`로 실행된다. 쓰기가 필요한 경로(`/tmp`, postgres 소켓 디렉터리)만 emptyDir로 붙였다.

내부 통신은 Service DNS 이름을 쓴다. 같은 네임스페이스라 `postgres`, `redis`, `minio`처럼 짧은 이름으로 충분하고, 정식 이름은 `api.album-dev.svc.cluster.local`이다.

```
k8s/
├── base/                     환경과 무관한 정의 (이미지 태그 없음, host는 placeholder)
│   ├── kustomization.yaml    리소스 목록 + 공통 ConfigMap
│   ├── postgres/ redis/ minio/   StatefulSet + Service
│   ├── api/ worker/ frontend/    Deployment + Service
│   ├── migrate/job.yaml
│   └── ingress.yaml
└── overlays/dev/             dev 환경 차이만
    ├── kustomization.yaml    namespace, 이미지 태그, LOG_LEVEL=DEBUG, Secret, Ingress host
    └── secrets.env           (VM에만 존재, gitignore)
```

## 이미지 전달 방식

M7(CI)이 생기기 전까지는 GHCR에 올리지 않고, VM에서 빌드한 이미지를 K3S의 containerd에 직접 넣는다.

```bash
scripts/build-images.sh dev-m2b              # api worker frontend
scripts/build-images.sh dev-m2b minio        # MinIO (최초 1회)
```

이미지 이름은 처음부터 `ghcr.io/winty5959/album-*`로 붙여서, CI가 생겨도 매니페스트는 태그만 바뀐다. 로컬에 넣은 이미지를 쓰려면 `imagePullPolicy: IfNotPresent`여야 한다 (`latest` 태그나 `Always`면 레지스트리에서 받으려다 실패한다).

## 배포 절차 (dev VM)

```bash
ssh kube-dev
cd ~/kube-study/k3s                      # 작업 PC에서 scripts/sync.sh dev로 최신화
scripts/k8s-secrets.sh dev               # 최초 1회: secrets.env 생성 (권한 600)
scripts/build-images.sh <tag>            # 코드가 바뀌었으면
# k8s/overlays/dev/kustomization.yaml 의 newTag를 <tag>로 수정
kubectl -n album-dev delete job db-migrate --ignore-not-found   # Job은 수정 불가라 지우고 다시 만든다
kubectl apply -k k8s/overlays/dev
kubectl -n album-dev wait --for=condition=complete job/db-migrate --timeout=120s
kubectl -n album-dev rollout status deploy/api
```

적용 전 변경 내용 미리 보기: `kubectl diff -k k8s/overlays/dev`. 렌더링 결과만 보기: `kubectl kustomize k8s/overlays/dev`.

작업 PC 브라우저: `scripts/tunnel.sh dev start` 후 `http://album.dev.local:8080` (`/etc/hosts`에 `127.0.0.1 album.dev.local` 필요, [access.md](access.md)).

### presigned URL과 포트

썸네일과 원본은 api가 서명한 URL로 브라우저가 MinIO에서 직접 받는다. 서명에 Host(포트 포함)가 들어가므로 api는 **요청이 들어온 Host 그대로** URL을 만든다. 그래서 같은 배포가 VM 안(`album.dev.local`)에서도, 터널(`album.dev.local:8080`)에서도 동작한다. 고정 주소가 필요하면 ConfigMap에 `S3_PUBLIC_ENDPOINT`를 넣으면 된다.

## 검증 결과 (2026-10-14)

| 항목 | 결과 |
|---|---|
| 배포 | 8개 Pod Running/Completed, PVC 3개 Bound (2Gi / 1Gi / 10Gi, local-path) |
| 마이그레이션 | 첫 배포 때 Postgres 기동 전이라 3회 재시작 후 성공(`backoffLimit: 6`), 재배포 시 "0 applied now" |
| smoke (VM 안, Traefik :80) | 업로드 → DONE → 썸네일 200×100 / 800×400 → 원본 → 삭제 통과 |
| smoke (작업 PC, SSH 터널 :8080) | 동일하게 통과 |
| 헤더 | `X-Served-By`에 api Pod 이름, `X-App-Version: dev-m2b` |
| Service DNS | `api.album-dev.svc.cluster.local`, `postgres-0.postgres.album-dev.svc.cluster.local` 조회 성공 |
| 보안 컨텍스트 | 모든 Pod UID ≠ 0, root 파일시스템 쓰기 불가 |
| api Pod 삭제 (E-01 미리보기) | 수 초 내 새 Pod Running |
| StatefulSet Pod 삭제 (E-08 미리보기) | postgres/minio/redis 재기동 후 사진 메타데이터와 썸네일 유지 |
| 리소스 사용량 (유휴) | api 78Mi, worker 60Mi, minio 90Mi, postgres 22Mi, redis 8Mi, frontend 4Mi |

### 발견한 문제

- **Postgres 재시작 직후 api 500:** 커넥션 풀이 이미 끊긴 연결을 그대로 내줘서 `AdminShutdown` 에러가 났다. api와 worker의 풀에 `check=ConnectionPool.check_connection`을 넣어, 꺼내기 전에 연결을 확인하게 했다. 수정 후 재시작 직후 5회 연속 200.
- **버킷 생성 시점:** 버킷을 `/readyz`에서만 만들었는데, M2에는 readiness probe가 없어 아무도 `/readyz`를 부르지 않는다. 첫 업로드 때도 만들도록 바꿨다.

## M3에서 완료한 것 (2026-10-15)

liveness/readiness/startup probe, requests/limits, Job TTL·실행 시간 제한,
cleanup CronJob(PROCESSING 작업 재시도, 고아 객체 삭제)을 추가했다.
API는 dependency가 준비된 뒤 트래픽을 받는다. 검증 결과는
[E-07](experiments/E-07.md), [E-08](experiments/E-08.md), [cleanup.md](cleanup.md)에 있다.
