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
