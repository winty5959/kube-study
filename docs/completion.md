# 개발 계획 완료 검증

2026-10-15 기준 M0~M9와 E-01~E-15를 완료했다. PRD 원문은 수정하지 않았다.

## PRD 완료 기준

| 기준 | 실제 검증과 근거 |
|---|---|
| 실험 15개 수행·기록 | [E-01~E-15 기록](experiments/README.md). 최초 실패와 수정 후 결과를 각 실험에 보존했다. |
| 빈 prod에서 세 단계 복구 | Azure OS reimage 직후 일곱 도구 부재 확인. 소스·외부 봉인 키 준비 후 K3S 설치, GitOps 설치, root apply 세 명령으로 앱과 모니터링 복구. [prod 기록](prod-bootstrap.md) |
| 코드 push부터 prod까지 GitOps 배포 | [E-11](experiments/E-11.md) 자동 dev 배포 5분 18초. [E-13](experiments/E-13.md) 승인된 PR #1 merge·수동 Sync·네 실제 imageID 일치. 직접 Deployment apply 없이 반영했다. 초기 root bootstrap과 PRD의 E-12·E-14 실험 개입은 별도다. |
| 양쪽 Grafana 1~5 실제 데이터 | dev·prod 각각 두 차례 최종 smoke 후 20개 패널 모두 finite 표본, 필수 알림 3개 로드 확인. [관측성](observability.md), [새 OS prod 화면](prod-bootstrap.md#재현-범위) |

## 개발·운영 검증

- M3: 헬스·readiness, 자원 제한, migration·cleanup, 처리 lease 복구를 구현했다. [E-07](experiments/E-07.md)·[E-08](experiments/E-08.md).
- M4~M5: 다섯 대시보드와 알림, HPA CPU 60%, KEDA worker scale-to-zero를 구현했다. [E-02](experiments/E-02.md) 41,809/41,809 조회 성공, [E-03](experiments/E-03.md) 500장 DONE·worker 0→2→0.
- M6: PDB eviction 거절, default-deny NetworkPolicy, 개별 ServiceAccount, 롤링 전략을 검증했다. E-01·E-04~E-10에 장애·복구 결과가 있다.
- M7~M8: 변경된 앱만 빌드하고 네 이미지 보안 검사 후 GHCR와 dev 태그를 갱신한다. 실제 PR CI도 통과했고 로그인·push·dev 갱신은 skipped였다. [CI](ci.md), [GitOps](gitops.md), E-11·E-12·E-15.
- M9: 승인된 Release PR 승격·네 digest 비교, rollout undo 대조, 컴포넌트별 Git revert와 수동 Sync를 통과했다. E-13·E-14와 빈 OS 복구 기록을 보관했다.

최종 양쪽 런타임 검사에서 일곱 앱 컨테이너의 non-root·read-only·CPU/메모리
requests/limits, 효과적인 ServiceAccount 토큰 비활성화, 상주 컨테이너 probes를 확인했다.
HPA dev 1~3/prod 2~6, KEDA dev 0~2/prod 0~5, local-path PVC 1/2/10Gi Bound와
앱 namespace RoleBinding 부재도 확인했다. 양쪽 root와 일곱 child, 총 16개
Application은 Synced·Healthy다.

빈 OS prod에서 실제 브라우저로 JPEG·PNG·WebP 28장 업로드, 24+4 페이지 이동,
DONE 상세·800×400 medium·처리 Pod 표시, 원본 다운로드 12,028바이트 정확한 일치,
UI 삭제를 확인했다. 자체 검증 자료만 정리한 뒤 prod 사진과 S3 원본·썸네일은 0개였다.
[업로드 접수 화면](experiments/screenshots/final-ui-gallery.png),
[상세 화면](experiments/screenshots/final-ui-detail.png).

VM에서 API 12개·worker 8개·scripts 27개, 총 47개 테스트와 ruff·actionlint가 통과했다.
Mac에 개발용 venv를 만들지 않았다. API 테스트의 기존 Starlette/httpx 경고는 숨기지 않았다.
기능별 Lore 커밋과 문서·스크린샷을 남겼고 Graphify update는 exit 0으로 완료했다.

## 최종 상태와 운영 한계

- dev API는 sha-f9fd24a, 나머지 세 이미지는 sha-72655e4다. prod 네 이미지는
  E-14 공식 롤백 결과 sha-a3e8669로 Git과 일치한다. dev·prod 차이는 의도된 실험 결과다.
- prod는 순수 수동 Sync다. rollout undo는 OutOfSync로 남다가 다음 수동 Sync에서
  Git 상태로 덮어쓰인다. PRD의 수동 Sync/selfHeal 병기 해석은 [계획](plan.md)에 기록했다.
- 사용자 승인에 따라 MinIO binary의 지정된 6건만 2026-11-14까지 예외다.
  만료일·잘못된 binary 경로 대조 검사는 모두 원래 6건으로 실패했다. 다른 HIGH/CRITICAL은
  승격을 차단한다. [보안 결정](minio-security.md).
- 단일 노드 local-path는 노드 장애 시 데이터 보호를 제공하지 않는다. 이번 복구는
  Git 상태와 외부 봉인 키 복원이며 기존 PVC 데이터 복구를 검증한 것은 아니다.
  HA·Longhorn·Loki 등 PRD 확장 과제는 이번 개발 계획 범위 밖이다.
