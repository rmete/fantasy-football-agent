"""
Unified LLM client wrapper supporting Anthropic, OpenAI, and Google Gemini
"""
from typing import Dict, Any, List, Optional
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified interface for multiple LLM providers"""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider or settings.LLM_PROVIDER
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the appropriate client based on provider"""
        if self.provider == "anthropic":
            from anthropic import Anthropic
            if not settings.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY not set")
            self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("Initialized Anthropic client")

        elif self.provider == "openai":
            from openai import OpenAI
            if not settings.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY not set")
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("Initialized OpenAI client")

        elif self.provider == "gemini":
            import google.generativeai as genai
            if not settings.GEMINI_API_KEY:
                raise ValueError("GEMINI_API_KEY not set")
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.client = genai
            logger.info("Initialized Gemini client")

        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

    def create_message(
        self,
        model: str,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> str:
        """
        Create a message using the configured LLM provider

        Returns the text response from the model
        """
        if self.provider == "anthropic":
            return self._create_anthropic_message(
                model, system, messages, max_tokens, temperature
            )
        elif self.provider == "openai":
            return self._create_openai_message(
                model, system, messages, max_tokens, temperature
            )
        elif self.provider == "gemini":
            return self._create_gemini_message(
                model, system, messages, max_tokens, temperature
            )

    def _create_anthropic_message(
        self,
        model: str,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Create message using Anthropic Claude"""
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages
        )
        return response.content[0].text

    def _create_openai_message(
        self,
        model: str,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Create message using OpenAI GPT"""
        # Convert messages format
        openai_messages = [{"role": "system", "content": system}]
        openai_messages.extend(messages)

        response = self.client.chat.completions.create(
            model=model,
            messages=openai_messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content

    def _create_gemini_message(
        self,
        model: str,
        system: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> str:
        """Create message using Google Gemini"""
        # Gemini doesn't have a separate system prompt, prepend to first message
        gemini_model = self.client.GenerativeModel(model)

        # Combine system prompt with user message
        combined_prompt = f"{system}\n\n{messages[0]['content']}"

        response = gemini_model.generate_content(
            combined_prompt,
            generation_config={
                "max_output_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        return response.text

    def _get_anthropic_model_id(self) -> str:
        """Get the configured Anthropic model ID"""
        valid_models = [
            "claude-sonnet-4-5-20250929",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]

        model_choice = settings.ANTHROPIC_MODEL
        if model_choice not in valid_models:
            logger.warning(
                f"Unknown ANTHROPIC_MODEL '{model_choice}'. "
                f"Valid options: {valid_models}. Defaulting to 'claude-sonnet-4-5-20250929'"
            )
            model_choice = "claude-sonnet-4-5-20250929"

        return model_choice

    def get_model_name(self, agent_type: str) -> str:
        """Get the appropriate model name for each provider"""
        # Get the configured Anthropic model
        anthropic_model = self._get_anthropic_model_id()

        # Model mappings for different providers
        model_mappings = {
            "anthropic": {
                "orchestrator": anthropic_model,
                "sit_start": anthropic_model,
                "trade": anthropic_model,
                "waiver": anthropic_model,
                "lineup": anthropic_model,
                "chat": anthropic_model,
            },
            "openai": {
                "orchestrator": "gpt-4o",
                "sit_start": "gpt-4o",
                "trade": "gpt-4o",
                "waiver": "gpt-4o",
                "lineup": "gpt-4o",
                "chat": "gpt-4o",
            },
            "gemini": {
                "orchestrator": "gemini-1.5-pro",
                "sit_start": "gemini-1.5-pro",
                "trade": "gemini-1.5-pro",
                "waiver": "gemini-1.5-pro",
                "lineup": "gemini-1.5-pro",
                "chat": "gemini-1.5-pro",
            },
        }

        return model_mappings[self.provider].get(
            agent_type,
            model_mappings[self.provider]["orchestrator"]
        )


# Create singleton instance
llm_client = LLMClient()
