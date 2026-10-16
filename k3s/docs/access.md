# 클러스터 접근 방법 (SSH 터널)

VM은 SSH(22)만 열려 있다. 앱, ArgoCD/Grafana UI, Kubernetes API는 SSH 터널로 작업 PC에 끌어와서 쓴다. 결정 배경은 [plan.md](plan.md) 1.4를 본다.

> 서버 켜기·접속·터널·끄기 전체 흐름과 문제 해결은 [server-access.md](server-access.md)에 정리되어 있다. 이 문서는 터널 포트 배치와 kubeconfig 등록 상세만 다룬다.

## 포트 배치

| 대상 (VM 쪽) | dev → 작업 PC | prod → 작업 PC |
|---|---|---|
| Traefik Ingress `:80` | `localhost:8080` | `localhost:8090` |
| Kubernetes API `:6443` | `127.0.0.1:16443` | `127.0.0.1:26443` |

ArgoCD, Grafana UI도 Ingress 호스트 이름으로 같은 HTTP 포트를 통해 노출한다 (M4, M8에서 추가).

## 최초 1회 설정

작업 PC에서는 저장소의 `k3s/` 디렉터리에서 아래 스크립트를 실행한다.

1. `~/.ssh/config`에 `kube-dev` 별칭 등록 ([azure-vm.md](azure-vm.md))
2. 작업 PC `/etc/hosts`에 이름 등록 (Traefik이 Host 헤더로 라우팅하므로 필요)

   ```
   127.0.0.1 album.dev.local argocd.dev.local grafana.dev.local
   127.0.0.1 album.local argocd.local grafana.local
   ```

3. 터널을 켜고 kubeconfig 등록

   ```bash
   scripts/tunnel.sh dev start
   scripts/fetch-kubeconfig.sh dev     # ~/.kube/config에 context k3s-dev 추가
   kubectl --context k3s-dev get nodes
   ```

`fetch-kubeconfig.sh`는 기존 `~/.kube/config`를 `config.bak.<시각>`으로 백업한 뒤 병합하며, current-context는 바꾸지 않는다. kubeconfig에는 클러스터 관리자 인증서가 들어 있으므로 저장소 안에 두지 않는다.

## 일상 사용

```bash
az vm start -g rg-seonung-kube-study -n vm-kube-dev   # VM이 꺼져 있으면
scripts/tunnel.sh dev start
open http://album.dev.local:8080
scripts/tunnel.sh dev stop
```

VM 쪽 작업(docker, helm, k6 등)은 `ssh kube-dev`로 접속해서 한다. 커밋 전에 VM에서 바로 실행해 보려면 `scripts/sync.sh dev`로 K3S 프로젝트를 `~/kube-study/k3s`에 복사한다 (`.gitignore` 대상과 `.venv`는 복사하지 않는다).

## 문제 해결

| 증상 | 원인과 조치 |
|---|---|
| `ssh` 타임아웃 | VM이 꺼짐(18:00 auto-shutdown) 또는 작업 PC 공인 IP 변경 → [azure-vm.md](azure-vm.md) |
| `bind: Address already in use` | 터널이 이미 켜져 있음 → `scripts/tunnel.sh dev status` |
| Traefik 404 | 해당 Host의 Ingress가 아직 없음 (M2 이전에는 정상) |
| `kubectl` 인증서 오류 | VM 재설치 후 kubeconfig가 바뀜 → `fetch-kubeconfig.sh` 재실행 |

## Mac에서 DNS 설정 없이 접속

`scripts/tunnel.sh dev start` 후 Chrome에서 [앨범](http://album.dev.localhost:8080), [Grafana](http://grafana.dev.localhost:8080), [ArgoCD](http://argocd.dev.localhost:8080)를 연다. `.localhost`는 loopback으로 해석되므로 Mac hosts 변경이 필요 없다. VM에서 쓰는 기존 `.dev.local` Host도 유지한다. Grafana 전용 forward `http://localhost:19001`도 사용할 수 있다.

2026-10-15 Chrome에서 album.dev.localhost:8080의 갤러리·버전 헤더 표시를
확인했고, grafana.dev.localhost:8080에서도 생성한 Secret으로 로그인했다.
전용 port-forward는 Grafana Pod 교체 시 종료될 수 있으므로 지속적인 접속에는
공용 Ingress SSH 터널의 localhost hostname을 권장한다.
