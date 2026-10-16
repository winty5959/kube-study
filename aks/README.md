# AKS 전환 프로젝트

이 폴더는 기존 K3S 사진 앨범을 AKS에서 재현하기 위한 독립 프로젝트입니다.
앱 기능과 데이터 스키마는 `k3s/`를 기준으로 필요한 파일을 한 번 복사하고,
그 뒤에는 `aks/`의 구현을 별도로 관리합니다. 현재 상태와 실행 결과는 아래 명세 및
`aks/docs/`의 증거를 기준으로 갱신합니다.

## 전환 순서

1. **기준과 제약 확인:** 원본 SHA, 구독·tenant, 권한, 리전, SKU/quota, 비용과 CIDR을 확정합니다.
2. **독립 소스와 CI 준비:** 필요한 앱·Kubernetes 파일만 가져오고 AKS 전용 선택 빌드·이미지 경로를 만듭니다.
3. **클러스터와 스토리지 구성:** Bicep, Azure Disk CSI, Ingress, 네트워크 정책과 관리 접근을 준비합니다.
4. **시크릿과 플랫폼 설치:** 새 클러스터용 자격 증명과 PostgreSQL, Redis, MinIO, ArgoCD, KEDA, 관측성을 준비합니다.
5. **dev GitOps와 앱 검증:** 마이그레이션·smoke hook과 자동 dev 배포를 구성하고 사진 업로드부터 삭제까지 확인합니다.
6. **복구와 운영 검증:** 데이터 백업·복원, 자원 수용, node drain, CSI 재연결, 중지·재개를 시험합니다.
7. **Release와 전환 리허설:** 동일 digest의 prod 학습 namespace 승격, 기존 실험 재수행, 쓰기 중지·접속 전환·롤백을 리허설합니다.
8. **비용과 완료 기록:** 실제 청구 가정, 복구 절차, 검증 증거와 남은 운영 결정을 기록합니다.

실제 K3S 사용자 트래픽 이전과 원본 K3S 환경 삭제는 별도 결정입니다. 같은 AKS의
`album-prod`는 격리된 운영 클러스터가 아니라 학습용 승격 대상입니다.

## 구현 명세

- [AKS 상세 구현 명세](../.omo/plans/aks-implementation.md)
- [최소 사양·비용 기준](../.omo/plans/aks-cost-baseline.md)
- [K3S 경로 정리 계획](../.omo/plans/k3s-onprem-aks-migration.md)

AKS 리소스를 만들기 전 실제 subscription/tenant, 권한, 지원 버전, 지역 quota,
네트워크 중복과 최신 가격을 다시 확인합니다. 계획의 SKU와 주소 범위는 사전 후보이며
구독에서 사용 가능한지 확인되기 전까지 배포 가능하다고 간주하지 않습니다.
