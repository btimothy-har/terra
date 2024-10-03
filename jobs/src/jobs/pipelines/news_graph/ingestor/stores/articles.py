import os

from llama_index.storage.docstore.postgres import PostgresDocumentStore

article_store = PostgresDocumentStore.from_uri(
    uri=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres:5432/terra",
    table_name="articles",
    schema_name="news",
    use_jsonb=True,
)
