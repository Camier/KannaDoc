import pytest


@pytest.mark.unit
def test_optional_args_claude_via_cliproxyapi_drops_top_p_when_temperature_set() -> None:
    """Claude (Anthropic) models proxied via CLIProxyAPI may reject specifying both temperature and top_p.

    We prefer temperature for academic/RAG stability.
    """

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="claude-3-5-sonnet",
        provider="cliproxyapi",
        temperature=0.2,
        max_length=2048,
        top_p=0.9,
    )

    assert args.get("temperature") == 0.2
    assert args.get("max_tokens") == 2048
    assert "top_p" not in args


@pytest.mark.unit
def test_optional_args_claude_via_cliproxyapi_clamps_temperature_to_one() -> None:
    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="claude-3-5-sonnet",
        provider="cliproxyapi",
        temperature=1.7,
        max_length=2048,
        top_p=-1,
    )

    assert args.get("temperature") == 1.0


@pytest.mark.unit
def test_optional_args_provider_none_does_not_clamp_temperature() -> None:
    """When provider is unknown (e.g., explicit model_url proxies), do not clamp.

    This avoids breaking OpenAI-compatible proxies with different supported ranges.
    """

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="any-model-via-proxy",
        provider=None,
        temperature=1.7,
        max_length=2048,
        top_p=-1,
    )

    assert args.get("temperature") == 1.7


@pytest.mark.unit
def test_optional_args_minimax_clamps_temperature_to_one_but_keeps_top_p() -> None:
    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="abab6.5s-chat",
        provider="minimax",
        temperature=1.2,
        max_length=2048,
        top_p=0.9,
    )

    assert args.get("temperature") == 1.0
    assert args.get("top_p") == 0.9


@pytest.mark.unit
def test_optional_args_minimax_temperature_zero_is_bumped_above_zero() -> None:
    """MiniMax temperature may be documented as (0, 1]; avoid sending 0.0."""

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="abab6.5s-chat",
        provider="minimax",
        temperature=0.0,
        max_length=2048,
        top_p=-1,
    )

    assert args.get("temperature", 0.0) > 0.0


@pytest.mark.unit
def test_optional_args_minimax_top_p_zero_is_bumped_above_zero() -> None:
    """MiniMax top_p may be documented as (0, 1]; avoid sending 0.0."""

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="abab6.5s-chat",
        provider="minimax",
        temperature=0.2,
        max_length=2048,
        top_p=0.0,
    )

    assert args.get("top_p", 0.0) > 0.0


@pytest.mark.unit
def test_optional_args_zai_top_p_zero_is_bumped_to_min() -> None:
    """Z.ai documents top_p in [0.01, 1]; avoid sending 0.0."""

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="glm-4.5-flash",
        provider="zai",
        temperature=0.2,
        max_length=2048,
        top_p=0.0,
    )

    assert args.get("top_p", 0.0) >= 0.01


@pytest.mark.unit
def test_optional_args_deepseek_reasoner_uses_max_tokens_only() -> None:
    """DeepSeek reasoning models should not receive temperature/top_p."""

    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="deepseek-reasoner",
        provider="deepseek",
        temperature=0.2,
        max_length=1234,
        top_p=0.9,
    )

    assert args == {"max_tokens": 1234}


@pytest.mark.unit
def test_optional_args_deepseek_r1_via_ollama_cloud_is_not_treated_as_reasoner() -> None:
    from app.core.llm.chat_service import ChatService

    args = ChatService._build_optional_openai_args(
        model_name="deepseek-r1",
        provider="ollama-cloud",
        temperature=0.2,
        max_length=2048,
        top_p=0.9,
    )

    assert args.get("temperature") == 0.2
    assert args.get("max_tokens") == 2048
    assert args.get("top_p") == 0.9
