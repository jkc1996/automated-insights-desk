# # router_client/graph_state.py
# from langgraph.checkpoint.redis import RedisSaver

# def get_checkpointer():
#     """
#     FIXED: Pass the URL string directly to RedisSaver.
#     The checkpointer will handle the connection factory internally.
#     """
#     redis_url = "redis://localhost:6379"
    
#     # Do not create a 'redis.from_url' object here. 
#     # Just pass the string.
#     checkpointer = RedisSaver.from_conn_string(redis_url)
    
#     return checkpointer