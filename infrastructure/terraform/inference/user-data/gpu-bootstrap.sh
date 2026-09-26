#!/bin/bash
set -xe

# Install NVIDIA driver and CUDA toolkit
apt-get update
apt-get install -y linux-headers-$(uname -r)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-docker.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | tee /etc/apt/sources.list.d/nvidia-docker.list
apt-get update
apt-get install -y nvidia-driver-535 nvidia-container-toolkit
systemctl restart docker

# Install kubelet and kubeadm
apt-get install -y docker.io kubelet kubeadm kubectl
systemctl enable --now kubelet

# Join EKS cluster
/etc/eks/bootstrap.sh ${cluster_name} --kubelet-extra-args '--node-labels workload=inference,accelerator=nvidia-a100'

# Enable GPU device plugin
kubectl apply -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml

# Install DCGM for monitoring
apt-get install -y datacenter-gpu-manager

# Configure GPU persistence mode
nvidia-smi -pm 1
nvidia-smi -ac 1215,797

echo "GPU inference node bootstrap complete"
