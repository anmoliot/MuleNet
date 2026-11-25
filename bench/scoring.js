import http from 'k6/http';
import { check } from 'k6';

const payload = open(__ENV.PAYLOAD);
export const options = {
  stages: [{ duration: '20s', target: 1 }, { duration: '20s', target: 8 }, { duration: '20s', target: 1 }],
  thresholds: { http_req_failed: ['rate==0'] },
};
export default function () {
  const response = http.post(__ENV.SCORE_URL, payload, {
    headers: { Authorization: `Bearer ${__ENV.SERVICE_TOKEN}`, 'Content-Type': 'application/json' },
  });
  check(response, { 'authenticated score returned': r => r.status === 200 });
}
