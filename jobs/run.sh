docker build -t terra_jobs:latest .

docker run \
  --rm \
  --name terra_jobs_$(date +%s) \
  --env-file .env \
  --network services_net_postgres \
  --network services_net_redis \
  --network services_net_neo4j \
  --volume services_terra_llm_logs:/src/logdir \
  terra_jobs \
  "$@"