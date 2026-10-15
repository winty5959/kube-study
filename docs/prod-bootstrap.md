# prod 재현 절차 (검증 완료)

prod는 dev와 독립된 VM·K3S 클러스터다. B4as_v2, 64GB 디스크와
18:00 KST 자동 종료를 사용한다. 2026-10-15 빈 VM을 생성해 도구와
GitOps 컨트롤러를 준비한 뒤, 앱 namespace와 사용자 데이터가 없는 것을 확인하고
K3S를 제거했다. 같은 VM에서 아래 세 명령만으로 클러스터·전체 서비스·모니터링을
재생성했다 (2026-10-15). 이후 Azure OS reimage까지 수행해 빈 OS에서도
같은 세 명령으로 재현했다. 승인된 Release 승격과 롤백은 E-13·E-14에서 통과했다.

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
앱 syncPolicy에는 automated가 없다. 실제 fresh bootstrap에서 초기 operation으로
앱 배포와 migration·smoke 훅이 성공했다. 이후 Release 변경이 수동 Sync 전까지
OutOfSync로 남는 동작은 [E-13](experiments/E-13.md)에서 검증했다.

## 실제 복구 결과

- 첫 명령과 둘째 명령 모두 exit 0. 별도 앱 apply·추가 Helm install·평문 Secret 생성은 없었다.
- 셋째 명령 이후 root-prod와 7개 child가 모두 Synced·Healthy가 됐다.
- 기존 키 복원으로 album-secrets와 grafana-admin이 복호화됐다. 값은 출력하지 않았다.
- API 2 Ready, frontend 2 Ready, Postgres·Redis·MinIO Ready를 확인했다.
- GHCR의 CI-published sha-a3e8669를 익명 pull했다. prod VM에서 이미지를 빌드하거나 import하지 않았다.
- 공개 라우팅 smoke: 업로드 → DONE → WebP 200×100·800×400 → 원본 3,462바이트 일치 → 삭제 통과.
- prod 관측성 checker: 대시보드 5개·20개 패널의 실제 finite 표본과 필수 알림 3개 확인.
- Grafana Secret 로그인 후 실제 시계열을 화면으로 확인했다. 초기 DB migration 중의
  Progressing·Degraded는 재시작 없이 해소됐다. 설치 중 smoke 이후 초기 표본 부족은
  설치 완료 후 새 smoke로 채웠다.

### 최초 K3S 재설치의 Grafana 증거

- [서비스](experiments/screenshots/prod-dashboard-01.png)
- [큐·워커](experiments/screenshots/prod-dashboard-02.png)
- [API 확장](experiments/screenshots/prod-dashboard-03.png)
- [리소스](experiments/screenshots/prod-dashboard-04.png)
- [처리 시간](experiments/screenshots/prod-dashboard-05.png)

### 재현 범위

최초 K3S 재설치에 이어 Azure `az vm reimage`로 OS를 초기화했다. 그 직후
k3s·docker·helm·kubeseal·argocd·k6·uv 일곱 도구가 모두 없는 것을 확인했다.
Git archive로 소스를 준비하고 저장소 밖 prod 봉인 키를 mode 600으로 복원한 뒤
위 세 명령만 실행했다. 앞의 두 명령은 exit 0, root apply는 생성에 성공했다.
추가 앱 apply·이미지 import·수동 Sync 없이 8개 Application 모두 Synced·Healthy가 됐다.
prod ciphertext 검증은 성공했고 dev ciphertext는 prod에서 거절됐다.

빈 OS 복구 후 혼합 JPEG·PNG·WebP 28장 업로드, 페이지당 24장과 다음 페이지 4장,
DONE 상세·800×400 이미지·처리 Pod 표시를 실제 브라우저에서 확인했다.
원본 다운로드 12,028바이트가 입력과 정확히 일치했고 UI 삭제도 통과했다.
검증용 나머지 27장 정리 후 DB 사진과 S3 원본·썸네일은 모두 0개였다.
[업로드 화면](experiments/screenshots/final-ui-gallery.png)과
[상세 화면](experiments/screenshots/final-ui-detail.png)을 보관했다.
업로드 로그의 PENDING은 접수 당시 상태이며 상세와 갤러리 상태는 DONE으로 갱신됐다.

새 OS에서 두 차례 전체 smoke와 관측성 checker가 통과했다. 실제 Grafana 화면도 확인했다:
[서비스](experiments/screenshots/prod-fresh-os-dashboard-01.png),
[큐·워커](experiments/screenshots/prod-fresh-os-dashboard-02.png),
[API 확장](experiments/screenshots/prod-fresh-os-dashboard-03.png),
[리소스](experiments/screenshots/prod-fresh-os-dashboard-04.png),
[처리 시간](experiments/screenshots/prod-fresh-os-dashboard-05.png).

현재 prod 네 이미지는 E-14의 공식 Git revert 결과인 sha-a3e8669다.
이는 Git 상태와 외부 키 백업을 통한 복구다. 기존 PVC 데이터의 백업·복구는
검증하지 않았으며 단일 노드 local-path의 노드 장애 데이터 손실 한계는 남는다.

Mac 터널은 `scripts/tunnel.sh prod start`, 앨범은
`http://album.prod.localhost:8090`, Grafana·ArgoCD도 같은 포트의
`grafana.prod.localhost`, `argocd.prod.localhost`로 접근한다.
