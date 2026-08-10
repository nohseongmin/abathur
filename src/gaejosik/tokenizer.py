"""토큰 카운터.

기본은 tiktoken(완전 오프라인). Claude의 토크나이저는 비공개라 정확히 재현할 수
없으므로 o200k_base를 프록시로 쓴다. 실제 Claude 수치가 필요하면 `--anthropic`
으로 Anthropic count_tokens API를 쓸 수 있고, 이때만 텍스트가 외부로 나간다.
"""

from __future__ import annotations

import os
from typing import Protocol

#: tiktoken 인코딩 기본값. GPT-4o/5 계열이 쓰는 최신 BPE로, 한국어 처리도
#: cl100k_base보다 낫다. 대조군으로 cl100k_base를 지정할 수 있다.
DEFAULT_ENCODING = "o200k_base"

#: 실제 Claude 토큰 수를 재고 싶을 때 쓰는 모델. Anthropic 경로에서만 사용.
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"

#: API 키를 읽는 환경변수 이름. 소스에 키를 두지 않는다.
API_KEY_ENV = "ANTHROPIC_API_KEY"


class TokenCounter(Protocol):
    name: str

    def count(self, text: str) -> int: ...


class TiktokenCounter:
    """오프라인 BPE 카운터."""

    def __init__(self, encoding: str = DEFAULT_ENCODING) -> None:
        try:
            import tiktoken
        except ImportError as exc:
            raise RuntimeError(
                "tiktoken이 설치돼 있지 않습니다. `pip install tiktoken`으로 설치하세요."
            ) from exc
        try:
            self._encoding = tiktoken.get_encoding(encoding)
        except (ValueError, KeyError) as exc:
            raise RuntimeError(f"알 수 없는 tiktoken 인코딩: {encoding}") from exc
        self.name = encoding

    def count(self, text: str) -> int:
        if not text:
            return 0
        return len(self._encoding.encode(text))


class AnthropicCounter:
    """Anthropic count_tokens API로 실제 Claude 토큰 수를 센다.

    주의 1: 이 경로에서만 텍스트가 Anthropic 서버로 전송된다. 기본 동작이 아니며,
    `--anthropic`을 명시할 때만 쓰인다.
    주의 2: count_tokens는 메시지 한 통 기준이라 고정 오버헤드가 함께 잡힌다.
    양쪽 문장에 같은 값이 더해지므로 절감률은 실제보다 낮게(보수적으로) 나온다.
    """

    def __init__(self, model: str = DEFAULT_ANTHROPIC_MODEL, client=None) -> None:
        self.name = f"anthropic:{model}"
        self._model = model
        if client is not None:
            self._client = client
            return
        api_key = os.environ.get(API_KEY_ENV)
        if not api_key:
            raise RuntimeError(
                f"{API_KEY_ENV} 환경변수가 없습니다. "
                "실제 Claude 토큰 수를 재려면 키를 설정하거나 tiktoken 기본값을 쓰세요."
            )
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "anthropic SDK가 없습니다. `pip install anthropic`으로 설치하세요."
            ) from exc
        self._client = anthropic.Anthropic(api_key=api_key)

    def count(self, text: str) -> int:
        if not text:
            return 0
        result = self._client.messages.count_tokens(
            model=self._model,
            messages=[{"role": "user", "content": text}],
        )
        return result.input_tokens


def build_counter(encoding: str = DEFAULT_ENCODING, *, use_anthropic: bool = False,
                  model: str = DEFAULT_ANTHROPIC_MODEL) -> TokenCounter:
    if use_anthropic:
        return AnthropicCounter(model)
    return TiktokenCounter(encoding)
