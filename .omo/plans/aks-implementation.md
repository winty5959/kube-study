# AKS 전환 상세 구현 명세

작성: **2026-10-16 KST** · 기준 HEAD `a64cdb3` · **구현 진행 중**.

참고 대화: [개발 계획 세부화](codex://threads/01a1421b-3811-7113-bffa-2b244b6a99eb),
[K3S → AKS 계획과 저장소 구조 확정](codex://threads/01a141ef-9600-7db3-9856-ecefa17822f2).
함께 읽을 문서: [K3S 경로 정리 계획](k3s-onprem-aks-migration.md),
[AKS 최소 사양·비용 근거](aks-cost-baseline.md), [저장소 작업 규칙](../../AGENTS.md).

이 문서는 앞선 세션에서 저장하지 못한 A0~A15 구현 카드를 완성했다. 사용자가
2026-10-16 이 계획을 기준으로 goal을 수립하고 프로젝트 구현을 요청해 실행에 들어갔다.
사용자 합의는 저장소 `winty5959/kube-study` 하나를 유지하고 기존 프로젝트를 `k3s/`,
새 AKS 전환 프로젝트를 `aks/`에 두는 것이다. 사용자가 AKS를 처음 사용하므로 임의 예산을
정하지 않고 현재 프로젝트를 실행할 최소 구성부터 검증한다. 사용자는 먼저 AX사업부문-인프라아키텍처팀
구독을 골랐으나, 이후 이를 정정해 Enterprise부문-아키텍처강화TF 구독과
`rg-seonung-aks-test`를 대상으로 선택했다. 계획 SKU F4s_v2는 사용할 수 없어 사용자가
최종 선택한 D4as_v5 두 대로 A3를 완료했다. 필요한 AKS Azure RBAC 역할은 사용자가 제공한
Owner 권한 경로로 부여했고, 결과와 비용은 증거 파일에 갱신했다.

## 1. 목표와 전환 경계

완료 목표는 기존 사진 업로드 → 큐 → 썸네일 → 목록·다운로드·삭제 흐름, GitOps,
관측성, HPA/KEDA와 학습 실험을 AKS에서 재현하고 실제 비용·복구 방법을 기록하는 것이다.
기존 K3S를 유지한 채 별도 AKS에서 검증하며, 실제 사용자 트래픽 이전은 리허설 결과를 보고 결정한다.

- 선행 조건: 상위 계획의 K3S 작업 1~6과 F1~F4를 완료한다. 완료 SHA를 A0에서 확정한다.
- 앱·DB 스키마·큐 처리·UI는 기존 구현을 재사용한다. 코드 복사는 A1에서 필요한 파일만 한 번 한다.
- AKS용 파일은 이후 `k3s/`를 import하거나 Kustomize/Helm 경로로 참조하지 않는다.
- AKS 안에 ArgoCD 1개를 설치한다. K3S ArgoCD에 AKS cluster credential을 등록하지 않는다.
- 기본 배포는 dev namespace 하나다. 같은 AKS의 prod namespace는 A12 승격 실습 때만 추가한다.
  이는 운영 장애 격리를 보장하는 별도 prod 클러스터가 아니다.
- 데이터 서비스는 PostgreSQL·Redis·MinIO를 유지한다. 관리형 DB/Redis, Blob, ACR, Key Vault,
  ApplicationSet, service mesh, 범용 배포 엔진, 별도 상시 build VM은 기본안에 추가하지 않는다.
- Mac에서는 Python venv와 컨테이너 이미지를 만들지 않는다. 기존 개발 VM 또는 hosted CI에서
  테스트·이미지 빌드를 수행한다. 부하 도구도 기존 VM에서 실행하고 그 VM 비용은 별도 기록한다.

현재 확인 가능한 원본: [PRD](../../k3s/docs/prd.md), [기존 완료 증거](../../k3s/docs/completion.md),
[실험 명세](../../k3s/docs/experiments/README.md), [MinIO 보안 기준](../../k3s/docs/minio-security.md).
아래 `k3s/...`는 기존 프로젝트 원본, `aks/...`는 **후속 구현 산출물**이며
현재 존재하는 구현으로 취급하지 않는다.

## 2. 최소 구성과 확정 방법

| 항목 | 계획 기본값 | 선택 이유·검증 조건 |
|---|---|---|
| Azure 대상 | Enterprise부문-아키텍처강화TF, `rg-seonung-aks-test` | 사용자가 최종 선택; RG와 AKS가 `koreacentral`에 생성됨 |
| 리전 | `koreacentral` | 기존 환경과 비용 문서 기준; 정책·SKU 가용성은 A0 확인 |
| 구성 방식 / 관리 tier | AKS Standard 구성 방식 / Free 관리 tier | 고정 작은 풀과 수동 stop/start; 유료 Standard tier와 구분 |
| 노드 | Linux x86_64, System 풀 1개; `Standard_D4as_v5` 2대 | 각 4 vCPU·16 GiB; 두 노드 Ready. F4s_v2는 선택 구독에서 Korea Central 사용 불가 |
| OS / OS disk | 지원되는 Ubuntu 이미지, Managed OS 64 GiB | 견적은 Premium SSD P6 2개; 실제 생성 SKU·크기를 확인 |
| 노드 확장 | 고정 2대, upgrade `maxSurge=1` | 자동 증설 없이 시작; 일반 가동 8 vCPU, surge 포함 12 vCPU quota 확인 |
| 네트워크 | Azure CNI Overlay + Cilium, Standard LB outbound | 기존 NetworkPolicy 유지, GHCR/Git/Helm outbound 확보 |
| zone | 다중 zone 미사용 | LRS 디스크의 재연결 조건을 단순화; 가용성은 학습 수준 |
| API server | public endpoint + 실제 관리 출발지 CIDR 허용 | 별도 Bastion/VPN 비용 없이 관리; `0.0.0.0/0`을 기본값으로 두지 않음 |
| 사용자 인증 | Entra 통합 + Azure RBAC | 기존 승인된 사용자/역할을 사용; 접근 불가 시 임의 admin credential 우회 금지 |
| 노드 identity | managed identity | custom subnet 권한을 A0 확인; 앱은 Azure API를 호출하지 않음 |
| Ingress | Traefik 1 replica, `ingress-system`, ClusterIP | K3S의 Traefik API 재사용, 앱 공개용 LB/IP 추가 방지 |
| 접근 | localhost port-forward, 필요 시 기존 VM SSH 터널 | 앱·Grafana·ArgoCD·S3 console을 공인 IP로 노출하지 않음 |
| 영속성 | `disk.csi.azure.com`, `StandardSSD_LRS`, RWO | 명시적 사용자 StorageClass, 6개 초기 PVC |
| 도구 | ArgoCD·KEDA·SealedSecrets·kube-prometheus-stack | 기존 고정 버전·작은 requests를 시작점으로 사용 |

System 풀에는 앱도 배치하므로 `CriticalAddonsOnly:NoSchedule` taint를 넣지 않는다.
별도 User 풀·Spot·NAP·cluster-autoscaler는 사용하지 않는다. 클러스터 2노드 조건과
노드당 4 vCPU·B 계열 미지원은 [시스템 풀 공식 문서](https://learn.microsoft.com/en-us/azure/aks/use-system-pools)를
기준으로 했다. 실제 생성 가능성과 앱 부하 수용은 아직 확인하지 않았다.

네트워크는 VNet `10.240.0.0/16`, node subnet `10.240.0.0/22`, pod CIDR
`10.244.0.0/16`, service CIDR `10.250.0.0/16`, DNS `10.250.0.10`, `maxPods=50`으로
생성했다. Enterprise 구독의 기존 VNet·subnet 범위와 겹치지 않는 것을 확인했다.
구독 밖의 조직/VPN 경로는 확인할 수 없었다. public API는 관리 출발지 하나의 `/32`만
허용하며 literal 주소는 증거와 Git에 남기지 않는다.

AKS RG는 `rg-seonung-aks-test`, cluster는 `aks-kube-study`다. Azure가 node RG
`MC_rg-seonung-aks-test_aks-kube-study_koreacentral`을 만들었다. 기존 K3S RG는 재사용하지 않았다.

선택한 D4as_v5 비용 기준은 월 730시간 **약 $354.83**, 예시 88시간 **약 $82.63**이며
I/O·전송·백업·surge·기존 VM은 별도다. 중지 상태에도 디스크·네트워크의 고정항목을
보수적으로 **$45.31/월** 반영했다. 사용 시간은 아직 정해지지 않았다.
F4s_v2를 구독에서 사용할 수 없어 D4as_v5를 선택했으며 비용 기준도 갱신했다.
간헐 사용의 `D4ads_v5` + ephemeral OS 대안은 지원·가동 시간을 확인한 뒤 별도로 비교한다.

## 3. 저장소·CI/CD 계약

```text
kube-study/
├── .github/workflows/
│   ├── ci.yaml, release.yaml             # K3S 소유
│   └── aks-ci.yaml, aks-release.yaml     # AKS 소유, A2/A12에서 추가
├── k3s/                                 # 기존 프로젝트
└── aks/
    ├── README.md
    ├── apps/, docker-compose.yaml, loadtest/
    ├── k8s/{base,overlays,gitops,secrets,monitoring}/
    ├── argocd/{bootstrap,prerequisites,observability}/
    ├── dashboards/, infra/, scripts/, docs/
    └── infra/azure/{main.bicep,main.example.bicepparam}
```

| 계약 | K3S | AKS |
|---|---|---|
| Git source | `k3s/**` | `aks/**` |
| GHCR | `album-{api,worker,frontend,minio}` | `album-aks-{api,worker,frontend,minio}` |
| image tag | 기존 `sha-<7자리 SHA>` / release alias | 같은 형식, 별도 image repository |
| Git release tag | `vMAJOR.MINOR.PATCH` | `aks-vMAJOR.MINOR.PATCH` |
| workflow concurrency / cache | K3S 접두사 | AKS 접두사 |
| 배포 | K3S dev 자동·prod 수동 | AKS dev 자동·prod 수동 |

AKS context 이름은 `aks-study`로 분리한다. AKS 앱 namespace는 `album-dev` / `album-prod`를
유지해 기존 앱·대시보드 helper 변경을 줄인다. 같은 이름이어도 클러스터는 다르므로
모든 운영 명령은 context를 명시하거나 스크립트가 시작 시 대상 context를 검증한다.
Argo Application은 `root-aks-dev`, `album-aks-dev`, `platform-aks-dev` 등으로 구분한다.
클러스터 공용 Helm 도구는 dev bootstrap 하나에서 소유한다. prod bootstrap에서 같은
KEDA·SealedSecrets·Traefik·monitoring 객체를 다시 관리하지 않는다.

Git diff·git add·Docker action context는 저장소 루트 좌표, helper 파일 읽기는
`Path(__file__).resolve()` 기반 AKS 프로젝트 좌표를 사용한다.
`defaults.run.working-directory`는 `uses:`의 context/path 입력을 바꾸지 않는다.
K3S selector의 `.github/workflows/` 전체 prefix 매칭은 상위 경로 정리 작업에서 좁힌다.
AKS도 자신의 두 workflow만 소유하며 docs-only 변경으로 이미지를 빌드·승격하지 않는다.

## 4. 실행 순서와 작업 크기

| 카드 | 결과 | 선행 |
|---|---|---|
| A0 | 원본 SHA·Open Tenant·quota·비용·접근 확정 | K3S 정리 완료 |
| A1 | 독립 AKS 소스와 문서 골격 | A0 |
| A2 | AKS 선택 빌드·scan·dev 이미지 게시 | A1 |
| A3 | 재현 가능한 AKS 인프라와 2 Ready 노드 | A0, A1 |
| A4 | CSI StorageClass·PVC 적응·재연결 준비 | A3 |
| A5 | Traefik·NetworkPolicy·관리 접근 | A2, A3 |
| A6 | 별도 시크릿과 데이터·필수 도구 bootstrap | A2, A4, A5 |
| A7 | AKS ArgoCD와 platform 선언 소유권 전환 | A6 |
| A8 | migration/smoke hook을 갖춘 dev GitOps | A7 |
| A9 | 기존 데이터의 백업·복원 리허설 | A8 |
| A10 | 관측성·HPA/KEDA·최소 자원 수용 | A8, A9 |
| A11 | node drain·CSI 재연결·stop/start | A10 |
| A12 | 필요 시 prod namespace와 동일 digest 승격 | A10, A11 |
| A13 | E-01~E-15 AKS 재수행 | A12 |
| A14 | 쓰기 중지·접속 전환·롤백 리허설 | A9, A11, A13 |
| A15 | 비용 대조·완료 기록·미사용 자원 정리 | A14 |

A2와 A3은 서로 다른 파일 작업으로 진행할 수 있지만 한 구현 담당자는 한 카드씩 완료한다.
A12를 생략하면 dev 환경 완료만 보고하며 E-13/E-14까지 전체 완료했다고 표시하지 않는다.
전체 학습 전환 완료를 목표로 실행 요청을 받으면 A12도 수행한다.

각 카드의 로그는 `.omo/evidence/aks-implementation/Axx-<주제>.txt`에 비밀 없는 결과만 남기고,
제품 운영 지침은 `aks/docs/`에 쓴다. 구현 시 카드별 기능 커밋에 Lore 결정·실제 검증·미검증을 기록한다.
한 카드가 크면 아래 하위 단계대로 나누되 미완성 인프라나 깨진 CI를 게시하지 않는다.
완료 체크박스는 실제 실행·검증 후에만 변경한다.

## 5. 구현 카드

### A0. 기준 상태와 Azure 실행 전제 확정

- [x] 완료
- **읽기:** 상위 계획 완료 기록, 비용 문서, `k3s/docs/{completion,azure-vm,operations}.md`,
  Azure Open Tenant 스킬 `/Users/seonung/.codex/skills/azure-open-tenant-subscription/SKILL.md`.
- **산출물:** `aks/docs/decisions.md`의 원본 SHA·사양·접근·주소 계획,
  `aks/docs/cost.md`의 생성 직전 견적. 자격 증명·ID·관리 IP 실값은 public 문서에 넣지 않는다.
- **순서:** (0a) 최신 HEAD/dirty 상태·K3S 두 환경 상태와 이미지 digest 확보 →
  (0b) 현재 CLI 인증 확인, 필요할 때만 지정 tenant 로그인 →
  (0c) 정확한 Enabled 구독 선택 → (0d) AKS 전용 RG 범위·region 정책·SKU·quota·역할 확인 →
  (0e) 현재 가격과 CIDR·접근 계획 확정.
- 로그인 확인은 스킬대로 `az account show --query '{name:name,state:state}' -o json`을 사용한다.
  구독명 일치만으로 tenant 일치를 단정하지 않는다. MFA/브라우저 인증은 CLI 흐름으로 진행한다.
- `az vm list-skus`, `az vm list-usage`, `az aks get-versions`로 region/SKU 지원·제한과
  **일반 8 vCPU 및 surge 포함 12 vCPU**를 확인한다. F family quota와 regional quota를 모두 본다.
  Entra/Azure RBAC 관리 접근, custom subnet identity 권한, 필요한 provider 상태를 확인한다.
  provider 등록·역할 부여는 기존 권한 확인과 구분해 해당 구현 요청 범위에서 처리한다.
- **성공 검증:** 원본 SHA, 지원되는 GA Kubernetes 버전, 대상 범위·2노드 SKU·quota와
  실제 관리 접근 방안이 기록되고 비용 문서의 가정과 모순이 없다.
- **실패 검증·복구:** tenant 불명/구독 중복·비활성/권한 부족이면 Azure 작업을 멈추고
  실패 범주만 보고한다. 다른 tenant·리전·SKU를 몰래 선택하거나 quota 증가를 승인된 것으로 취급하지 않는다.
  로컬 계획 보완은 가능하다. 기존 Azure 리소스 변경은 없다.
- **커밋 단위:** `docs(aks): record deployment constraints and baseline`.

### A1. 필요한 소스만 독립 AKS 프로젝트로 준비

- [x] 완료
- **수정:** `aks/README.md`, `.gitignore`, `aks/.gitignore`, 위 구조의 AKS 디렉터리.
- **복사 원본:** 완료 SHA의 `k3s/apps`, `k3s/k8s`, `k3s/argocd`, `k3s/dashboards`,
  `k3s/infra/{argocd,keda,sealed-secrets,monitoring,minio,compose}`, `k3s/loadtest`,
  필요한 `k3s/scripts`, `k3s/docker-compose.yaml`.
  K3S 설치·VM 생성·containerd import·K3S kubeconfig 수집 스크립트는 복사 대상에서 제외한다.
- **순서:** (1a) 추적 파일 allowlist 확보 → (1b) 앱·lockfile·필요한 설정 복사 →
  (1c) 문서에 원본 SHA와 AKS 미배포 상태 표시 → (1d) 원본 프로젝트와 경로 경계 확인.
- `.env`, venv, kubeconfig, 개인 키, 봉인 키, Graphify/CodeGraph 캐시와 실험 결과 이미지는 복사하지 않는다.
  K3S SealedSecret ciphertext도 배포 입력으로 복제하지 않고 A6에서 새 키로 준비한다.
  기존 E-XX 성공 기록은 참고만 하고 AKS 결과 문서는 미실행 상태로 새로 만든다.
- **성공 검증:** 루트 `.git` 하나와 기존 origin 유지, K3S diff 없음,
  앱 source/lockfile이 지정 SHA와 일치한다. 새 루트 README 링크와 복사 allowlist를 검사한다.
  자동 GitOps 진입점이나 workflow를 아직 활성화하지 않는다.
- **실패 검증·복구:** 비밀 파일이 포함되면 전송·commit 전에 자신의 복사에서 제거한다.
  타인의 dirty 파일은 변경하지 않는다. AKS 안에 `../k3s` 참조가 남으면 해당 참조를 자체 파일로 바꾼다.
- **커밋 단위:** `chore(aks): seed the independent conversion project`.

### A2. AKS 선택 CI·이미지 이름·최초 이미지 게시

- [x] 완료
- **읽기/수정:** `.github/workflows/aks-ci.yaml`, `aks/scripts/{changed-components,set-image-tag,
  prepare-release}.py`, `aks/scripts/tests/{test_changed_components,test_image_tags,test_release}.py`,
  `aks/k8s/{base,overlays,gitops}/**`, `aks/infra/minio/trivyignore.yaml`.
- **순서:** (2a) 모든 이미지 reference와 helper 정규식을 `album-aks-*`로 수정 →
  (2b) repo-relative 변경 감지와 Docker context 설정 → (2c) 기존 test/lint/scan 흐름 적용 →
  (2d) 최초 네 이미지 build/scan/push → (2e) AKS dev overlay만 태그 승격.
- API/worker/frontend뿐 아니라 migrate·PostSync smoke·cleanup의 API image와 MinIO도 포함한다.
  selector의 unchanged tag 추출, tag helper, release parser·test fixture까지 같은 이름을 사용한다.
  dev는 `sha-<7자리 SHA>`, release parser는 A12의 `aks-vMAJOR.MINOR.PATCH`만 받도록 준비한다.
- 최초 AKS bootstrap은 네 image repository가 비어 있으므로 전체 build를 명시적으로 한 번 수행한다.
  이후 API-only는 api만 build/push하되 unchanged component도 기존 dev artifact를 scan한다.
  manifest-only는 렌더 검사, docs-only는 build·push·overlay 승격 없음으로 판정한다.
- HIGH/CRITICAL gate는 기존 정책을 유지한다. MinIO의 6건 예외는 정확한 finding/path와
  **2026-11-14 만료**를 유지하고, 새 finding·경로·기한을 자동 허용하지 않는다.
- **성공 검증:** hosted CI에서 네 image manifest digest 조회, AKS dev만 승격,
  API-only/AKS workflow-only/K3S-only/docs-only fixture 판정 및 root cwd/AKS cwd 검사.
  `actionlint`, VM의 기존 pytest/ruff, frontend `node --check`, 렌더 검사를 수행한다.
- **실패 검증·복구:** 미게시 unchanged image·잘못된 tag·만료/다른 경로 예외는 gate 실패,
  승격 미발생이어야 한다. K3S workflow·overlay를 바꾸면 안 된다. 충돌한 bot push는
  직전 rebase 후 정상 push하거나 실패하며 force-push하지 않는다.
- **커밋 단위:** `ci(aks): isolate selective builds and dev promotion`.

### A3. 작은 Bicep 명세로 AKS 생성·상태 확인

- [x] 완료
- **수정:** `aks/infra/azure/main.bicep`, `main.example.bicepparam`, `aks/docs/bootstrap.md`.
  실제 구독·관리 CIDR·identity를 포함한 로컬 parameter 파일은 ignore한다.
- **순서:** (3a) 확정 Day-0 값으로 VNet/subnet과 cluster 선언 → (3b) Bicep build/validate/what-if →
  (3c) AKS 전용 RG에 incremental deployment → (3d) Azure 결과·노드·관리 인증 확인.
- RG 내부 단일 Bicep 파일을 사용하고 Terraform/azd와 중복 상태 관리하지 않는다.
  API version은 생성 시점 지원되는 stable 버전으로 고정한다. 2 System nodes·VMSS·Managed OS
  64 GiB·Free tier·CNI Overlay/Cilium·outbound LB·authorized ranges·Entra/Azure RBAC를 명시한다.
  자동 유료 addon과 node autoscaling을 넣지 않는다. `maxSurge=1`과 지원되는 upgrade/OS patch
  정책·점검 시간을 기록하고 업그레이드 후 A11 재검증 조건을 적는다.
- 관리 kubeconfig는 새 `aks-study` context에 병합한다. 기존 K3S context를 덮어쓰지 않고
  kubeconfig·인증 토큰은 ignore된 파일에서만 관리한다. 필요한 `kubelogin` 흐름을 문서화한다.
- **성공 검증:** Bicep build·validate·what-if 통과, 실제 `provisioningState=Succeeded`,
  `powerState.code=Running`, System pool count=2, Node 2개 Ready, Cilium/CSI/metrics-server 정상.
  생성 OS disk SKU·크기와 node RG를 비용 문서에 대조한다. 재 what-if에 예상 밖 삭제가 없다.
- **실패 검증·복구:** 정책/quota/SKU 실패는 오류 범주를 기록하고 설정을 고친다.
  일부 생성됐다면 해당 deployment의 AKS 소유 리소스만 조회한다. K3S나 공유 RG를 삭제하지 않는다.
  public API 제한 때문에 연결되지 않으면 CIDR·RBAC부터 확인하고 unrestricted/admin 우회하지 않는다.
- **커밋 단위:** `infra(aks): declare the minimum learning cluster`.

### A4. Azure Disk CSI와 명시적 PVC 정책

- [x] 완료
- **수정:** `aks/k8s/gitops/dev/platform/storage-class.yaml`,
  `aks/k8s/base/{postgres,redis,minio}/statefulset.yaml`, `aks/infra/monitoring/values.yaml`,
  `aks/docs/storage.md`. The StorageClass lives inside the dev platform Kustomize root so ArgoCD's
  default load restriction accepts it and the prod platform Application cannot claim the same
  cluster-scoped object.
- **StorageClass:** 이름 `album-standard-ssd-retain`, provisioner `disk.csi.azure.com`,
  `skuName=StandardSSD_LRS`, `volumeBindingMode=WaitForFirstConsumer`, `reclaimPolicy=Retain`,
  `allowVolumeExpansion=true`, fsType `ext4`. AKS 기본 class를 수정하지 않고 새 class를 사용한다.
- 초기 PVC는 PostgreSQL 2Gi, Redis 1Gi, MinIO 10Gi, Prometheus 5Gi, Grafana 1Gi,
  Alertmanager 1Gi로 비용 문서와 일치시킨다. 모든 claim에 class를 명시한다.
  원본 UID·fsGroup·RWO를 유지하고 컨테이너에서 실제 파일을 쓸 수 있는지 확인한다.
- **순서:** (4a) 별도 class 렌더/적용 → (4b) 일회용 PVC+소비 Pod로 provisioning 확인 →
  (4c) 실제 Azure disk SKU·용량·가격 tier 확인 → (4d) 앱/관측성 선언에 class 반영.
  WaitForFirstConsumer의 소비 Pod 없는 Pending은 정상이며 즉시 실패로 취급하지 않는다.
- **성공 검증:** 소비 Pod 이후 Bound, 쓰기/재시작 후 데이터 유지, 실제 disk가 Standard SSD LRS.
  작은 요청이 예상보다 큰 disk로 만들어졌다면 실제 과금 용량으로 견적을 고친다.
  6개 초기 PVC의 요청 총량 20Gi와 비용표 과금 tier 총량 40Gi를 구분한다.
- **실패 검증·복구:** CSI 권한·quota·attach·permission 오류를 확인한다. 기존 Bound claim의
  storageClass/StatefulSet volumeClaimTemplates를 강제로 바꾸지 않는다. 변경이 필요하면
  새 PVC에 복원 후 전환한다. Retain은 백업이 아니며 삭제한 일회용 claim의 disk도 별도로 정리한다.
- **커밋 단위:** `storage(aks): adapt persistent claims to Azure Disk CSI`.

### A5. Traefik·네트워크 정책·localhost 접근

- [x] 완료
- **수정:** `aks/infra/traefik/values.yaml`, `aks/k8s/base/{application,minio,policy}/**`,
  `aks/k8s/overlays/dev/kustomization.yaml`, `aks/k8s/gitops/{dev/platform,hooks}/**`,
  `aks/scripts/tunnel.sh`, `aks/docs/access.md`.
- **순서:** (5a) Traefik chart 42.0.0 / app 3.7.14 및 CRD 고정·1 replica·100m/128Mi requests →
  (5b) `ingress-system` ClusterIP Service와 Ingress/IngressRoute 적용 →
  (5c) Cilium 정책의 namespace/Pod selector 적응 → (5d) localhost 경로 확인.
- K3S `traefik.kube-system` 주소와 정책의 kube-system selector를 `ingress-system`으로 바꾼다.
  PostSync/smoke-access 정책도 같은 주소·selector를 사용한다. ingressClass를 명시한다.
  DNS UDP/TCP 53, API/worker/cleanup/migrate→데이터, Prometheus→metrics,
  KEDA→Redis, smoke→gateway/API의 허용 경로를 유지한다.
- dev host는 `album.aks.localhost`, prod는 A12에서 `album.aks.prod.localhost`를 사용한다.
  `S3_ENDPOINT`는 내부 MinIO Service, `S3_PUBLIC_ENDPOINT`는 기존의 빈 값으로 두어
  요청 Host/port에서 서명 주소를 유도한다. 프록시는 Host와 URL path/query를 보존한다.
- `kubectl --context aks-study -n ingress-system port-forward service/traefik 8080:80 --address 127.0.0.1`
  로 접근한다. VM에서 실행한다면 이 localhost 포트에 SSH 터널을 추가한다.
  `/originals/`, `/thumbnails/`는 GET/HEAD만 허용하며 S3 쓰기·console은 공개 경로에 넣지 않는다.
- **성공 검증:** A5에서는 prerequisite namespace를 먼저 준비하고 기존 frontend image의
  일회용 Deployment/Service로 Host·gateway 경로를 확인한다. 실제 정책의 namespace/label을
  가진 일회용 HTTP/TCP probe Pod로 DNS와 허용/차단 경로를 확인하고 정리한다.
  새 ingress Public IP/LB Service가 없어야 한다. 실제 API·데이터·KEDA/Prometheus 연결과
  browser 원본·두 썸네일·presigned GET/HEAD는 A8/A10에서 검증한다.
  A5 시점에 데이터 서비스나 app이 이미 실행된 것으로 보고하지 않는다.
- **실패 검증·복구:** 잘못된 Host와 허용되지 않은 TCP 경로의 거절을 확인한다.
  S3 외부 PUT/DELETE 거절·서명 query 변조는 A8의 실제 MinIO 경로로 함께 확인한다.
  gateway 오류는 policy/route를 고치고 전체 policy 삭제로 검사만 통과시키지 않는다.
- **커밋 단위:** `network(aks): preserve ingress and policy behavior`.

### A6. 시크릿·데이터 서비스·필수 도구 bootstrap

- [x] 완료
- **수정:** `aks/scripts/{seal-environment,install-gitops,install-keda,install-monitoring}.sh`,
  `aks/k8s/secrets/dev/{album,monitoring}/**`, `aks/argocd/prerequisites/dev/**`,
  `aks/infra/{argocd,keda,sealed-secrets,monitoring}/values*.yaml`, `aks/docs/bootstrap.md`.
- **순서:** (6a) namespace·CSI/Traefik·SealedSecrets → (6b) AKS 전용 자격 증명 봉인 →
  (6c) PostgreSQL/Redis/MinIO → (6d) KEDA·monitoring·ArgoCD 준비.
  Helm chart는 원본 KEDA `2.21.0`, SealedSecrets `2.20.0`, kube-prometheus-stack `92.7.0`을
  시작점으로 실제 AKS 버전과 호환성을 확인한다. ArgoCD도 기존 설치 스크립트의 고정 버전을 확인한다.
  미호환이면 해당 chart만 올리고 이유·렌더 차이·자원 증가를 기록한다.
- AKS 전용 sealing key를 생성·외부 백업하고 controller cert로 strict name/namespace 봉인한다.
  기존 K3S 키와 ciphertext는 유지한다. 평문 `.env`는 외부 보안 위치/ignore 파일에만 둔다.
  이미지가 public인지 확인하고 private이면 scoped GHCR pull Secret을 별도로 봉인한다.
  `GITHUB_TOKEN`을 장기 imagePull credential로 복사하지 않는다.
- Grafana admin Secret도 AKS에서 새로 봉인한다. 시크릿 이름·필수 key 존재와 복호화 성공만
  확인하고 data, password, key 본문은 출력하지 않는다.
- **성공 검증:** 데이터 3종 Ready·6 PVC Bound, operator/CRD 정상,
  Helm 전체 렌더의 sidecar/initContainer/DaemonSet requests와 실제 노드 allocatable 기록.
  기본 requests 합계·실측 사용량을 비용 문서와 비교한다.
- **실패 검증·복구:** 잘못된 namespace의 ciphertext는 복호화 실패해야 한다.
  key backup 부재면 데이터 이전 단계로 진행하지 않는다. CRD나 Secret이 준비되지 않은
  상태에서 app을 자동 Sync하지 않는다. 기존 PVC를 uninstall/delete하여 복구하지 않는다.
- **실행 결과 (2026-10-16):** 차트 `kubeVersion` 제약과 Helm lint/template이 모두 통과해
  계획 버전을 유지했다. SealedSecrets, KEDA, Prometheus stack, Argo CD가 AKS 1.36.4에서
  Ready이며 각 CRD가 Established다. 독립 키 백업은 외부 경로에 mode `0600`, 상위 디렉터리는
  `0700`이고, 두 SealedSecret 모두 Synced다. namespace 오용 검사는 복호화 실패를 확인했다.
  세 데이터 StatefulSet과 모니터링 세 Pod가 Ready, PVC 6개가 모두 Bound다. 실측 requests와
  node allocatable/사용량은 비용 기준 문서에 기록했다. 자세한 출력은
  `.omo/evidence/aks-implementation/A6-bootstrap.txt`에 있다.
- **커밋 단위:** `platform(aks): bootstrap tools and independent sealed credentials`.

### A7. AKS ArgoCD와 platform 소유권 전환

- [x] 완료
- **수정:** `aks/argocd/root-dev.yaml`, `aks/argocd/bootstrap/dev/**`,
  `aks/argocd/observability/**`, `aks/k8s/gitops/dev/platform/**`, `aks/docs/gitops.md`.
- **순서:** (7a) root/children/Helm source 전체 렌더 → (7b) A6 실제 helm release와 spec 대조 →
  (7c) AKS platform 도구를 ArgoCD로 인계 → (7d) platform Healthy 확인.
  app 자동 Sync는 A8의 migration·smoke 준비가 끝난 뒤 활성화한다.
- repoURL은 기존 저장소, `targetRevision=main`, source.path는 `aks/...`,
  Helm valueFiles는 `$values/aks/infra/...`로 지정한다. Helm ref 전용 source에는 path를 붙이지 않는다.
  destination은 AKS 내부 `https://kubernetes.default.svc`다.
- Traefik·StorageClass도 단일 platform Application이 소유한다. 공용 chart는 dev bootstrap에서
  한 번 관리한다. 기존 releaseName·namespace를 유지해 중복 release/controller를 만들지 않는다.
  CRD→controller→Secret→data→application 순서와 실제 Healthy 조건을 확인한다.
- root-prod를 이후 추가할 때 `/operation` ignore와 `RespectIgnoreDifferences=true`를 보존한다.
  수동 prod Sync operation을 root가 반복 실행하지 않도록 spec을 유지한다.
- **성공 검증:** Argo repo-server와 동일 Kustomize 버전/options, 고정 Helm chart로 렌더;
  모든 AKS child source가 aks 경로, platform children Synced/Healthy, 중복 helm release 없음.
  K3S Argo와 PVC·image digest는 기준 상태와 일치한다.
- **실패 검증·복구:** 잘못된 path/values는 로컬 렌더에서 실패해야 한다. 인계가 실패하면
  자신의 AKS root 자동 Sync만 중지하고 마지막 검증된 specs로 복구한다. Application
  cascade 삭제나 Helm uninstall로 PVC·CRD를 제거하지 않는다.
- **실행 결과 (2026-10-16):** `root-dev`와 6개 child Application이 모두 Synced/Healthy다.
  `platform-dev`의 다중 source는 Traefik 42.0.0을 기존 `traefik` releaseName/namespace로
  렌더하고 `aks/k8s/gitops/dev/platform`의 StorageClass·data 서비스와 함께 관리한다.
  Helm inventory에는 deployed Traefik release가 하나다. Traefik은 ClusterIP를 유지하며
  내부 DNS hostname을 Ingress status에 게시한다. KEDA의 AKS 소유 webhook fields는 Argo
  ignore rule로 보존한다. 세 data StatefulSet은 Ready 1/1, PVC 6개는 Bound다. album child와
  앱 Deployment/Job/CronJob은 아직 없어 A8 migration/smoke 전에 앱을 시작하지 않았다.
  상세 결과는 `.omo/evidence/aks-implementation/A7-gitops.txt`에 있다.
- **커밋 단위:** `gitops(aks): reconcile the AKS platform independently`.

### A8. migration·cleanup·smoke와 dev 자동 배포

- [ ] 완료
- **수정:** `aks/k8s/{base/migrate,base/cleanup,gitops/hooks,gitops/dev/application}/**`,
  `aks/scripts/{smoke.py,kustomization.yaml}`, `aks/argocd/bootstrap/dev/album-dev.yaml`.
- **순서:** (8a) data/credentials가 별도 platform에 Ready인지 확인 → (8b) API와 같은 image의
  PreSync migration·PostSync smoke 구성 → (8c) 렌더·실패 gate 검사 → (8d) dev 자동 Sync 활성화.
- migration은 기존 advisory lock·schema_migrations·파일별 transaction을 유지한다.
  Job에 DB 권한만 전달하고 S3/Redis 설정을 요구하지 않는다. PostSync는 AKS Traefik 내부 주소와
  `SMOKE_HOST=album.aks.localhost`로 서명 Host를 보존한다. script ConfigMap 경로도 AKS 안에 둔다.
- cleanup CronJob의 API image, RBAC·serviceAccount·NetworkPolicy·deadline을 유지한다.
  worker의 processing list 회수·3회 retry 의미를 이전 때문에 변경하지 않는다.
- **성공 검증:** PreSync→Ready rollout→PostSync 순서, 업로드/DONE/200·800px WebP/
  원본 동일 bytes/삭제 smoke 성공; 같은 migration 재실행은 추가 적용 0.
  CI dev 승격 후 ArgoCD 자동 배포와 `X-App-Version`, `X-Served-By`를 확인한다.
  A5의 실제 frontend→DB 차단/API→DB 허용, presigned GET/HEAD,
  외부 S3 PUT/DELETE 거절·서명 변조 실패와 browser 원본·썸네일 동작도 여기서 확인한다.
- **실패 검증·복구:** 잘못된 DB 설정의 migration 실패가 신규 app rollout을 막고
  기존 서비스/PVC를 유지해야 한다. 정상 Git 설정으로 복구 후 Sync한다. 실패 PostSync를
  삭제해서 성공으로 표시하거나 DB 전체를 초기화하지 않는다.
- **커밋 단위:** `gitops(aks): gate dev rollouts with migration and smoke hooks`.

### A9. 실제 데이터 백업·복원 리허설

- [ ] 완료
- **수정:** `aks/docs/data-migration.md`, `aks/docs/experiments/AKS-DATA.md`,
  필요한 경우 기존 도구를 호출하는 작은 backup/restore 스크립트. 백업 payload는 Git에 넣지 않는다.
- **순서:** (9a) 이전 대상으로 선택한 K3S 환경의 실제 rows·객체·bytes·queue 상태 확인 →
  (9b) 일관된 DB dump와 originals/thumbnails 복사 → (9c) AKS dev에 복원 →
  (9d) 비교·smoke → (9e) 목적지 fixture 정리 또는 보존 상태 기록.
- K3S의 빈 OS 복구 증거는 데이터 복원 증거가 아니다. 데이터가 0개라고 가정하지 않는다.
  원본에서 쓰기 중지가 필요한 경우 별도 실행 요청의 대상·시간을 확인한다.
  중지하지 않은 snapshot은 최종 전환용 일관성 검증으로 표시하지 않는다.
- DB의 row ID/status/key와 각 객체 key·크기·checksum을 대조한다. ETag를 모든 객체의
  MD5라고 가정하지 않는다. 외부 보안 위치에 저장한 dump를 새 DB에 실제 restore하여 확인한다.
- 목적지의 API 쓰기·worker·cleanup을 일시 중지하고 관련 Argo 자동 복구/KEDA가 작업을
  재개하지 않도록 통제한다. 목적지 fixture는 먼저 백업·식별하고 복원 범위를 한정한다.
  복원 중 image/schema를 변경하지 않고 동일 버전의 migration 상태를 대조한 뒤 재개한다.
- 최종 이전 방식은 쓰기 정지 후 큐/processing 목록을 비우는 것으로 단순화한다.
  미완료 작업은 기존 retry/cleanup 규칙으로 정합성을 확인한다. **Redis가 비었다는 이유만으로
  PROCESSING rows를 유실 처리하지 않으며**, 메인/processing queue·DB를 함께 확인한다.
  Redis 무조건 flush 또는 live DB/PVC 원시 파일 복사는 수행하지 않는다.
- **성공 검증:** row/status·원본·썸네일 key/checksum 일치, 무작위 기존 사진 조회·다운로드,
  새 upload→DONE→delete 성공, 누락/중복 처리 없음. 원본 K3S 데이터는 보존된다.
- **실패 검증·복구:** 누락 객체·손상 dump·남은 processing 작업이 있으면 전환을 보류한다.
  리허설 목적지에만 검증된 snapshot을 다시 복원하고 원본 데이터에 역방향 덮어쓰기를 하지 않는다.
- **커밋 단위:** `docs(aks): record the data restore rehearsal`.

### A10. 관측성·HPA/KEDA·최소 사양 수용 검증

- [ ] 완료
- **수정:** `aks/infra/monitoring/values*.yaml`, `aks/k8s/monitoring/**`, `aks/dashboards/**`,
  `aks/k8s/base/{api/hpa.yaml,worker/scaledobject.yaml}`, `aks/scripts/check-observability.py`,
  `aks/docs/{observability,cost}.md`.
- **순서:** (10a) AKS에 없는 managed control-plane scrape 비활성 상태 확인 →
  (10b) dashboards/alerts·ServiceMonitor namespace selector 확인 →
  (10c) 정상 기능·200 VU·500장 upload → (10d) 리소스 부족·실측·비용 후보 판정.
- 모니터링은 클러스터에 한 벌만 설치한다. 기존 5개 dashboard/20개 panel과
  `AlbumQueueBacklog`, `AlbumAPIErrorRate`, `AlbumCrashLoop`를 재사용한다.
  직접 접근할 수 없는 scheduler/controller/etcd target을 억지로 공개하지 않는다.
- API dev HPA 1~3/CPU 60%, worker KEDA 0~2/Redis list `thumbnail:jobs`를 유지한다.
  metrics-server·KEDA Redis 접근과 queue metric을 확인한다. addon KEDA와 Helm KEDA를 중복 설치하지 않는다.
- **성공 검증:** 20 panel에 유한 실측 sample, 세 alert loaded, HPA 1→3→1,
  worker 0→2→0과 500장 DONE. API 3·worker 2·frontend 2·관측성·migrate/cleanup이 겹쳐도
  자원 부족 Pending/반복 OOM/Eviction/DiskPressure 없음; 노드별 requests는 실제 allocatable의
  80% 이내다. chart sidecar·DaemonSet·rollout surge까지 포함한다.
- **실패 검증·복구:** panel 무자료·invalid PromQL·KEDA 접근 실패는 실패로 기록한다.
  F4s_v2가 부족하면 실제 증거로 D4as_v5를 비교한다. SKU 교체는 새 System 풀→검증→drain→
  이전 풀 제거 순서와 일시 4노드 비용/quota를 별도로 계획한다. requests/limits를 무조건 줄이지 않는다.
- **커밋 단위:** `observability(aks): verify scaling and minimum cluster capacity`.

### A11. node drain·CSI 재연결·중지/재개

- [ ] 완료
- **수정:** `aks/docs/operations.md`, `aks/docs/experiments/{AKS-NODE,AKS-STOP}.md`,
  `aks/scripts/aks-power.sh`가 필요하다면 start/stop 두 동작과 대상 확인만 구현한다.
- **순서:** (11a) fixture/row/checksum·PDB·PV topology 기준 기록 → (11b) 노드 1개 drain →
  (11c) 다른 노드 재배치·CSI attach·smoke → (11d) uncordon →
  (11e) 쓰기/queue 종료 후 cluster stop → (11f) start·기능·데이터 재검증.
- API 1 replica의 `minAvailable=1`은 drain을 막을 수 있다. API를 2 이상으로 준비하고
  frontend 2개와 다른 노드 배치·requests를 확인한다. 실험 중 HPA/Argo가 replica를 되돌리지
  않도록 제한된 선언 변경 또는 해당 앱 일시 pause를 기록하고 끝나면 원상복구한다.
  drain을 통과시키려고 PDB를 무조건 삭제하거나 force eviction하지 않는다.
- LRS disk는 PV nodeAffinity에 맞는 노드에만 붙는다. single-replica DB/Redis/MinIO 중단을
  허용하고 detach/attach 시간, Multi-Attach/timeout 여부, 최종 checksum을 측정한다.
  전체 2노드 복구 완료와 API replica 선언 복원을 확인한 뒤 stop 실험을 수행한다.
- stop/start는 명시한 subscription/RG/AKS 이름에 `az aks stop` / `az aks start`를 사용한다.
  관리 VMSS를 직접 deallocate하지 않는다. stop 전에 쓰기 종료·queue 상태·복구 자료를 확인하고,
  start 때 kubeconfig/endpoint·Node·PVC·Argo·Secret·metrics·smoke를 다시 확인한다.
  전체 중지 때 마지막 노드의 PDB가 남지 않도록 앱의 자동 Sync를 일시 정지하고,
  쓰기·queue 종료 후 API/frontend/worker를 0으로 내리는 학습용 종료 절차를 먼저 검증한다.
  KEDA/HPA와 충돌하지 않는지 확인하고 원래 선언·정책을 기록한다. start 후 Git 선언으로
  replica와 자동 Sync를 복원해야 재개 완료다. A12 이후에는 prod도 같은 절차에 포함한다.
- **성공 검증:** stop `powerState.code=Stopped`, start `Running` + `provisioningState=Succeeded`,
  2 Node Ready·기존 데이터 유지. CLI exit 0만으로 성공을 판단하지 않는다.
- **실패 검증·복구:** PDB block·attach 지연·capacity 실패는 해당 상태와 경과 시간을 기록한다.
  drain 실패면 uncordon하고 마지막 선언으로 되돌린다. stop이 실패했다면 컴퓨트 비용 절감을
  완료로 보고하지 않는다. NAP/standalone Pod/장기 중지·endpoint 변경 제한을 공식 문서와 대조한다.
- **커밋 단위:** `ops(aks): document drain and stop-start recovery`.

### A12. prod namespace와 동일 digest Release 실습

- [ ] 완료
- **수정:** `.github/workflows/aks-release.yaml`, `aks/scripts/{prepare-release,set-image-tag}.py`,
  해당 tests, `aks/argocd/{root-prod.yaml,bootstrap/prod/**,prerequisites/prod/**}`,
  `aks/k8s/{overlays,gitops,secrets}/prod/**`, `aks/docs/release.md`.
- **순서:** (12a) prod Secret·3 데이터 PVC·platform 준비 → (12b) prod app 수동 Sync 선언 →
  (12c) release dry-run·정규식/digest 테스트 → (12d) `aks-v...` release PR →
  (12e) 승인된 merge·수동 Sync·smoke와 digest 대조.
- prod는 `album-prod`, host `album.aks.prod.localhost`다. Redis 주소·Secret scope·Host를 dev와
  구분한다. 같은 cluster 공용 도구와 monitoring은 한 번만 관리한다. prod data disk는 초기
  용량 비용 약 +$1.80/월, I/O 별도이며 실제 생성 결과와 CPU/메모리 추가량을 기록한다.
- workflow trigger는 `aks-v*`, parser는 정확한 `aks-vMAJOR.MINOR.PATCH`다.
  release branch `codex/aks-release-<release>`와 concurrency/cache를 K3S와 분리한다.
  네 dev image의 실제 manifest digest를 읽어 release alias를 만들고 **rebuild하지 않는다**.
  기존 alias가 다른 digest라면 덮어쓰지 않는다. PR은 AKS prod overlay만 변경한다.
- **성공 검증:** dry-run이 파일을 수정하지 않음, Git tag prefix 교차 거절,
  네 dev/release manifest digest 일치, merge 전 prod 변경 없음, merge 후에도 app은
  승인된 수동 Sync에서만 승격. root-prod가 operation을 재실행하지 않는다.
  prod 추가 상태에서도 노드별 allocatable 대비 requests·OOM/pressure와 두 환경 smoke를
  재확인한다. 부족하면 쓰지 않는 prod를 종료하거나 증설 비용을 보고하며 requests를 임의로 줄이지 않는다.
- **실패 검증·복구:** 미게시 dev tag·다른 digest·잘못된 release tag는 PR/승격 실패.
  승인되지 않은 merge/Sync는 실행하지 않는다. 실패 배포는 마지막 AKS prod Git 선언으로 복구한다.
- **커밋 단위:** `release(aks): promote verified manifests into the prod namespace`.

### A13. 기존 15개 실험을 AKS에서 새로 수행

- [ ] 완료
- **수정:** `aks/docs/experiments/{README,TEMPLATE,E-01,...,E-15}.md`,
  관련 `aks/loadtest/` 명령·context/URL 설정.
- **순서:** dev의 안전한 단일 실험부터 수행하고 각 실험의 변경·fixture를 복구한 뒤 다음으로 간다.
  E-13/E-14는 A12 이후 prod 실습에서 수행한다. 이전 K3S의 결과·시간·스크린샷은 재사용하지 않는다.
- 각 결과에 실행 시각 KST, context/namespace, Git SHA·image digest, 명령·실측,
  통과/실패·복구 상태를 기록한다. 아래 매핑과 A11/A9 추가 실험을 함께 사용한다.
- **성공 검증:** 15개 각각의 AKS 결과와 복구 증거가 존재하고 README의 상태와 일치한다.
  의도한 E-06 OOM을 기본 최소 사양의 반복 OOM과 구분한다. K3S CPU credit 조건을 F4s_v2에
  복사하지 않고 실제 AKS node 사용률/pressure를 기록한다.
- **실패 검증·복구:** 실패/미실행을 통과로 바꾸지 않는다. live 조작은 명시된 실험으로 한정한다.
  Argo dev selfHeal이나 HPA와 충돌하는 직접 patch는 일시 pause 또는 실험 선언을 기록한다.
  종료 후 원래 Git·replica·limit·queue와 GitOps 자동 정책을 복원한다.
- **커밋 단위:** 실험 묶음별 `docs(aks): record E-XX acceptance and recovery`.

### A14. 쓰기 정지·접속 전환·롤백 리허설

- [ ] 완료
- **수정:** `aks/docs/{data-migration,cutover}.md`, `aks/docs/experiments/AKS-CUTOVER.md`.
- **순서:** (14a) 두 환경 상태·source backup·복구 기준과 중단 시간을 기록 →
  (14b) 원본 쓰기 차단·queue/processing 작업 종료 → (14c) 최종 일관된 DB/객체 복원 →
  (14d) 테스트 접속을 AKS로 전환 → (14e) upload/read/delete →
  (14f) AKS 쓰기 중지·원본 접속 복구 및 이후 데이터 처리 검증.
- 두 클러스터에 동시에 쓰기를 허용하지 않는다. 기본 localhost 환경에서는 URL/터널 선택으로
  접속 전환을 실습하며 DNS·public IP를 새로 만들지 않는다.
- 롤백 기준은 migration 실패, checksum/row 불일치, 지속 readiness 실패 또는 smoke 실패다.
  무손실 롤백은 **목적지 신규 쓰기 전**에 검증한다. 신규 쓰기를 허용했다면 K3S로 즉시 되돌려
  데이터가 보존된다고 주장하지 않는다. 쓰기 종료 후 AKS DB/객체를 백업·대조하고,
  테스트 fixture라면 양쪽 정리, 실제 데이터라면 검증된 역방향 복원 방법을 먼저 확정한다.
- **성공 검증:** 쓰기 정지 경계, 최종 row/객체 비교, AKS 기능, 원본 복구가 관찰되고
  전환 후 신규/삭제 데이터가 어떻게 처리됐는지 기록된다.
- **실패 검증·복구:** 최종 snapshot 불일치면 접속을 전환하지 않는다. 이미 전환했다면
  쓰기를 멈추고 기준 snapshot과 변경분 처리 계획을 검증한다. 원본 disk를 삭제하지 않는다.
  실제 K3S 운영 데이터·트래픽의 이전/정리는 리허설 결과 검토 후 그 작업에 대한 별도 요청으로 수행한다.
- **커밋 단위:** `docs(aks): prove cutover and rollback boundaries`.

### A15. 실제 비용·완료 증거·장기 미사용 정리

- [ ] 완료
- **수정:** `aks/docs/{completion,cost,operations,cleanup}.md`, `aks/README.md`.
- **순서:** (15a) 기능·CI/CD·15실험·복원·stop/start 결과 연결 →
  (15b) 과금 반영 후 AKS RG와 node RG meter 조회 → (15c) 견적과 실제 차이 설명 →
  (15d) 현재 running/stopped 상태·미사용 disk·임시 pool·fixture 정리 상태 기록.
- 생성 후 24~48시간 지연된 실제 비용으로 VM/OS disk/PVC/LB/IP/I/O/egress/backup을 구분한다.
  시작·종료/실험·surge 시간과 기존 build VM 비용도 기록한다. Free tier와 worker=0을
  전체 무료로 표현하지 않는다. 예산·알림 수신자는 결과를 보고 정하며 임의 연락처를 만들지 않는다.
- 처음에는 수동 start/stop만 운영한다. 장기 미사용 삭제는 backup restore 증거와
  AKS 전용 resource inventory를 확인하고 별도 삭제 요청이 있을 때 수행한다.
  Retain disk는 cluster/PVC 삭제 후에도 과금될 수 있어 소유와 참조를 개별 확인한다.
- **성공 검증:** A0~A14 상태·증거 링크, 누락/미실행, 실제 최소 SKU 판정과 비용,
  실행 가능한 start/stop/복구·정리 지침이 일치한다. `git diff --check`, 문서 링크 검사,
  `graphify update .` 완료·exit status를 기록한다. Graphify 품질 검사는 완료 gate에 넣지 않는다.
- **실패 검증·복구:** 과금 미반영이면 비용 확인 대기라고 적고 견적을 실제 청구로 표시하지 않는다.
  소유 불명 disk·공유 리소스는 삭제하지 않는다. 완료 상태는 실제 검증된 범위로 제한한다.
- **커밋 단위:** `docs(aks): close acceptance with costs and recovery evidence`.

## 6. E-01~E-15 적용표

| 실험 | AKS에서 관찰할 동작 | 카드·복구 기준 |
|---|---|---|
| E-01 셀프 힐링 | API 2개 이상에서 1 Pod 교체, 응답 유지 | A13; HPA/replica 원상복구 |
| E-02 HPA | 200 VU, requests 대비 CPU 60%, 1→3→1 | A10/A13; 부하 종료·축소 확인 |
| E-03 KEDA | 500장, queue 증가·worker 0→2→0 | A10/A13; fixture/processing queue 정리 |
| E-04 롤링 | Ready 새 version과 이전 version, 오류 수 | A13; 안정된 Git 이미지 선언 복구 |
| E-05 rollout 중단 | 잘못된 readiness가 기존 Ready 서비스 유지 | A13; pause/실험 선언 복구, live undo와 Git을 구분 |
| E-06 OOM | 의도한 64Mi limit·OOMKilled·3회 후 FAILED | A13; 정상 limit·fixture 복구 |
| E-07 DB 장애 | readiness 실패/liveness 유지·DB 회복 | A13; StatefulSet와 app Healthy 복구 |
| E-08 영속성 | data Pod 교체 뒤 row·원본·썸네일 동일 | A9/A13; CSI disk/PVC 보존 |
| E-09 NetworkPolicy | frontend→DB 거절, API→DB 허용·대조군 | A5/A13; 실험용 허용 정책 제거 |
| E-10 ConfigMap | 설정 hash·rollout·새 썸네일 크기 | A13; 기존 설정·fixture 복구 |
| E-11 GitOps CI | AKS API-only build·scan·dev 자동 Sync | A2/A8/A13; K3S 승격 미발생 확인 |
| E-12 selfHeal | dev 드리프트가 Git 선언으로 복구 | A7/A13; HPA 소유 replica와 구분 |
| E-13 승격 | 네 dev/release digest 동일, prod 수동 Sync | A12/A13; 승인 전 prod 미변경 |
| E-14 롤백 | live undo는 OutOfSync, 수동 Sync가 Git 적용 | A12/A13; Git revert로 마지막 선언 복구 |
| E-15 배포 gate | 실패 PreSync가 신규 rollout 차단 | A8/A13; 정상 migration 설정·Sync 복구 |

추가 AKS 실험은 **AKS-DATA**(DB·객체 복원), **AKS-NODE**(drain·RWO 재연결),
**AKS-STOP**(중지/재개), **AKS-CUTOVER**(쓰기 경계·롤백) 네 개다.
PDB·단일 replica 데이터 서비스·LRS 제약으로 무중단 전체 노드 장애를 약속하지 않는다.

## 7. 가벼운 LLM의 작업 입력과 종료 보고

한 번에 `A번호 + 이 카드 + 직접 참조 파일 + 직전 증거`를 전달한다.
예: “A5만 구현한다. A2/A3 완료 SHA와 A4의 CSI 상태를 읽고, AKS Traefik·정책·접근 파일을
수정한다. K3S 변경 없이 gateway happy path와 S3 쓰기 차단·DB 차단을 실제 검증해 보고한다.”

1. 카드 시작마다 선행 완료 여부·현재 HEAD/dirty 상태·context를 확인한다.
2. 코드 구조는 CodeGraph부터 조회하고 YAML/Markdown은 해당 파일만 읽는다.
3. UI·비즈니스 로직 변경, shared 모듈 추출, 자동화 플랫폼 추가는 카드 수행에 섞지 않는다.
4. 기존 pytest/ruff/actionlint와 실제 렌더/앱 표면을 사용한다. 순수 문구 검증용 테스트는 추가하지 않는다.
5. 성공 시 `변경 파일 / 실제 실행 검사·판정 / 미실행 이유 / 복구 상태 / 커밋 SHA / 다음 카드`를 보고한다.
6. secret·key·credential·kubeconfig는 로그·Graphify 입력·commit에서 제외하며 제외 건수만 기록한다.
7. 실패가 있으면 해당 카드 완료를 주장하지 않는다. 무관한 코드 정리나 과거 테스트 수 재보고로 대체하지 않는다.

## 8. 이번 문서 작성의 검증 범위와 공식 근거

참고 세션 두 개의 최종 합의, 현재 Markdown/YAML, CodeGraph의 앱·CI helper·smoke 소스,
기존 Lore 결정을 확인해 작성했다. Azure Open Tenant 및 Azure Kubernetes 스킬을 읽었고,
공식 AKS 문서를 Context7으로 재확인했다. 최소 가격은 같은 날 앞선 세션에서 조회한
비용 문서의 근거를 사용하며 이번에는 가격 API를 새로 조회하지 않았다.

- [AKS 시스템 풀 조건](https://learn.microsoft.com/en-us/azure/aks/use-system-pools)
- [Free/Standard 관리 tier](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers)
- [Azure CNI Overlay](https://learn.microsoft.com/en-us/azure/aks/azure-cni-overlay)
- [API server authorized ranges](https://learn.microsoft.com/en-us/azure/aks/api-server-authorized-ip-ranges)
- [Azure Disk CSI·StorageClass](https://learn.microsoft.com/en-us/azure/aks/create-volume-azure-disk)
- [LRS·zone와 디스크](https://learn.microsoft.com/en-us/azure/aks/reliability-availability-zones-configure)
- [AKS 중지/재개 조건](https://learn.microsoft.com/en-us/azure/aks/start-stop-cluster)
- [AKS 이전 가이드](https://learn.microsoft.com/en-us/azure/aks/aks-migration)

현재 A0~A15는 모두 미실행이다. 실제 Azure 인증·계약 가격·권한·SKU·quota·지원 버전,
클러스터 수용량, 데이터 복원과 제품 테스트 결과를 검증 완료로 표시하지 않는다.
