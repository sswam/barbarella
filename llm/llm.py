#!/usr/bin/env python3

"""
llm.py: A simple wrapper for various language model APIs including OpenAI ChatGPT,
Anthropic's Claude, Perplexity, and Google models.
"""

# TODO create compatible libraries for other APIs in future
# TODO consider splitting off the OpenAI specific stuff into a separate library
# TODO use cached responses if possible

import sys

from sys import stdin, stdout
import os
import logging
import re
from typing import IO
from math import inf
import time
import random
from pathlib import Path
import textwrap
import asyncio
import json

import argh
import tab
import tiktoken
from slugify import slugify

from ally import main

# TODO slow modules, to load dynamically in future
import openai
from openai import AsyncOpenAI
import anthropic
import claude
import google.generativeai as genai
from transformers import AutoTokenizer

def load_module(module_name):
    import importlib
    globals()[module_name] = importlib.import_module(module_name)

__version__ = "0.1.2"

logger = logging.getLogger(__name__)


# Settings

LOGDIR = Path(os.environ["HOME"])/"llm.log"
LOGFILE_NAME_MAX_LEN = 100
RETRIES = 20
exceptions_to_retry = (openai.RateLimitError, openai.APIConnectionError, openai.InternalServerError,
	anthropic.RateLimitError, anthropic.APIConnectionError, anthropic.InternalServerError)

default_model = 'claude'
default_model_small = 'gpt-4o-mini'

MODELS = {
	"o1-preview": {
		"alias": ["op", "gertie"],
		"vendor": "openai",
		"description": "The o1 series of large language models are trained with reinforcement learning to perform complex reasoning. o1 models think before they answer, producing a long internal chain of thought before responding to the user.",
		"cost_in": 15,
		"cost_out": 60,
	},
	"o1-mini": {
		"alias": ["om", "feyn"],
		"vendor": "openai",
		"description": "A faster, cheaper reasoning model particularly effective for coding. o1-mini is 80% cheaper than o1-preview, offering a cost-effective solution for applications requiring reasoning but not broad knowledge.",
		"cost_in": 3,
		"cost_out": 12,
	},
	"gpt-4": {
		"alias": ["4", "emmy"],
		"vendor": "openai",
		"id": "gpt-4o-2024-08-06",
		"description": "GPT-4o is our most advanced multimodal model that's faster and cheaper than GPT-4 Turbo with stronger vision capabilities. The model has 128K context and an October 2023 knowledge cutoff.",
		"cost_in": 2.5,
		"cost_out": 10,
	},
	"gpt-4o-mini": {
		"alias": ["4m", "dav"],
		"vendor": "openai",
		"description": "GPT-4o mini is our most cost-efficient small model that's smarter and cheaper than GPT-3.5 Turbo, and has vision capabilities. The model has 128K context and an October 2023 knowledge cutoff.",
		"cost_in": 0.15,
		"cost_out": 0.6,
	},

	"claude": {
		"alias": ["c", "claud"],
		"vendor": "anthropic",
		"id": "claude-3-5-sonnet-20240620",
		"description": "Claude 3.5 Sonnet is Anthropic's latest AI model, offering improved intelligence, speed, and cost-effectiveness compared to previous versions, with new capabilities in reasoning, coding, and vision.",
		"cost_in": 3,
		"cost_out": 15,
	},
	"claude-haiku": {
		"alias": ["i", "clia"],
		"vendor": "anthropic",
		"id": "claude-3-haiku-20240307",
		"description": "Claude 3 Haiku is Anthropic's fastest and most affordable large language model, offering high-speed processing, state-of-the-art vision capabilities, and strong benchmark performance for enterprise applications.",
		"cost_in": 0.25,
		"cost_out": 1.25,
	},

	"llama-3.1-sonar-huge-128k-online": {
		"alias": ["sho"],
		"vendor": "perplexity",
		"cost_req": 5,   # per thousand
		"cost_in": 5,
		"cost_out": 5,
	},
	"llama-3.1-sonar-large-128k-online": {
		"alias": ["slo"],
		"vendor": "perplexity",
		"cost_req": 0.005,
		"cost_in": 1,
		"cost_out": 1,
	},
	"llama-3.1-sonar-small-128k-online": {
		"alias": ["sso"],
		"vendor": "perplexity",
		"cost_req": 0.005,
		"cost_in": 0.2,
		"cost_out": 0.2,
	},
	"llama-3.1-sonar-large-128k-chat": {
		"alias": ["sl"],
		"vendor": "perplexity",
		"cost_in": 1,
		"cost_out": 1,
	},
	"llama-3.1-sonar-small-128k-chat": {
		"alias": ["ss"],
		"vendor": "perplexity",
		"cost_in": 0.2,
		"cost_out": 0.2,
	},
	"llama-3.1-70b-instruct": {
		"alias": ["l70"],
		"vendor": "perplexity",
		"cost_in": 1,
		"cost_out": 1,
	},
	"llama-3.1-8b-instruct": {
		"alias": ["l8"],
		"vendor": "perplexity",
		"cost_in": 0.2,
		"cost_out": 0.2,
	},

	"gemini-1.5-pro-latest": {
		"alias": ["gp"],
		"vendor": "google",
		"description": "Our next-generation Gemini model with a breakthrough 1 million context window.",
		"cost_in": 0,    # free tier, for PAYG it's complicated
		"cost_out": 0,
	},
	"gemini-1.5-flash-latest": {
		"alias": ["gf"],
		"vendor": "google",
		"description": "Our fastest multimodal model with great performance for diverse, repetitive tasks and a 1 million context window.",
		"cost_in": 0,    # free tier, for PAYG it's complicated
		"cost_out": 0,
	},
}

MODELS[default_model]["alias"].append("d")
MODELS[default_model_small]["alias"].append("s")


# The default model is $LLM_MODEL or default_model as above.

env_llm_model = os.environ.get("ALLEMANDE_LLM_DEFAULT")
env_llm_model_small = os.environ.get("ALLEMANDE_LLM_DEFAULT_SMALL")

if env_llm_model in MODELS:
	default_model = env_llm_model
if env_llm_model_small in MODELS:
	default_model_small = env_llm_model_small

ALLOWED_ROLES = ["user", "assistant", "system"]

DEFAULT_TEMPERATURE = 1
TOKEN_LIMIT = inf


# Initialize clients

os.environ["HF_HUB_OFFLINE"] = "1"

openai_async_client = openai.AsyncOpenAI()
perplexity_async_client = openai.AsyncOpenAI(
	base_url="https://api.perplexity.ai",
	api_key=os.environ.get("PERPLEXITY_API_KEY"),
)
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

llama3_tokenizer = None


def get_llama3_tokenizer():
	global llama3_tokenizer
	if not llama3_tokenizer:
		try:
		#	llama3_tokenizer = AutoTokenizer.from_pretrained("meta-llama/Meta-Llama-3-8B")
			llama3_tokenizer = AutoTokenizer.from_pretrained("baseten/Meta-Llama-3-tokenizer")
		except Exception as e:
			logger.warning("Trying to download llama3_tokenizer.")
			del os.environ["HF_HUB_OFFLINE"]
			try:
				llama3_tokenizer = AutoTokenizer.from_pretrained("baseten/Meta-Llama-3-tokenizer")
			except OSError as ex:
				raise IOError(f"failed to load llama3 tokenizer: {ex}")
	return llama3_tokenizer


fake_completion = {
	"choices": [
		{
			"finish_reason": "stop",
			"index": 0,
			"message": {
				"content": "\n\nSure, Sam! Here's a dad joke for you: \"Why did the tomato turn red? Because it saw the salad dressing!\"",
				"role": "assistant"
			}
		}
	],
	"created": 1678809131,
	"id": "chatcmpl-6u1EZ06waciROkpOqDHVdi2HtL3iX",
	"model": "gpt-3.5-turbo-0301",
	"object": "chat.completion",
	"usage": {
		"completion_tokens": 104,
		"prompt_tokens": 24,
		"total_tokens": 128
	}
}


def get_model_by_alias(model):
	""" If the model is an alias or abbreviation, expand it. """
	abbrev_models = [k for k, v in MODELS.items() if model in v.get("alias", [])]
	if len(abbrev_models) == 1:
		model = abbrev_models[0]
	return model


class AutoInit:  # pylint: disable=too-few-public-methods
	""" Automatically set attributes from kwargs. """
	def __init__(self, **kwargs):
		for k, v in kwargs.items():
			if hasattr(self, k):
				setattr(self, k, v)
	def __str__(self):
		attributes = []
		for key, value in vars(self).items():
			if not key.startswith('_'):
				attributes.append(f"{key}={value!r}")
		class_name = self.__class__.__name__
		return f"{class_name}({', '.join(attributes)})"


class Options(AutoInit):  # pylint: disable=too-few-public-methods
	""" Options for the chat function. """
	model: str = default_model
	fake: bool = False
	temperature: float|None = None
	token_limit: int|None = None
	indent: str|None = None
	def __init__(self, **kwargs):
		if kwargs.get("model"):
			kwargs["model"] = get_model_by_alias(kwargs["model"])
		super().__init__(**kwargs)


opts: Options = Options()


def set_opts(_opts):
	"""Set the global options."""
	global opts  # pylint: disable=global-statement
	opts = Options(**_opts)
	if opts.model in ("", None):
		opts.model = default_model
	if opts.model in ("s", "small"):
		opts.model = default_model_small


async def achat_openai(messages, client=openai_async_client):
	""" Chat with OpenAI ChatGPT models asynchronously. """
	model = opts.model
	if "id" in MODELS[model]:
		model = MODELS[model]["id"]

	logger.debug("model: %s", model)

	temperature = opts.temperature
	token_limit = opts.token_limit

	if temperature is None:
		temperature = DEFAULT_TEMPERATURE
	if token_limit is None:
		token_limit = TOKEN_LIMIT

	options = {
		"messages": messages,
		"model": model,
		"temperature": temperature,
	}

	if token_limit != inf:
		options["max_tokens"] = token_limit

	response = await client.chat.completions.create(
		**options
	)

	logger.debug("llm: response: %s", response)

	message = response.choices[0].message
	output_message = {
		"role": message.role,
		"content": message.content,
	}

	return output_message


async def achat_perplexity(messages):
	""" Chat with Perplexity models asynchronously. """
	return await achat_openai(messages, client=perplexity_async_client)


async def achat_claude(messages):
	""" Chat with Anthropic Claude models asynchronously. """
	model = opts.model
	if "id" in MODELS[model]:
		model = MODELS[model]["id"]

	temperature = opts.temperature
	token_limit = opts.token_limit

	if temperature is None:
		temperature = DEFAULT_TEMPERATURE
	if token_limit is None:
		token_limit = TOKEN_LIMIT

	options = {
		"model": model,
		"temperature": temperature,
	}

	if token_limit != inf:
		options["token_limit"] = token_limit

	response = await claude.chat_claude(messages, _async=True, **options)
	completion = claude.response_completion(response)
	message = { "role": "assistant", "content": completion }
	return message


async def achat_google(messages):
	""" Chat with Google models asynchronously. """
	model = opts.model
	if "id" in MODELS[model]:
		model = MODELS[model]["id"]

	temperature = opts.temperature
	token_limit = opts.token_limit

	if temperature is None:
		temperature = DEFAULT_TEMPERATURE
	if token_limit is None:
		token_limit = TOKEN_LIMIT

	options = {
		"model": model,
		"temperature": temperature,
	}

	if token_limit != inf:
		options["max_output_tokens"] = token_limit

	model_obj = genai.GenerativeModel(model)

	history = []
	for msg in messages[:-1]:
		history.append(genai.ChatMessage(
			author="user" if msg["role"] == "user" else "model",
			content=msg["content"],
		))

	chat = model_obj.start_chat(history=history)

	response = await chat.send_message_async(messages[-1]["content"])

	output_message = {
		"role": "assistant",
		"content": response.text,
	}

	return output_message


async def allm_chat(messages):
	""" Send a list of messages to the model, and return the response asynchronously. """
	logger.debug("llm_chat: input: %r", messages)

	model = opts.model
	vendor = MODELS[model]["vendor"]

	if opts.fake:
		return fake_completion
	if vendor == "anthropic":
		return await achat_claude(messages)
	if vendor == "openai":
		return await achat_openai(messages)
	if vendor == "perplexity":
		return await achat_perplexity(messages)
	if vendor == "google":
		return await achat_google(messages)
	raise ValueError(f"unknown model: {model}")


def split_message_line(message, allowed_roles=None):
	""" Split a message into a role and content. """

	try:
		role, message = message.split(":", 1)
	except ValueError as ex:
		raise ValueError(f"invalid message, missing role: {message}") from ex

	if allowed_roles is not None and role not in allowed_roles:
		raise ValueError(f"invalid role in message: {role}")

	message = message.strip()

	return role, message


def lines_to_messages(lines, system=None):
	""" Convert a list of lines to a list of messages, with roles. """

	messages = []

	if system is not None:
		system_message_obj = {"role": "system", "content": system}
		logger.info("system message: %s", system_message_obj)
		messages.append(system_message_obj)

	# add the input messages
	i = 0
	line = lines[0]
	while i < len(lines):
		role, message = split_message_line(line, allowed_roles=ALLOWED_ROLES)
		while True:
			i += 1
			if i == len(lines):
				break
			line = lines[i].rstrip('\r\n')
			if line and not re.match(r'^\s', line):
				break
			line = re.sub(r'^\s', '', line)
			message += "\n" + line

		message_obj = {"role": role, "content": message}
		logger.info("input message: %s", message_obj)
		messages.append(message_obj)

		# the role alternates by default
		role = "assistant" if role == "user" else "user"

	return messages


def messages_to_lines(messages):
	""" Convert a list of messages to a list of lines, with roles. """
	lines = []
	# add the output messages

	for message in messages:
		role = message['role']
		content = message['content'].strip()
		content = re.sub(r'\n', '\n\t', content)
		line = f"{role}:\t{content}\n"
		lines.append(line)
	return lines


def read_utf_replace(istream):
	""" Read input, replacing invalid UTF-8 with the replacement character. """
	try:
		input_data = istream.buffer.read()
		input_text = input_data.decode("utf-8", errors="replace")
	except UnicodeDecodeError as ex:
		logger.warning("error reading input: %s", ex)
		input_text = istream.read()
	return input_text


async def aprocess(*prompt, prompt2: str|None=None, istream: IO[str]=None, ostream: IO[str]=None, model: str=default_model, indent=None, temperature=None, token_limit=None, retries=RETRIES, empty_ok=False, empty_to_empty=True, log=True, lines=False, repeat=False, json=False):
	"""Process some text through the LLM with a prompt asynchronously."""
	if __name__ == "__main__":
		istream = stdin
		ostream = stdout

	set_opts(vars())

	prompt = " ".join(prompt)
	prompt = prompt.rstrip()

	input_text = read_utf_replace(istream)
	input_text = input_text.rstrip()

	if not input_text and empty_to_empty:
		return ""
	if not input_text and not empty_ok:
		raise ValueError("no input")

	if prompt2:
		prompt2 = prompt2.rstrip()
	if repeat:
		prompt2 = re.sub(r"\bbelow\b", "above", prompt)

	if not lines:
		return await aprocess2(prompt, prompt2, input_text, ostream=ostream, model=model, indent=indent, temperature=temperature, token_limit=token_limit, retries=retries, log=log, json=json)

	# split the input into lines
	lines = input_text.splitlines()
	output = []

	for line in lines:
		line = line.rstrip()
		if not line:
			continue
		output1 = await aprocess2(prompt, prompt2, line, ostream=ostream, model=model, indent=indent, temperature=temperature, token_limit=token_limit, retries=retries, log=log, json=json)
		output.append(output1)

	output_s = "\n".join(output)

	return output_s


async def aprocess2(prompt, prompt2, input_text, ostream, model, indent, temperature, token_limit, retries, log, json):
	""" Process some text through the LLM with a prompt asynchronously. """
	full_input = f"""
{prompt}

{input_text}
"""
	if prompt2:
		full_input += "\n" + prompt2 + "\n"
	return await aquery(full_input, ostream=ostream, model=model, indent=indent, temperature=temperature, token_limit=token_limit, retries=retries, log=log, json=json)


async def aquery(*prompt, ostream: IO[str]|None=None, model: str=default_model, indent=None, temperature=None, token_limit=None, retries=RETRIES, log=True, json=False):
	""" Ask the LLM a question asynchronously. """
	if __name__ == "__main__":
		ostream = stdout
	set_opts(vars())
	return await aretry(aquery2, retries, *prompt, ostream=ostream, log=log, json=json)


async def aquery2(*prompt, ostream: IO[str]|None=None, log=True, json=False):
	""" Ask the LLM a question asynchronously. """
	prompt = " ".join(prompt)
	prompt = prompt.rstrip() + "\n"

	# TODO use a system message?

	input_message = {"role": "user", "content": prompt}
	output_message = await allm_chat([input_message])
	content = output_message["content"]

	# fix indentation for code
	if opts.indent:
		logger.warning("fix indentation for code")
		lines = content.splitlines()
		lines = tab.fix_indentation_list(lines, opts.indent)
		content = "".join(lines)

	# log the input and output
	if log:
		LOGDIR.mkdir(parents=True, exist_ok=True)
		basename = slugify(prompt)[:LOGFILE_NAME_MAX_LEN]
		logfile = LOGDIR/(f"answer.{basename}.md")
		logfile_prompt = LOGDIR/(f"prompt.{basename}.md")
		while logfile.exists():
			time_s = time.strftime("%Y-%m-%dT%H:%M:%S")
			logfile = LOGDIR/f"answer.{basename}.{time_s}.md"
			logfile_prompt = LOGDIR/Path(f"prompt.{basename}.{time_s}.md")
		logfile_prompt.write_text(prompt.rstrip()+"\n", encoding="utf-8")
		logfile.write_text(content.rstrip()+"\n", encoding="utf-8")

	if json:
		try:
			content = json.loads(content)
		except json.JSONDecodeError:
			logger.warning("Failed to parse JSON response")

	if ostream:
		if isinstance(content, dict):
			json.dump(content, ostream, indent=2)
		else:
			print(content, file=ostream)
		return ""

	return content


# TODO use backoff module?
async def aretry(fn, n_tries, *args, sleep_min=1, sleep_max=2, **kwargs):
	""" Retry an async function n_tries times. """
	for i in range(n_tries):
		try:
			return await fn(*args, **kwargs)
		except exceptions_to_retry as ex:
			delay = random.uniform(sleep_min, sleep_max)
			logger.warning("retry: exception, sleeping for %.3f: %s", delay, ex)
			msg = str(ex)
			if i == n_tries - 1:
				raise
			await asyncio.sleep(delay)
			sleep_min *= 2
			sleep_max *= 2
	return None


async def achat(istream=stdin, ostream=stdout, model=default_model, fake=False, temperature=None, token_limit=None, retries=RETRIES):
	""" Chat with the LLM asynchronously. """
	set_opts(vars())
	return await aretry(achat2, retries, istream=istream, ostream=ostream)


async def achat2(istream=stdin, ostream=stdout):
	""" Chat with the LLM asynchronously. """
	input_lines = read_utf_replace(istream).splitlines()
	input_messages = lines_to_messages(input_lines)
	response_message = await allm_chat(input_messages)
	output_lines = messages_to_lines([response_message])
	ostream.writelines(output_lines)


def chat(istream=stdin, ostream=stdout, model=default_model, fake=False, temperature=None, token_limit=None, retries=RETRIES):
	""" Synchronous wrapper for achat. """
	return asyncio.run(achat(istream, ostream, model, fake, temperature, token_limit, retries))


@argh.arg("prompt", nargs="+", help="prompt text")
@argh.arg("-o", "--output", dest="ostream", default=None, help="output file")
@argh.arg("-m", "--model", default=default_model, help="model name")
@argh.arg("-I", "--indent", default=None, help="indentation string")
@argh.arg("-t", "--temperature", type=float, help="temperature")
@argh.arg("-n", "--token-limit", type=int, help="token limit")
@argh.arg("-r", "--retries", type=int, default=RETRIES, help="number of retries")
@argh.arg("-l", "--log", action="store_true", help=f"log to a file in {LOGDIR}")
@argh.arg("-j", "--json", action="store_true", help="output JSON")
def query(*prompt, ostream: IO[str]|None=None, model: str=default_model, indent=None, temperature=None, token_limit=None, retries=RETRIES, log=True, json=False):
	""" Synchronous wrapper for aquery. """
	return asyncio.run(aquery(*prompt, ostream=ostream, model=model, indent=indent, temperature=temperature, token_limit=token_limit, retries=retries, log=log, json=json))


@argh.arg("prompt", nargs="+", help="prompt text")
@argh.arg("-P", "--prompt2", help="second prompt text")
@argh.arg("-i", "--input", dest="istream", default=None, help="input file")
@argh.arg("-o", "--output", dest="ostream", default=None, help="output file")
@argh.arg("-m", "--model", default=default_model, help="model name")
@argh.arg("-I", "--indent", default=None, help="indentation string")
@argh.arg("-t", "--temperature", type=float, help="temperature")
@argh.arg("-n", "--token-limit", type=int, help="token limit")
@argh.arg("-r", "--retries", type=int, default=RETRIES, help="number of retries")
@argh.arg("-e", "--empty-to-empty", action="store_true", help="return empty string for empty input")
@argh.arg("-E", "--empty-ok", action="store_true", help="allow empty input")
@argh.arg("-l", "--log", action="store_true", help=f"log to a file in {LOGDIR}")
@argh.arg("-x", "--lines", action="store_true", help="process each line separately, like perl -p")
@argh.arg("-R", "--repeat", action="store_true", help="repeat the prompt as prompt2, changing 'below' to 'above' only")
@argh.arg("-j", "--json", action="store_true", help="output JSON")
def process(*prompt, prompt2: str|None=None, istream: IO[str]=None, ostream: IO[str]=None, model: str=default_model, indent=None, temperature=None, token_limit=None, retries=RETRIES, empty_ok=False, empty_to_empty=True, log=True, lines=False, repeat=False, json=False):
	""" Synchronous wrapper for aprocess. """
	return asyncio.run(aprocess(*prompt, prompt2=prompt2, istream=istream, ostream=ostream, model=model, indent=indent, temperature=temperature, token_limit=token_limit, retries=retries, empty_ok=empty_ok, empty_to_empty=empty_to_empty, log=log, lines=lines, repeat=repeat, json=json))


def count(istream=stdin, model=default_model, in_cost=False, out_cost=False):
	""" count tokens in a file """
	set_opts(vars())
	text = read_utf_replace(istream)
	model = MODELS[opts.model]
	vendor = model["vendor"]
	if vendor == "openai":
		try:
			enc = tiktoken.encoding_for_model(opts.model)
		except KeyError:
			enc_name = "o200k_base"
			logger.warning(f"model {opts.model} not known to tiktoken, assuming {enc_name}")
			enc = tiktoken.get_encoding(enc_name)
		tokens = enc.encode(text)
		n_tokens = len(tokens)
	elif vendor == "anthropic":
		n_tokens = claude.count(text)
	elif vendor == "perplexity":
		llama3_tokenizer = get_llama3_tokenizer()
		tokens = llama3_tokenizer.tokenize(text)
		n_tokens = len(tokens)
	else:
		raise ValueError(f"unknown model vendor: {vendor}")
	rv = [n_tokens]
	if in_cost:
		rv.append(model["cost_in"] * n_tokens / 1e6)
	if out_cost:
		rv.append(model["cost_out"] * n_tokens / 1e6)
	if in_cost or out_cost and "cost_req" in model:
		rv.append(model["cost_req"] / 1e3)
	return tuple(rv)


def models(detail=False, alias=False):
	""" List the available models. """
	for name, model in MODELS.items():
		print(name, end="")
		if alias:
			for a in model.get("alias", []):
				print(f"\t{a}", end="")
		print()
		if not detail:
			continue
		for k, v in model.items():
			if k == "description":
				v = textwrap.fill(v, width=80, subsequent_indent='\t\t')
			print(f"\t{k}: {v}")


if __name__ == "__main__":
	main.run([chat, query, process, count, models])
