from functools import wraps
from typing import Any, Callable, Coroutine
from dotenv import load_dotenv
from langfuse import Langfuse

load_dotenv()

langfuse = Langfuse()


def trace_node(name: str):
    """
    Decorator for tracing LangGraph nodes with Langfuse.
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):

        @wraps(func)
        async def wrapper(*args, **kwargs):

            span = langfuse.start_span(name=name)

            try:
                result = await func(*args, **kwargs)

                span.update(
                    output=str(result)
                )

                return result

            except Exception as e:
                span.update(
                    level="ERROR",
                    status_message=str(e)
                )
                raise

            finally:
                span.end()

        return wrapper

    return decorator