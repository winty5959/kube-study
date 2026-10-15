# 운영 구성

## 워크로드 권한

API, worker, frontend, PostgreSQL, Redis, MinIO, migration, cleanup은 각각
별도 ServiceAccount를 사용한다. 애플리케이션이 Kubernetes API를 호출하지
않으므로 RoleBinding을 부여하지 않고 토큰 자동 마운트를 비활성화한다.
환경 변수와 볼륨으로 지정한 Secret은 kubelet이 전달하므로 Pod 자체에
Secret 조회 권한을 줄 필요가 없다.

2026-10-15 dev에서 8개 ServiceAccount 모두 `get secrets` 권한이 없음을
`kubectl auth can-i --as=...`로 확인했다. 실행 중인 모든 앨범 Pod의 projected
volume에 ServiceAccount token이 없었고, 데이터 StatefulSet 3개의 변경
rollout과 migration Job도 성공했다.

## 배포와 종료

API·frontend·worker는 maxUnavailable=0, maxSurge=1로 교체한다.
API와 frontend는 preStop 10초 후 종료하고 유예 시간은 45초다.
worker는 SIGTERM 후 현재 작업을 마치며 종료 유예 60초를 사용한다.
PDB는 API·frontend 각각 minAvailable=1이다. 단일 replica API의 자발적
eviction을 막을 수 있지만 강제 Pod 삭제나 노드 장애를 막지는 않는다.

E-01에서 API 대체 Pod는 약 4초 만에 준비됐고 354건 조회가 모두 성공했다.
E-04의 첫 실행은 504 한 건으로 실패했다. 종료 대기 추가 후 재실행은
353건 모두 성공했고 v1·v2 응답이 교체 구간에서 함께 관측됐다.

## 객체 다운로드 경로

공개 `/originals/`, `/thumbnails/`는 Traefik IngressRoute가 GET·HEAD만
MinIO로 전달한다. 업로드와 삭제는 API가 내부 MinIO Service에 서명해 수행한다.
Host 헤더는 그대로 전달되어 presigned SigV4 검증이 유지된다.
공개 객체 경로의 PUT은 HTTP 405였고 전체 사진 smoke는 통과했다.
