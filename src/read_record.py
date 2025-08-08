import os
import json
import time
import azure.functions as func
from azure.cosmos import CosmosClient, exceptions as cosmos_exceptions
from azure.storage.blob import BlobServiceClient, BlobAccessTier
from azure.core.exceptions import ResourceNotFoundError

def main(req: func.HttpRequest) -> func.HttpResponse:
    record_id = req.params.get('id')
    if not record_id:
        return func.HttpResponse("Missing 'id' parameter", status_code=400)

    # Cosmos DB setup
    cosmos_client = CosmosClient(
        url=os.getenv("COSMOS_DB_ENDPOINT"),
        credential=os.getenv("COSMOS_DB_KEY")
    )
    database = cosmos_client.get_database_client('BillingDB')
    container = database.get_container_client('BillingRecords')

    try:
        record = container.read_item(item=record_id, partition_key=record_id)
        return func.HttpResponse(json.dumps(record), status_code=200)

    except cosmos_exceptions.CosmosResourceNotFoundError:
        # Not in Cosmos DB, check Blob
        blob_service_client = BlobServiceClient.from_connection_string(
            os.getenv("BLOB_STORAGE_CONNECTION_STRING")
        )
        blob_client = blob_service_client.get_container_client(
            'billing-archive'
        ).get_blob_client(f"archive/{record_id}.json")

        try:
            properties = blob_client.get_blob_properties()
        except ResourceNotFoundError:
            return func.HttpResponse("Record not found", status_code=404)

        if properties.access_tier == 'Archive':
            blob_client.set_access_tier(BlobAccessTier.HOT)
            return func.HttpResponse(
                "Blob is in Archive tier. Rehydration initiated. Try again later.",
                status_code=202
            )

        blob_data = blob_client.download_blob().readall()
        return func.HttpResponse(blob_data, status_code=200)

    except Exception as e:
        return func.HttpResponse(f"Server error: {str(e)}", status_code=500)
