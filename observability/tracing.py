from functools import wraps
from observability.langfuse_client import langfuse


def trace_node(name: str, as_type: str = "span"):
    """
    Langfuse tracing decorator compatible with Langfuse v3.x
    """

    def decorator(func):

        @wraps(func)
        async def wrapper(*args, **kwargs):

            with langfuse.start_as_current_observation(
                name=name,
                as_type=as_type
            ) as span:

                kwargs["span"] = span

                try:
                    result = await func(*args, **kwargs)

                    span.update(
                        metadata={"status": "completed"}
                    )

                    return result

                except Exception as e:

                    span.update(
                        metadata={
                            "status": "error",
                            "error": str(e)
                        }
                    )

                    raise

        return wrapper

    return decorator