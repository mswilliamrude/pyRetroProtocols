# Azure VNet Native Container Deployment Guide

This guide contains the exact, verified commands to build a Linux container in Azure Container Registry (ACR) and deploy it natively into a private Virtual Network (VNet) using Azure Container Instances (ACI).

### Step 1: Prepare the Dockerfile
Ensure your project contains a valid Linux `Dockerfile` in the root directory. It must install your dependencies and explicitly bind your application to `0.0.0.0` (all interfaces) so it can accept traffic from the VNet.

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
# Ensure your python script binds to 0.0.0.0:8080!
CMD ["python", "unimind_mcp.py"]
```

### Step 2: Build the Image in Azure (ACR Build)
This command zips your local source code, sends it to Azure, and builds the Docker image natively on a Linux build agent in the cloud. You do not need Docker installed locally.

```bash
az acr build \
  --registry wdrcentralus \
  --image unimind-linux:latest \
  --subscription AEPSovereign_EncryptedTransport_Sandbox \
  .
```

### Step 3: Create the Dedicated Container Subnet
Native serverless containers require an empty, dedicated subnet in your VNet. This command creates the subnet and "delegates" it to the ACI service.

```bash
az network vnet subnet create \
  --resource-group aet-apt-localdev-es2 \
  --vnet-name aet-psrdev-centralus-vnet \
  --name aet-psrdev-centralus-docker0 \
  --address-prefixes 10.0.5.0/24 \
  --delegations Microsoft.ContainerInstance/containerGroups
```
*(If the subnet already exists, use `az network vnet subnet update` with the same delegation flag).*

### Step 4: Retrieve Registry Credentials
Your private VNet container needs permission to pull the image from your private Azure Container Registry.

```bash
ACR_PW=$(az acr credential show --name wdrcentralus --query "passwords[0].value" -o tsv)
```

### Step 5: Deploy the Native Container
This command deploys the container directly into your private VNet. It explicitly defines the Linux OS type, compute resources, and geographic location to bypass Azure CLI quirks.

```bash
az container create \
  --resource-group aet-apt-localdev-es2 \
  --name unimind-app \
  --image wdrcentralus.azurecr.io/unimind-linux:latest \
  --registry-login-server wdrcentralus.azurecr.io \
  --vnet aet-psrdev-centralus-vnet \
  --subnet aet-psrdev-centralus-docker0 \
  --ip-address private \
  --port 8080 \
  --registry-username wdrcentralus \
  --registry-password ${ACR_PW} \
  --os-type Linux \
  --cpu 1 \
  --memory 1.5 \
  --location centralus
```

### Step 6: Verify and Connect
Retrieve the dynamic private IP assigned to your new container:

```bash
az container show \
  --resource-group aet-apt-localdev-es2 \
  --name unimind-app \
  --query ipAddress.ip -o tsv
```

You can now connect your Opencode/MCP client to `http://<PRIVATE_IP>:8080/sse` natively across your VNet!
