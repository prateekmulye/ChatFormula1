import pytest
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.state import add_messages


def test_add_messages_empty_lists():
    left = []
    right = []
    result = add_messages(left, right)
    assert result == []


def test_add_messages_left_empty():
    left = []
    right = [HumanMessage(content="Hello")]
    result = add_messages(left, right)
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert isinstance(result[0], HumanMessage)


def test_add_messages_right_empty():
    left = [HumanMessage(content="Hello")]
    right = []
    result = add_messages(left, right)
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert isinstance(result[0], HumanMessage)


def test_add_messages_both_populated():
    left = [HumanMessage(content="Hello")]
    right = [AIMessage(content="Hi there!")]
    result = add_messages(left, right)
    assert len(result) == 2
    assert result[0].content == "Hello"
    assert isinstance(result[0], HumanMessage)
    assert result[1].content == "Hi there!"
    assert isinstance(result[1], AIMessage)


def test_add_messages_with_different_message_types():
    left = [HumanMessage(content="Hello")]
    right = [AIMessage(content="Hi there!"), HumanMessage(content="How are you?")]
    result = add_messages(left, right)
    assert len(result) == 3
    assert result[0].content == "Hello"
    assert isinstance(result[0], HumanMessage)
    assert result[1].content == "Hi there!"
    assert isinstance(result[1], AIMessage)
    assert result[2].content == "How are you?"
    assert isinstance(result[2], HumanMessage)
