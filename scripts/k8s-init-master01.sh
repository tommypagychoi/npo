#!/usr/bin/env bash
set -euo pipefail

CONTROL_PLANE_ENDPOINT="${CONTROL_PLANE_ENDPOINT:-115.71.7.223:6443}"
MASTER01="${MASTER01:-192.168.10.37}"
POD_CIDR="${POD_CIDR:-10.244.0.0/16}"
SERVICE_CIDR="${SERVICE_CIDR:-10.96.0.0/12}"

sudo kubeadm init \
  --control-plane-endpoint "$CONTROL_PLANE_ENDPOINT" \
  --upload-certs \
  --apiserver-advertise-address "$MASTER01" \
  --pod-network-cidr "$POD_CIDR" \
  --service-cidr "$SERVICE_CIDR"

mkdir -p "$HOME/.kube"
sudo cp -f /etc/kubernetes/admin.conf "$HOME/.kube/config"
sudo chown "$(id -u):$(id -g)" "$HOME/.kube/config"

kubectl apply -f https://github.com/flannel-io/flannel/releases/latest/download/kube-flannel.yml
kubeadm token create --print-join-command | tee "$HOME/join-worker.sh"
sudo kubeadm init phase upload-certs --upload-certs | tail -n 1 | tee "$HOME/certificate-key.txt"
