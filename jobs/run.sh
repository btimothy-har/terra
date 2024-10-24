docker build -t terra_jobs:latest .

docker run \
  --rm \
  --name terra_jobs_$(date +%s) \
  --env-file .env \
  -e POSTGRES_USER=${POSTGRES_USER} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e NEWS_API_KEY=${NEWS_API_KEY} \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  --network services_net_postgres \
  --network services_net_redis \
  --network services_net_neo4j \
  --volume terra_llm_logs:/src/logdir \
  terra_jobs:latest \
  "$@"