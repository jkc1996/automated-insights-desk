import time
from functools import wraps
from observability.langfuse_client import langfuse


def trace_node(name: str, as_type: str = "span"):
    """
    Langfuse tracing decorator (compatible with Langfuse v3.x)

    Features:
    - automatic span creation
    - latency tracking
    - error tracking
    - span injection into function
    """

    def decorator(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):

            with langfuse.start_as_current_observation(
                name=name,
                as_type=as_type
            ) as span:

                kwargs["span"] = span

                start_time = time.time()

                try:
                    result = await func(*args, **kwargs)

                    latency_ms = (time.time() - start_time) * 1000

                    span.update(
                        metadata={
                            "status": "success",
                            "latency_ms": round(latency_ms, 2)
                        }
                    )

                    return result

                except Exception as e:

                    latency_ms = (time.time() - start_time) * 1000

                    span.update(
                        metadata={
                            "status": "error",
                            "latency_ms": round(latency_ms, 2),
                            "error": str(e)
                        }
                    )

                    raise

        return wrapper

    return decorator