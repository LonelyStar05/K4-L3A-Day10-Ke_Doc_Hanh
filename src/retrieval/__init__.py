from .embeddings import MiniLMEmbeddings
from .index import LocalEmbeddingIndex, SearchResult
from .qa import AnswerResult, answer_question

__all__ = [
    "AnswerResult",
    "LocalEmbeddingIndex",
    "MiniLMEmbeddings",
    "SearchResult",
    "answer_question",
    "build_agent",
    "build_llm",
    "run_agent_question",
]


def __getattr__(name):
    if name in {"build_agent", "run_agent_question"}:
        from . import agent

        return getattr(agent, name)
    if name == "build_llm":
        from .llm import build_llm

        return build_llm
    raise AttributeError(name)
