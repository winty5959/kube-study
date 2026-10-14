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

마일스톤이 진행되며 채워진다.

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
