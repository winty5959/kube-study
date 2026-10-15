# CI와 Release

## 이미지 CI

`.github/workflows/ci.yaml`은 앱·MinIO 빌드 입력·workflow·태그 도구 변경에
반응한다. 네 컴포넌트를 병렬로 lint/test/build/scan하고 PR은 push하지 않는다.
main에서는 HIGH/CRITICAL 0건인 이미지만 GHCR로 push한다. 검사 후 다시
빌드하지 않는다. 네 작업이 모두 성공해야 dev 태그를 컴포넌트별 bot 커밋으로
갱신한다. 이 커밋은 k8s 경로만 바꾸므로 빌드 루프가 생기지 않는다.

2026-10-15 [첫 hosted CI](https://github.com/winty5959/kube-study/actions/runs/38665670846):

| 컴포넌트 | 결과 |
|---|---|
| API | lint/test/build/Trivy/push 성공 |
| worker | lint/test/build/Trivy/push 성공 |
| frontend | JavaScript 확인/build/Trivy/push 성공 |
| MinIO | 빌드 성공, Trivy에서 미수정 upstream 6건으로 실패 |
| dev 갱신 | 전체 성공 조건을 만족하지 않아 skipped |

세 이미지의 `sha-76e5b30` 태그가 public GHCR에 존재한다. MinIO는 새 이미지를
공개하지 않았다. 미수정 6건의 정책 결정은 [MinIO 자료](minio-security.md)를 따른다.
CI에는 클러스터 인증 정보나 VM 자격이 없고 GITHUB_TOKEN만 사용한다.

## Release

`vMAJOR.MINOR.PATCH` tag에서 dev overlay에 기록된 CI sha 태그를 읽는다.
`imagetools create --prefer-index=false`로 같은 manifest에 release alias를 추가한다.
단일 manifest를 새 index로 바꾸지 않으며 원본 digest 주소로 태깅한다.
원본·별칭 manifest의 SHA256이 같아야 prod 변경을 커밋한다. 이미 존재하는
release alias가 다른 digest면 덮어쓰지 않고 실패한다.

컴포넌트별 prod 태그 커밋을 `codex/release-<tag>` 브랜치에 만들고 근거 표가
포함된 PR을 생성한다. PR merge 후 album-prod의 Sync는 수동이다. 15개 태그·승격
단위 테스트, ruff와 actionlint는 VM에서 통과했다. 실제 Release 실행·PR merge와
prod digest 검증은 아직 수행하지 않았다.

VM의 익명 registry 접근으로 API manifest를 읽고 raw SHA256과 registry digest가
같음을 확인했다. `imagetools create --dry-run --prefer-index=false` 결과도 원본의
단일 플랫폼 manifest와 일치했다. dry-run은 registry에 새 태그를 쓰지 않았다.
