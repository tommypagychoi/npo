#!/usr/bin/env bash
set -euo pipefail

K8S_VERSION_MINOR="${K8S_VERSION_MINOR:-v1.36}"
NODE_IP="${NODE_IP:-}"

if [ -n "$NODE_IP" ]; then
  echo "KUBELET_EXTRA_ARGS=--node-ip=$NODE_IP" | sudo tee /etc/default/kubelet >/dev/null
fi

sudo mkdir -p /etc/needrestart/conf.d
echo "\$nrconf{restart} = 'a';" | sudo tee /etc/needrestart/conf.d/99-k8s-auto.conf >/dev/null

sudo swapoff -a
sudo sed -i.bak '/ swap / s/^/#/' /etc/fstab

cat <<MODS | sudo tee /etc/modules-load.d/k8s.conf >/dev/null
overlay
br_netfilter
MODS

sudo modprobe overlay
sudo modprobe br_netfilter

cat <<SYSCTL | sudo tee /etc/sysctl.d/99-kubernetes-cri.conf >/dev/null
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
SYSCTL

sudo sysctl --system

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y apt-transport-https ca-certificates curl gpg containerd

sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml >/dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
sudo systemctl enable --now containerd
sudo systemctl restart containerd

sudo mkdir -p -m 755 /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/${K8S_VERSION_MINOR}/deb/Release.key" |
  sudo gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg

printf 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/%s/deb/ /\n' "$K8S_VERSION_MINOR" |
  sudo tee /etc/apt/sources.list.d/kubernetes.list >/dev/null

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a apt-get install -y kubelet kubeadm kubectl
sudo apt-mark hold kubelet kubeadm kubectl
sudo systemctl enable --now kubelet

echo "k8s common setup complete on $(hostname)"
