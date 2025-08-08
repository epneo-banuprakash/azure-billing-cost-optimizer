import azure.functions as func
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient
import json
from datetime import datetime, timedelta, timezone

def main(change_feed: func.DocumentList, context: func.Context) -> None:
    cosmos_client = CosmosClient(
        url='COSMOS_DB_ENDPOINT',
        credential='COSMOS_DB_KEY'
    )
    database = cosmos_client.get_database_client('BillingDB')
    container = database.get_container_client('BillingRecords')
    
    blob_service_client = BlobServiceClient.from_connection_string(
        'BLOB_STORAGE_CONNECTION_STRING'
    )
    blob_container_client = blob_service_client.get_container_client('billing-archive')
    
    three_months_ago = (datetime.now(timezone.UTC) - timedelta(days=90)).isoformat()
    
    for doc in change_feed:
        if doc['created_at'] < three_months_ago:
            # Archive to Blob Storage
            blob_name = f"archive/{doc['id']}.json"
            blob_client = blob_container_client.get_blob_client(blob_name)
            blob_client.upload_blob(json.dumps(doc), overwrite=True)
            
            # Set TTL to delete from Cosmos DB after archival
            doc['ttl'] = 1  # Delete after 1 second
            container.upsert_item(doc)

        # Set TTL to 90 days for records that are not archived
        doc['ttl'] = int(timedelta(days=90).total_seconds())