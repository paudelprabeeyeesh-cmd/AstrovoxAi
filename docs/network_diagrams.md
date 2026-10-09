# Network Diagrams

## Production Network Topology

```mermaid
flowchart TB
    subgraph Internet
        Users[End Users]
        CDN[Vercel CDN]
    end
    
    subgraph DMZ
        WAF[Cloudflare WAF]
        LB[Load Balancer]
    end
    
    subgraph VPC
        Ingress[Ingress Controller]
        Backend[Backend Pods]
        Frontend[Frontend Pods]
    end
    
    subgraph Data Layer
        PG[(PostgreSQL)]
        Redis[(Redis)]
        S3[S3/R2 Storage]
    end
    
    subgraph Observability
        Prom[Prometheus]
        Graf[Grafana]
        Jaeg[Jaeger]
        Alert[Alertmanager]
    end
    
    Users --> CDN
    CDN --> WAF
    WAF --> LB
    LB --> Ingress
    Ingress --> Backend
    Ingress --> Frontend
    Backend --> PG
    Backend --> Redis
    Backend --> S3
    Backend --> Prom
    Prom --> Graf
    Backend --> Jaeg
    Prom --> Alert
```

## Docker Compose Network (Local Dev)

```mermaid
flowchart TB
    subgraph Host
        Browser[Browser :3000]
        CLI[CLI :8000]
    end
    
    subgraph Docker Network
        Frontend[Frontend :80]
        Backend[Backend :8000]
        Redis[Redis :6379]
        PG[(PostgreSQL :5432)]
        Prom[Prometheus :9090]
        Graf[Grafana :3001]
    end
    
    Browser --> Frontend
    Frontend --> Backend
    CLI --> Backend
    Backend --> Redis
    Backend --> PG
    Prom --> Backend
    Graf --> Prom
```

## Kubernetes Network Policies

```mermaid
flowchart TB
    subgraph Namespace: astrovox
        subgraph Frontend
            FE_Pod[Frontend Pod]
        end
        
        subgraph Backend
            BE_Pod[Backend Pod]
        end
        
        subgraph Data
            PG[(PostgreSQL)]
            Redis[(Redis)]
        end
    end
    
    FE_Pod -->|"Allow: Ingress"| BE_Pod
    BE_Pod -->|"Allow: DB Access"| PG
    BE_Pod -->|"Allow: Cache Access"| Redis
```

## Service Mesh (Optional)

```mermaid
flowchart TB
    subgraph Cluster
        FE[Frontend] -->|mTLS| GW[API Gateway]
        GW -->|mTLS| BE1[Backend Pod 1]
        GW -->|mTLS| BE2[Backend Pod 2]
        BE1 -->|mTLS| PG[(PostgreSQL)]
        BE2 -->|mTLS| PG
    end
    
    subgraph Control Plane
        Istiod[Istiod]
        Jaeger[Jaeger]
    end
    
    Istiod --> FE
    Istiod --> GW
    Istiod --> BE1
    Istiod --> BE2
    BE1 --> Jaeger
    BE2 --> Jaeger
```

## Multi-Region Architecture

```mermaid
flowchart TB
    subgraph Region: us-east-1
        CDN1[CDN]
        LB1[Load Balancer]
        BE1[Backend]
        PG1[(PostgreSQL Primary)]
        Redis1[(Redis)]
    end
    
    subgraph Region: eu-west-1
        CDN2[CDN]
        LB2[Load Balancer]
        BE2[Backend]
        PG2[(PostgreSQL Replica)]
        Redis2[(Redis)]
    end
    
    subgraph Global
        DNS[Global DNS]
        Monitor[Cross-Region Monitor]
    end
    
    DNS --> CDN1
    DNS --> CDN2
    LB1 --> BE1
    LB2 --> BE2
    BE1 --> PG1
    BE2 --> PG2
    PG1 -->|"Streaming Replication"| PG2
    Monitor --> LB1
    Monitor --> LB2
```

## WebSocket Connection Flow

```mermaid
flowchart TB
    Client[Client] -->|"wss://api.astrovox.ai/ws/chat/{id}"| WAF[WAF]
    WAF --> LB[Load Balancer]
    LB --> WS[WebSocket Router]
    WS --> BE[Backend Worker]
    BE --> Redis[(Redis Pub/Sub)]
    Redis --> BE2[Backend Worker 2]
    BE --> Client
```

## External Integrations

```mermaid
flowchart TB
    subgraph AstrovoxAI
        BE[Backend]
    end
    
    subgraph External Services
        OpenAI[OpenAI API]
        Anthropic[Anthropic API]
        Google[Google AI]
        Groq[Groq API]
        Ollama[Ollama]
        Stripe[Stripe]
        Email[SendGrid]
        S3[S3/R2]
    end
    
    BE --> OpenAI
    BE --> Anthropic
    BE --> Google
    BE --> Groq
    BE --> Ollama
    BE --> Stripe
    BE --> Email
    BE --> S3
```
