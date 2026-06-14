"""Seed data: historical incident post-mortems and SOPs for the vector store."""

SEED_DOCUMENTS = [
    {
        "id": "incident-001",
        "title": "2024-01 Database Connection Pool Exhaustion",
        "content": """
Incident: PostgreSQL connection pool exhausted on payment-service.
Symptoms: 502 errors, high latency, connection timeout logs.
Root Cause: Misconfigured pgBouncer max_client_conn=20 under traffic spike.
Resolution:
1. Increased pgBouncer max_client_conn to 200
2. Enabled connection pooling mode=transaction
3. Restarted pgBouncer: sudo systemctl restart pgbouncer
4. Monitored: watch -n1 'psql -c "select count(*) from pg_stat_activity"'
Rollback: Revert pgbouncer.ini to previous version from git
Time to Resolve: 45 minutes
""",
    },
    {
        "id": "incident-002",
        "title": "2024-02 Memory Leak in Node.js API Gateway",
        "content": """
Incident: API gateway OOM killed repeatedly, high memory growth over 6h.
Symptoms: Process RSS growing unbounded, eventual SIGKILL, pod restarts.
Root Cause: Unclosed event listeners accumulating on each request in middleware.
Resolution:
1. Identified leak with: node --expose-gc --inspect app.js
2. Heap snapshot comparison showed listener accumulation
3. Fixed: emitter.removeAllListeners() in request cleanup
4. Deployed hotfix with rolling restart: kubectl rollout restart deploy/api-gateway
5. Set NODE_OPTIONS=--max-old-space-size=512 as guardrail
Rollback: kubectl rollout undo deploy/api-gateway
Time to Resolve: 2 hours
""",
    },
    {
        "id": "incident-003",
        "title": "2024-03 Kafka Consumer Lag Spike",
        "content": """
Incident: Order-processing Kafka consumer lag grew to 500K messages.
Symptoms: Order fulfilment delayed 20+ minutes, lag visible in Kafka UI.
Root Cause: Single-threaded consumer with slow downstream DB writes.
Resolution:
1. Increased consumer partition parallelism: KAFKA_CONCURRENCY=10
2. Enabled batch processing: max.poll.records=500
3. Added async DB write with retry: asyncio.gather(*writes, return_exceptions=True)
4. Rebalanced partitions: kafka-reassign-partitions.sh
Rollback: Reduce KAFKA_CONCURRENCY back to 1, restart consumer group
Time to Resolve: 1.5 hours
""",
    },
    {
        "id": "incident-004",
        "title": "2024-04 Redis Cache Stampede",
        "content": """
Incident: Mass cache miss caused thundering herd hitting database.
Symptoms: DB CPU 100%, Redis hit rate dropped to 2%, latency 10x.
Root Cause: All cache keys expired simultaneously after planned Redis flush.
Resolution:
1. Enable cache lock (mutex) pattern with redis-py: SET lock NX EX 5
2. Implemented probabilistic early expiry (PER algorithm)
3. Added jitter to TTL: ttl = base_ttl + random.randint(0, 300)
4. Warmed cache from DB snapshot before next deploy
Rollback: Temporarily bypass cache with CACHE_ENABLED=false env var
Time to Resolve: 30 minutes
""",
    },
    {
        "id": "incident-005",
        "title": "2024-05 Kubernetes Node NotReady - Disk Pressure",
        "content": """
Incident: 3 worker nodes entered NotReady state due to disk pressure.
Symptoms: Pods evicted, kubectl get nodes shows DiskPressure taint.
Root Cause: Container log rotation disabled, logs filled /var/log.
Resolution:
1. Identify: df -h on nodes via kubectl debug
2. Clear: journalctl --vacuum-size=500M && docker system prune -f
3. Configure log rotation: /etc/logrotate.d/containers
4. Set container log limit in kubelet: --container-log-max-size=50Mi
5. Drain and uncordon: kubectl drain node-X --ignore-daemonsets && kubectl uncordon node-X
Rollback: Not applicable (cleanup operation)
Time to Resolve: 1 hour
""",
    },
    {
        "id": "sop-001",
        "title": "SOP: High CPU on Microservice",
        "content": """
Standard Operating Procedure for High CPU Usage:
1. Identify the process: top -p $(pgrep -f service-name)
2. Take thread dump: kill -3 <PID> or jstack <PID> for JVM
3. Check for infinite loops: look for tight retry loops in logs
4. Profile if needed: py-spy top --pid <PID>
5. Check recent deployments: git log --oneline -10
6. If runaway: kubectl rollout undo deploy/<service>
7. Scale horizontally as temporary mitigation: kubectl scale deploy/<service> --replicas=5
""",
    },
    {
        "id": "sop-002",
        "title": "SOP: Service Unavailable / 503 Errors",
        "content": """
Standard Operating Procedure for 503 Service Unavailable:
1. Check pod health: kubectl get pods -n <namespace>
2. Check endpoints: kubectl get endpoints <service>
3. View recent events: kubectl describe svc <service>
4. Check liveness/readiness probes in pod spec
5. View pod logs: kubectl logs <pod> --previous
6. Check HPA: kubectl get hpa
7. Verify ingress config: kubectl describe ingress <name>
8. Emergency scale-up: kubectl scale deploy/<service> --replicas=10
""",
    },
]
