FROM python:3.12.4

### Messy workaround to get the latest version of ChatOllama with support for base_url
RUN apt-get -y update
RUN apt-get -y install git

RUN git clone https://github.com/langchain-ai/langchain.git
RUN cd langchain/libs/partners/ollama && pip install -e .
RUN cd
### End of workaround

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir "psycopg[binary]" \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.headless=true", "--server.enableCORS=false", "--server.baseUrlPath=/chat", "--browser.gatherUsageStats=false", "--theme.base=dark"]