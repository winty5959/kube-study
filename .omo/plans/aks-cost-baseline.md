# AKS 최소 사양과 비용 기준

조회일: **2026-10-16 KST**. [전체 계획](k3s-onprem-aks-migration.md) · [구현 카드](aks-implementation.md).

## 1. 먼저 결론

현재 소스의 요청 자원을 기준으로 산정한 최소 **계획 후보**는 AKS Standard 구성 방식의
**Free 관리 tier, 시스템 풀 1개, Standard_F4s_v2 2대(각 4 vCPU·8 GiB)**였다.
클러스터 합계는 8 vCPU·16 GiB다. 앱·PostgreSQL·Redis·MinIO와 기존 ArgoCD,
KEDA, SealedSecrets, Prometheus/Grafana를 함께 실행하는 학습 환경을 가정한다.
2026-10-16 확인에서 AX사업부문-인프라아키텍처팀 구독의 Korea Central은 F4s_v2를
`NotAvailableForSubscription`으로 표시했다. 이를 배포 가능하다고 간주하지 않는다.
`Standard_D4as_v5`는 사용 가능으로 조회됐지만 선택하지 않았다.

| 사용 패턴 | 계산 기준 | AKS 월 기본 예상액(USD) |
|---|---|---:|
| 상시 실행 | 730시간, 노드 2대 | **$325.63, 약 $326** |
| 예시: 평일 하루 4시간 | 22일 × 4시간 = 88시간 | **$79.11, 약 $80** |
| 예시: 평일 하루 8시간 | 176시간 | **$112.90, 약 $113** |
| 한 달 내내 중지, 자원 유지 | 컴퓨트 0, 디스크·IP·LB 잔존 가정 | **최대 약 $45.31의 고정항목을 보수적으로 반영** |

위 사용 패턴 금액은 F4s_v2 기준의 비교 추정이며 현재 선택 구독에서 F4s_v2를 만들 수 있다는 뜻이 아니다. D4as_v5를 선택하면 현재 공개 가격으로 2대 상시 실행의 총 기준은 약 $354.83/월이고, 실제 가격과 디스크 구성은 배포 직전 다시 확인해야 한다.

이 표는 예산 약속이나 청구 상한이 아니다. 디스크 I/O·네트워크 전송·백업·실험 중 추가
노드·업그레이드 surge 비용은 별도다. 88/176시간은 사용자의 사용시간 결정이 아닌 비교 예시다.
실제 과금 시간에는 준비·기동·종료 시간도 포함된다. 기존 K3S VM 비용은 이 표에 포함하지 않는다.
환율·부가세·기업 계약 할인·크레딧을 임의 적용하지 않고 USD 공개 종량제로 비교한다.

## 2. 왜 K3S와 같은 B 계열 VM 1대가 아닌가

현재 Microsoft 시스템 풀 문서의 제한 목록은 최소 2노드, 노드당 4 vCPU·4 GB 이상,
B 계열 미지원, 최소 30 pods 지원을 명시한다. 본문 일부는 production을 따로 언급하지만
제한 목록에는 일반 조건으로 적혀 있으므로 이번 비용 계획은 **2노드 기준**을 채택한다.
오래된 1노드/2 vCPU 예제를 최소 비용 보장 근거로 사용하지 않는다. 생성 시점에 공식
문서와 실제 구독 제한을 다시 확인하고, 더 작은 구성이 공식 지원되는 것이 확인될 때만
명세와 비용표를 함께 수정한다. [시스템 풀 조건](https://learn.microsoft.com/en-us/azure/aks/use-system-pools)

Free는 **관리 비용**이 무료라는 의미다. 노드 VM·디스크·네트워크는 별도 청구되며
가동률 SLA는 없다. `AKS Standard 구성 방식(Base SKU)`과 유료 `Standard 관리 tier`를
구분한다. Automatic의 기본 유료 tier·자동 노드 증설은 이 학습 목적에 필요하지 않다.
[AKS 관리 tier](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers)

F4s_v2는 4 vCPU·8 GiB인 x86_64 SKU다. 공개 가격 비교 후보 중 컴퓨트가 가장 저렴하지만
선택 구독의 Korea Central에서는 사용할 수 없다. 모든 Azure SKU 중 절대 최저가라고 주장하지 않는다.
CPU 4개 조건을 맞추려고 앱 요청량보다 큰 총 CPU를 확보하게 된다.
[Fsv2 사양](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/compute-optimized/fsv2-series)

## 3. 현재 저장소에서 확인한 requests

근거는 `k3s/k8s/base/**`, `k3s/infra/{argocd,keda,sealed-secrets,monitoring}/values.yaml`이다.
requests는 스케줄링 예약량이며
실측 사용량·안전한 최대 사용량이 아니다. 아래는 컨테이너 requests 합계로, chart가
추가하는 sidecar/initContainer 및 AKS 시스템 구성 요소는 별도로 계산해야 한다.

| 구성 | replicas 가정 | CPU requests | 메모리 requests |
|---|---:|---:|---:|
| API | 1 | 100m | 128 MiB |
| frontend | 기존 값 2 유지 | 50m | 32 MiB |
| PostgreSQL | 1 | 100m | 128 MiB |
| Redis | 1 | 50m | 64 MiB |
| MinIO | 1 | 100m | 128 MiB |
| worker | 유휴 0, 최대 2 | 0~200m | 0~256 MiB |
| 앱 소계 | API 1, worker 0 | **400m** | **480 MiB** |
| ArgoCD | controller/server/repoServer/redis 각 1 | 275m | 480 MiB |
| KEDA | operator/metrics/webhook | 125m | 160 MiB |
| SealedSecrets | 1 | 25m | 32 MiB |
| 모니터링 | 기존 5종 + node-exporter 2개 | 490m | 960 MiB |
| 기존 구성 소계 | worker 0 | **1,315m** | **2,112 MiB** |
| Traefik 신규 예약 | 학습용 1개 제안값 | 100m | 128 MiB |
| migrate+cleanup Job | 둘 다 겹치는 경우 | 100m | 128 MiB |
| HPA/API 3 + worker 2 시 증가 | 기본 대비 | 400m | 512 MiB |
| 계획상 앱/도구 최대 requests 소계 | 위 조건 합계 | **1,915m** | **2,880 MiB** |

여기에 CoreDNS·Cilium·CSI·metrics-server·kube-proxy 등 실제 AKS 시스템 Pod, OS/kubelet
예약량, chart sidecar, image pull/rollout surge가 들어간다. 따라서 2.8 GiB requests만 보고
클러스터 RAM 4 GiB면 된다고 결론내리면 안 된다. 모든 limits 합계와 OOM 시나리오는 별도다.

실제 최소 사양 수용 기준(A6/A10):

1. 고정 chart를 렌더해서 sidecar·initContainer·DaemonSet까지 requests를 합산한다.
2. 실제 `Node.status.allocatable`에서 노드별 CPU/메모리 requests가 80%를 넘지 않도록 배치한다.
3. API 3/worker 2, 두 frontend, migrate/cleanup, 관측성 동시 실행에서 requests 부족 Pending이 없어야 한다.
4. 정상 업로드와 기존 부하 실험 중 반복 OOM·Eviction·DiskPressure가 없어야 한다. 의도한 E-06 OOM은 별도다.
5. 한 노드 drain 때 데이터 Pod 중단은 허용하지만 다른 노드로 재배치·CSI 재연결 후 회복되어야 한다.
6. 8 GiB 노드에서 메모리 문제가 재현되면 불필요한 부가기능부터 확인한다. 실제 부족이면 D4as_v5로
   변경하고 비용을 다시 보고한다. 무조건 requests/limits를 줄여 검사만 통과시키지 않는다.

## 4. SKU 비교

Korea Central, Linux, 종량제, 일반 VM 서비스, `isPrimaryMeterRegion=true`를 선택했다.
Windows·Spot·Low Priority·HDInsight·Cloud Services의 동명 meter는 제외했다.

| 후보 | 노드 1대 사양 | 시간당 1대 | 2대 × 730h 컴퓨트 | 판단 |
|---|---|---:|---:|---|
| Standard_F4s_v2 | 4 vCPU / 8 GiB | $0.192 | $280.32 | Korea Central에서 선택 구독에 unavailable; 견적 비교용만 |
| Standard_D4as_v5 | 4 vCPU / 16 GiB | $0.212 | $309.52 | 구독에서 사용 가능; 변경 결정 전까지 미선택; 상시 컴퓨트 +$29.20/월 |
| Standard_D4ads_v5 | 4 vCPU / 16 GiB, 로컬 임시 디스크 | $0.254 | $370.84 | ephemeral OS가 가능하면 간헐 사용 시 비교 가치 |

F4s_v2는 Managed OS 64 GiB로 계획하고 계산에서는 Premium SSD P6를 반영한다.
데이터 PVC의 Standard SSD 설정이 OS 디스크에도 적용된다고 가정하지 않는다.
생성된 OS disk SKU/크기를 반드시 조회하며 기본 128 GiB가 생기면 이 견적과 다르다.
64 GiB는 부하 시 이미지/로그 여유 검증 대상이며 임의로 32 GiB까지 줄이지 않는다.

Ephemeral OS는 애플리케이션 PVC와 다르다. D4ads_v5의 실제 ephemeral 지원·OS image·
디스크 크기를 확인한 경우에만 OS 디스크 2개 비용을 뺄 수 있다.
같은 네트워크/PVC 조건에서 D4ads_v5 ephemeral 대안은 730h 약 $395.74,
88h 약 $69.60이다. 사용시간이 미정인 지금은 더 큰 VM으로 기본안을 바꾸지 않지만,
월 약 165시간 미만 사용한다면 이 대안이 F4s_v2+Managed OS보다 저렴할 수 있다.
계산: OS 절감 $20.414 ÷ 시간당 컴퓨트 증가 $0.124 ≈ 164.63시간.
[AKS OS 디스크 선택](https://learn.microsoft.com/en-us/azure/aks/concepts-storage)

## 5. 월 고정항목 산정

기본 상태는 AKS dev namespace 하나다. 기존 관측성도 유지하여 Prometheus/Grafana/Alertmanager
PVC를 포함했다. managed 서비스·ACR·Key Vault·NAT Gateway·Bastion은 추가하지 않는다.

| 항목 | 수량·과금 단위 | 단가 | 월 계산 |
|---|---|---:|---:|
| AKS Free 관리 tier | 클러스터 1개 | $0 | $0 |
| OS disk | P6 LRS 64 GiB × 2 | $10.207/월 | $20.414 |
| PostgreSQL 2 GiB | E1 LRS 4 GiB 과금 × 1 | $0.30/월 | $0.30 |
| Redis 1 GiB | E1 LRS 4 GiB 과금 × 1 | $0.30/월 | $0.30 |
| MinIO 10 GiB | E3 LRS 16 GiB 과금 × 1 | $1.20/월 | $1.20 |
| Prometheus 5 GiB | E2 LRS 8 GiB 과금 × 1 | $0.60/월 | $0.60 |
| Grafana 1 GiB | E1 LRS 4 GiB 과금 × 1 | $0.30/월 | $0.30 |
| Alertmanager 1 GiB | E1 LRS 4 GiB 과금 × 1 | $0.30/월 | $0.30 |
| Standard LB 基本 rule 묶음 | 1개, outbound 포함, 월 730h 잔존 가정 | $0.025/h | $18.25 |
| Standard IPv4 public IP | outbound 1개 × 730h | $0.005/h | $3.65 |
| **고정항목 합계** | 디스크 $23.414 + 네트워크 $21.90 | | **$45.314** |

PVC 요청 총량 20 GiB와 Azure 디스크 과금 총량 40 GiB가 다르다. 작은 PVC도 개별 디스크의
과금 tier로 올림한다. 공유 디스크를 쓰지 않으므로 `Disk Mount` meter는 합산하지 않는다.
요청량이 작아도 128 GiB 디스크가 생성되는지 등 실제 provisioning 결과를 A4에서 확인한다.
[디스크 과금 방식](https://azure.microsoft.com/en-us/pricing/details/managed-disks/)

```text
기본안 월 비용 = 2 × 0.192 × 실제 가동시간 H
               + 2 × 10.207
               + (4 × 0.30 + 0.60 + 1.20)
               + 0.025 × LB 유지시간
               + 0.005 × IP 유지시간
               + I/O + 전송 + 백업 + 임시 증설 비용
표에서는 LB/IP 유지시간을 보수적으로 730시간 사용한다.
```

기본 접근은 Traefik ClusterIP를 localhost port-forward로 연결한다. 공개 앱용
LoadBalancer Service를 만들지 않아 추가 ingress IP를 피한다. 그래도 GHCR pull·Git/Helm
조회용 outbound Standard LB/IP는 남는다. 공개 서비스가 필요하면 ingress IP 수·LB rule
수를 다시 산정하고 TLS·접근 제한까지 별도 작업에 포함한다.

추가 과금 처리:

- Standard SSD I/O: 조회한 primary `Disk Transactions LRS Disk Operations`는 $0.0027/10K.
  예를 들어 과금 대상 1천만 operations는 $2.70이며 실제 meter와 시간별 상한은 사용량으로 확인한다.
- Standard LB 처리량 meter: $0.005/GB. 무료 구간 등 실제 적용 조건은 청구 내역으로 확인하며
  상시 무료라고 가정하지 않는다. 인터넷 egress·리전 간 트래픽은 별도다.
- 실험용 prod namespace를 켜면 PostgreSQL/Redis/MinIO 데이터 disk 세 개가 추가된다.
  동일 초기 크기라면 용량 비용 +$1.80/월, I/O 별도. 노드 추가는 자원 검증 후에만 한다.
- 백업은 기존 보안 저장 위치를 우선 사용한다. Azure snapshot/backup vault/storage account를
  추가하면 보존량과 기간을 비용표에 더한다. `Retain` disk는 PVC 삭제 후에도 과금된다.
- 노드 업그레이드 `maxSurge=1`이면 잠시 1대가 더 필요하다. SKU-family/regional quota에
  최소 12 vCPU 여유를 확인하고 임시 VM/OS disk 비용을 기록한다.
- 기존 K3S VM을 build runner로 켜면 그 VM 비용도 별도 기록한다. hosted CI로 충분하면
  추가 상시 개발 VM을 만들지 않는다.

## 6. 비용을 실제로 줄이는 운영 순서

1. 클러스터 1개·시스템 풀 1개에 앱도 함께 배치한다. 앱 전용 풀, Spot 풀, NAP,
   cluster-autoscaler, 다중 zone, 다중 클러스터는 처음에 넣지 않는다.
2. dev만 상시 선언한다. prod namespace는 A12 승격 실습을 시작할 때 추가한다.
3. 현재 requests에서 시작하고 실제 데이터로 조정한다. worker 0~2, API 1~3을 유지한다.
   worker가 0이어도 AKS 노드 비용은 계속 발생한다.
4. 작업 종료 후 앱 쓰기/큐 처리 종료를 확인하고 `az aks stop`을 실행한 뒤
   `powerState.code=Stopped`를 확인한다. AKS 관리 VMSS를 직접 deallocate하지 않는다.
5. 다음 사용 시 start 후 Node/PVC/Argo/앱 smoke를 검사한다. PDB/drain과 재시작 대기를
   A11에서 검증한다. 중지 성공과 시작 성공은 CLI exit code만으로 판정하지 않는다.
6. 처음에는 수동 start/stop 두 명령으로 운영한다. 별도 scheduler·자동화 계정·GitHub OIDC는
   사용자가 자동 종료를 요청하거나 잊음이 반복될 때만 검토한다. 현재 자동화는 만들지 않는다.
7. 장기 미사용 시 backup 확인 후 AKS 삭제와 retained disk 정리를 별도 계획한다.
   공유 K3S RG는 삭제하지 않는다. 중지와 삭제는 다른 작업이다.

stop은 컴퓨트 절감 기능이며, 디스크·IP 등의 잔존 비용을 0으로 만들지 않는다.
현재 문서는 NAP 사용 cluster의 stop 제한, PDB에 따른 지연, 재개 시 capacity 문제와
API endpoint 변경 가능성도 안내한다. [AKS 중지/재개](https://learn.microsoft.com/en-us/azure/aks/start-stop-cluster)

생성 후 24~48시간의 과금 반영을 기다린 다음 AKS RG와 node RG를 함께 보아 meter별
실제 비용과 견적을 대조한다. 예산 알림은 자동 지출 차단 기능이 아니다. 예산값·수신자는
실제 최소 견적을 본 뒤 정하며 이번 계획에서 연락처나 임의 상한을 만들지 않는다.

## 7. 출처와 재계산 방법

가격은 공식 [Azure Retail Prices API](https://prices.azure.com/api/retail/prices?api-version=2023-01-01-preview)에서 직접 조회했다.
API version `2023-01-01-preview`, USD, Consumption, primary meter를 사용했다.
가격 문서의 조회 날짜는 2026-10-16이고 가격 자체의 effective date는 meter마다 다르다.
지역 VM/디스크는 `koreacentral`, 공통 네트워크 가격은 `Global` primary meter다.

재조회 filter(문자열을 URL encode해서 `$filter`에 전달):

```text
armRegionName eq 'koreacentral' and armSkuName eq 'Standard_F4s_v2'
serviceName eq 'Virtual Machines' and armRegionName eq 'koreacentral'
  and priceType eq 'Consumption' and armSkuName eq 'Standard_D4as_v5'
armRegionName eq 'koreacentral' and skuName eq 'P6 LRS'
armRegionName eq 'koreacentral' and productName eq 'Standard SSD Managed Disks'
serviceName eq 'Load Balancer' and isPrimaryMeterRegion eq true
productName eq 'IP Addresses' and skuName eq 'Standard' and isPrimaryMeterRegion eq true
```

정확히 같은 meterName/productName/unitOfMeasure를 고른다. `P6 LRS Disk`는
Premium **Managed Disks** 항목을 사용하며 Premium Page Blob과 중복 합산하지 않는다.
empty result는 무료가 아니다. LB의 지역 조회가 비어 있으면 Global primary meter를 확인한다.
`NextPageLink`가 있으면 다음 페이지까지 읽고, 429는 제한된 재시도 후 미조회로 표시한다.

최종 배포 견적은 공개 소매가격이 아니라 선택한 AX 구독의 실제 계약 가격·조직 정책·
측정된 디스크 SKU를 반영해 갱신한다. Azure Retail Prices API에서 D4as_v5를 다시
조회한 값은 $0.212/노드·시간(USD)이다. 이를 선택한다면 2대 상시 컴퓨트는 $309.52/월,
문서의 기존 고정항목 추정과 합계 약 $354.83/월이며 88시간 예시는 약 $82.63이다.
이 수치는 공개 소매가격 기반 비교값으로 기업 계약·세금·I/O·전송을 포함하지 않는다.
CLI로 선택 구독에 로그인해 quota/SKU/RG를 조회했지만 AKS 리소스는 생성하지 않았다.
