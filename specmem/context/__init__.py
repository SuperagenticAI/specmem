"""Streaming Context API for SpecMem.

Provides real-time context streaming and token budget optimization for AI agents.
"""

from specmem.context.api import ContextResponse, StreamCompletion, StreamingContextAPI
from specmem.context.estimator import TokenEstimator
from specmem.context.formatter import ContextFormatter
from specmem.context.optimizer import ContextChunk, ContextOptimizer
from specmem.context.profiles import AgentProfile, ProfileManager


__all__ = [
    "AgentProfile",
    "ContextChunk",
    "ContextFormatter",
    "ContextOptimizer",
    "ContextResponse",
    "ProfileManager",
    "StreamCompletion",
    "StreamingContextAPI",
    "TokenEstimator",
]
