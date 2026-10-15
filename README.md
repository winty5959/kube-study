# kube-study: Mini Photo Album on K3S

쿠버네티스 학습용 작은 사진 앨범 서비스. 이미지를 업로드하면 worker가 비동기로 썸네일을 만든다.
서비스 자체보다 Pod 분리, 오토스케일링(HPA/KEDA), 관측성, 장애 대응, GitOps CI/CD를 직접 겪어 보는 것이 목적이다.

- 요구사항 원문(PRD v1.1): [docs/prd.md](docs/prd.md)
- 작업 계획과 확정된 결정 사항: [docs/plan.md](docs/plan.md)
- 학습 실험 E-01~E-15 상세 명세와 기록 템플릿: [docs/experiments/](docs/experiments/README.md)
- 서버 켜기·접속·SSH 터널·끄기: [docs/server-access.md](docs/server-access.md)

## 구성

| 영역 | 기술 |
|---|---|
| 앱 | FastAPI(api), Pillow(worker), nginx 정적(frontend) |
| 데이터 | PostgreSQL, Redis(큐), MinIO(오브젝트 스토리지) |
| 클러스터 | Azure VM 위 K3S 단일 노드 (dev / prod 분리) |
| 배포 | Kustomize(base + overlays), 인프라는 Helm |
| CI/CD | GitHub Actions → GHCR, ArgoCD(GitOps, app-of-apps) |
| 관측성 | kube-prometheus-stack, Grafana 대시보드 |

## 디렉터리

현재 구현과 준비 상태는 다음과 같다.

```
apps/        api, worker, frontend 소스와 Dockerfile
k8s/         base 매니페스트와 dev/prod overlay
argocd/      bootstrap(root Application), dev/prod Application 정의
infra/       Azure VM 스크립트, Helm values
scripts/     VM 초기화, SSH 터널, 동기화 스크립트
loadtest/    k6 스크립트, 대량 업로드 스크립트
dashboards/  Grafana 대시보드 JSON
docs/        계획, 운영 절차, 실험 기록(experiments/E-XX.md)
```

## 현재 상태

| 범위 | 상태 |
|---|---|
| M0~M6 | 완료, E-01~E-10 검증·기록 |
| M7 CI | 완료. 변경된 앱만 재빌드, 네 보안 검사·공개 이미지·dev 승격 성공. MinIO 6건만 2026-11-14까지 승인 예외 |
| M8 dev GitOps | 완료. root/7 child 정상 동기화, E-11·E-12·E-15 통과 |
| M9 prod | 완료. 승격·E-13·E-14 및 빈 OS에서 세 명령 복구 통과 |

M0~M9 개발 계획과 E-01~E-15 실험을 모두 완료했다.
[완료 검증](docs/completion.md), [계획](docs/plan.md), [CI](docs/ci.md),
[prod 재현](docs/prod-bootstrap.md)에 결과와 운영 한계를 기록했다.

prod 터널에서는 [앨범](http://album.prod.localhost:8090)과
[Grafana](http://grafana.prod.localhost:8090)에 접속한다.

dev SSH 터널을 켠 뒤 [앨범](http://album.dev.localhost:8080)과
[Grafana](http://grafana.dev.localhost:8080)에 접속한다. Chrome에서 hosts 수정 없이
loopback으로 연결된다.
