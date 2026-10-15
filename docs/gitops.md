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
