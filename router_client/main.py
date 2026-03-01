# router_client/main.py
from router_client.graph_state import get_checkpointer
# ... other imports ...

def process_chat(user_input: str, thread_id: str):
    with get_checkpointer() as checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the graph and get the final output
        result = app.invoke({"messages": [("user", user_input)]}, config=config)
        return result["messages"][-1].content