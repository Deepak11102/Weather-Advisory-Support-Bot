import os
from dotenv import load_dotenv

load_dotenv()


def get_llm():
    key = os.getenv("GROQ_API_KEY")
    if not key:
        return None
    from langchain_groq import ChatGroq
    return ChatGroq(model=os.getenv("LLM_MODEL", "openai/gpt-oss-120b"), api_key=key, temperature=0)