# 서버 접속 가이드

dev/prod 서버(Azure VM)를 켜고, 접속하고, 앱·클러스터에 붙고, 끄는 방법을 한곳에 모은 문서다.
VM을 처음 만드는 절차는 [azure-vm.md](azure-vm.md), 접근 방식을 정한 이유는 [plan.md](plan.md) 1.4에 있다.

> 이 문서와 저장소에는 공인 IP, SSH 키, kubeconfig 내용을 적지 않는다. 모두 작업 PC 안(`~/.ssh`, `~/.kube`)에만 있다.

---

## 1. 전체 그림

```
 작업 PC (맥북)                                    Azure VM (vm-kube-dev)
 ───────────────                                   ────────────────────────────────
                       인터넷 (TCP 22만 허용)
  터미널 ── ssh kube-dev ───────────────────────▶  sshd ── 셸 (docker, kubectl, helm …)
                                                    │
  브라우저 ─ localhost:8080 ┐                       │  Traefik :80  ─▶ album / (Grafana, ArgoCD)
  kubectl ─ 127.0.0.1:16443 ┴─ SSH 터널(암호화) ──▶  │  K8s API :6443
                                                    └─ K3S 클러스터
```

- VM 방화벽(NSG)은 **작업 PC 공인 IP에서 오는 TCP 22(SSH)만** 허용한다. 80·443·6443은 인터넷에 열려 있지 않다.
- 그래서 웹 화면과 Kubernetes API는 **SSH 터널**로 가져온다. 터널은 "작업 PC의 포트 하나를 SSH 연결 안으로 넣어 VM 안의 포트로 이어 주는 통로"다. 작업 PC에서 `localhost:8080`에 접속하면, 실제로는 VM 안의 `127.0.0.1:80`(Traefik)에 접속한 것과 같다.

### 접속 정보 요약

| 항목 | dev | prod (M9에서 생성) |
|---|---|---|
| Azure 리소스 그룹 | `rg-seonung-kube-study` | 동일 |
| VM 이름 | `vm-kube-dev` | `vm-kube-prod` |
| SSH 별칭 | `kube-dev` | `kube-prod` |
| SSH 사용자 / 키 | `azureuser` / `~/.ssh/kube-study` | 동일 |
| 앱 주소 (터널 경유) | `http://album.dev.local:8080` | `http://album.local:8090` |
| K8s API (터널 경유) | `https://127.0.0.1:16443` | `https://127.0.0.1:26443` |
| kubectl context | `k3s-dev` | `k3s-prod` |
| 자동 종료 | 매일 KST 18:00 | 동일 |

---

## 2. 최초 1회 준비 (작업 PC)

이미 끝난 항목은 건너뛴다.

| # | 작업 | 확인 방법 |
|---|---|---|
| 1 | Azure CLI 로그인: `az login --tenant ktopen.onmicrosoft.com` 후 `az account set --subscription 'AX사업부문-인프라아키텍처팀'` | `az account show --query name -o tsv` |
| 2 | SSH 키 `~/.ssh/kube-study`(개인키), `.pub`(공개키) 존재 | `ls ~/.ssh/kube-study*` |
| 3 | `~/.ssh/config`에 별칭 등록 (아래) | `ssh kube-dev hostname` → `vm-kube-dev` |
| 4 | `/etc/hosts`에 도메인 등록 (아래, sudo 필요) | `ping -c1 album.dev.local` → 127.0.0.1 |
| 5 | kubeconfig 등록: 터널을 켠 상태에서 `scripts/fetch-kubeconfig.sh dev` | `kubectl config get-contexts k3s-dev` |

### `~/.ssh/config`

```
Host kube-dev
  HostName <VM 공인 IP>          # az network public-ip show -g rg-seonung-kube-study -n pip-kube-dev --query ipAddress -o tsv
  User azureuser
  IdentityFile ~/.ssh/kube-study
  IdentitiesOnly yes
  ServerAliveInterval 30
```

공인 IP는 Static이라 VM을 껐다 켜도 바뀌지 않는다(2026-10-14 확인).

### `/etc/hosts`

Traefik은 요청의 **Host 이름**을 보고 어느 서비스로 보낼지 정한다. 그래서 IP가 아니라 `album.dev.local` 같은 이름으로 접속해야 하고, 이 이름은 실제 DNS에 없으므로 작업 PC가 직접 알게 한다.

```bash
sudo sh -c 'cat >> /etc/hosts <<EOF
127.0.0.1 album.dev.local grafana.dev.local argocd.dev.local
127.0.0.1 album.local grafana.local argocd.local
EOF'
```

127.0.0.1인 이유: 터널의 입구가 작업 PC 자신(localhost)이기 때문이다.

---

## 3. 서버 켜기

auto-shutdown(18:00) 이후나 직접 끈 뒤에는 VM이 꺼져 있다.

```bash
RG=rg-seonung-kube-study
az vm show -d -g $RG -n vm-kube-dev --query powerState -o tsv   # "VM running" / "VM deallocated"
az vm start -g $RG -n vm-kube-dev                               # 약 20~30초
```

켜진 뒤 바로 접속이 안 될 수 있다. 부팅 후 SSH가 열리기까지 20~30초, K3S와 앱 Pod가 다시 뜨기까지 30초~1분 정도 더 걸린다. **K3S와 앱은 자동으로 다시 뜬다**(k3s 서비스가 부팅 시 자동 시작, Pod는 이전 상태로 복구). 따로 `kubectl apply`할 필요 없다.

준비됐는지 확인:

```bash
ssh kube-dev 'kubectl get nodes; kubectl -n album-dev get pods'
```

모든 Pod가 `Running`(db-migrate는 `Completed`)이면 준비 완료. 재부팅 후에는 `RESTARTS`가 1씩 늘어 있는 게 정상이다.

---

## 4. 서버 접속 (SSH)

```bash
ssh kube-dev                        # 대화형 셸
ssh kube-dev 'kubectl get pods -A'  # 명령 하나만 실행하고 돌아옴
exit                                # 셸 종료 (서버는 계속 켜져 있다)
```

VM 안의 작업 위치는 `~/kube-study`다. 작업 PC에서 고친 코드를 커밋 없이 VM에 반영하려면 작업 PC에서:

```bash
scripts/sync.sh dev                 # 작업 트리를 VM ~/kube-study 로 복사
```

`.gitignore` 대상, `.venv`, VM에만 있는 비밀 파일(`.env`, `secrets.env`)은 복사하지도, 지우지도 않는다. 정식 반영은 `git push` 후 VM에서 `git pull`.

파일 하나 주고받기:

```bash
scp kube-dev:kube-study/some/file ./     # VM → 작업 PC
scp ./file kube-dev:/tmp/                # 작업 PC → VM
```

---

## 5. 터널 통신

### 5.1 기본 터널 (`scripts/tunnel.sh`)

```bash
scripts/tunnel.sh dev start    # 백그라운드로 터널을 연다
scripts/tunnel.sh dev status   # 열려 있으면 "Master running (pid=...)"
scripts/tunnel.sh dev stop     # 닫는다
```

열리는 통로:

| 작업 PC | → VM 안 | 용도 |
|---|---|---|
| `localhost:8080` | `127.0.0.1:80` (Traefik) | 앱, 이후 Grafana(M4)·ArgoCD(M8) UI |
| `127.0.0.1:16443` | `127.0.0.1:6443` (K8s API) | 작업 PC의 `kubectl --context k3s-dev` |

prod는 `scripts/tunnel.sh prod start`이며 포트만 8090 / 26443으로 다르다. dev와 prod 터널은 동시에 열 수 있다.

터널이 열린 상태에서:

```bash
open http://album.dev.local:8080             # 브라우저로 앱 열기
kubectl --context k3s-dev get pods -n album-dev
```

`kubectl`을 매번 `--context`로 쓰기 싫으면 `kubectl config use-context k3s-dev`. 다만 다른 클러스터(k3d 등)를 쓸 때 헷갈리지 않도록 `--context`를 붙이는 쪽을 권한다.

### 5.2 Ingress가 없는 서비스에 임시로 붙기

MinIO 콘솔처럼 Ingress로 노출하지 않은 서비스는 **두 단계**로 연결한다. VM 안에서 `kubectl port-forward`로 서비스를 VM의 포트로 꺼내고, 그 포트를 SSH 터널로 작업 PC까지 가져온다.

```bash
# 터미널 1: VM 안에서 서비스 → VM 127.0.0.1:9001
ssh kube-dev 'kubectl -n album-dev port-forward svc/minio 9001:9001'

# 터미널 2: 작업 PC 9001 → VM 127.0.0.1:9001
ssh -N -L 9001:127.0.0.1:9001 kube-dev
# 브라우저: http://localhost:9001
#   로그인: VM의 ~/kube-study/k8s/overlays/dev/secrets.env 에 있는 S3_ACCESS_KEY / S3_SECRET_KEY
#   (ssh kube-dev 'cat ~/kube-study/k8s/overlays/dev/secrets.env' 로 직접 확인. 다른 곳에 복사하지 않는다)
```

끝나면 두 터미널에서 `Ctrl+C`.

터널이 열려 있으면 작업 PC에서 한 번에 할 수도 있다: `kubectl --context k3s-dev -n album-dev port-forward svc/minio 9001:9001`.

### 5.3 터널 동작 원리 (참고)

`tunnel.sh`는 아래 명령을 백그라운드로 실행한다.

```bash
ssh -f -N -M -S $TMPDIR/kube-tunnel-dev.sock \
    -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
    -L 8080:127.0.0.1:80 -L 16443:127.0.0.1:6443 kube-dev
```

| 옵션 | 의미 |
|---|---|
| `-L A:host:B` | 작업 PC 포트 A로 들어온 연결을 VM 기준 `host:B`로 전달 |
| `-N` | 원격 명령을 실행하지 않고 포워딩만 |
| `-f` | 연결 후 백그라운드로 전환 |
| `-M -S <소켓>` | 제어 소켓을 만들어 나중에 `status`/`stop`으로 이 연결을 찾는다 |
| `ExitOnForwardFailure` | 포트를 못 열면(이미 사용 중 등) 조용히 살아 있지 않고 실패 |
| `ServerAliveInterval=30` | 30초마다 생존 신호를 보내 유휴 연결이 끊기는 것을 막음 |

---

## 6. 서버 중단

### 6.1 작업을 마칠 때 (권장 순서)

```bash
scripts/tunnel.sh dev stop                          # 1. 터널 닫기
az vm deallocate -g rg-seonung-kube-study -n vm-kube-dev   # 2. VM 끄기 (약 30초)
az vm show -d -g rg-seonung-kube-study -n vm-kube-dev --query powerState -o tsv   # "VM deallocated"
```

- **`deallocate`를 쓴다.** `az vm stop`이나 VM 안의 `sudo shutdown`은 OS만 끄고 **컴퓨팅 요금이 계속 나간다**.
- 끄기 전에 앱이나 클러스터를 따로 정리할 필요는 없다. 데이터는 PVC(디스크)에 남고, 다음에 켜면 그대로 복구된다(2026-10-14 deallocate → start로 확인).
- 깜빡해도 **매일 KST 18:00에 자동으로 deallocate** 된다. 그 이후까지 작업하려면 다시 `az vm start`.

### 6.2 꺼져 있어도 나가는 비용

| 항목 | 꺼진 동안 |
|---|---|
| VM 컴퓨팅 | 0 (deallocate 상태) |
| OS 디스크 64 GiB (Standard SSD) | 약 $4.8/월 |
| 공인 IP (Standard, Static) | 약 $3.6/월 |

### 6.3 자동 종료 시각 바꾸기 / 끄기

```bash
# 시각 변경 (UTC 기준. KST 20:00 = UTC 1100)
az vm auto-shutdown -g rg-seonung-kube-study -n vm-kube-dev --time 1100
# 자동 종료 해제 (권장하지 않음)
az vm auto-shutdown -g rg-seonung-kube-study -n vm-kube-dev --off
```

### 6.4 앱만 멈추고 VM은 유지

```bash
ssh kube-dev 'kubectl -n album-dev scale deploy --all --replicas=0'   # 앱 Pod만 정지
ssh kube-dev 'kubectl apply -k ~/kube-study/k8s/overlays/dev'         # 원래 replica로 복구
```

---

## 7. 하루 작업 흐름 예시

```bash
# 시작
az vm start -g rg-seonung-kube-study -n vm-kube-dev
ssh kube-dev 'kubectl -n album-dev get pods'      # Running 확인 (안 되면 30초 뒤 재시도)
scripts/tunnel.sh dev start
open http://album.dev.local:8080

# 작업: 작업 PC에서 편집 → scripts/sync.sh dev → ssh kube-dev 에서 빌드/배포
#        (빌드·배포 절차는 k8s-dev.md)

# 종료
scripts/tunnel.sh dev stop
az vm deallocate -g rg-seonung-kube-study -n vm-kube-dev
```

---

## 8. 문제 해결

| 증상 | 원인 | 조치 |
|---|---|---|
| `ssh: connect to host ... port 22: Operation timed out` | VM이 꺼져 있음 | `az vm show -d ... --query powerState` → `az vm start` |
| 위와 같은데 VM은 running | 작업 PC 공인 IP가 바뀌어 NSG가 막음 (집↔회사 이동, 공유기 재시작 등) | 아래 "공인 IP 변경" |
| `Permission denied (publickey)` | 다른 키를 쓰고 있음 | `~/.ssh/config`의 `IdentityFile ~/.ssh/kube-study`, `IdentitiesOnly yes` 확인 |
| `REMOTE HOST IDENTIFICATION HAS CHANGED` | VM을 새로 만들어 호스트 키가 바뀜 | `ssh-keygen -R <VM 공인 IP>` 후 재접속 |
| `bind [127.0.0.1]:8080: Address already in use` | 터널이 이미 열려 있거나 다른 프로그램이 8080 사용 | `scripts/tunnel.sh dev status` / `lsof -nP -iTCP:8080 -sTCP:LISTEN` |
| 터널은 열렸는데 `Connection reset by peer` | VM을 막 켜서 Traefik이 아직 기동 중 | 30초~1분 뒤 재시도 |
| 터널이 갑자기 안 됨 (`status`는 running) | 와이파이 변경·절전으로 SSH 연결이 끊김 | `scripts/tunnel.sh dev stop` 후 `start` |
| 브라우저 404 page not found | 주소를 IP나 `localhost`로 입력함(Host 불일치) | `http://album.dev.local:8080`으로 접속, `/etc/hosts` 확인 |
| 썸네일 이미지만 깨짐 | presigned URL 유효시간(1시간) 경과 | 새로고침 |
| `kubectl`: `connection refused` (127.0.0.1:16443) | 터널이 닫혀 있음 | `scripts/tunnel.sh dev start` |
| `kubectl`: 인증서 오류 | VM/K3S를 새로 설치함 | `scripts/fetch-kubeconfig.sh dev` 재실행 |
| `az`: 인증 만료 오류 | Azure CLI 토큰 만료 | `az login --tenant ktopen.onmicrosoft.com` |

### 작업 PC 공인 IP 변경

```bash
curl -fsS https://api.ipify.org; echo        # 현재 공인 IP 확인
az network nsg rule update -g rg-seonung-kube-study --nsg-name nsg-kube-dev \
  -n allow-ssh-workpc --source-address-prefixes "$(curl -fsS https://api.ipify.org)/32"
```

규칙 반영까지 수십 초 걸릴 수 있다. prod는 `--nsg-name nsg-kube-prod`.

---

## 9. 보안 수칙

- **열린 포트는 22뿐이다.** 앱·API 포트를 NSG에서 열지 않는다. 필요하면 터널을 쓴다.
- **개인키 `~/.ssh/kube-study`는 작업 PC 밖으로 내보내지 않는다.** 권한은 600이어야 한다(`ls -l ~/.ssh/kube-study`).
- **kubeconfig(`~/.kube/config`)에는 클러스터 관리자 인증서가 들어 있다.** 저장소나 채팅에 붙여 넣지 않는다.
- **VM에만 있는 비밀 파일:** `~/kube-study/.env`(compose), `~/kube-study/k8s/overlays/dev/secrets.env`(K8s Secret 원본). 둘 다 gitignore 대상이며 커밋하지 않는다.
- 터널의 입구는 `127.0.0.1`(작업 PC 자신)에만 열린다. 같은 와이파이의 다른 기기에서는 접근할 수 없다.

## 관련 문서

- [azure-vm.md](azure-vm.md): VM 생성·삭제, 리소스 구성
- [access.md](access.md): 터널 포트 배치와 kubeconfig 등록 상세
- [k8s-dev.md](k8s-dev.md): dev 클러스터 빌드·배포 절차
- [local-compose.md](local-compose.md): docker-compose 실행
