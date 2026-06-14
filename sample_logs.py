"""Sample log file for testing the incident analysis pipeline."""

SAMPLE_LOGS = """
2024-06-13T10:00:01Z INFO  payment-service [main] Starting service on port 8080
2024-06-13T10:00:05Z INFO  payment-service [main] Connected to PostgreSQL pool (max=20)
2024-06-13T10:02:11Z INFO  api-gateway [req-001] POST /checkout 200 OK 42ms
2024-06-13T10:05:33Z WARN  payment-service [pool] Connection pool utilization at 85% (17/20)
2024-06-13T10:06:01Z ERROR payment-service [pool] Connection pool exhausted! All 20 connections in use
2024-06-13T10:06:01Z ERROR payment-service [req-422] FATAL: remaining connection slots reserved for replication superuser
  at java.sql.DriverManager.getConnection(DriverManager.java:664)
  at com.app.db.PoolManager.acquire(PoolManager.java:112)
  at com.app.service.PaymentService.processPayment(PaymentService.java:87)
2024-06-13T10:06:02Z ERROR api-gateway [req-423] Upstream payment-service timeout after 30000ms
2024-06-13T10:06:03Z ERROR api-gateway [req-424] 502 Bad Gateway - payment-service unavailable
2024-06-13T10:06:04Z ERROR api-gateway [req-425] 502 Bad Gateway - payment-service unavailable
2024-06-13T10:06:10Z WARN  api-gateway [circuit] Circuit breaker OPEN for payment-service
2024-06-13T10:06:15Z ERROR order-service [req-501] Failed to confirm payment: connection refused to payment-service:8080
2024-06-13T10:06:16Z ERROR order-service [req-502] Retry 1/3 failed for payment confirmation
2024-06-13T10:06:18Z ERROR order-service [req-502] Retry 2/3 failed for payment confirmation
2024-06-13T10:06:21Z ERROR order-service [req-502] Retry 3/3 failed for payment confirmation - giving up
2024-06-13T10:06:21Z ERROR order-service [req-502] Order #ORD-99871 stuck in PENDING state
2024-06-13T10:07:00Z WARN  metrics [alert] p99 latency for /checkout spiked to 28000ms (threshold: 2000ms)
2024-06-13T10:07:05Z ERROR pgbouncer [conn] FATAL: max_client_conn=20 reached, refusing connection
2024-06-13T10:07:10Z INFO  ops-alert [pagerduty] Page sent to on-call engineer
""".strip()


if __name__ == "__main__":
    print(SAMPLE_LOGS)
