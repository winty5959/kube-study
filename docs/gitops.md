# GitOps 부트스트랩 (구현 진행 중)

## 컨트롤러

VM에서 `scripts/install-gitops.sh`를 실행한다. ArgoCD chart 10.10.3과
Sealed Secrets chart 2.20.0을 설치한다. ArgoCD는 SSH 터널 뒤에서 HTTP로
접근하며 공개 HTTP 포트를 열지 않는다. Application 상태의 Lua health 검사는
자식 앱의 Synced·Healthy 상태를 확인해 app-of-apps wave 순서를 기다린다.

## Secret과 키 백업

`scripts/seal-environment.sh dev|prod`는 VM에 있는 기존 `secrets.env`와
Grafana Secret을 strict namespace/name scope로 암호화한다. 평문은 파이프로만
전달하고 출력하지 않는다. `k8s/secrets/<env>/*sealed.yaml`만 Git에 넣는다.

컨트롤러 복호화 키 백업은 VM의
`~/.local/share/kube-study/sealed-secrets-key-<env>.yaml`에 mode 600으로 저장한다.
작업 PC에도 동일한 저장소 밖 경로로 복사한다. 키를 잃으면 Git의 암호문만으로
Secret을 복원할 수 없다. 키 갱신 후에는 백업도 다시 생성해야 한다.

새 VM에서는 K3S 설치 단계에서 키를 복원하고, 이후 ArgoCD·컨트롤러를 설치한다.
이미 컨트롤러가 실행 중인 경우 키를 apply한 뒤 컨트롤러 Pod를 재시작해 읽게 한다.
백업 파일과 평문 Secret은 Git·Graphify·로그 입력에 포함하지 않는다.

## 확인 기록

2026-10-15 dev에서 두 컨트롤러 설치가 성공했다. 기존 DB/S3/Grafana 자격으로
암호화된 Secret을 생성했고, 키 백업을 VM 및 작업 PC의 저장소 밖에 보관했다.
dev 평문 generator를 SealedSecret 참조로 교체했다. 복호화된 세 값이 기존 Secret과 모두 일치함을 값 출력 없이 확인했고, API·PostgreSQL·MinIO 재배포 후 전체 smoke가 통과했다. root Application 동기화는 다음 단계에서 검증한다.

## 배포 순서와 훅

root-dev는 child Application의 health 및 sync 상태를 기다린다.

| Wave | 앱 |
|---|---|
| -3 | Sealed Secrets, KEDA 컨트롤러 |
| -2 | monitoring namespace와 Grafana SealedSecret |
| -1 | album namespace, DB·Redis·MinIO, ServiceAccount, NetworkPolicy, album SealedSecret |
| 0 | 모니터링 Helm 앱, album 애플리케이션 |
| 1 | Grafana dashboards, ServiceMonitor, PrometheusRule |

platform과 application은 같은 dev overlay를 가져와 필요한 리소스만 선택하므로
CI가 수정하는 이미지 태그의 원본이 하나다. 마이그레이션은 application의
PreSync Job이다. 최초 설치에서 필요한 DB·Secret·ServiceAccount는 앞선
platform 앱에서 준비한다. PostSync는 같은 API 이미지를 사용하는 smoke Job이고,
ConfigMap에 저장된 `scripts/smoke.py`를 그대로 실행한다.

smoke는 내부 Traefik Service를 사용하며 공개 Host를 유지해 presigned URL도
검증한다. 별도 ServiceAccount는 API 권한과 토큰이 없고, egress는 DNS와
Traefik Pod의 8000 포트로 제한한다. 실패한 Job은 진단을 위해 보존한다.
2026-10-15 dev에서 실제 Job을 실행해 업로드·DONE·WebP 2종·원본·삭제가 통과했다.

기존 Grafana Secret 인수 시에는 `sealedsecrets.bitnami.com/managed=true`를 먼저 지정한다. 처음 root 동기화에서 unmanaged Secret을 덮어쓰지 못해 credentials 앱이 Degraded가 된 것을 확인하고, 자격을 바꾸지 않고 관리 권한을 인수하도록 bootstrap을 보완했다.
