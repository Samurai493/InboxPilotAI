"""Tests for workflow token usage aggregation."""
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, LLMResult

from app.services.llm_token_usage import WorkflowTokenUsageCallback, _extract_from_llm_result


def test_extract_openai_style_llm_output():
    response = LLMResult(
        generations=[[]],
        llm_output={"token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}},
    )
    u = _extract_from_llm_result(response)
    assert u["input_tokens"] == 10
    assert u["output_tokens"] == 5
    assert u["total_tokens"] == 15


def test_extract_from_chat_generation_response_metadata():
    msg = AIMessage(
        content="hi",
        response_metadata={"token_usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}},
    )
    response = LLMResult(
        generations=[[ChatGeneration(message=msg)]],
        llm_output={},
    )
    u = _extract_from_llm_result(response)
    assert u["input_tokens"] == 3
    assert u["output_tokens"] == 2
    assert u["total_tokens"] == 5


def test_callback_dedupes_same_run_id():
    cb = WorkflowTokenUsageCallback()
    response = LLMResult(
        generations=[[]],
        llm_output={"token_usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
    )
    cb.on_chat_model_end(response, run_id="same")
    cb.on_llm_end(response, run_id="same")
    s = cb.get_summary()
    assert s["totals"]["llm_calls"] == 1
    assert s["totals"]["total_tokens"] == 2
