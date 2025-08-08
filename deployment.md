# Deployment Instructions for AzureBillingCostOptimizer

This document provides step-by-step instructions to deploy the cost optimization solution for managing billing records in an Azure serverless architecture. The solution uses Azure Cosmos DB for active data, Azure Blob Storage for archived data, Azure Functions for archival and API logic, and Azure Monitor for oversight. These instructions ensure a seamless setup with no data loss, no downtime, and no changes to existing API contracts.

## Prerequisites

Before starting, ensure you have:
- An **Azure account** with permissions to create:
  - Azure Cosmos DB (serverless mode)
  - Azure Blob Storage
  - Azure Functions
  - Azure Monitor
- **Azure CLI** installed (version 2.30 or later).
- **Python 3.8+** for Azure Functions development.
- **Git** installed for cloning the repository.
- A **GitHub account** to host the repository.
- Basic familiarity with Azure portal and CLI commands.

## Repository Structure

Ensure the following files are present in the `AzureBillingCostOptimizer` repository:
```
AzureBillingCostOptimizer/
├── src/
│   ├── archive_records.py         # Azure Function for archival
│   ├── read_record.py            # Azure Function for read API
├── scripts/
│   ├── enable_ttl.sh             # Azure CLI script for Cosmos DB TTL
│   ├── setup_blob_storage.sh     # Azure CLI script for Blob Storage setup
├── diagrams/
│   ├── architecture.png          # Solution architecture diagram
├── conversation_log.md           # AI interaction log
├── solution.md                   # Solution details
├── README.md                     # Project overview
├── deployment.md                 # This file
```

## Deployment Steps

### 1. Clone the Repository
Clone the repository to your local machine:
```bash
git git clone https://github.com/epneo-banuprakash/azure-billing-cost-optimizer
cd azure-billing-cost-optimizer
```

### 2. Set Up Azure Resources

#### a. Create Azure Cosmos DB
1. Create a serverless Cosmos DB account:
   ```bash
   az cosmosdb create \
     --name <cosmos-account> \
     --resource-group <resource-group> \
     --locations regionName=<location> \
     --capabilities EnableServerless
   ```
   Replace `<cosmos-account>`, `<resource-group>`, and `<location>` (e.g., `eastus`).

2. Create a database and container:
   ```bash
   az cosmosdb sql database create \
     --account-name <cosmos-account> \
     --resource-group <resource-group> \
     --name BillingDB

   az cosmosdb sql container create \
     --account-name <cosmos-account> \
     --resource-group <resource-group> \
     --database-name BillingDB \
     --name BillingRecords \
     --partition-key-path "/id"
   ```

3. Enable TTL (90 days) on the `BillingRecords` container:
   ```bash
   bash scripts/enable_ttl.sh
   ```
   Update `scripts/enable_ttl.sh` with your `<resource-group>` and `<cosmos-account>`.

#### b. Create Azure Blob Storage
1. Create a storage account and container:
   ```bash
   bash scripts/setup_blob_storage.sh
   ```
   Update `scripts/setup_blob_storage.sh` with your `<storage-account>`, `<resource-group>`, and `<location>`.

2. Verify the lifecycle policy in the script moves blobs to Archive tier after 90 days.

#### c. Create Azure Functions App
1. Create a Function App:
   ```bash
   az functionapp create \
     --name <function-app> \
     --resource-group <resource-group> \
     --consumption-plan-location <location> \
     --runtime python \
     --runtime-version 3.8 \
     --functions-version 4 \
     --storage-account <storage-account>
   ```

2. Configure environment variables for the Function App:
   ```bash
   az functionapp config appsettings set \
     --name <function-app> \
     --resource-group <resource-group> \
     --settings \
       "COSMOS_DB_ENDPOINT=<cosmos-endpoint>" \
       "COSMOS_DB_KEY=<cosmos-key>" \
       "BLOB_STORAGE_CONNECTION_STRING=<blob-connection-string>"
   ```
   Obtain `<cosmos-endpoint>` and `<cosmos-key>` from the Cosmos DB account (Azure portal: Keys section). Get `<blob-connection-string>` from the Blob Storage account (Access Keys section).

### 3. Deploy Azure Functions

#### a. Deploy Archival Function
1. Navigate to the Function code:
   ```bash
   cd src
   ```

2. Deploy `archive_records.py` as a Function triggered by Cosmos DB Change Feed:
   ```bash
   func azure functionapp publish <function-app> --publish-local-settings
   ```

3. Configure the Change Feed trigger:
   - In the Azure portal, update the Function’s binding to connect to `BillingDB/BillingRecords`.
   - Set the lease container to `leases` in Cosmos DB (auto-created).

#### b. Deploy Read API Function
1. Deploy `read_record.py` as an HTTP-triggered Function:
   ```bash
   func azure functionapp publish <function-app> --publish-local-settings
   ```

2. Verify the HTTP endpoint (e.g., `https://<function-app>.azurewebsites.net/api/read_record?id=<record-id>`).

### 4. Configure Monitoring
1. Set up Azure Monitor for the resources:
   - Navigate to the Azure portal → Monitor → Alerts.
   - Create alerts for:
     - **RU Consumption**: Cosmos DB RU usage exceeding budget (e.g., 5M RUs/month).
     - **Archival Failures**: Function execution errors or dead-letter queue entries.
     - **Rehydration Delays**: Blob Storage access times >5 seconds.

2. Example alert rule (RU spike):
   ```bash
   az monitor metrics alert create \
     --name "HighRUUsage" \
     --resource-group <resource-group> \
     --scopes /subscriptions/<subscription-id>/resourceGroups/<resource-group>/providers/Microsoft.DocumentDB/databaseAccounts/<cosmos-account> \
     --condition "avg TotalRequestUnits > 5000000" \
     --action <action-group-id>
   ```

### 5. Test the Deployment
1. **Write Test**: Insert a sample record into Cosmos DB:
   ```bash
   az cosmosdb sql container item create \
     --account-name <cosmos-account> \
     --resource-group <resource-group> \
     --database-name BillingDB \
     --container-name BillingRecords \
     --item '{"id": "test1", "created_at": "2025-08-01T00:00:00Z", "data": "test"}'
   ```

2. **Archival Test**: Manually trigger the archival Function or wait 90 days to verify the record moves to Blob Storage (`billing-archive/archive/test1.json`).

3. **Read Test**: Query the read API for a recent and an archived record:
   ```bash
   curl https://<function-app>.azurewebsites.net/api/read_record?id=test1
   ```

4. **Monitoring Test**: Check Azure Monitor for RU usage and Function logs.

## Troubleshooting

- **Archival Failure**: Check Function logs in Azure portal; verify dead-letter queue (if configured).
- **API Errors**: Ensure environment variables are set correctly; test Cosmos DB/Blob Storage connectivity.
- **Latency Issues**: Confirm Blob Storage rehydration completes within seconds; adjust Hot tier caching if needed.
- **RU Spikes**: Review query patterns in Cosmos DB; optimize indexing.

## Post-Deployment

- **Verify Cost Savings**: Monitor costs in Azure Cost Management after 1 month (expect ~$39.25/month vs. ~$151.25/month).
- **Reconciliation Job**: Schedule a periodic Function to compare Cosmos DB and Blob Storage for data consistency.
- **Multi-Region**: For high availability, deploy Functions to a secondary region and configure failover.

## Additional Notes

- **CI/CD**: Use GitHub Actions to automate Function deployments (see `README.md` for setup).
- **Security**: Restrict Cosmos DB and Blob Storage access with role-based access control (RBAC).
- **Diagram**: View `diagrams/architecture.png` for the architecture overview.
- **AI Log**: See `conversation_log.md` for details on solution development with Grok 3.

For further details, refer to `solution.md` and `README.md`.