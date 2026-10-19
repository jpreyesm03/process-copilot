"""The topic gate's decision logic, with a scripted model (no network)."""

from agentkit.llm import LLMResponse
from agentkit.topic import TopicGate


class Reply:
    def __init__(self, text=None, error=False):
        self.text, self.error = text, error

    def chat(self, messages, tools=None):
        if self.error:
            raise RuntimeError("429")
        return LLMResponse(content=self.text, tokens_in=90, tokens_out=5)


def test_allow_block_and_undecided():
    assert TopicGate(Reply("ALLOW"), "orders").check("Which vendors are slow?").allowed is True
    assert TopicGate(Reply("BLOCK."), "orders").check("Write a poem").allowed is False
    assert TopicGate(Reply("Maybe, it depends"), "orders").check("?").allowed is None


def test_provider_errors_fail_closed():
    assert TopicGate(Reply(error=True), "orders").check("Which vendors are slow?").allowed is None


def test_policy_names_the_domain():
    assert "purchase orders" in TopicGate(Reply("ALLOW"), "purchase orders").system
