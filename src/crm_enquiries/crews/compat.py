"""CrewAI provider compatibility shims.

CrewAI 1.15.x injects ``cache_breakpoint`` into all LLM messages for prompt
caching. Anthropic handles it; Groq and other providers reject it with 400.
See: https://github.com/crewAIInc/crewAI/issues/5886
"""

from __future__ import annotations


def apply_crewai_compat() -> None:
    import crewai.llms.cache as crewai_cache

    crewai_cache.mark_cache_breakpoint = lambda msg: msg

    try:
        import litellm

        litellm.drop_params = True
    except ImportError:
        pass


apply_crewai_compat()
