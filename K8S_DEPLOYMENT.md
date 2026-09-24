# Kubernetes Deployment Guide

## Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or local with minikube/kind)
- `kubectl` configured with cluster access
- `helm` v3+ installed
- Ingress controller (nginx-ingress) installed
- cert-manager installed (for TLS certificates)
- External Secrets Operator or sealed-secrets (for secrets management)

## Quick Start

### 1. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 2. Create Secrets

```bash
kubectl create secret generic astrovox-secrets \
  --namespace=astrovox \
  --from-literal=DATABASE_URL=postgresql://user:pass@host:5432/astrovox \
  --from-literal=REDIS_URL=redis://redis:6379 \
  --from-literal=REDIS_PASSWORD=your-redis-password \
  --from-literal=NEO4J_URI=bolt://neo4j:7687 \
  --from-literal=NEO4J_USER=neo4j \
  --from-literal=NEO4J_PASSWORD=your-neo4j-password \
  --from-literal=JAEGER_URL=http://jaeger:14268/api/traces \
  --from-literal=OPENAI_API_KEY=your-openai-key \
  --from-literal=ANTHROPIC_API_KEY=your-anthropic-key \
  --from-literal=GOOGLE_GENERATIVEAI_API_KEY=your-google-key \
  --from-literal=JWT_SECRET_KEY=your-jwt-secret \
  --from-literal=POSTGRES_PASSWORD=your-postgres-password \
  --from-literal=STRIPE_SECRET_KEY=your-stripe-key \
  --from-literal=STRIPE_WEBHOOK_SECRET=your-webhook-secret \
  --dry-run=client -o yaml | kubectl apply -f -
```

### 3. Deploy with Helm

```bash
helm repo add astrovox https://charts.astrovox.ai
helm install astrovox ./helm \
  --namespace astrovox \
  --create-namespace \
  --set image.tag=latest \
  --set secret.data.DATABASE_URL=postgresql://user:pass@host:5432/astrovox
```

### 4. Or Deploy with kubectl

```bash
kubectl apply -f k8s/
```

### 5. Verify Deployment

```bash
kubectl get pods -n astrovox
kubectl get services -n astrovox
kubectl get ingress -n astrovox
kubectl get hpa -n astrovox
```

### 6. Access the Application

```bash
# Port forward for local access
kubectl port-forward service/astrovox-backend 8000:8000 -n astrovox
kubectl port-forward service/astrovox-frontend 8080:80 -n astrovox

# Test
curl http://localhost:8000/health
curl http://localhost:8080/health
```

## Configuration

### Environment Variables

See `.env.example` for the complete list of environment variables.

### Resource Limits

Default resource limits are set in `values.yaml` for Helm and in individual manifests for kubectl.

### Autoscaling

Horizontal Pod Autoscaler is configured in `k8s/hpa.yaml` with:
- Min replicas: 3
- Max replicas: 10
- CPU target: 70%
- Memory target: 80%

### Ingress

Update the host in `k8s/ingress.yaml` or `values.yaml` to match your domain.

```yaml
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: astrovox-tls
  rules:
  - host: api.yourdomain.com
```

## Monitoring

### Prometheus

Prometheus is configured to scrape metrics from the backend at `/metrics`.

### Grafana

Import the dashboard from `monitoring/grafana-dashboard.json`.

### Alerts

Alert rules are defined in `monitoring/alerts.yml`.

## Troubleshooting

### Pods not starting

```bash
kubectl describe pod <pod-name> -n astrovox
kubectl logs <pod-name> -n astrovox
```

### Image pull errors

```bash
kubectl get events -n astrovox
kubectl describe pod <pod-name> -n astrovox | grep -A 10 "Events"
```

### Health check failures

```bash
kubectl exec -it <pod-name> -n astrovox -- curl -f http://localhost:8000/health
```

## Rollback

```bash
# Rollback deployment
kubectl rollout undo deployment/astrovox-backend -n astrovox

# Check rollout status
kubectl rollout status deployment/astrovox-backend -n astrovox
```

## Scaling

```bash
# Scale manually
kubectl scale deployment/astrovox-backend -n astrovox --replicas=5

# Check HPA
kubectl get hpa -n astrovox
```
