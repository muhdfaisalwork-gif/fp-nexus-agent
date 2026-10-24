import os
import json
import requests
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        pass


class OpenRouterProvider(BaseLLMProvider):
    """
    OpenRouter Multi-Model Provider.
    Defaults to 100% free models with automatic free-tier fallback chain.
    """
    FREE_MODELS = [
        "qwen/qwen3.8-27b:free",
        "google/gemma-4-26b-a4b-it:free",
        "liquid/lfm-2.5-2.6b:free",
        "nvidia/nemotron-3.5-lightning:free",
        "cohere/north-mini-code:free",
        "apodex/apodex-1.1-mini:free",
        "thinkingmachines/inkling:free"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        fallback_models: Optional[List[str]] = None
    ):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.model = model or os.getenv("OPENROUTER_MODEL") or self.FREE_MODELS[0]
        fallbacks_env = os.getenv("OPENROUTER_FALLBACK_MODELS", "")
        if fallback_models:
            self.fallback_models = fallback_models
        elif fallbacks_env:
            self.fallback_models = [m.strip() for m in fallbacks_env.split(",") if m.strip()]
        else:
            self.fallback_models = [m for m in self.FREE_MODELS if m != self.model]

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenRouter API key is missing. Set OPENROUTER_API_KEY in .env or Settings.")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Try active model then free fallback models
        models_to_try = [self.model] + [m for m in self.fallback_models if m != self.model]
        last_error = None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/muhdfaisalwork-gif/fp-nexus-agent",
            "X-Title": "FP Nexus Freelance Agent",
            "Content-Type": "application/json"
        }

        for model_candidate in models_to_try:
            payload = {
                "model": model_candidate,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            timeout = int(os.getenv("OPENROUTER_TIMEOUT", "15"))
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        msg = choices[0].get("message", {})
                        content = msg.get("content")
                        if not content and msg.get("reasoning"):
                            content = msg.get("reasoning")
                        if content and isinstance(content, str) and content.strip():
                            return content
                    last_error = f"Model {model_candidate} returned empty content"
                    continue
                else:
                    # If daily free quota is exceeded account-wide, break immediately to failover
                    if "free-models-per-day" in resp.text:
                        last_error = f"OpenRouter daily free quota exhausted: {resp.text[:150]}"
                        break
                    # Rate limit (429), unavailable (404), or service error (5xx), fallback to next candidate
                    last_error = f"Model {model_candidate} returned HTTP {resp.status_code}: {resp.text[:150]}"
                    continue
            except Exception as e:
                last_error = str(e)
                continue

        raise RuntimeError(f"All attempted OpenRouter models failed. Last error: {last_error}")



class OllamaProvider(BaseLLMProvider):
    """
    Local Ollama Provider. 100% Free, zero external network dependency.
    Auto-detects available installed models if the requested model is not found.
    """
    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL") or "qwen3:8b"
        self._ensure_available_model()

    def _ensure_available_model(self):
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                installed = [m.get("name", "") for m in r.json().get("models", [])]
                installed_clean = [name.split(":")[0] for name in installed]
                if self.model not in installed and self.model.split(":")[0] not in installed_clean:
                    # Select best available model from priority order
                    preferred_order = [
                        "deepcoder:1.5b", "qwen3:8b", "deepseek-r1:8b", "qwen3.5:latest",
                        "qwen3.5:4b", "qwen2.5-coder:7b", "qwen2.5-coder:14b", "gemma4:e4b"
                    ]
                    for pref in preferred_order:
                        if pref in installed or pref.split(":")[0] in installed_clean:
                            self.model = pref
                            return
                    if installed:
                        self.model = installed[0]
        except Exception:
            pass

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        import re
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "15"))
        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                # Strip chain-of-thought tokens from reasoning models (DeepSeek-R1 / Qwen thinking)
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                return content
            raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
        except Exception as e:
            raise RuntimeError(f"Failed to communicate with local Ollama at {self.base_url}: {e}")


class OpenAIProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            raise ValueError("OpenAI API key missing.")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=45
        )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and isinstance(content, str) and content.strip():
                    return content
            raise RuntimeError(f"OpenAI returned empty content: {resp.text[:150]}")
        raise RuntimeError(f"OpenAI error {resp.status_code}: {resp.text}")


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.model = model or os.getenv("ANTHROPIC_MODEL") or "claude-3-5-sonnet-20241022"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            raise ValueError("Anthropic API key missing.")
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            content_list = data.get("content", [])
            if content_list and "text" in content_list[0]:
                text = content_list[0]["text"]
                if text and isinstance(text, str) and text.strip():
                    return text
            raise RuntimeError(f"Anthropic returned empty text: {resp.text[:150]}")
        raise RuntimeError(f"Anthropic error {resp.status_code}: {resp.text}")


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model = model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash"

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        if not self.api_key:
            raise ValueError("Gemini API key missing.")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        parts = []
        if system_prompt:
            parts.append({"text": f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"})
        parts.append({"text": prompt})

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        resp = requests.post(url, json=payload, timeout=45)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts_list = candidates[0].get("content", {}).get("parts", [])
                if parts_list and "text" in parts_list[0]:
                    txt = parts_list[0]["text"]
                    if txt and isinstance(txt, str) and txt.strip():
                        return txt
            raise RuntimeError(f"Gemini returned empty text: {resp.text[:150]}")
        raise RuntimeError(f"Gemini error {resp.status_code}: {resp.text}")


class CustomOpenAICompatibleProvider(BaseLLMProvider):
    def __init__(self, base_url: str, api_key: str = "", model: str = "default"):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1500
    ) -> str:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        resp = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json={"model": self.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens},
            timeout=45
        )
        if resp.status_code == 200:
            data = resp.json()
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content")
                if content and isinstance(content, str) and content.strip():
                    return content
            raise RuntimeError(f"Custom endpoint returned empty content: {resp.text[:150]}")
        raise RuntimeError(f"Custom endpoint error {resp.status_code}: {resp.text}")

