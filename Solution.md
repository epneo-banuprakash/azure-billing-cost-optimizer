# Cost Optimization Solution for Azure Serverless Billing Records

This document details a cost optimization solution for a read-heavy Azure Cosmos DB storing 2 million billing records (300 KB each, ~600 GB), with records older than three months rarely accessed. The solution reduces costs while ensuring:
- **Simplicity**: Easy to deploy and maintain.
- **No Data Loss/Downtime**: Seamless transition without data loss or service interruptions.
- **No API Changes**: Existing read/write APIs remain unchanged.
- **Latency**: Seconds-scale response for archived records.

## Solution Overview

A **tiered storage approach** minimizes costs:
- **Active Data**: Records <3 months old stay in Azure Cosmos DB (serverless mode) for low-latency access.
- **Archived Data**: Records >3 months old move to Azure Blob Storage (Archive tier) for cost savings.
- **Archival**: Azure Functions, triggered by Cosmos DB Change Feed, archive records and set TTL for deletion.
- **Read API**: Azure Functions query Cosmos DB or Blob Storage transparently.
- **Monitoring**: Azure Monitor tracks costs and performance.

**Cost Savings**: Reduces costs from ~$150/month to ~$39.25/month (~73% savings).

### Architecture Diagram

![Architecture Diagram](diagrams/architecture.png)

*Clients interact via APIs (Azure API Management/App Service). Azure Functions handle read/write, querying Cosmos DB or Blob Storage. Change Feed triggers archival. Azure Monitor oversees performance.*

## Implementation Details

### 1. Archival Process
- **Component**: Azure Function (Cosmos DB Change Feed trigger).
- **Purpose**: Archives records >3 months old to Blob Storage, sets TTL for deletion.
- **Features**:
  - Incremental processing via Change Feed.
  - Ensures archival before deletion.
  - Retry logic for failures.
- **Artifact**: `src/archive_records.py`.

### 2. Read API Logic
- **Component**: Azure Function (HTTP trigger).
- **Purpose**: Queries Cosmos DB; if not found, retrieves from Blob Storage (rehydrates if archived).
- **Features**:
  - Maintains API contract.
  - Handles rehydration latency.
  - Caches frequent archived records in Hot tier.
- **Artifact**: `src/read_record.py`.

### 3. Cosmos DB Configuration
- **Setup**: Enable TTL (90 days) on `BillingRecords` container.
- **Indexing**: Exclude unused fields to reduce RU costs.
- **Artifact**: `scripts/enable_ttl.sh`.

### 4. Blob Storage Configuration
- **Setup**: Create `billing-archive` container with lifecycle policy to archive after 90 days.
- **Cost**: ~$0.00099/GB/month (Archive tier) vs. $0.25/GB/month (Cosmos DB).
- **Artifact**: `scripts/setup_blob_storage.sh`.

### 5. Monitoring
- **Component**: Azure Monitor.
- **Purpose**: Tracks RU consumption, rehydration delays, and Function failures.
- **Alerts**:
  - RU spikes.
  - Archival failures.
  - Rehydration delays.

## Cost Savings Estimate

- **Current**:
  - Storage: 600 GB × $0.25/GB = $150/month.
  - RUs: 1M reads × 5 RUs × $0.25/M = $1.25/month.
  - **Total**: ~$151.25/month.
- **Proposed**:
  - Cosmos DB: 150 GB × $0.25/GB = $37.50/month.
  - Blob Storage Archive: 450 GB × $0.00099/GB = $0.45/month.
  - Rehydration: 450 GB × 1% × $0.01/GB = $0.045/month.
  - RUs: $1.25/month.
  - **Total**: ~$39.25/month.
- **Savings**: ~$112/month (73%).

## Failure Points and Mitigations

1. **Archival Failure**:
   - **Issue**: Network/Blob Storage issues.
   - **Mitigation**: Retry with backoff; dead-letter queue.
   - **Fix**: Monitor queue, reconcile records.

2. **Rehydration Latency**:
   - **Issue**: Slow rehydration exceeds latency.
   - **Mitigation**: Cache frequent records in Hot tier (7 days).
   - **Fix**: Adjust caching via access pattern analysis.

3. **RU Spikes**:
   - **Issue**: Query spikes increase costs.
   - **Mitigation**: Optimize indexing; set RU alerts.
   - **Fix**: Use autoscale mode if needed.

4. **Data Consistency**:
   - **Issue**: Deletion before archival.
   - **Mitigation**: Verify Blob Storage upload before TTL.
   - **Fix**: Periodic reconciliation job.

5. **API Downtime**:
   - **Issue**: Function/API Management outage.
   - **Mitigation**: Multi-region deployment; HA API Management.
   - **Fix**: Monitor uptime, implement failover.

## Meeting Requirements

- **Simplicity**: Managed Azure services, minimal code.
- **No Data Loss**: Change Feed, retries, and verification ensure archival.
- **No Downtime**: Background archival, transparent API.
- **No API Changes**: Unified read/write API across storage layers.
- **Latency**: Cosmos DB <10ms; Blob rehydration ~seconds.

## Bonus Points

- **Diagram**: `diagrams/architecture.png`.
- **Scripts**: `src/` and `scripts/` directories.
- **AI Log**: `conversation_log.md` details Grok 3 interactions.

## Conclusion

This solution reduces costs by 73% using tiered storage, ensuring reliability for thousands of users with robust error handling and monitoring. See `deployment.md` for deployment instructions.