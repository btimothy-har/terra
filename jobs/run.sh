docker build -t terra_jobs:latest .

docker run \
  --rm \
  --name terra_jobs_$(date +%s) \
  -v "$(pwd)/.artifacts:/src/artifacts" \
  -e ENV=${ENV} \
  -e ELL_DB=ell_studio \
  -e FARGS_LLM_TOKEN_LIMIT=1000000 \
  -e POSTGRES_DB=terra \
  -e POSTGRES_USER=${POSTGRES_USER} \
  -e POSTGRES_PASSWORD=${POSTGRES_PASSWORD} \
  -e NEO4J_PASSWORD=${NEO4J_PASSWORD} \
  -e NEWS_API_KEY=${NEWS_API_KEY} \
  -e OPENROUTER_API_KEY=${OPENROUTER_API_KEY} \
  -e OPENAI_API_KEY=${OPENAI_API_KEY} \
  -e PPLX_API_KEY=${PPLX_API_KEY} \
  --network terra_internal \
  --network services_net_postgres \
  --network services_net_redis \
  --network services_net_neo4j \
  terra_jobs:latest \
  "$@"