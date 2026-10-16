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

## K3S 기준과 AKS 적응 항목

K3S의 사진 앨범 기능, 이미지 digest 승격, Traefik 진입점과 GET/HEAD 전용 S3 접근
정책을 기준으로 삼습니다. AKS에서는 `local-path`를 Azure Disk CSI PVC로 바꾸고,
node/zone 배치, RWO 재연결, 백업과 복원까지 확인합니다. 이전 완료 기록은 빈 OS에
Git과 키를 복구한 결과이며 데이터 복원 검증이 아닙니다. 실제 DB·객체 데이터량을
확인한 뒤 dump/restore, 원본·썸네일 복사, 큐와 DB 정합성, 쓰기 중지·재개와 롤백 후
변경 데이터 처리까지 리허설합니다. 현재 데이터가 없다고 가정하지 않습니다.

구현 전 결정 및 확인 항목:

- **비용·격리:** 실제 tenant/subscription, 허용 리전·SKU·quota·정책과 최신 비용을
  A0에서 확인합니다. 기본안에는 별도 AKS prod 클러스터가 없고, `album-prod`는 같은
  클러스터의 학습 namespace입니다. 실제 운영 격리 수준과 예산 한도는 owner 결정입니다.
- **이미지·ID:** GHCR을 유지할지 ACR로 옮길지, SealedSecrets 재봉인 키를 둘지
  Workload Identity와 Key Vault를 쓸지 결정합니다. 새 클러스터는 기존 K3S sealing key를
  재사용하지 않습니다.
- **네트워크·스토리지:** Traefik IngressRoute와 presigned URL 동작, S3 GET/HEAD-only
  경계, NetworkPolicy DNS 및 ingress selector 차이를 검증합니다. Azure Disk CSI의
  zone 제약, node 교체 시 PVC 재연결, 백업·복원 절차를 실측합니다.
- **관측성·데이터 서비스:** kube-prometheus-stack을 재사용할지 Azure 관리형 관측성을
  쓸지 비용과 운영 부담을 비교합니다. MinIO 예외 만료는 재승인 없이 연장하지 않습니다.
  PostgreSQL·Redis·Blob 관리형 전환은 AKS 이전과 별도 결정입니다.
- **접근:** 관리 경로는 localhost tunnel을 기본으로 하고 public API endpoint를 만들지
  않습니다. 사용자 접근 경로를 열기 전에 인증, DNS/TLS, 허용 CIDR의 owner 결정을 기록합니다.

## K3S 실험의 AKS 재적용

아래는 실행 전 매핑입니다. 각 실험은 상세 명세 A13 선행 조건을 확인한 뒤 기록하고,
통과하지 않은 항목은 완료로 표시하지 않습니다.

| 실험 | AKS에서 확인할 동작 | 계획 카드와 복구 기준 |
|---|---|---|
| E-01 셀프 힐링 | API replica 하나를 교체해도 응답 유지 | A13; 원래 replica/HPA 복구 |
| E-02 HPA | 200 VU에서 CPU 60% 기준 1→3→1 | A10/A13; 부하 종료·축소 확인 |
| E-03 KEDA | 500장 처리 큐에서 worker 0→2→0 | A10/A13; fixture와 큐 정리 |
| E-04 롤링 업데이트 | 새/이전 digest, Ready 상태와 오류 수 | A13; 안정된 Git 이미지 복구 |
| E-05 rollout 중단 | readiness 실패 중 기존 Ready 서비스 유지 | A13; 실험 선언 복구, live undo와 Git 구분 |
| E-06 OOM | 64Mi limit에서 OOMKilled 및 3회 후 FAILED | A13; 정상 limit/fixture 복구 |
| E-07 DB 장애 | readiness 실패, liveness 유지, DB 복구 | A13; DB와 앱 Healthy 확인 |
| E-08 영속성 | Pod 교체 후 row·원본·썸네일 유지 | A9/A13; CSI disk/PVC 보존 |
| E-09 NetworkPolicy | frontend→DB 차단, API→DB 허용과 대조군 | A5/A13; 실험 정책 제거 |
| E-10 ConfigMap | 설정 hash·rollout·새 썸네일 크기 | A13; 기존 설정과 fixture 복구 |
| E-11 GitOps CI | AKS 전용 build와 scan, dev 자동 Sync | A2/A8/A13; K3S 승격 없음 확인 |
| E-12 selfHeal | dev drift가 Git 선언으로 복구 | A7/A13; HPA 소유 replica와 구분 |
| E-13 승격 | dev/release digest 일치, prod 수동 Sync | A12/A13; 승인 전 prod 미변경 |
| E-14 롤백 | live undo의 OutOfSync와 수동 Sync 결과 | A12/A13; Git revert로 선언 복구 |
| E-15 배포 gate | 실패 PreSync가 새 rollout 차단 | A8/A13; 정상 migration 설정 복구 |

추가 실험은 `AKS-DATA`(실제 DB와 객체 백업 복원·정합성), `AKS-NODE`(drain 후
RWO PVC 분리/재연결), `AKS-STOP`(수동 중지·재개와 비용/복구), `AKS-CUTOVER`
(쓰기 경계·접속 변경·롤백 데이터 처리)입니다. PDB, 단일 replica 데이터 서비스,
LRS의 제약을 기록하며 전체 노드 장애 시 무중단을 약속하지 않습니다.

현재 이 문서는 실행 로드맵입니다. 아래 구현 명세와 비용 기준에 적힌 작업은 별도 증거가
갱신되기 전까지 미실행이며, 구독 SKU·quota·정책 및 배포 가능성을 보장하지 않습니다.

## 구현 명세

- [AKS 상세 구현 명세](../.omo/plans/aks-implementation.md)
- [최소 사양·비용 기준](../.omo/plans/aks-cost-baseline.md)
- [K3S 경로 정리 계획](../.omo/plans/k3s-onprem-aks-migration.md)

AKS 리소스를 만들기 전 실제 subscription/tenant, 권한, 지원 버전, 지역 quota,
네트워크 중복과 최신 가격을 다시 확인합니다. 계획의 SKU와 주소 범위는 사전 후보이며
구독에서 사용 가능한지 확인되기 전까지 배포 가능하다고 간주하지 않습니다.
