# CTO Interview — 100 Architecture Questions

## Architecture & Design

1. Why did you choose FastAPI over Flask or Django?
2. Why PostgreSQL with pgvector instead of Pinecone or Weaviate?
3. Why Redis for caching instead of Memcached?
4. Why Neo4j for GraphRAG instead of a relational graph extension?
5. Why Next.js 16 over React SPA?
6. Why WebSockets for streaming instead of Server-Sent Events?
7. Why raw SQL instead of an ORM like SQLAlchemy?
8. Why not use Kubernetes from day one?
9. Why multiple LLM adapters instead of one provider?
10. Why circuit breakers around every external dependency?

## Scalability

11. How would you scale from 100 to 10,000 concurrent users?
12. What is your current bottleneck?
13. How do you handle hot partitions in PostgreSQL?
14. How would you implement connection pooling for 1000 concurrent requests?
15. What is your strategy for read replicas?
16. How do you handle cache invalidation at scale?
17. What is your approach to database sharding?
18. How would you implement rate limiting for 1M users?
19. What is your CDN strategy for static assets?
20. How do you prevent thundering herd on cache expiry?

## Security

21. How do you store JWT secrets securely?
22. Why refresh tokens instead of just access tokens?
23. How do you prevent SQL injection?
24. How do you handle prompt injection attacks?
25. What is your secret rotation strategy?
26. How do you audit privileged actions?
27. How do you prevent IDOR vulnerabilities?
28. What is your approach to CORS?
29. How do you secure WebSocket connections?
30. How do you handle PII in logs?

## AI Engineering

31. How do you evaluate LLM response quality?
32. What metrics do you track for RAG performance?
33. How do you detect hallucinations?
34. What is your context window management strategy?
35. How do you handle multi-modal inputs?
36. What is your approach to agent orchestration?
37. How do you prevent infinite agent loops?
38. How do you handle tool failures in agent workflows?
39. What is your strategy for embedding drift?
40. How do you benchmark different LLM providers?

## Reliability

41. What is your RTO and RPO?
42. How do you handle database failover?
43. What is your backup strategy?
44. How do you test disaster recovery?
45. How do you handle partial outages?
46. What is your approach to graceful degradation?
47. How do you prevent cascading failures?
48. What is your retry strategy for external APIs?
49. How do you handle message duplication?
50. What is your approach to eventual consistency?

## Observability

51. How do you trace a request across services?
52. What metrics do you collect?
53. How do you correlate logs across services?
54. How do you set up alerts?
55. What is your dashboard strategy?
56. How do you debug production issues?
57. How do you measure latency percentiles?
58. What is your approach to error budgeting?
59. How do you track cost per request?
60. How do you monitor LLM provider health?

## Data

61. How do you handle schema migrations?
62. What is your data validation strategy?
63. How do you handle data deletion requests?
64. What is your approach to data encryption?
65. How do you handle GDPR requests?
66. What is your data retention policy?
67. How do you handle PII in vector embeddings?
68. What is your approach to data lineage?
69. How do you handle data backups?
70. How do you test database migrations?

## Performance

71. How do you measure API latency?
72. What is your target p99 latency?
73. How do you optimize database queries?
74. What is your caching strategy?
75. How do you handle large file uploads?
76. What is your approach to connection pooling?
77. How do you optimize LLM token usage?
78. What is your strategy for batch processing?
79. How do you handle concurrent WebSocket connections?
80. How do you profile production systems?

## Testing

81. How do you test AI features?
82. What is your test coverage target?
83. How do you test WebSocket endpoints?
84. How do you test streaming responses?
85. How do you test LLM integrations?
86. What is your approach to contract testing?
87. How do you test security features?
88. How do you test performance?
89. What is your CI/CD pipeline?
90. How do you test database migrations?

## Operations

91. How do you deploy to production?
92. What is your rollback strategy?
93. How do you handle secrets in CI/CD?
94. How do you manage infrastructure as code?
95. What is your approach to blue-green deployments?
96. How do you handle configuration management?
97. How do you manage feature flags?
98. How do you handle A/B testing?
99. How do you manage dependencies?
100. How do you handle technical debt?
