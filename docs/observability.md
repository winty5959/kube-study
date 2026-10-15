# 관측성 운영과 검증

VM에서 `scripts/install-monitoring.sh dev`를 실행한다. kube-prometheus-stack
92.7.0에 Prometheus, Alertmanager, Grafana, node-exporter, kube-state-metrics를
설치한다. K3S 내장 제어 평면의 별도 scrape endpoint는 비활성화한다.
데이터는 local-path PVC에 저장하며 Prometheus 보존 기간은 2일이다.

Grafana 관리자 계정은 VM에서 생성한 monitoring/grafana-admin Secret을
사용한다. 비밀번호와 평문 Secret은 Git에 저장하지 않는다. SSH 터널을 통해
grafana.dev.local에 접근한다.

`dashboards/`의 JSON 5개는 sidecar가 ConfigMap에서 자동으로 읽는다.
서비스 개요, 큐와 worker 수, API CPU와 replica 수, Pod 리소스와 재시작,
썸네일 처리 시간을 표시한다. API와 worker는 ServiceMonitor로 15초마다 수집한다.
필수 알림은 큐 100 초과 5분, API 5xx 비율 5% 초과 2분,
CrashLoopBackOff 1분이다.

2026-10-15 dev VM에서 `uv run --python 3.13 scripts/check-observability.py dev`가
종료 코드 0으로 완료됐다. Grafana API로 5개 대시보드의 등록을 확인하고
20개 패널의 모든 PromQL 대상에서 유한한 실제 표본을 확인했다.
Prometheus API로 필수 알림 3개의 등록도 확인했다. 업로드부터 삭제까지
smoke 검증이 통과했다. UI 스크린샷과 부하 중 시계열 증거는 실험 단계에서
추가한다. 알림 등록 검증만으로 실제 발화를 주장하지 않는다.

같은 날 Grafana 웹 UI에서 실제 시계열과 범례를 확인했다. API CPU와
replica 수, 큐와 worker 수는 replica 축을 오른쪽에 분리했다. 화면 증거는
`docs/experiments/screenshots/`에 저장한다. 맥북 DNS 설정이 없을 때에는
VM의 Grafana Service port-forward를 SSH `localhost:19001` 터널로 연결한다.
브라우저 로그인 전에 생성된 관리자 비밀번호의 끝 줄바꿈을 제거하고
Grafana DB와 Secret을 함께 정규화했다. 새 설치에서는 줄바꿈 없이 생성한다.

스크린샷 저장 과정에서 full-page capture가 Grafana canvas를 resize해
그리기 전 화면을 저장하는 문제를 확인했다. viewport capture로 교체했고,
E-01~E-10·E-12·E-15는 각 실험 시간의 보존된 Prometheus 시계열을 표시해
다시 저장했다. 실험이나 부하를 재현한 것으로 취급하지 않고 기존 실제
측정 데이터의 표시를 바로잡았다. M4 UI 그림은 현재 시계열로 확인한다.
