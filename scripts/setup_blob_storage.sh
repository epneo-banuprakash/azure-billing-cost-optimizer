az storage account create \
  --name <storage-account> \
  --resource-group <resource-group> \
  --location <location> \
  --sku Standard_LRS

az storage container create \
  --account-name <storage-account> \
  --name billing-archive \
  --auth-mode key

# Set lifecycle policy to move to Archive tier after 90 days
az storage account management-policy create \
  --account-name <storage-account> \
  --resource-group <resource-group> \
  --policy '{
    "rules": [
      {
        "name": "archiveRule",
        "type": "Lifecycle",
        "definition": {
          "filters": {
            "blobTypes": ["blockBlob"],
            "prefixMatch": ["billing-archive/"]
          },
          "actions": {
            "baseBlob": {
              "tierToArchive": {
                "daysAfterModificationGreaterThan": 90
              }
            }
          }
        }
      }
    ]
  }'