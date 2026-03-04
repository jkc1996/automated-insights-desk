async def check_user_intent(llm, user_query: str):

    prompt = f"""
Classify the user request into ONE category:

database_analysis
report_generation
out_of_scope

User request:
{user_query}

Return only the category.
"""

    result = await llm.ainvoke(prompt)

    category = result.content.strip().lower()

    if category == "out_of_scope":
        return False, """
I am an Automated Insights Desk assistant.

I can help with:

• SQL database analysis
• retrieving metrics
• generating analytical reports

Please ask a question related to database analytics.
"""

    return True, None