"""Test Mapping Engine for SpecMem.

Provides framework-agnostic test mapping and code analysis capabilities.
"""

from specmem.testing.analyzer import CodeAnalyzer, SpecCandidate
from specmem.testing.engine import TestMappingEngine
from specmem.testing.frameworks import TestFramework


__all__ = [
    "CodeAnalyzer",
    "SpecCandidate",
    "TestFramework",
    "TestMappingEngine",
]
