# prod 재현 절차 (통합 검증 대기)

prod는 dev와 독립된 VM·K3S 클러스터다. B4as_v2, 64GB 디스크와
18:00 KST 자동 종료를 사용한다. 2026-10-15 빈 VM을 생성해 도구와
GitOps 컨트롤러를 설치했다. 아직 앱 이미지 승격 및 새 클러스터 재현 검증은
완료하지 않았다.

## 준비된 구성

- album-prod HPA 2~6, worker 0~5, Redis scaler 주소는 prod namespace.
- 앱은 PR merge 이후 수동 Sync. 인프라 child 앱과 root는 자동 Sync.
- dev·prod 각각의 봉인 키와 무작위 자격을 사용한다.
- prod ciphertext 검증 성공과 dev ciphertext의 prod 복호화 거절을 확인했다.
- VM과 작업 PC 양쪽에 prod 키를 저장소 밖 mode 600 파일로 백업했다.
- prod platform·application·root Kustomize 렌더링이 성공했다.

## 새 클러스터에서 세 명령

체크아웃과 **해당 prod 클러스터의** 키 백업을 VM에 먼저 준비한다.
키 백업은 Git으로 가져올 수 없으므로 별도로 보관·복원해야 한다.

```bash
SEALED_KEY_BACKUP="$HOME/.local/share/kube-study/sealed-secrets-key-prod.yaml" \
  bash scripts/vm-setup.sh prod
scripts/install-gitops.sh prod
kubectl apply -f argocd/root-prod.yaml
```

첫 명령이 K3S 설치 직후 기존 봉인 키를 복원한다. 둘째가 ArgoCD와
Sealed Secrets 컨트롤러를 설치한다. 셋째가 나머지 인프라와 앱을 복원한다.
추가 Helm install·평문 Secret 생성·직접 앱 apply는 재현 절차에 포함하지 않는다.

처음 생성하는 album-prod child Application에는 일회성 `operation.sync`를
함께 지정해 bootstrap 명령으로 초기 배포를 요청한다. root는 기존 child의
`/operation`을 비교 및 재적용에서 제외하므로 이 일회성 요청을 재생하지 않는다.
앱 syncPolicy에는 automated가 없고 이후 Release PR의 이미지 변경은 수동
Sync 전까지 OutOfSync로 남는다. 이 동작은 실제 fresh bootstrap 검증에서
확인해야 하며, 렌더 성공만으로 재현 완료를 주장하지 않는다.

Mac 터널은 `scripts/tunnel.sh prod start`, 앨범은
`http://album.prod.localhost:8090`, Grafana·ArgoCD도 같은 포트의
`grafana.prod.localhost`, `argocd.prod.localhost`로 접근한다.
