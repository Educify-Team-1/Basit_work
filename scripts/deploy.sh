#!/bin/bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting deployment of AI Matching System${NC}"

# Check prerequisites
echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
command -v kubectl >/dev/null 2>&1 || { echo -e "${RED}❌ kubectl is required but not installed${NC}"; exit 1; }
command -v helm >/dev/null 2>&1 || { echo -e "${RED}❌ helm is required but not installed${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ docker is required but not installed${NC}"; exit 1; }

# Build Docker images
echo -e "${YELLOW}🏗️  Building Docker images...${NC}"
docker build -t matching-api:latest .
docker build -f Dockerfile.training -t matching-training:latest .

# Push to registry (if specified)
if [ ! -z "$DOCKER_REGISTRY" ]; then
    echo -e "${YELLOW}📤 Pushing images to registry...${NC}"
    docker tag matching-api:latest $DOCKER_REGISTRY/matching-api:latest
    docker tag matching-training:latest $DOCKER_REGISTRY/matching-training:latest
    docker push $DOCKER_REGISTRY/matching-api:latest
    docker push $DOCKER_REGISTRY/matching-training:latest
fi

# Create namespace
echo -e "${YELLOW}📁 Creating namespace...${NC}"
kubectl create namespace matching-system --dry-run=client -o yaml | kubectl apply -f -

# Deploy with Helm
echo -e "${YELLOW}⚙️  Deploying with Helm...${NC}"
helm upgrade --install matching-system ./helm/matching-system \
    --namespace matching-system \
    --set image.tag=latest \
    --set training.image.tag=latest \
    --wait --timeout=10m

# Wait for deployment
echo -e "${YELLOW}⏳ Waiting for deployment to be ready...${NC}"
kubectl wait --for=condition=available --timeout=300s deployment/matching-api -n matching-system

# Get service URL
echo -e "${YELLOW}🔍 Getting service information...${NC}"
kubectl get services -n matching-system
kubectl get ingress -n matching-system

echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo -e "${GREEN}🌐 API should be available at the ingress URL${NC}"

# Run health check
echo -e "${YELLOW}🏥 Running health check...${NC}"
kubectl port-forward -n matching-system svc/matching-api-service 8080:80 &
PF_PID=$!
sleep 5

if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
fi

kill $PF_PID 2>/dev/null || true

echo -e "${GREEN}🎉 Deployment script completed!${NC}"