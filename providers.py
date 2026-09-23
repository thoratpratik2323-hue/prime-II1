"""
providers.py — Free LLM API Directory & Switcher for Prime AI.
Curated from awesome-free-llm-apis (509+ free models from 31 providers).
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

FREE_PROVIDERS: List[Dict[str, Any]] = [
    {
        "id": "gemini",
        "name": "Google Gemini",
        "env_var": "GEMINI_API_KEY",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "default_model": "gemini-3.6-flash",
        "free_tier": "15 RPM, 1,500 RPD, 1M Context Window",
        "credit_card": "NO",
        "speed": "⚡⚡⚡⚡ Extremely Fast (~120 t/s)",
        "signup_url": "https://aistudio.google.com/app/apikey",
        "recommended_models": ["gemini-3.6-flash", "gemini-2.5-flash", "gemini-2.5-pro"]
    },
    {
        "id": "groq",
        "name": "Groq LPU (Ultra-Fast)",
        "env_var": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "openai/gpt-oss-120b",
        "free_tier": "30 RPM, 14,400 RPD, 500+ tokens/sec",
        "credit_card": "NO",
        "speed": "⚡⚡⚡⚡⚡ Blazing (~550 t/s)",
        "signup_url": "https://console.groq.com/keys",
        "recommended_models": ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"]
    },
    {
        "id": "cerebras",
        "name": "Cerebras AI (World's Fastest Inference)",
        "env_var": "CEREBRAS_API_KEY",
        "base_url": "https://api.cerebras.ai/v1",
        "default_model": "llama3.3-70b",
        "free_tier": "30 RPM, 1M tokens/day, 2000 tokens/sec",
        "credit_card": "NO",
        "speed": "⚡⚡⚡⚡⚡ Ludicrous Speed (~2100 t/s)",
        "signup_url": "https://cloud.cerebras.ai/",
        "recommended_models": ["llama3.3-70b", "llama3.1-8b"]
    },
    {
        "id": "github",
        "name": "GitHub Models (Azure AI)",
        "env_var": "GITHUB_TOKEN",
        "base_url": "https://models.github.ai/inference",
        "default_model": "gpt-4o",
        "free_tier": "15 RPM, 150 RPD (Free GitHub Personal Access Token)",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Fast (~60 t/s)",
        "signup_url": "https://github.com/marketplace/models",
        "recommended_models": ["gpt-4o", "gpt-4o-mini", "Meta-Llama-3.3-70B-Instruct"]
    },
    {
        "id": "openrouter",
        "name": "OpenRouter (Aggregator)",
        "env_var": "OPENROUTER_API_KEY",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "nvidia/nemotron-3.5-lightning:free",
        "free_tier": "35+ permanently free models (:free suffix)",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Variable (~80 t/s)",
        "signup_url": "https://openrouter.ai/keys",
        "recommended_models": [
            "nvidia/nemotron-3.5-lightning:free",
            "qwen/qwen3.8-27b:free",
            "nex-agi/nex-n2.5-pro:free"
        ]
    },
    {
        "id": "mistral",
        "name": "Mistral AI",
        "env_var": "MISTRAL_API_KEY",
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "codestral-latest",
        "free_tier": "1 RPS, 1B tokens/month (La Plateforme Experimentation)",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Fast (~90 t/s)",
        "signup_url": "https://console.mistral.ai/api-keys",
        "recommended_models": ["codestral-latest", "mistral-small-latest", "pixtral-12b"]
    },
    {
        "id": "deepseek",
        "name": "DeepSeek Official",
        "env_var": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "free_tier": "Free initial trial tokens upon sign up",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Moderate (~50 t/s)",
        "signup_url": "https://platform.deepseek.com/api_keys",
        "recommended_models": ["deepseek-chat", "deepseek-reasoner"]
    },
    {
        "id": "ollama",
        "name": "Ollama (100% Local & Offline)",
        "env_var": "OLLAMA_HOST",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.2:latest",
        "free_tier": "Unlimited (100% Local on your Hardware, Zero Cost, Zero API Key)",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Local Hardware Speed",
        "signup_url": "https://ollama.com/",
        "recommended_models": ["llama3.2:latest", "qwen2.5:latest", "mistral:latest", "deepseek-r1:1.5b"]
    },
    {
        "id": "nvidia",
        "name": "NVIDIA NIM",
        "env_var": "NVIDIA_API_KEY",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "default_model": "meta/llama-3.3-70b-instruct",
        "free_tier": "1,000 free inference credits (Phone verification)",
        "credit_card": "NO",
        "speed": "⚡⚡⚡⚡ Very Fast (~140 t/s)",
        "signup_url": "https://build.nvidia.com/settings/api-keys",
        "recommended_models": ["meta/llama-3.3-70b-instruct", "deepseek-ai/deepseek-r1"]
    },
    {
        "id": "cloudflare",
        "name": "Cloudflare Workers AI",
        "env_var": "CLOUDFLARE_API_KEY",
        "base_url": "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1",
        "default_model": "@cf/meta/llama-3.3-70b-instruct",
        "free_tier": "10,000 Neurons/day free permanently",
        "credit_card": "NO",
        "speed": "⚡⚡⚡ Fast (~85 t/s)",
        "signup_url": "https://dash.cloudflare.com/profile/api-tokens",
        "recommended_models": ["@cf/meta/llama-3.3-70b-instruct", "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"]
    }
]


def get_providers_list() -> List[Dict[str, Any]]:
    return FREE_PROVIDERS


def get_provider_by_id(provider_id: str) -> Optional[Dict[str, Any]]:
    p_id = provider_id.lower().strip()
    for p in FREE_PROVIDERS:
        if p["id"] == p_id:
            return p
    return None


def get_provider_key(provider_id: str) -> str:
    p = get_provider_by_id(provider_id)
    if not p:
        return ""
    env_var = p.get("env_var", "")
    return (os.getenv(env_var) or "").strip()


def is_provider_configured(provider_id: str) -> bool:
    return bool(get_provider_key(provider_id))
