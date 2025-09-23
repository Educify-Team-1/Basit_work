#!/bin/bash

set -e

echo "🔧 Setting up monitoring stack..."

# Add Helm repositories
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Install Prometheus
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring \
    --create-namespace \
    --set grafana.adminPassword=admin123 \
    --set grafana.service.type=LoadBalancer

# Install custom dashboards
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: matching-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  matching-system.json: |
    {
      "dashboard": {
        "title": "Matching System Metrics",
        "panels": [
          {
            "title": "API Requests",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(matching_requests_total[5m])"
              }
            ]
          },
          {
            "title": "Response Time",
            "type": "graph", 
            "targets": [
              {
                "expr": "histogram_quantile(0.95, rate(matching_duration_seconds_bucket[5m]))"
              }
            ]
          }
        ]
      }
    }
EOF

echo "✅ Monitoring setup completed!"