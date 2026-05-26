#!/bin/bash
# setup-keyvault-for-picocloth.sh
# One-time setup: store the OpenAI key in Azure Key Vault for the fleet

set -euo pipefail

VAULT_NAME="shivaram-ai-kv"
SECRET_NAME="openai-api-key-master"

echo "🔐 PicoCloth Key Vault Setup"
echo "───────────────────────────────────────────────────────────"
echo ""

# Check Azure CLI
if ! command -v az &>/dev/null; then
  echo "❌ Azure CLI not found. Install: https://aka.ms/installazurecli"
  exit 1
fi

# Check login
if ! az account show &>/dev/null; then
  echo "🔑 Logging in to Azure..."
  az login --output none
fi

echo "   Vault:  $VAULT_NAME"
echo "   Secret: $SECRET_NAME"
echo ""

# Prompt for key (or read from env)
if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  echo "   Found OPENAI_API_KEY in environment."
  read -p "   Use this key? [Y/n]: " confirm
  if [[ "${confirm:-Y}" =~ ^[Yy] ]]; then
    KEY="$OPENAI_API_KEY"
  else
    read -sp "   Enter OpenAI API key: " KEY
    echo ""
  fi
else
  read -sp "   Enter OpenAI API key: " KEY
  echo ""
fi

if [[ -z "$KEY" ]]; then
  echo "❌ No key provided."
  exit 1
fi

# Store in Key Vault
echo ""
echo "📤 Storing secret in Key Vault..."
az keyvault secret set \
  --vault-name "$VAULT_NAME" \
  --name "$SECRET_NAME" \
  --value "$KEY" \
  --description "PicoCloth fleet OpenAI API key" \
  --output none

echo "   ✅ Secret stored successfully!"

# Verify
echo ""
echo "🔍 Verifying retrieval..."
VERIFY=$(az keyvault secret show \
  --vault-name "$VAULT_NAME" \
  --name "$SECRET_NAME" \
  --query value -o tsv)

if [[ "${VERIFY:0:10}" == "${KEY:0:10}" ]]; then
  echo "   ✅ Retrieval verified (first 10 chars match)"
else
  echo "   ⚠️  Retrieval mismatch — check permissions"
fi

# Show VM access commands
echo ""
echo "───────────────────────────────────────────────────────────"
echo "Next steps:"
echo ""
echo "  1. On each Azure VM, test with:"
echo "     ./scripts/security/fetch-secrets.sh openai-api-key-master"
echo ""
echo "  2. Launch fleet with Key Vault:"
echo "     ./scripts/launch-consultants.sh --keyvault"
echo ""
echo "  3. The VMs already have 'Key Vault Secrets User' role."
echo "     If fetch fails, wait 2-5 min for RBAC propagation."
echo ""
