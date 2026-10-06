
"""
This module contains reusable functions"""


from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chat_models import BaseChatModel
import os
from dotenv import load_dotenv

load_dotenv()


def get_model() -> BaseChatModel:
    model = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    return model