from pymilvus import MilvusClient, DataType
import logging
import sys

# Configure logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# URI: Internal Docker network alias
URI = "http://milvus-standalone:19530" 
COLLECTION = "rag_pages_v1"

# DIMENSIONS (Adjusted based on Research/Current Stack)
DIM_TEXT   = 1024  # BGE-M3 standard
DIM_LAYOUT = 768   # LayoutLMv3 standard
DIM_VISUAL = 128   # ColQwen/ColPali standard (Current Layra Model)

def main():
    try:
        logger.info(f"🔌 Connecting to Milvus at {URI}...")
        client = MilvusClient(uri=URI, token="root:Milvus")
        
        # 1. Cleanup previous test
        if client.has_collection(COLLECTION):
            logger.warning(f"⚠️  Collection {COLLECTION} exists. Dropping for fresh schema test...")
            client.drop_collection(COLLECTION)

        # 2. Define Schema (Milvus 2.4+ Multi-Vector Style)
        logger.info("📐 Defining multi-vector schema...")
        schema = MilvusClient.create_schema(
            auto_id=True,
            enable_dynamic_field=False,
            description="Page-level RAG: Text + Layout + Visual + CURIEs"
        )

        # -- Identity --
        schema.add_field(field_name="id", datatype=DataType.INT64, is_primary=True, auto_id=True)

        # -- Linkage --
        schema.add_field(field_name="doc_id", datatype=DataType.VARCHAR, max_length=256)
        schema.add_field(field_name="page_id", datatype=DataType.INT32)

        # -- Content Payload --
        # Max length 65535 is standard soft limit for VARCHAR in Milvus
        schema.add_field(field_name="content", datatype=DataType.VARCHAR, max_length=65535)

        # -- Metadata --
        schema.add_field(field_name="is_figure_page", datatype=DataType.BOOL)
        schema.add_field(field_name="caption", datatype=DataType.VARCHAR, max_length=8192, nullable=True)

        # -- CURIEs (Entity Linking) --
        # Ex: ["PUBCHEM.COMPOUND:394162", "TAXON:3544"]
        schema.add_field(
            field_name="curies",
            datatype=DataType.ARRAY,
            element_type=DataType.VARCHAR,
            max_capacity=256,
            max_length=128,
            nullable=True,
        )

        # -- Vectors (Multi-Modal) --
        # Note: Milvus 2.4+ allows multiple vector fields in one collection
        schema.add_field(field_name="text_vec", datatype=DataType.FLOAT_VECTOR, dim=DIM_TEXT)
        schema.add_field(field_name="layout_vec", datatype=DataType.FLOAT_VECTOR, dim=DIM_LAYOUT)
        schema.add_field(field_name="visual_vec", datatype=DataType.FLOAT_VECTOR, dim=DIM_VISUAL)

        # 3. Create Collection
        logger.info("🚀 Creating collection...")
        index_params = client.prepare_index_params()

        # Indexes for each vector field (Required for search)
        index_params.add_index(field_name="text_vec", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
        index_params.add_index(field_name="layout_vec", index_type="HNSW", metric_type="COSINE", params={"M": 16, "efConstruction": 200})
        index_params.add_index(field_name="visual_vec", index_type="HNSW", metric_type="IP", params={"M": 16, "efConstruction": 200}) # IP for ColQwen

        client.create_collection(
            collection_name=COLLECTION,
            schema=schema,
            index_params=index_params
        )
        
        logger.info(f"✅ SUCCESS: Collection {COLLECTION} created with multi-vector schema!")
        
        # 4. Verify
        desc = client.describe_collection(COLLECTION)
        logger.info(f"📋 Verification: {desc}")

    except Exception as e:
        logger.error(f"❌ FAILED: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()