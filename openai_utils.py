import sys
import logging

import openai
import tiktoken

from tenacity import (
    retry,
    stop_after_attempt,
    wait_random_exponential,
    after_log,
)  # for exponential backoff

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAI_PRICING = {
    'gpt-35-turbo': {'prompt': 0.0015, 'completion': 0.002},
    'gpt-35-turbo-16k': {'prompt': 0.003, 'completion': 0.004},
    'gpt-4-0613': {'prompt': 0.03, 'completion': 0.06},
    'gpt-4-32k': {'prompt': 0.06, 'completion': 0.12},
    'embedding': {'hugging_face': 0, 'text-embedding-ada-002': 0.0001}
    }


OPENAI_MODEL_CONTEXT_LENGTH = {
    'gpt-35-turbo': 4097,
    'gpt-35-turbo-16k': 16385,
    'gpt-4-0613': 8192,
    'gpt-4-32k': 32768
    }


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(20),
    after=after_log(logger, logging.INFO),
)
def completion_with_backoff(**kwargs):
    return openai.ChatCompletion.create(**kwargs)


def llm_call_cost(response):
    """Returns the cost of the LLM call in dollars"""
    model = response["model"]
    usage = response["usage"]
    prompt_cost = OPENAI_PRICING[model]["prompt"]
    completion_cost = OPENAI_PRICING[model]["completion"]
    prompt_token_cost = (usage["prompt_tokens"] * prompt_cost)/1000
    completion_token_cost = (usage["completion_tokens"] * completion_cost)/1000
    return prompt_token_cost + completion_token_cost


def llm_call(model,
             function_schema=None,
             output_schema=None,
             system_prompt="You are an AI assistant that answers user questions using the context provided.",
             user_prompt="Please help me answer the following question:"):

    kwargs = {}
    if function_schema is not None:
        kwargs["functions"] = function_schema
    if output_schema is not None:
        kwargs["function_call"] = output_schema

    response = completion_with_backoff(
        model=model,
        temperature=0,
        messages=[
            {"role": "system",
                "content": system_prompt},
            {"role": "user",
                "content": user_prompt}
        ],
        **kwargs
    )

    # print cost of call
    call_cost = llm_call_cost(response)
    print(f"🤑 LLM call cost: ${call_cost:.4f}")
    return response, call_cost


def get_num_tokens_simple(model, prompt):
    """Estimate the number of tokens in the prompt using tiktoken"""
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(prompt))
    return num_tokens
