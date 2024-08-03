from redis.asyncio import Redis

async def get_redis_client() -> Redis:
    # redis = Redis(
    #     host=REDIS_HOST,
    #     port=REDIS_PORT,
    #     decode_responses=True
    # )
    print("get_redis_client")
    return "world"