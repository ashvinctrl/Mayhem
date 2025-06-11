#!/bin/bash

# This script deploys the application to a Kubernetes cluster.

# Exit immediately if a command exits with a non-zero status.
set -e

# Define the Kubernetes deployment configuration file
K8S_DEPLOYMENT_CONFIG="configs/kubernetes_deployment.yaml"

# Check if the Kubernetes deployment configuration file exists
if [ ! -f "$K8S_DEPLOYMENT_CONFIG" ]; then
    echo "Kubernetes deployment configuration file not found: $K8S_DEPLOYMENT_CONFIG"
    exit 1
fi

# Apply the Kubernetes deployment configuration
echo "Deploying application to Kubernetes..."
kubectl apply -f "$K8S_DEPLOYMENT_CONFIG"

# Wait for the deployment to complete
echo "Waiting for deployment to complete..."
kubectl rollout status deployment/project-mayhem

echo "Deployment completed successfully."