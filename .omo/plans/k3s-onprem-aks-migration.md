# K3S 폴더 정리와 AKS 전환 개발 계획

갱신: 2026-10-16 KST · 계획 시작 HEAD `a64cdb3` · K3S 작업 1~6 및 F1~F4 완료.
참고: [Plan k3s to AKS migration](codex://threads/01a141ef-9600-7db3-9856-ecefa17822f2).

이번 요청으로 AKS를 로드맵에서 상세 개발 명세로 확장했다. 저장소는 기존
`winty5959/kube-study` 하나, 기존 프로젝트는 `k3s/`, 새 프로젝트는 `aks/`다.
아래 작업 1~6은 K3S 경로 정리이고, 이후 AKS 작업은 별도 명세 A0~A15로 진행한다.

| 문서 | 용도 |
|---|---|
| 이 문서 | 기존 K3S 폴더 이동·CI·VM·GitOps 경로 전환 |
| [AKS 상세 구현 명세](aks-implementation.md) | 최소 구성, 수정 파일, 작업 순서, 검증·복구 기준 |
| [AKS 최소 사양과 비용](aks-cost-baseline.md) | 현재 앱 requests 분석, SKU 비교, 상시/시간제/중지 비용 |

사용자는 AKS를 처음 사용하므로 임의 예산을 정하지 않고 프로젝트가 돌아가는
최소 구성을 먼저 산정한다. 계획 작성이 끝났고, 2026-10-16 사용자가 이 계획에 따라
goal을 세우고 구현을 진행하도록 요청했다. 실행 중 live 상태·권한·비용 전제와
완료 증거를 카드별로 갱신한다.


## 계획 요약

**Who this is for and what changes for them:** 기존 K3S 개발을 계속하면서 AKS 전환을 준비하는 개발자를 위한 계획이다. 같은 저장소 안에서 두 프로젝트를 구분하고 기존 개발·배포 흐름을 이어간다.

**What you'll get:** 기존 프로젝트의 폴더 이동, 문서·스크립트·자동화 경로 정리, dev/prod 경로 전환 검증, AKS 상세 구현 명세·최소 비용 산정과 완료 기록.

**Why this approach:** 저장소와 기존 이력을 유지하고 임시 호환 경로로 감시 중인 배포를 보호한 뒤 개발 환경부터 전환한다.

**What it will NOT do:** 실제 사용자 트래픽·데이터를 K3S에서 AKS로 이전하거나 기존 K3S 환경을 삭제하지 않는다. 별도 AKS A0~A15 구축·검증은 이 goal의 범위다.

**Effort:** Large
**Risk:** Medium - 자동 감시 중인 GitOps 경로와 삭제 옵션이 있는 VM 동기화를 순서대로 전환해야 한다.
**Decisions to sanity-check:** 단일 기존 저장소, 기존 K3S와 미래 AKS의 폴더 분리, 기존 CI의 dev 자동 승격과 prod 수동 승격 유지. AKS 기본안은 단일 학습 클러스터이며 상세 사양·비용·접근 방식은 연결된 AKS 명세를 따른다.

Current execution: K3S tasks 1-6 and final checks F1-F4 are complete with evidence. The user first
selected AX사업부문-인프라아키텍처팀, then explicitly changed the AKS target to the
Enterprise부문-아키텍처강화TF subscription and `rg-seonung-aks-test`. A0 found
Standard_F4s_v2 unavailable and the user chose Standard_D4as_v5. Using the user's Owner access,
AKS cluster RBAC roles were assigned. A0-A11 and A14 have implementation evidence in
`.omo/evidence/aks-implementation/`. A12 awaits user review/approval of release PR #4; A13
awaits E-13/E-14; A15 awaits posted Azure cost data. These cards remain in progress.
K3S traffic/data migration and source-environment deletion remain outside this goal.

---

> TL;DR (machine): Large / Medium risk / same repository; K3S relocation and F1-F4 checks complete; AKS A0-A11 and A14 complete in the user-selected Enterprise subscription on two D4as_v5 nodes; A12/A13/A15 remain in progress; live K3S cutover/deletion is excluded.

## Scope
### Affected user and ideal state
**Affected user:** 개발자와 기존 K3S dev/prod 운영 흐름. 개발자는 같은 Git 저장소의 k3s/에서 기존 개발을 계속하고, 향후 aks/에서 전환 프로젝트를 진행한다.

| Row | Statement | Reason |
| --- | --- | --- |
| IS-1 | 같은 저장소에 k3s/와 aks/가 있고 기존 개발 명령이 k3s/에서 동작 | 사용자 확정 구조 |
| IS-2 | CI·Release·GitOps가 이동 경로를 정확히 해석 | 빌드 및 배포 연속성 |
| IS-3 | 리소스·데이터·키와 prod 수동 승격 정책 보존 | 구조 변경으로 운영 상태를 잃지 않음 |
| IS-4 | AKS 구현 순서와 최소 비용을 별도 명세로 제공 | AKS 구현은 이번 범위 밖 |
| IS-5 | 기능별 Lore 커밋과 실제 검증 증거를 기존 origin에 게시 | 추적성과 재현성 |
| GAP-1 | 기존 앱·문서·인프라가 저장소 루트에 있음 | 작업 2로 해소 |
| GAP-2 | CI와 selector가 루트 경로를 가정 | 작업 2·4로 해소 |
| GAP-3 | live ArgoCD와 VM이 옛 경로 사용 | 작업 1·2·4·5로 해소 |
| GAP-4 | AKS 상세 구현 명세와 최소 비용 근거 부족 | 작업 3으로 해소 |
| GAP-5 | 이동 후 검증·커밋 증거 없음 | 작업 6·최종 검증으로 해소 |

### Must have
- 단일 Git 루트/origin: https://github.com/winty5959/kube-study.git. 기존 이력/태그 유지.
- 최종 루트: .git/, .github/workflows/, .gitignore, AGENTS.md, README.md, k3s/, aks/. 기존 ignored 도구 캐시 및 .omo 계획 자료는 별도 관리한다.
- k3s/로 apps/, argocd/, dashboards/, docs/, infra/, k8s/, loadtest/, scripts/, docker-compose.yaml을 이동한다. k3s/.gitignore에는 컴포넌트 로컬 실행·동기화 보호 규칙을 둔다.
- 루트 README는 두 프로젝트 안내, 기존 README와 운영 문서는 k3s/ 안에서 관리. aks/README.md에는 로드맵만 작성한다.
- .github/workflows는 루트 유지. Argo repoURL 및 GHCR album-* 이름은 유지하고 Git 소스 path 및 Helm valueFiles를 수정한다.
- 기준 a64cdb3. 실제 작업 시작 시 최신 HEAD/dirty 상태를 다시 확인하며 타인의 변경을 덮어쓰지 않는다.
- 기존 합의: Mac에 venv/이미지를 만들지 않고 VM/CI에서 검사, prod album은 수동 Sync, MinIO 지정 6건 예외 만료 2026-11-14 유지.

### Must NOT have (guardrails, anti-slop, scope boundaries)
- 이 계획 작성 세션에서 구현·커밋·push·클러스터 조작을 수행하지 않는다.
- onprem/, kube-study-k3s 새 저장소, 중첩 .git, submodule, shared/ 추출을 추가하지 않는다.
- K3S 구조 작업에는 AKS 앱 복제/클러스터 생성·과금을 섞지 않는다. AKS는 후속 A0~A15 명세를 따른다. managed DB/Blob/ACR 전환은 기본안에서 제외한다.
- 이미지 태그·namespace·리소스 이름·PVC·봉인 키·운영 정책을 폴더 변경 때문에 바꾸지 않는다. 정상 CI에 따른 dev 새 이미지 승격은 별도 기록한다.
- 과거 Actions/PR/실험 URL 일괄 치환, VM 비밀 파일 재생성, 원본 데이터·원격·태그 삭제, force-push, rsync 상위 루트 --delete 금지.

## Verification strategy
검증은 구현 담당자가 수행한다. 로그인·권한 문제 등 실제 외부 의존성만 미검증으로 남긴다.
- Test decision: tests-after. 기존 pytest/ruff/actionlint 및 JavaScript 구문 검사와 실제 경로 QA를 사용한다. 새 회귀 사례는 selector의 프로젝트별 workflow 구분·저장소 접두사 및 rsync 보호처럼 실패 가능성이 있는 변경에 한정한다.
- pytest/ruff는 VM의 기존 uv 환경에서 실행한다. 역사 문서의 47개 결과는 새 실행 결과로 주장하지 않는다.
- git diff 경로는 repo-relative, shell cwd는 component-relative일 수 있다. 두 좌표계를 별도로 검증한다.
- 모든 QA 로그는 비밀 값 없이 .omo/evidence/k3s-aks-layout/ 아래 저장한다. 비밀 비교는 일치/불일치 및 개수만 기록한다.
- Graphify는 update . 완료와 종료 상태만 기록. 비밀 파일은 입력에서 제외하고 제외 개수만 보고한다.

## Execution strategy
### 실행 순서
준비/구조 작업: 1 → 2; 로드맵 3은 작업 2와 독립 문서로 준비할 수 있으나 같은 파일을 동시 수정하지 않는다.
게시/전환 작업: 2·3 → 4 → 5 → 6. live dev와 prod 전환은 반드시 순차적이다.
최종 검증은 F1~F4. K3S 구현은 사용자의 2026-10-16 goal 요청으로 승인되어 수행했다. 사용자는 AKS 대상으로 먼저 AX사업부문-인프라아키텍처팀을 골랐고 이후 Enterprise부문-아키텍처강화TF와 `rg-seonung-aks-test`로 정정했다. A0-A11은 실제 Azure 검증과 증거를 완료했고 A12-A15를 이 goal에서 계속한다.

### Dependency matrix
| Todo | Depends on | Blocks | Can parallelize with |
| --- | --- | --- | --- |
| 1 | 없음 | 2,4 | 없음 |
| 2 | 1 | 4 | 3의 내용 조사 |
| 3 | 1 | 4 | 2 |
| 4 | 2,3 | 5 | 없음 |
| 5 | 4 | 6 | 없음 |
| 6 | 5 | F1~F4 | 없음 |

## Todos
> Implementation + Test = ONE todo. Never separate.
- [x] 1. 기준 상태와 경로 전환 복구 자료 확보
  Recommended task executor category: quick — 기존 상태 조회와 보존 목록 정리.
  What to do / Must NOT do: git status/log/remotes/tags와 추적 파일 목록을 확보한다. k3s-dev/prod context에서 root/child 16개 source.path, values 경로, syncPolicy, operation 상태, workloads/Jobs, PVC, 이미지 tag/digest를 비밀 없는 필드로 기록한다. 원본 root manifest와 child specs 및 외부 봉인 키 백업 존재를 확인한다. 자동 Sync root-prod와 수동 album-prod를 구분한다.
  Closes: GAP-3. Blocked by: 없음. Blocks: 2,4.
  References: .gitignore; k3s/docs/plan.md 1.2~1.6; k3s/docs/completion.md; k3s/argocd/root-{dev,prod}.yaml; k3s/argocd/bootstrap/{dev,prod}/*.yaml; k3s/scripts/sync.sh.
  Acceptance criteria: git rev-parse --show-toplevel가 kube-study이며 원격 유지, live 기존 경로 전체 목록과 rollback 기준 HEAD 확보. 로그에 Secret data나 키 본문 없음.
  QA happy: git status --short; git rev-parse HEAD; git remote -v; git tag --list; kubectl --context k3s-dev -n argocd get applications -o json 및 prod 동등 명령을 필요한 source/policy/status 필드로만 필터. Evidence: .omo/evidence/k3s-aks-layout/task-1-baseline.txt.
  QA failure: context 접속 불가/키 백업 부재면 해당 항목을 미검증으로 명시하고 live 전환 4를 보류한다. 로컬 설계/편집은 계속 가능하나 bridge 삭제 완료를 주장하지 않는다.
  Commit: N — 준비 증거는 민감 값 없이 최종 완료 문서에 요약.

- [x] 2. K3S 이동과 모든 실행 경로를 하나의 일관된 변경으로 구현
  Recommended task executor category: unspecified-high — 코드·CI·GitOps 경로가 같은 시점에 일치해야 한다.
  What to do / Must NOT do: 명시된 프로젝트 파일을 git mv로 k3s/에 옮긴다. .git/.github/AGENTS.md/root ignore는 유지한다. 루트 README를 인덱스로 만들고 기존 README를 k3s/README.md에 보존한다. k3s에서 실행하는 상대 경로는 유지하되 저장소 루트 좌표만 수정한다.
  CI: .github/workflows/{ci,release}.yaml의 paths, helper 호출, action Docker context, node/trivy 파일 경로, Python working-directory, git add/commit, overlay 수정, release dry-run 입력을 k3s 위치로 맞춘다. defaults.run.working-directory만으로 uses: action 입력 경로가 바뀌지 않음을 반영한다. selector의 git diff 입력은 k3s/apps/...와 k3s/scripts/... 및 root의 K3S 소유 workflow 파일만 명시적으로 처리한다. 기존 .github/workflows/ 전체 prefix 매칭을 좁혀 미래 aks-ci.yaml/aks-release.yaml 수정이 K3S 빌드를 유발하지 않게 한다. selector 출력 Docker context는 workflow checkout 루트 기준 k3s/apps/...로 정하고 helper 파일 접근은 __file__ 기준 컴포넌트 루트로 고정한다. repo 루트와 k3s cwd 양쪽 실행을 검사한다. aks/ 문서 변경은 K3S rebuild/promotion을 유발하지 않는다.
  GitOps: source.path에 k3s/를 추가하고 Helm $values/k3s/infra/...를 사용한다. 외부 Helm repoURL과 차트 버전은 유지. k3s 내부 Kustomize 상대 참조는 이동 전후 같은 대상인지 검사한다. k3s/scripts/kustomization.yaml에서 생성하는 smoke ConfigMap과 app 외부 상대 참조도 포함한다.
  전환 bridge: live 목록의 모든 옛 Kustomize source.path에는 새 대응 경로를 가리키는 최소 Kustomization을 남긴다. 단, 옛 argocd/bootstrap/{dev,prod}는 새 bootstrap으로 forwarding하지 않고 기존 child Application spec을 그대로 보존한다. 그래야 첫 push에서 prod 경로가 먼저 전환되지 않는다. 기존 $values/infra/...의 소비 파일은 동일 내용의 임시 사본으로 보존한다. 옛 bootstrap 참조에 필요한 manifest도 보존한다. 새 root 정의는 k3s/argocd/root-*.yaml에만 둔다. bridge는 root/child 전환 완료 후 작업 5에서 제거한다.
  VM: sync source를 k3s/로 한정하고 목적지를 ~/kube-study/k3s/로 변경한다. 빈 env/미지원 env/상위 경로를 거부한다. root ignore 보호가 전송 루트 변경으로 빠지지 않도록 k3s/.gitignore 및 명시적 비밀/venv exclude+protect를 정리한다. 원격 .git과 형제 aks/는 건드리지 않는다. SSH 키·외부 sealing key 위치는 유지한다.
  문서: 현재 운영 명령과 clone 후 cd, scp, sync/bootstrap 경로를 모두 갱신한다. k3s/docs 내부 링크는 상대 관계 유지, 기존 완료 증거 URL은 보존한다.
  Closes: GAP-1, GAP-2, GAP-3. Blocked by: 1. Blocks: 4.
  References: 이동 전 README.md; .github/workflows/*.yaml; k3s/scripts/{changed-components,prepare-release,set-image-tag}.py; k3s/scripts/{sync,build-images,vm-setup,install-gitops}.sh; k3s/scripts/tests/; k3s/argocd/**; k3s/k8s/**; k3s/dashboards/kustomization.yaml; k3s/infra/**; k3s/docker-compose.yaml; k3s/docs/**.
  Acceptance criteria: git diff --check 통과. VM에서 cd ~/kube-study/k3s/apps/api && uv run pytest ../../scripts/tests && uv run pytest && uv run ruff check .; worker도 해당 uv pytest/ruff. node --check k3s/apps/frontend/public/app.js; actionlint .github/workflows/ci.yaml .github/workflows/release.yaml; for script in k3s/scripts/*.sh; do bash -n "$script" || exit; done. 새 위치의 venv는 VM에서 uv sync --frozen으로 재구성하고 기존 venv를 복사하지 않는다. 의존성 설치는 VM만 사용한다. Argo repo-server의 Kustomize 버전과 build options를 조회해 같은 렌더러 설정으로 로컬 작업 트리의 각 옛/새 source.path를 kustomize build한다. 중괄호 인수 하나로 여러 디렉터리를 주지 않고 각 경로를 개별 실행한다. Helm chart는 기존 고정 버전으로 helm template에 실제 대응 values 파일들을 순서대로 전달해 렌더한다. bridge 렌더 리소스와 새 렌더의 GVK/namespace/name 및 PVC/SealedSecret specs 일치. bootstrap spec 차이는 source.path/values 접두사 변경으로 한정한다. prod 수동 정책과 root ignoreDifferences[/operation]/RespectIgnoreDifferences 유지.
  QA happy: selector에 k3s/apps/api 변경을 주면 api만 선택, K3S 소유 workflow 변경이면 네 개, aks/README.md 변경이면 없음. root cwd와 k3s cwd에서 동일 선택. 실제 git diff --name-only fixture 및 최초 전체 이동 diff에서도 누락 없음. Python pytest로 회귀 고정. Evidence: .omo/evidence/k3s-aks-layout/task-2-checks.txt.
  QA failure: 임시 로컬 rsync 목적지에 보존 파일/형제 폴더를 두고 rsync -ani --delete와 구현 필터로 삭제·전송 대상에 비밀/venv/형제 aks가 포함되지 않음을 검증한다. 빈/잘못된 env는 실패해야 한다. 존재하지 않는 values 참조는 로컬 검증에서 실패하며 live에는 적용하지 않는다. bridge Kustomize 보안 제한으로 외부 참조가 거절되면 이 상태로 push하지 않고 해당 entrypoint를 동일 렌더의 임시 사본으로 구성해 다시 검사한다.
  Commit: Y — refactor(layout): move the existing K3S project under k3s. 이동·필수 문서·CI·GitOps 경로·bridge는 하나의 구조 변경 기능이며 분리 시 깨지는 중간 커밋을 만들지 않는다. 검증 후 로컬 commit, push는 작업 4.

- [x] 3. AKS 프로젝트 안내와 전환 로드맵 작성
  Recommended task executor category: writing — 코드 복제 없이 전환 경계와 다음 결정을 문서화.
  What to do / Must NOT do: aks/README.md에 기존 K3S와 비교, 전환 단계와 각 단계 검증을 적고 root README에서 연결한다. 순서: 요구/비용/구독 quota 확인 → IaC/네트워크/ID 설계 → ingress/영속성/시크릿 적응 → GitOps/관측성/HPA·KEDA → 데이터 복원 리허설 → 실험 재수행 → 트래픽 전환과 복구. AKS 기본안은 aks-implementation.md와 aks-cost-baseline.md를 따른다. 실제 구독의 SKU 가용성·quota·정책과 생성 시점의 가격은 A0에서 확인한다. 별도 AKS prod 클러스터는 기본안에 없다.
  플랫폼 항목: Traefik IngressRoute와 GET/HEAD-only S3 경로·presigned URL 유지, local-path에서 CSI PVC 및 node/zone/재연결·백업 설계, GHCR/ACR 선택, SealedSecrets 키/재봉인 또는 Workload Identity/Key Vault 선택, NetworkPolicy DNS/ingress selector 차이, 기존 kube-prometheus-stack 재사용/관리형 관측성 비용. MinIO 예외 만료는 재승인 없이 늘리지 않는다. managed PostgreSQL/Redis/Blob 전환은 클러스터 이전과 별도 결정이다.
  데이터: 이전 완료 기록은 빈 OS Git/키 복구이며 데이터 복원 검증이 아님을 명시. 새 계획에서 실제 데이터량 확인, DB dump/restore, 원본/썸네일 객체 복사, 큐·DB 정합성, 쓰기 중지/재개, 롤백 후 변경 데이터 처리까지 리허설로 검증한다. 현재 데이터 0개라고 가정하지 않는다.
  Closes: GAP-4. Blocked by: 1. Blocks: 4.
  References: k3s/docs/{prd,plan,completion,minio-security}.md; k3s/k8s/base/{application,minio,policy}; k3s/infra/monitoring/values.yaml; Microsoft AKS migration https://learn.microsoft.com/en-us/azure/aks/aks-migration ; CSI https://learn.microsoft.com/en-us/azure/aks/create-volume-azure-disk . 구현 시 해당 리전의 최신 지원 상태/버전 재확인.
  Acceptance criteria: aks/에는 README roadmap만 있으며 구현 완료/배포 가능하다고 표현하지 않는다. E-01~E-15 재적용 매핑, AKS 추가 node/drain/CSI 장애 실험, 비용·격리·접근의 다음 결정이 각각 기재된다.
  QA happy: root README → k3s/README와 aks/README → 기존 요구/실험 링크를 파일 존재 검사와 Markdown 링크 검사로 순회. Evidence: .omo/evidence/k3s-aks-layout/task-3-docs.txt.
  QA failure: 실행 지시 없는 로드맵인지 확인, 실제 API/SKU 가격·지원 설명에는 공식 출처·조회일·실제 구독 검증 여부를 구분한다. CI selector의 aks-only fixture가 empty임을 확인.
  Commit: Y — docs(aks): map the AKS conversion roadmap. 기능별 Lore 사용, 실제 배포 미실행 명시.

- [x] 4. 기존 원격에 게시하고 VM·GitOps 경로를 dev부터 전환
  Recommended task executor category: unspecified-high — 자동 root reconciler와 수동 prod workload 정책의 순서 제어.
  What to do / Must NOT do: 작업 2·3 로컬 commit의 검사 결과를 확인하고 기존 origin main에 정상 push한다. force-push·새 repo 생성 금지. 기존 정책의 main CI는 workflow 수정 때문에 네 이미지 모두 재빌드하고 dev를 자동 승격할 수 있다. 이를 사전 계획대로 관찰하고 기준 digest와 새 dev digest를 구별한다. 기존 이미지와 prod tag는 유지한다.
  VM 경로 준비: 원격 ~/kube-study/k3s를 준비한 뒤 기존 VM-only env 파일은 외부 채널/로그 노출 없이 같은 파일 권한으로 새 상대 위치에 사본을 보존한다. 값 비교는 boolean만 기록한다. 기존 .env가 없어 새 credential 생성으로 진행하는 상황을 차단하며 원본은 삭제하지 않는다. sealing key는 기존 외부 위치에서 사용한다. 이후 새 sync dry-run 확인 후 sync한다. 원격 기존 .git이 있으면 old tracked tree와 rsync --delete가 충돌하지 않도록 git status를 먼저 확인하고 git checkout/pull 경로와 rsync 개발 경로를 일치시킨다.
  GitOps: push 직후 old bootstrap/values/bridge가 기존 root 감시를 계속 만족하는지 확인한다. dev에서 kubectl --context k3s-dev apply -f k3s/argocd/root-dev.yaml로 동일 root 객체의 path를 변경하고 child가 k3s 경로를 사용하도록 확인한다. 새 children을 일괄 수동 apply하지 않는다. dev Ready/smoke 이후 prod root를 동일 방식으로 갱신한다. album-prod의 operation.sync.prune가 신규 실행되지 않도록 기존 root ignoreDifferences와 RespectIgnoreDifferences를 유지하고, root/child를 삭제·재생성하지 않는다. 실제 prod workload sync가 필요한 diff가 생기면 적용 전에 원인을 해결한다. 기능 release는 이 구조 작업에 포함하지 않는다.
  Closes: GAP-2, GAP-3. Blocked by: 2,3. Blocks: 5.
  References: baseline 작업 1; .github/workflows/*.yaml; k3s/argocd/root-*.yaml 및 bootstrap; k3s/scripts/{sync,compose-env,seal-environment}.sh; k3s/docs/{gitops,prod-bootstrap,ci}.md.
  Acceptance criteria: main CI 성공, GHCR 익명 pull 가능, dev 선택 빌드/스캔 후 승격 정상. PR CI에서는 registry 로그인/push/dev 갱신이 skip. root+child 16개 모두 Synced/Healthy이며 경로가 있는 Git source.path 10개는 k3s/ 접두사를 사용한다. Helm의 path 없는 ref: values에는 path를 강제로 추가하지 않는다. valueFiles 8개는 $values/k3s/infra/...이며 외부 차트 source는 불변이다. 실제 live 목록이 예상 개수와 다르면 누락을 먼저 해소한다. prod workload image/PVC UID와 Job/operation 시작 상태가 구조 변경 전후 보존된다. GitOps diff에는 이름 변경·PVC 삭제·예상 밖 prune 없음.
  QA happy: gh run list/view로 실제 main 및 검증 PR 실행 확인, PR은 merge하지 않고 종료한다. kubectl --context k3s-{dev,prod}로 source/status/digest/Jobs/PVC 비교. VM에서 새 cwd로 smoke·관측성 검사 실행. Evidence: .omo/evidence/k3s-aks-layout/task-4-cutover.txt.
  QA failure: renderer/CI 실패 시 old bridges와 baseline prod 유지, 호환 파일을 제거하지 않는다. dev root 전환 실패 시 baseline root path를 복원해 원인을 수정하고 진행한다. 옛 entrypoint bridge는 실제 workload가 동일하도록 작성돼 있어야 하며 이미지 rollback이 필요하면 기존 Git revert+prod 수동 승인 절차를 따른다. live prod에 잘못된 URL·path를 주입하는 실패 실험은 금지.
  Commit: N — source 전환 정의는 작업 2에 이미 게시, live 적용 증거만 기록.

- [x] 5. 이전 경로 호환 파일 제거 및 최종 구조 확정
  Recommended task executor category: quick — 참조가 사라진 임시 파일만 명시적으로 제거.
  What to do / Must NOT do: 작업 1의 옛 entrypoint/Helm values 목록과 live sources를 대조해 소비자가 없는지 확인한 뒤 bridge/bootstrap/values 사본만 제거한다. 경로 전체 rm -rf 대신 git에 추적된 임시 파일 목록으로 제거한다. VM의 옛 env/데이터·키는 이 작업에서 삭제하지 않는다. root .github/README/AGENTS/.gitignore와 k3s/aks 최종 트리를 확인한다.
  Closes: GAP-1, GAP-3. Blocked by: 4. Blocks: 6.
  References: 작업 1 live source inventory, 작업 2 bridge 목록, 작업 4 cutover evidence.
  Acceptance criteria: 이전 경로를 참조하는 live Applications/Helm values가 0개이고 기존 루트 프로젝트 디렉터리의 임시 파일이 없어도 모든 새 entrypoint 렌더 성공. root에서 k3s와 aks는 같은 git rev-parse --show-toplevel를 반환한다.
  QA happy: 각 앱 source를 재조회하고 새 Kustomization/values 파일 존재 및 kustomize build 확인. push 후 Argo refresh에서 manifest generation error 없음. Evidence: .omo/evidence/k3s-aks-layout/task-5-cleanup.txt.
  QA failure: 옛 경로 소비자가 하나라도 있거나 context 확인이 안 되면 제거를 보류하고 작업 4에서 해소한다. 제거 diff에 비호환 파일이 있으면 staged diff에서 제외한다.
  Commit: Y — chore(gitops): remove compatibility paths after the K3S cutover. Lore에 두 환경 live source 확인 근거 포함, 검증 후 같은 origin에 push.

- [x] 6. 기능·Release 계약 확인과 완료 기록 게시
  Recommended task executor category: writing — 실제 검증을 문서와 기능별 이력으로 연결.
  What to do / Must NOT do: 새 VM 작업 경로에서 기존 smoke/관측성 검사 실행, 브라우저 업로드→썸네일→원본 바이트 비교→삭제 확인. 회귀 테스트/CI 근거와 실제 실행 개수 기록. Release helper dry-run 및 기존 script tests로 k3s prod overlay 대상·동일 digest 별칭·수동 Sync 계약 검증, 별도 prod release 배포나 새 v* 태그는 이 구조 작업에서 만들지 않는다. 기존 실험 결과는 삭제/재작성하지 않고 이동 검증 문서를 k3s/docs/layout-migration.md에 추가한다. root README와 기존 운영 문서의 현재 구조가 일치하는지 확인한다.
  Closes: GAP-5. Blocked by: 5. Blocks: F1~F4.
  References: k3s/docs/{completion,ci,gitops,prod-bootstrap}.md; k3s/scripts/{smoke,check-observability,prepare-release}.py; k3s/scripts/tests; .github/workflows/release.yaml.
  Acceptance criteria: 두 환경 기능/관측성 및 source 상태 통과, 새 cwd와 Release staging 경로 검증, 동일 repo 원격 SHA에 기능별 커밋 존재. Graphify update . exit status 기록; 민감 파일을 입력에서 제외, 내용/이름 대신 제외 건수만 보고. 남은 검증 제한은 실제 사유와 함께 기록한다.
  QA happy: VM cd ~/kube-study/k3s에서 docs의 smoke/관측성 명령 및 python3 scripts/prepare-release.py --release v0.0.0 --dry-run을 실행하되 tag/push/실제 registry alias는 생성하지 않는다. 브라우저 접근은 기존 터널을 사용하고 QA 데이터만 정리. Evidence: .omo/evidence/k3s-aks-layout/task-6-acceptance.txt 및 화면 캡처.
  QA failure: dry-run 전후 git diff/registry 변경 없음, QA 삭제 후 테스트 데이터만 제거됐는지 확인. 증거 없는 이전 기록을 이번 PASS로 재사용하지 않는다.
  Commit: Y — docs(layout): record verified K3S directory migration. 실제 Tested/Not-tested·Constraint·Reversibility만 Lore에 넣고 기존 origin으로 push.

## 최종 확인 항목
아래는 한 번의 자체 검토 체크리스트다. 별도 병렬 에이전트·다중 승인 보고서를 의무화하지 않는다. 실패가 없고 증거가 갖춰지면 완료를 보고한다.
- [x] F1. Plan compliance audit
  작업 1~6 및 Must have/NOT를 실제 git diff·원격 SHA와 대조. 근거: .omo/evidence/k3s-aks-layout/f1-compliance.txt.
- [x] F2. Code quality review
  prefix/cwd 혼동, action 입력, rsync 보호, GitOps root/child 정책을 리뷰하고 VM 테스트·lint 결과 확인. 근거: .omo/evidence/k3s-aks-layout/f2-review.txt.
- [x] F3. Real manual QA
  dev/prod 실제 기능과 기존 20개 관측성 패널 표본, 새 경로 개발 루프 및 live source·PVC·prod operation 보존 확인. 근거: .omo/evidence/k3s-aks-layout/f3-runtime.txt.
- [x] F4. Ideal-state fidelity
  아래 IS-1~5를 1:1 증거와 매핑. 실패는 누락 작업으로 환원, 완료로 포장하지 않음. 근거: .omo/evidence/k3s-aks-layout/f4-fidelity.txt.

## Commit strategy
기존 main 직접 커밋 정책을 유지한다. 이동+필수 경로+CI+bridge는 하나의 구조 변경 기능으로 묶어 중간 깨진 상태를 게시하지 않는다. AKS 로드맵, bridge 제거, 완료 증거는 각각 독립 기능 커밋이다. 검사 후 정상 push하며 force-push와 tag 재발행은 하지 않는다. 기능별 비자명 결정에는 lore-commits를 사용한다. 계획 작성만 진행하는 현재 턴에는 커밋하지 않는다.

## Success criteria
| IS | Delivering todo(s) | Proving QA scenario | Evidence |
| --- | --- | --- | --- |
| IS-1 | 2,3,5 | 단일 Git 루트·새 작업 cwd·README 링크 | task-2-checks.txt, task-5-cleanup.txt |
| IS-2 | 2,4,6 | selector 접두사/실제 main·PR CI/GitOps/Release dry-run | task-2-checks.txt, task-4-cutover.txt, task-6-acceptance.txt |
| IS-3 | 1,2,4,5 | PVC·키·prod digest/operation 보존 및 sync 보호 실패 사례 | task-1-baseline.txt, task-4-cutover.txt, task-5-cleanup.txt |
| IS-4 | 3 | aks roadmap와 미확정 owner decision 경계 | task-3-docs.txt |
| IS-5 | 6,F1~F4 | 실제 실행 증거와 origin commit SHA | task-6-acceptance.txt, f1~f4 자료 |
증거 상대 파일명은 모두 .omo/evidence/k3s-aks-layout/ 아래다. 계획 작성 시점에는 제품 QA가 없었으며, 구현 goal에서 실행한 결과만 해당 증거 파일에 기록했다.

## 가벼운 LLM을 위한 작업 방법

1. 한 번에 작업 하나를 맡는다. 해당 카드와 참조 파일만 우선 읽고, 종료 시 `변경 파일 / 실행한 검사 / 미실행 이유 / 다음 작업`을 보고한다.
2. 큰 작업 2는 로컬에서 **2a 파일 이동 → 2b CI/helper 경로 → 2c VM sync 보호 → 2d GitOps 호환 파일 → 2e 전체 렌더·회귀 검사**로 나눈다. 중간 결과는 체크리스트로 남기고, 이 다섯 부분이 맞아야 하나의 구조 변경 커밋으로 게시한다.
3. 작업 4는 **4a push·CI → 4b VM 경로 준비 → 4c dev root → 4d prod root** 순서다. dev가 실패하면 prod로 진행하지 않는다.
4. 코드 탐색은 CodeGraph, 문서·YAML은 파일 도구를 사용한다. 기존 AGENTS.md의 Lore 규칙이 이미 설정되어 있으므로 중복 설정하지 않는다.
5. 테스트를 새 프레임워크로 바꾸지 않는다. 기존 테스트와 변경 위험에 맞는 작은 실패 사례를 사용한다. Graphify 출력 품질은 제품 완료 조건이 아니다.
6. UI·앱 기능·DB 스키마를 이전 때문에 리팩터링하지 않는다. 중첩 Git, shared/ 추출, 범용 deploy 엔진, ApplicationSet, 자동 다중 클러스터 운영 플랫폼은 추가하지 않는다.
7. 비밀 파일/키는 Graphify·로그·커밋에서 제외하며 건수만 보고한다. 이번 확인에서 민감 파일 15개가 감지되어 제외됐다.
8. 미래 제품 문서·스크립트 경로는 계획상 산출물이다. 해당 파일이 아직 없다는 이유로 이번 계획 세션에서 구현하지 않는다.

## CI/CD 격리 계약 — 후속 AKS 구현에도 적용

| 항목 | K3S | AKS |
|---|---|---|
| Git 저장소 | winty5959/kube-study | 동일 |
| 워크플로 | 루트 ci.yaml / release.yaml | 루트 aks-ci.yaml / aks-release.yaml |
| 소스·배포 경로 | k3s/** | aks/** |
| 이미지 | album-{api,worker,frontend,minio} | album-aks-{api,worker,frontend,minio} |
| Git release 태그 | 기존 vMAJOR.MINOR.PATCH | aks-vMAJOR.MINOR.PATCH |
| ArgoCD | 기존 dev/prod 각각 유지 | AKS 안의 1개 ArgoCD |
| prod 의미 | 기존 K3S prod | 같은 AKS의 승격 실습 namespace; 운영 격리 아님 |

- ArgoCD는 저장소 전체가 아니라 repoURL + source.path + destination으로 구분한다. Git 알림 자체는 양쪽에 와도 자기 경로 렌더 결과가 같으면 워크로드 변경이 없어야 한다.
- AKS 앱은 K3S 경로 정리 완료 SHA에서 필요한 파일만 한 번 복사한다. 이후 상호 import/Kustomize 참조를 만들지 않는다. 자동 양방향 복사 도구도 만들지 않는다.
- `.github/workflows/`는 루트에 유지한다. K3S workflow는 AKS 전용 workflow 변경으로 실행/승격하지 않아야 하며 그 반대도 같다.
- Git diff·git add·Docker context는 저장소 루트 기준, helper의 파일 읽기는 프로젝트 루트 기준이다. `defaults.run.working-directory`가 `uses:` action 입력을 바꾼다고 가정하지 않는다.
- manifest 변경은 해당 프로젝트 렌더 검사, README 변경은 빌드/승격 없음. API-only 변경은 해당 프로젝트 api만 빌드한다. scan과 prod 동일 digest 승격은 유지한다.
- cache scope, concurrency, release branch를 프로젝트별로 구분한다. bot main push는 직전 rebase 후 정상 push하며 충돌 시 실패한다. force-push하지 않는다.
- 향후 required check를 지정할 경우 path filter로 영원히 pending이 남지 않게 고정 결과 job 등 작은 해결책을 적용한다. 구조 정리 중 branch protection을 임의 변경하지 않는다.
- 기존 47개 테스트·완료 실험은 과거 증거다. 이번 계획 검증 결과나 AKS 결과로 복사하지 않는다.

## 이번 갱신의 검증 범위

참고 세션 최종 합의, 현재 YAML/CodeGraph 소스, 기존 Lore 결정을 확인했다.
Azure 공식 문서·Retail Prices API는 비용 문서에 출처를 남긴다.
CodeGraph MCP/CLI와 Graphify CLI는 사용 가능하며, 초기 Graphify update는 exit 0이다.
실제 Azure 로그인·구독·SKU quota 조회, 제품 테스트, 배포는 실행하지 않았다.
