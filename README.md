# kube-study

쿠버네티스 학습 프로젝트를 하나의 Git 저장소에서 관리합니다. 기존 K3S 서비스는
`k3s/`에서 계속 운영하고, AKS 전환 프로젝트는 `aks/`에서 독립적으로 진행합니다.

| 경로 | 목적 |
|---|---|
| [`k3s/`](k3s/README.md) | 기존 사진 앨범 앱, K3S 배포, 실험·운영 문서 |
| [`aks/`](aks/README.md) | AKS 전환 계획과 구현 |
| [K3S 경로 정리 계획](.omo/plans/k3s-onprem-aks-migration.md) | 저장소 구조와 기존 배포 경로 전환 |
| [AKS 구현 명세](.omo/plans/aks-implementation.md) | AKS A0~A15 실행·검증 카드 |
| [AKS 비용 기준](.omo/plans/aks-cost-baseline.md) | 최소 구성과 비용 가정 |

저장소 루트의 `.github/workflows/`는 K3S CI와 Release workflow를 유지합니다.
두 workflow는 `k3s/` 변경만 감지하며, AKS는 별도 workflow와 이미지 이름을 사용합니다.

구현 상태는 계획 문서와 각 프로젝트의 완료 증거를 따릅니다. AKS 리소스 생성과
배포는 실제 구독의 접근 권한, SKU/quota, 생성 시점 비용을 확인한 뒤 진행합니다.
