# AstrovoxAi Helm Chart

This chart provides a production-ready deployment of AstrovoxAi - an AI-powered automation platform.

## Prerequisites

- Kubernetes 1.16+
- Helm 3.0+
- PV provisioner support in the underlying infrastructure

## Installing the Chart

To install the chart with the release name `my-release`:

```bash
helm install my-release ./astrovoxai
```

To install with a custom namespace:

```bash
helm install my-release ./astrovoxai --namespace astrovoxai --create-namespace
```

## Configuration

The following tables lists the configurable parameters of the AstrovoxAi chart and their default values.

### Backend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of backend replicas | `2` |
| `image.repository` | Backend image repository | `astrovoxai/backend` |
| `image.tag` | Backend image tag | `appVersion` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `service.type` | Backend service type | `ClusterIP` |
| `service.port` | Backend service port | `80` |
| `resources.limits` | Resource limits | `cpu: 1000m, memory: 1024Mi` |
| `resources.requests` | Resource requests | `cpu: 500m, memory: 512Mi` |
| `autoscaling.enabled` | Enable HPA | `false` |
| `autoscaling.minReplicas` | Minimum replicas | `1` |
| `autoscaling.maxReplicas` | Maximum replicas | `10` |
| `autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `80` |

### Frontend Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `frontend.replicaCount` | Number of frontend replicas | `2` |
| `frontend.image.repository` | Frontend image repository | `astrovoxai/frontend` |
| `frontend.image.tag` | Frontend image tag | `appVersion` |
| `frontend.image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `frontend.service.type` | Frontend service type | `ClusterIP` |
| `frontend.service.port` | Frontend service port | `80` |
| `frontend.resources.limits` | Resource limits | `cpu: 500m, memory: 256Mi` |
| `frontend.resources.requests` | Resource requests | `cpu: 250m, memory: 128Mi` |
| `frontend.autoscaling.enabled` | Enable HPA | `false` |
| `frontend.autoscaling.minReplicas` | Minimum replicas | `1` |
| `frontend.autoscaling.maxReplicas` | Maximum replicas | `10` |
| `frontend.autoscaling.targetCPUUtilizationPercentage` | Target CPU utilization | `80` |

### AstrovoxAi Application Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `astrovoxai.app.name` | Application name | `AstrovoxAi` |
| `astrovoxai.app.version` | Application version | `1.0.0` |
| `astrovoxai.app.debug` | Enable debug mode | `false` |
| `astrovoxai.server.host` | Server host | `0.0.0.0` |
| `astrovoxai.server.port` | Server port | `8000` |
| `astrovoxai.server.workers` | Number of worker processes | `4` |
| `astrovoxai.database.url` | Database connection URL | `` |
| `astrovoxai.database.pool_size` | Database pool size | `10` |
| `astrovoxai.redis.url` | Redis connection URL | `` |
| `astrovoxai.supabase.url` | Supabase project URL | `` |
| `astrovoxai.supabase.anon_key` | Supabase anon key | `` |
| `astrovoxai.supabase.service_role_key` | Supabase service role key | `` |
| `astrovoxai.openai.api_key` | OpenAI API key | `` |
| `astrovoxai.anthropic.api_key` | Anthropic API key | `` |
| `astrovoxai.google.api_key` | Google AI API key | `` |
| `astrovoxai.features.enable_websocket` | Enable WebSocket support | `true` |
| `astrovoxai.features.enable_file_upload` | Enable file upload | `true` |
| `astrovoxai.features.enable_email` | Enable email functionality | `true` |
| `astrovoxai.features.enable_webhooks` | Enable webhook support | `true` |
| `astrovoxai.rate_limit.enabled` | Enable rate limiting | `true` |
| `astrovoxai.rate_limit.default` | Default rate limit | `120/minute` |
| `astrovoxai.rate_limit.auth` | Auth endpoint rate limit | `5/minute` |
| `astrovoxai.monitoring.enabled` | Enable monitoring | `true` |
| `astrovoxai.monitoring.prometheus_port` | Prometheus metrics port | `9090` |
| `astrovoxai.monitoring.metrics_endpoint` | Metrics endpoint | `/metrics` |
| `astrovoxai.logging.level` | Log level | `INFO` |
| `astrovoxai.logging.format` | Log format | `json` |
| `astrovoxai.security.jwt_secret` | JWT secret key | `` |
| `astrovoxai.security.jwt_expiration_hours` | JWT expiration hours | `24` |
| `astrovoxai.security.bcrypt_rounds` | Bcrypt rounds | `12` |
| `astrovoxai.storage.type` | Storage type (local/s3/gcs) | `local` |
| `astrovoxai.storage.local_path` | Local storage path | `./storage` |
| `astrovoxai.storage.bucket` | S3/GCS bucket name | `` |
| `astrovoxai.storage.region` | S3/GCS region | `` |
| `astrovoxai.storage.access_key_id` | S3/GCS access key ID | `` |
| `astrovoxai.storage.secret_access_key` | S3/GCS secret access key | `` |

### Ingress Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `ingress.enabled` | Enable ingress controller | `false` |
| `ingress.className` | Ingress class name | `` |
| `ingress.annotations` | Ingress annotations | `{}` |
| `ingress.hosts[0].host` | Backend hostname | `astrovoxai.example.com` |
| `ingress.hosts[0].paths[0].path` | Backend path | `/` |
| `ingress.hosts[0].paths[0].pathType` | Backend path type | `Prefix` |
| `ingress.tls` | TLS configuration | `[]` |
| `frontend.ingress.enabled` | Enable frontend ingress | `false` |
| `frontend.ingress.className` | Frontend ingress class name | `` |
| `frontend.ingress.annotations` | Frontend ingress annotations | `{}` |
| `frontend.ingress.hosts[0].host` | Frontend hostname | `frontend.astrovoxai.example.com` |
| `frontend.ingress.hosts[0].paths[0].path` | Frontend path | `/` |
| `frontend.ingress.hosts[0].paths[0].pathType` | Frontend path type | `Prefix` |
| `frontend.ingress.tls` | Frontend TLS configuration | `[]` |

## Specifying Image Pull Secrets

If your Kubernetes cluster requires image pull secrets to pull images from a private registry, you can specify them as follows:

```bash
helm install my-release ./astrovoxai \
    --set imagePullSecrets[0].name=myregistrykey
```

## Persistence

The chart uses an emptyDir volume for temporary storage by default. For persistent storage, you can configure a PersistentVolumeClaim:

```bash
helm install my-release ./astrovoxai \
    --set backend.persistence.enabled=true \
    --set backend.persistence.size=10Gi
```

## Upgrading the Chart

To upgrade the chart with the release name `my-release`:

```bash
helm upgrade my-release ./astrovoxai
```

## Uninstalling the Chart

To uninstall the chart with the release name `my-release`:

```bash
helm uninstall my-release
```

## Configuration and Installation Details

[Read through the values.yaml file](https://github.com/your-org/astrovoxai/blob/main/charts/astrovoxai/values.yaml) for a comprehensive overview of the available configurations.

## Maintainers

| Name | Email | URL |
|------|-------|-----|
| AstrovoxAi Team | dev@astrovoxai.com | https://github.com/your-org/astrovoxai |

## License

This chart is licensed under the MIT License - see the [LICENSE](https://github.com/your-org/astrovoxai/blob/main/LICENSE) file for details.

## Source Code

- https://github.com/your-org/astrovoxai