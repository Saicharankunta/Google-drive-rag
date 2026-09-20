from __future__ import annotations

from src.config import Settings


SYSTEM_PROMPT = """You are a helpful assistant that answers questions using only the provided context from Google Drive documents.
If the answer is not in the context, say you don't know based on the indexed documents.
Cite the source file name when possible.
Format answers in Markdown (headings, lists, bold, code blocks) when it improves clarity."""


def build_messages(question: str, context: str) -> list[dict[str, str]]:
    user_content = f"""Context from Google Drive:
---
{context}
---

Question: {question}"""
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def generate(self, question: str, context: str) -> str:
        messages = build_messages(question, context)
        provider = self._settings.llm_provider

        if provider == "groq":
            return self._generate_groq(messages)
        if provider == "ollama":
            return self._generate_ollama(messages)

        raise ValueError(f"Unknown LLM_PROVIDER: {provider}. Use 'groq' or 'ollama'.")

    def _generate_groq(self, messages: list[dict[str, str]]) -> str:
        if not self._settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when LLM_PROVIDER=groq")

        from groq import Groq

        client = Groq(api_key=self._settings.groq_api_key)
        response = client.chat.completions.create(
            model=self._settings.groq_model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    def _generate_ollama(self, messages: list[dict[str, str]]) -> str:
        import httpx

        response = httpx.post(
            f"{self._settings.ollama_base_url}/api/chat",
            json={
                "model": self._settings.ollama_llm_model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=300.0,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]
