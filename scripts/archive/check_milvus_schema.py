#!/usr/bin/env python3
"""
Check Milvus schema and indexing for LAYRA thesis deployment.

IMPORTANT: Milvus port 19530 is NOT exposed to host. Run this script inside the backend container:
  docker exec layra-backend python3 /app/check_milvus_schema.py
"""

from pymilvus import MilvusClient, DataType
import json

def main():
    print("=== LAYRA Milvus Schema Check ===")
    
    # Connect to Milvus
    # Use internal service name when running inside container
    # For host execution, this will fail - run inside backend container
    uri = "http://milvus-standalone:19530"
    print(f"Connecting to Milvus at {uri}...")
    print("Note: If running from host, use docker exec to run inside backend container")
    
    try:
        client = MilvusClient(uri=uri)
        print("✓ Connected to Milvus")
        
        # List all collections
        collections = client.list_collections()
        print(f"\n1. Collections found: {len(collections)}")
        
        for i, collection_name in enumerate(collections, 1):
            print(f"\n   {i}. Collection: '{collection_name}'")
            
            # Get collection info
            if client.has_collection(collection_name):
                # Get collection schema
                schema = client.describe_collection(collection_name)
                print(f"      Schema fields: {len(schema.get('fields', []))}")
                
                # Show field details
                for field in schema.get('fields', []):
                    field_name = field.get('name', 'unknown')
                    field_type = field.get('type', DataType.UNKNOWN)
                    if field_type != DataType.UNKNOWN:
                        field_type_name = DataType(field_type).name
                    else:
                        field_type_name = str(field_type)
                    
                    dim = field.get('params', {}).get('dim', 'N/A')
                    max_length = field.get('params', {}).get('max_length', 'N/A')
                    
                    print(f"      - {field_name}: {field_type_name}", end="")
                    if dim != 'N/A':
                        print(f" (dim={dim})", end="")
                    if max_length != 'N/A':
                        print(f" (max_length={max_length})", end="")
                    if field.get('is_primary', False):
                        print(" [PRIMARY KEY]", end="")
                    print()
                
                # Get collection stats
                stats = client.get_collection_stats(collection_name)
                row_count = stats.get('row_count', 0)
                print(f"      Row count: {row_count}")
                
                # Get index info
                indexes = client.list_indexes(collection_name)
                print(f"      Indexes: {len(indexes)}")
                for idx_name in indexes:
                    index_info = client.describe_index(collection_name, idx_name)
                    print(f"        - {idx_name}: {index_info.get('index_type', 'N/A')}")
                    print(f"          Metric: {index_info.get('metric_type', 'N/A')}")
                    print(f"          Params: {index_info.get('params', {})}")
            
            else:
                print(f"      Collection does not exist")
        
        # Check for thesis-related collections
        print("\n2. Searching for thesis-related collections...")
        thesis_collections = [c for c in collections if 'thesis' in c.lower() or 'colqwen' in c]
        
        if thesis_collections:
            print(f"   Found {len(thesis_collections)} thesis-related collections:")
            for col in thesis_collections:
                print(f"   - {col}")
                
                # Get sample data if available
                try:
                    # Try to get first few rows
                    query_result = client.query(
                        collection_name=col,
                        filter="",
                        output_fields=["file_id", "image_id", "page_number"],
                        limit=3
                    )
                    
                    if query_result:
                        print(f"     Sample data ({len(query_result)} rows):")
                        for i, row in enumerate(query_result):
                            file_id = row.get('file_id', 'N/A')
                            image_id = row.get('image_id', 'N/A')
                            page = row.get('page_number', 'N/A')
                            print(f"       Row {i+1}: file_id={file_id[:30]}..., image_id={image_id[:20]}..., page={page}")
                    else:
                        print(f"     No data in collection")
                        
                except Exception as e:
                    print(f"     Error querying: {str(e)[:100]}")
        else:
            print("   No thesis-related collections found")
        
        # Check index parameters
        print("\n3. Index Configuration Summary:")
        for collection_name in collections:
            indexes = client.list_indexes(collection_name)
            for idx_name in indexes:
                index_info = client.describe_index(collection_name, idx_name)
                if index_info.get('index_type') == 'HNSW':
                    print(f"   Collection '{collection_name}':")
                    print(f"     Index: {idx_name} (HNSW)")
                    print(f"     Metric: {index_info.get('metric_type', 'N/A')}")
                    params = index_info.get('params', {})
                    print(f"     M: {params.get('M', 'N/A')}")
                    print(f"     efConstruction: {params.get('efConstruction', 'N/A')}")
        
    except Exception as e:
        print(f"✗ Error connecting to Milvus: {e}")
        return
    
    print("\n=== Check Complete ===")

if __name__ == "__main__":
    main()