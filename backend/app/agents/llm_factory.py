import os
from typing import Type, TypeVar, Optional
from pydantic import BaseModel
from google import genai
from openai import OpenAI
from app.config import settings

T = TypeVar("T", bound=BaseModel)

class LLMFactory:
    """
    Centralized LLM Factory providing automatic fallback support:
    - Primary: OpenAI (if valid API key & quota available)
    - Fallback: Google Gemini (gemini-3.5-flash-lite / gemini-3.5-flash)
    - Extensible: Easy to append Claude, DeepSeek, Ollama, etc.
    """

    @staticmethod
    def get_gemini_client() -> Optional[genai.Client]:
        gemini_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if gemini_key:
            return genai.Client(api_key=gemini_key)
        return None

    @staticmethod
    def get_openai_client() -> Optional[OpenAI]:
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key and not openai_key.startswith("sk-proj-invalid"):
            return OpenAI(api_key=openai_key)
        return None

    @classmethod
    def parse_structured(
        cls,
        prompt: str,
        response_schema: Type[T],
        system_prompt: str = "",
        image_b64: Optional[str] = None,
        mime_type: Optional[str] = "image/png"
    ) -> T:
        """
        Parses structured data into a Pydantic schema using OpenAI or Gemini fallback.
        """
        # 1. Try OpenAI if configured
        openai_client = cls.get_openai_client()
        if openai_client:
            try:
                user_content = []
                if image_b64:
                    user_content.append({
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime_type};base64,{image_b64}"}
                    })
                    user_content.append({"type": "text", "text": prompt})
                else:
                    user_content = prompt

                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_content})

                model_name = settings.OPENAI_MODEL if settings.OPENAI_MODEL and "luna" not in settings.OPENAI_MODEL else "gpt-4o-mini"

                completion = openai_client.beta.chat.completions.parse(
                    model=model_name,
                    messages=messages,
                    response_format=response_schema
                )
                if completion.choices and completion.choices[0].message.parsed:
                    return completion.choices[0].message.parsed
            except Exception as e:
                print(f"[LLMFactory] OpenAI request failed or quota exceeded: {e}. Falling back to Gemini...")

        # 2. Fallback to Gemini
        gemini_client = cls.get_gemini_client()
        if gemini_client:
            try:
                contents = []
                if image_b64:
                    import base64
                    img_bytes = base64.b64decode(image_b64)
                    contents.append({
                        "inline_data": {
                            "mime_type": mime_type or "image/png",
                            "data": img_bytes
                        }
                    })
                
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                contents.append(full_prompt)

                # Strip additionalProperties for Gemini compatibility
                def clean_schema(s: dict) -> dict:
                    if isinstance(s, dict):
                        s.pop("additionalProperties", None)
                        s.pop("title", None)
                        for v in s.values():
                            clean_schema(v)
                    elif isinstance(s, list):
                        for item in s:
                            clean_schema(item)
                    return s

                json_schema = clean_schema(response_schema.model_json_schema())

                # Gemini structured response via response_schema
                response = gemini_client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=contents,
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": json_schema
                    }
                )
                
                if response.text:
                    return response_schema.model_validate_json(response.text)
            except Exception as ge:
                print(f"[LLMFactory] Gemini request failed: {ge}")

        raise RuntimeError("Both OpenAI and Gemini LLM providers failed or have invalid credentials.")

def get_model():
    """Helper method returning the active LLMFactory instance."""
    return LLMFactory()
