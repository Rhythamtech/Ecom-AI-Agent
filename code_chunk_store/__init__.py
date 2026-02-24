"""Code chunk store package init."""

"""This package provides a minimal, self-contained MVP for ingesting
database schemas, business logic, and Q&A logic as text chunks and
retrieving them for LLM context assembly.

The implementation is intentionally lightweight and dependency-free to work
in a fresh environment. It uses a simple bag-of-words style vector
representation and cosine similarity for retrieval.
"""
