az cosmosdb sql container update \
  --resource-group <resource-group> \
  --account-name <cosmos-account> \
  --database-name BillingDB \
  --name BillingRecords \
  --ttl 7776000  # 90 days in seconds