async def check_user_intent(llm, user_query: str, history: list[str] | None = None):

    history_text = ""

    if history:
        history_text = "\n".join(history[-3:])  # last 3 turns

    prompt = f"""
You are an intent classifier for a data analytics assistant.

Possible categories:
- database_analysis
- report_generation
- out_of_scope

Conversation history:
{history_text}

User request:
{user_query}

Rules:
• If the user asks about metrics, revenue, growth, database queries → database_analysis
• If the user asks to generate or save reports → report_generation
• If the request is unrelated to data analytics → out_of_scope
• Short follow-ups like "what about March?" should inherit intent from history, do not block use in this case. he/she may be referring to previous question about metrics or reports.

Return ONLY the category.
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