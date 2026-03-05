from dotenv import load_dotenv
from langfuse import get_client

load_dotenv()

# Global Langfuse client
langfuse = get_client()