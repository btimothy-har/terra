import os

from langchain_openai import ChatOpenAI
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

PROJECT_NAME = "news_graph"

EMBED_DIM = 1024
EMBED_MODEL = "dunzhang/stella_en_1.5B_v5"

VECTOR_STORE_PARAMS = {
    "host": "postgres",
    "port": "5432",
    "database": "terra",
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
    "hybrid_search": True,
    "embed_dim": EMBED_DIM,
    "use_jsonb": True,
    "hnsw_kwargs": {"hnsw_ef_construction": 400, "hnsw_m": 16, "hnsw_ef_search": 100},
}

SOURCES = [
    "cnn.com",
    "bbc.co.uk",
    "vox.com",
    "globalissues.org",
    "egyptian-gazette.com",
    "cbslocal.com",
    "euronews.com",
    "financialpost.com",
    "time.com",
    "sky.com",
    "washingtonpost.com",
    "cbc.ca",
    "aljazeera.com",
    "channelnewsasia.com",
    "dailymail.co.uk",
    "huffingtonpost.co.uk",
    "independent.co.uk",
    "politico.com",
    "washingtontimes.com",
    "nikkei.com",
    "economist.com.na",
    "hrmasia.com",
    "nationalpost.com",
    "google.com",
    "technode.com",
    "thediplomat.com",
    "asiasentinel.com",
    "bostonherald.com",
    "campaignasia.com",
    "cbsnews.com",
    "cnbc.com",
    "computerworld.com",
    "dailyherald.com",
    "eastasiaforum.org",
    "financeasia.com",
    "huffpost.com",
    "japantimes.co.jp",
    "nytimes.com",
    "politico.eu",
    "theworld.org",
    "rand.org",
    "scmp.com",
    "euronews247.com",
    "theguardian.com",
    "yahoo.com",
    "dailywire.com",
    "reuters.com",
]

llm = ChatOpenAI(
    model="qwen/qwen-2.5-72b-instruct",
    temperature=0,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

embeddings = HuggingFaceEmbedding(
    model_name=EMBED_MODEL, parallel_process=True, num_workers=4
)

splitter = SemanticSplitterNodeParser(
    buffer_size=2,
    embed_model=embeddings,
    breakpoint_percentile_threshold=90,
)
