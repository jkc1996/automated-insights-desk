# router_client/graph_state.py
import os
from langgraph.checkpoint.redis import RedisSaver

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379/0")

def get_checkpointer():
    """Initializes the Redis connection and ensures indexes are created."""
    checkpointer = RedisSaver.from_conn_string(REDIS_URI)
    
    # IMPORTANT: initialize indexes (ONE TIME ONLY)
    checkpointer.setup()
    
    return checkpointer