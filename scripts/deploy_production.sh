#!/bin/bash

# Production deployment script for Project Mayhem
# This script deploys the chaos engineering platform to a production Kubernetes cluster

set -e

echo "🚀 Starting Project Mayhem Production Deployment"

# Configuration
NAMESPACE="chaos-engineering"
IMAGE_TAG="${IMAGE_TAG:-latest}"
REGISTRY="${REGISTRY:-your-registry.com}"
IMAGE_NAME="${REGISTRY}/chaos-orchestrator:${IMAGE_TAG}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check if we can connect to Kubernetes cluster
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

# Create namespace
create_namespace() {
    log_info "Creating namespace: ${NAMESPACE}"
    
    if kubectl get namespace ${NAMESPACE} &> /dev/null; then
        log_warn "Namespace ${NAMESPACE} already exists"
    else
        kubectl create namespace ${NAMESPACE}
        log_info "Namespace ${NAMESPACE} created ✓"
    fi
}

# Build and push Docker image
build_and_push_image() {
    log_info "Building Docker image: ${IMAGE_NAME}"
    
    # Build the image
    docker build -t ${IMAGE_NAME} .
    
    # Push to registry
    log_info "Pushing image to registry..."
    docker push ${IMAGE_NAME}
    
    log_info "Image built and pushed ✓"
}

# Generate secrets
generate_secrets() {
    log_info "Generating production secrets..."
    
    # Generate random secrets if they don't exist
    API_KEY="${CHAOS_API_KEY:-$(openssl rand -hex 32)}"
    FLASK_SECRET="${FLASK_SECRET_KEY:-$(openssl rand -hex 32)}"
    DB_URL="${DATABASE_URL:-sqlite:///app/data/chaos_platform.db}"
    
    # Create secret YAML
    cat <<EOF > /tmp/chaos-secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: chaos-secrets
  namespace: ${NAMESPACE}
type: Opaque
data:
  database-url: $(echo -n "${DB_URL}" | base64 -w 0)
  api-key: $(echo -n "${API_KEY}" | base64 -w 0)
  flask-secret-key: $(echo -n "${FLASK_SECRET}" | base64 -w 0)
EOF
    
    # Apply secrets
    kubectl apply -f /tmp/chaos-secrets.yaml
    rm /tmp/chaos-secrets.yaml
    
    log_info "Secrets generated and applied ✓"
    log_warn "API Key: ${API_KEY}"
    log_warn "Please save the API key securely!"
}

# Deploy Prometheus
deploy_prometheus() {
    log_info "Deploying Prometheus..."
    
    # Add Prometheus Helm repo
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    # Install Prometheus
    helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false \
        --set prometheus.prometheusSpec.retention=30d \
        --wait
    
    log_info "Prometheus deployed ✓"
}

# Deploy Grafana
deploy_grafana() {
    log_info "Deploying Grafana..."
    
    # Install Grafana (if not included in Prometheus stack)
    helm upgrade --install grafana grafana/grafana \
        --namespace monitoring \
        --set adminPassword="${GRAFANA_PASSWORD:-secure_admin_password_2025}" \
        --set persistence.enabled=true \
        --set persistence.size=10Gi \
        --wait
    
    log_info "Grafana deployed ✓"
}

# Deploy application
deploy_application() {
    log_info "Deploying Chaos Orchestrator application..."
    
    # Update image in deployment config
    sed "s|chaos-orchestrator:latest|${IMAGE_NAME}|g" configs/kubernetes_deployment_production.yaml > /tmp/deployment.yaml
    
    # Apply deployment
    kubectl apply -f /tmp/deployment.yaml
    rm /tmp/deployment.yaml
    
    # Wait for deployment to be ready
    kubectl wait --for=condition=available --timeout=300s deployment/chaos-orchestrator -n ${NAMESPACE}
    
    log_info "Application deployed ✓"
}

# Configure monitoring
configure_monitoring() {
    log_info "Configuring monitoring and dashboards..."
    
    # Create ServiceMonitor for Prometheus to scrape our app
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: chaos-orchestrator-monitor
  namespace: ${NAMESPACE}
  labels:
    app: chaos-orchestrator
spec:
  selector:
    matchLabels:
      app: chaos-orchestrator
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
EOF
    
    log_info "Monitoring configured ✓"
}

# Run health checks
run_health_checks() {
    log_info "Running health checks..."
    
    # Check if pods are running
    kubectl get pods -n ${NAMESPACE} -l app=chaos-orchestrator
    
    # Check service endpoints
    kubectl get endpoints -n ${NAMESPACE}
    
    # Test health endpoint
    CLUSTER_IP=$(kubectl get svc chaos-orchestrator-service -n ${NAMESPACE} -o jsonpath='{.spec.clusterIP}')
    
    if kubectl run test-pod --rm -i --restart=Never --image=curlimages/curl:latest -- \
        curl -f "http://${CLUSTER_IP}/health"; then
        log_info "Health check passed ✓"
    else
        log_error "Health check failed ✗"
        exit 1
    fi
}

# Display deployment information
display_info() {
    log_info "Deployment completed successfully! 🎉"
    
    echo ""
    echo "📋 Deployment Information:"
    echo "=========================="
    echo "Namespace: ${NAMESPACE}"
    echo "Image: ${IMAGE_NAME}"
    echo ""
    
    echo "📝 Access Information:"
    echo "====================="
    
    # Get ingress information
    if kubectl get ingress chaos-orchestrator-ingress -n ${NAMESPACE} &> /dev/null; then
        INGRESS_HOST=$(kubectl get ingress chaos-orchestrator-ingress -n ${NAMESPACE} -o jsonpath='{.spec.rules[0].host}')
        echo "Public URL: https://${INGRESS_HOST}"
    else
        echo "To access locally, run:"
        echo "kubectl port-forward svc/chaos-orchestrator-service -n ${NAMESPACE} 8080:80"
        echo "Then visit: http://localhost:8080"
    fi
    
    echo ""
    echo "🔑 API Key: ${API_KEY}"
    echo ""
    echo "📊 Monitoring:"
    echo "Prometheus: kubectl port-forward svc/prometheus-kube-prometheus-prometheus -n monitoring 9090:9090"
    echo "Grafana: kubectl port-forward svc/prometheus-grafana -n monitoring 3000:80"
    echo ""
    
    log_info "Happy chaos engineering! 💥"
}

# Main deployment flow
main() {
    log_info "Project Mayhem Production Deployment v1.0.0"
    
    check_prerequisites
    create_namespace
    build_and_push_image
    generate_secrets
    
    # Deploy monitoring stack (optional, skip if already exists)
    if [[ "${SKIP_MONITORING:-false}" != "true" ]]; then
        deploy_prometheus
    fi
    
    deploy_application
    configure_monitoring
    run_health_checks
    display_info
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "clean")
        log_info "Cleaning up deployment..."
        kubectl delete namespace ${NAMESPACE} --ignore-not-found=true
        log_info "Cleanup completed"
        ;;
    "update")
        log_info "Updating application..."
        build_and_push_image
        kubectl rollout restart deployment/chaos-orchestrator -n ${NAMESPACE}
        kubectl rollout status deployment/chaos-orchestrator -n ${NAMESPACE}
        log_info "Update completed"
        ;;
    "status")
        log_info "Deployment status:"
        kubectl get all -n ${NAMESPACE}
        ;;
    *)
        echo "Usage: $0 {deploy|clean|update|status}"
        echo "  deploy: Full deployment (default)"
        echo "  clean:  Remove all resources"
        echo "  update: Update application only"
        echo "  status: Show deployment status"
        exit 1
        ;;
esac
