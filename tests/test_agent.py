from __future__ import annotations

from dataclasses import replace
import unittest

from core.config import load_settings, require_llm_credentials
from retrieval.agent import build_agent, run_agent_question


class EmptyIndex:
    def search(self, query: str, top_k: int = 4):
        del query, top_k
        return []

    def lookup(self, value: str):
        del value
        return None


class AgentTests(unittest.TestCase):
    def test_mock_provider_builds_and_answers_without_credentials(self) -> None:
        settings = replace(load_settings(), llm_provider="mock", model_name="mock")
        require_llm_credentials(settings)

        agent = build_agent(settings, EmptyIndex())

        self.assertEqual(
            run_agent_question(agent, "What papers are indexed?"),
            "I don't know from the indexed corpus.",
        )

    def test_real_provider_requires_its_key(self) -> None:
        settings = replace(load_settings(), llm_provider="openai", openai_api_key=None)
        with self.assertRaisesRegex(RuntimeError, "OPENAI_API_KEY"):
            require_llm_credentials(settings)


if __name__ == "__main__":
    unittest.main()
