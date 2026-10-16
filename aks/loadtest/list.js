import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 200 },
    { duration: __ENV.DURATION || '3m', target: 200 },
    { duration: '10s', target: 0 },
  ],
  thresholds: { http_req_failed: ['rate<0.01'], checks: ['rate>0.99'] },
};

export default function () {
  const hostHeader = __ENV.HOST_HEADER;
  const params = hostHeader ? { headers: { Host: hostHeader } } : {};
  const response = http.get(`${__ENV.BASE_URL || 'http://album.aks.localhost'}/api/photos`, params);
  check(response, { 'list returns 200': (r) => r.status === 200 });
}
