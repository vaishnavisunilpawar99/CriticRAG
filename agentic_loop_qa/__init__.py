"""
CRITIC — Trustworthy AI through Iterative Self-Correction
AgenticLoopQA: Autonomous Multi-Agent Reasoning with Self-Reflection

A small, dependency-light framework for open-domain question answering
in which a Generator agent proposes an answer, a Critic agent checks it
against retrieved evidence and its own reasoning, and a Refiner agent
revises the answer until the Critic approves or a budget is exhausted.
"""

__version__ = "0.1.0"
