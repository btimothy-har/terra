docker run \
  --rm \
  --name terra_jobs_$(date +%s) \
  -e ELL_DIR=/src/logdir \
  -e FARGS_LLM_RATE_LIMIT=10 \
  --env-file .env \
  --network services_net_postgres \
  --network services_net_redis \
  --network services_net_neo4j \
  --volume terra_llm_logs:/src/logdir \
  terra_jobs:latest \
  "$@"
