from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()

langfuse = get_client()


def main():

    print("Starting Langfuse test...")

    # Root span (acts as trace)
    with langfuse.start_as_current_observation(
        name="user_question",
        as_type="span"
    ) as root_span:

        root_span.update(
            input="Find revenue growth between Feb and March 2026"
        )

        # Router span
        with langfuse.start_as_current_observation(
            name="router_supervisor",
            as_type="span"
        ) as router_span:

            router_span.update(
                metadata={
                    "decision": "analyze_database"
                }
            )

        # LLM generation
        with langfuse.start_as_current_observation(
            name="analyst_reasoning",
            as_type="generation",
            model="gpt-4o"
        ) as generation:

            generation.update(
                input="Generate SQL for revenue growth"
            )

            generation.update(
                output="SELECT revenue FROM company_metrics WHERE month IN ('Feb','Mar')"
            )

        # Tool span
        with langfuse.start_as_current_observation(
            name="analyst_tool_execution",
            as_type="span"
        ) as tool_span:

            tool_span.update(
                metadata={
                    "sql_query": "SELECT revenue FROM company_metrics..."
                }
            )

            tool_span.update(
                output="Feb=133000, Mar=139000"
            )

        root_span.update(
            output="Growth = 4.51%"
        )

    # Important for short scripts
    langfuse.flush()

    print("Langfuse test finished.")


if __name__ == "__main__":
    main()