apiVersion: v1
kind: Namespace
metadata:
  name: astrovox-ai
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: astrovox-config
  namespace: astrovox-ai
data:
  LOG_LEVEL: "info"
  MODEL_CACHE_SIZE: "1000"
  MAX_BATCH_SIZE: "32"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-server
  namespace: astrovox-ai
spec:
  replicas: 3
  selector:
    matchLabels:
      app: inference-server
  template:
    metadata:
      labels:
        app: inference-server
    spec:
      containers:
        - name: inference-server
          image: astrovox/inference:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              memory: "4Gi"
              cpu: "2"
            limits:
              memory: "16Gi"
              cpu: "8"
              nvidia.com/gpu: "1"
          envFrom:
            - configMapRef:
                name: astrovox-config
---
apiVersion: v1
kind: Service
metadata:
  name: inference-service
  namespace: astrovox-ai
spec:
  selector:
    app: inference-server
  ports:
    - port: 80
      targetPort: 8000
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
  namespace: astrovox-ai
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-server
  minReplicas: 1
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
