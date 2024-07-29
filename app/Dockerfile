FROM python:3.12.4

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health
ENTRYPOINT ["streamlit", "run", "main.py", "--server.port=8501", "--server.headless=true", "--server.enableCORS=false", "--server.baseUrlPath=/chat", "--browser.gatherUsageStats=false", "--theme.base=dark"]