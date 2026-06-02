import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.REPOMIND_BASE_URL || "http://localhost:8000";
const API_KEY = __ENV.REPOMIND_API_KEY || "";
const REPO_ID = __ENV.REPOMIND_REPO_ID || "";

export const options = {
  scenarios: {
    authentication: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "1m",
      exec: "authentication",
    },
    repository_reads: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "1m",
      exec: "repositoryReads",
    },
    intelligence_reads: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 10),
      duration: __ENV.DURATION || "1m",
      exec: "intelligenceReads",
      startTime: "5s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

function headers() {
  return API_KEY ? { headers: { "x-api-key": API_KEY } } : {};
}

export function authentication() {
  const res = http.get(`${BASE_URL}/config`, headers());
  check(res, { "config authorized": (r) => r.status === 200 });
  sleep(1);
}

export function repositoryReads() {
  const res = http.get(`${BASE_URL}/repositories`, headers());
  check(res, { "repositories listed": (r) => r.status === 200 });
  sleep(1);
}

export function intelligenceReads() {
  if (!REPO_ID) {
    sleep(1);
    return;
  }
  const status = http.get(`${BASE_URL}/repositories/${REPO_ID}/status`, headers());
  const reports = http.get(`${BASE_URL}/repositories/${REPO_ID}/reports`, headers());
  const portfolio = http.get(`${BASE_URL}/repositories/intelligence`, headers());
  check(status, { "status available": (r) => r.status === 200 });
  check(reports, { "reports available": (r) => r.status === 200 });
  check(portfolio, { "portfolio available": (r) => r.status === 200 });
  sleep(1);
}
