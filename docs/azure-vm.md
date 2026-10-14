# Azure VM 운영 절차

dev/prod K3S 노드는 KT Open Tenant의 Azure VM이다. 결정 배경은 [plan.md](plan.md) 1.3을 본다.

## 구성

| 리소스 | 이름 | 비고 |
|---|---|---|
| 리소스 그룹 | `rg-seonung-kube-study` | koreacentral |
| VNet | `vnet-kube-study` (10.20.0.0/16) | dev `snet-dev` 10.20.1.0/24, prod `snet-prod` 10.20.2.0/24 |
| VM | `vm-kube-dev` / `vm-kube-prod` | Standard_B4as_v2, Ubuntu 24.04, Standard SSD 64 GiB |
| NSG | `nsg-kube-<env>` | 작업 PC 공인 IP → TCP 22만 허용 |
| 공인 IP | `pip-kube-<env>` | Static, SSH 용도로만 사용 |
| auto-shutdown | VM별 | 매일 KST 18:00 (UTC 09:00) |

공인 IP 주소, SSH 키는 저장소에 기록하지 않는다. 작업 PC의 `~/.ssh/config`에 별칭(`kube-dev`, `kube-prod`)으로만 둔다.

## 생성

```bash
# 사전 조건: az login 완료, ~/.ssh/kube-study(.pub) 존재
infra/azure/create-vm.sh dev     # prod는 M9 직전에 실행
```

스크립트는 여러 번 실행해도 안전하다(이미 있는 리소스는 갱신만 한다). 실행 시점의 작업 PC 공인 IP로 NSG 규칙을 만든다.

작업 PC `~/.ssh/config` 예시:

```
Host kube-dev
  HostName <스크립트 출력의 공인 IP>
  User azureuser
  IdentityFile ~/.ssh/kube-study
  IdentitiesOnly yes
```

## 일상 운영

```bash
RG=rg-seonung-kube-study
az vm start      -g $RG -n vm-kube-dev     # 작업 시작
az vm deallocate -g $RG -n vm-kube-dev     # 작업 종료 (과금 중지. stop만 하면 과금 계속됨)
az vm show -d    -g $RG -n vm-kube-dev --query powerState -o tsv
```

auto-shutdown은 deallocate로 동작한다. 공인 IP와 디스크는 꺼져 있어도 소액 과금된다.

## 작업 PC 공인 IP가 바뀌었을 때

SSH가 타임아웃되면 NSG 규칙의 허용 IP를 갱신한다.

```bash
az network nsg rule update -g rg-seonung-kube-study --nsg-name nsg-kube-dev \
  -n allow-ssh-workpc --source-address-prefixes "$(curl -fsS https://api.ipify.org)/32"
```

## 삭제

```bash
az group delete -n rg-seonung-kube-study   # 모든 리소스 삭제, 되돌릴 수 없음
```
