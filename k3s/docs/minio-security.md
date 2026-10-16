# MinIO CI 보안 결정 자료

계획서는 마지막 공개 MinIO 릴리스를 유지하기로 결정했고, M7 HIGH 검사에서
걸리면 예외 또는 다른 S3 구현을 다시 결정하도록 정했다. 원본 이미지의
HIGH/CRITICAL 49건 중 외부 Go 모듈과 Go 표준 라이브러리는 수정 버전으로
갱신했다. 최종 스캔은 외부 의존성 HIGH/CRITICAL 0건, MinIO 자체 6건이었다. MinIO 자체 아래 6건은 Trivy가 수정 버전을 제시하지 않는다.

| ID | 수준 | 영향 기능 |
|---|---|---|
| [CVE-2026-33322](https://avd.aquasec.com/nvd/cve-2026-33322) | CRITICAL | OIDC JWT 알고리즘 혼동 |
| [CVE-2026-33419](https://avd.aquasec.com/nvd/cve-2026-33419) | CRITICAL | LDAP 계정 열거와 로그인 제한 부재 |
| [CVE-2026-34204](https://avd.aquasec.com/nvd/cve-2026-34204) | HIGH | replication 헤더의 SSE metadata 주입 |
| [CVE-2026-39414](https://avd.aquasec.com/nvd/cve-2026-39414) | HIGH | S3 Select CSV의 메모리 할당 DoS |
| [CVE-2026-40344](https://avd.aquasec.com/nvd/cve-2026-40344) | HIGH | unsigned trailer의 signature 검증 우회 |
| [CVE-2026-41145](https://avd.aquasec.com/nvd/cve-2026-41145) | HIGH | query credential·unsigned trailer signature 우회 |

## 적용한 경로 제한

- MinIO console과 admin API는 Ingress에 공개하지 않는다.
- OIDC와 LDAP는 구성하지 않는다.
- 외부 객체 경로는 Traefik IngressRoute에서 GET·HEAD만 MinIO로 전달한다.
  PUT `/originals/method-policy-probe`는 frontend에서 405로 거절됐다.
- 클러스터 내부 S3 쓰기는 NetworkPolicy가 허용한 API·worker·cleanup만 사용한다.
  클라이언트의 인증 헤더를 S3로 전달하지 않고 SDK가 서버 자격으로 서명한다.
- VM NSG는 작업 PC의 SSH만 허용하며 HTTP는 SSH 터널로 접근한다.

이 제한은 MinIO 소스 취약점을 수정한 것이 아니다. 허용된 서버 Pod가
침해되면 S3 서비스에 접근할 수 있으며 그 잔여 위험이 남는다.

## 승인된 기간 제한 예외 (2026-10-15)

사용자가 MinIO 유지와 위 6건의 기간 제한 예외를 승인했다. 예외 만료일은
2026-11-14이며 `infra/minio/trivyignore.yaml`의 `usr/bin/minio` 경로에만
적용한다. 다른 HIGH/CRITICAL은 수정 버전 유무와 관계없이 계속 실패시킨다.
API·worker·frontend에는 이 예외 파일을 적용하지 않는다. 만료 후에는 MinIO
검사가 다시 실패하므로 보안 상태와 유지 결정을 재검토해야 한다.

VM에서 동일 이미지에 과거 만료일을 넣은 임시 YAML과 다른 binary 경로를 넣은
임시 YAML로 검사했다. 두 경우 모두 정확히 위 6건이 다시 검출돼 exit 1이었다.
정상 승인 파일은 exit 0, 예외 없는 strict 재검사도 6건·exit 1이었다.

## 고정된 외부 의존성 검증

Go 1.27.2와 Alpine 3.24를 사용하고, 갱신된 `go.mod`·`go.sum`을 저장소에
고정했다. `-mod=readonly` 빌드가 성공했으며 다시 검사해 외부 HIGH/CRITICAL
0건과 위 upstream 6건만 확인했다. 공개하지 않은 별도 컨테이너를 VM loopback에
잠시 띄워 bucket 생성, 18 MiB multipart PUT, HEAD 크기, GET 바이트 일치,
객체·bucket 삭제를 검증하고 컨테이너를 제거했다. 기존 사용자 데이터는 사용하지
않았다. 이 검증은 보안 예외 승인이나 CI gate 통과를 의미하지 않는다.
