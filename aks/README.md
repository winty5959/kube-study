# AKS 전환 프로젝트

이 폴더는 `k3s/`의 사진 앨범을 Azure Kubernetes Service에서 재현하는 독립 프로젝트입니다. 앱 동작과 데이터 모델은 기록된 원본 SHA에서 필요한 파일만 복사했고, 이후 배포·CI·이미지는 `aks/` 전용 경로와 이름으로 관리합니다.

## 현재 상태

- A1 소스 골격을 원본 `6ca720be871727c240259664d9c1d1515766f42d`에서 복사했습니다. 복사 범위와 제외 항목은 [원본 기준 기록](docs/source-baseline.md)에 있습니다.
- A0는 AX사업부문-인프라아키텍처팀 구독으로 확인 중입니다. 기존 K3S RG `rg-seonung-kube-study`는 `koreacentral`에 있고, AKS 전용 후보 `rg-seonung-kube-study-aks`는 아직 없습니다.
- 구독에서 계획 SKU `Standard_F4s_v2`가 `koreacentral` 사용 불가로 표시되어 인프라 생성은 보류 중입니다. 별도 선택 없이 SKU나 리전을 바꾸지 않습니다.
- Azure AKS 리소스는 아직 생성하지 않았습니다. A0 결과와 다음 결정은 [결정 기록](docs/decisions.md)에 남깁니다.

## 전환 순서

1. 기준 SHA, 구독·tenant, 권한, 리전, SKU/quota, 비용, 접근 CIDR을 확인합니다.
2. 독립 소스와 AKS 전용 선택 빌드·이미지 승격을 준비합니다.
3. Bicep으로 AKS와 네트워크를 선언하고 2개 노드, Azure Disk CSI, Ingress, 관리 접근을 확인합니다.
4. AKS 전용 시크릿, PostgreSQL, Redis, MinIO, ArgoCD, KEDA와 관측성을 준비합니다.
5. dev GitOps와 업로드·큐·썸네일·목록·다운로드·삭제 흐름을 검증합니다.
6. 데이터 백업·복원, 자원 수용, node drain, CSI 재연결, 중지·재개를 시험합니다.
7. 동일 이미지 digest의 학습용 prod namespace 승격과 E-01~E-15 실험을 기록합니다.
8. 비용, 복구 절차와 완료 결과를 정리합니다.

## 설계 경계

AKS에서는 `local-path` 대신 Azure Disk CSI PVC를 사용하고, node 교체 시 RWO 볼륨 재연결과 백업·복원을 실측합니다. 관리형 DB/Redis, Blob, ACR, Key Vault, 별도 prod 클러스터와 사용자 트래픽 이전은 기본안에 포함하지 않습니다. 같은 클러스터의 `album-prod`는 학습용 승격 namespace이며 운영 격리를 제공하지 않습니다.

관리 API는 승인된 출발지 범위로 제한하고 `0.0.0.0/0`을 사용하지 않습니다. 앱·Grafana·ArgoCD·S3 console은 공인 endpoint로 노출하지 않고 localhost port-forward 또는 승인된 VM tunnel을 사용합니다. 실제 경로와 CIDR은 A0에서 확인한 뒤 기록합니다.

기존 K3S 사용자 트래픽 이전과 K3S 환경 삭제는 별도 결정입니다. 여기서는 기존 dev/prod 서비스와 데이터를 보존한 채 별도 AKS에서 전환을 검증합니다.

## 문서와 증거

- [결정 기록](docs/decisions.md)
- [복사한 원본과 제외 항목](docs/source-baseline.md)
- [상세 구현 명세](../.omo/plans/aks-implementation.md)
- [최소 사양·비용 기준](../.omo/plans/aks-cost-baseline.md)
- [K3S 정리 계획과 완료 증거](../.omo/plans/k3s-onprem-aks-migration.md)
