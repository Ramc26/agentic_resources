import os
import json
import threading
import time
from typing import Any, Dict, Optional

from urllib.parse import urljoin

from crewai import Agent, Task, Crew, LLM
from crewai.tools import tool as crew_tool
from dotenv import load_dotenv
from resources.mcp_client import MCPClient
from resources.selectors import rank_files_by_query
from resources.markdown_utils import extract_markdown_points
from tools.validation_tool import validate_contact

# Ensure CrewAI telemetry is disabled before importing CrewAI (telemetry may init at import time)
os.environ.setdefault("CREWAI_TELEMETRY", "false")
# Disable OpenTelemetry SDK entirely to avoid outbound telemetry attempts
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

SERVER_BASE_URL = os.getenv("MCP_SERVER_BASE_URL", "http://127.0.0.1:8000")
SERVER_SSE_URL = urljoin(SERVER_BASE_URL, "/mcp/sse")


def _extract_markdown_points(markdown_text: str, section_header: str) -> list[str]:
	return extract_markdown_points(markdown_text, section_header)


def build_agent(tools: list | None = None) -> Agent:
	# Use Gemini via CrewAI's LLM wrapper (LiteLLm under the hood)
	llm = LLM(
		model=os.getenv("LITELLM_MODEL", "gpt-4o-mini"),
		api_key=os.getenv("OPENAI_API_KEY"),
		temperature=0.1,
		max_retries=3,
		request_timeout=60,
	)
	return Agent(
		role="Research and Retrieval Agent",
		goal=(
			"Answer user questions by deciding between: calling MCP tools (web_get/web_search) for live info,"
			" reading MCP resources for project context, or simply responding. Perform multi-step reasoning if needed."
			"\n\nTool use policy: Use a tool ONLY if necessary to answer the question. Once you have enough"
			" information, DO NOT call additional tools. Never call the same tool more than once for a single"
			" question. If sufficient information is already provided in the prompt/context, respond directly"
			" with the final answer without any tool calls."
		),
		backstory=(
			"Connected to an MCP server exposing tools and resources. Prefer tools for current events/web,"
			" and prefer resources for local project knowledge. Follow the tool format strictly."
		),
		llm=llm,
		allow_delegation=False,
		verbose=True,
		memory=True,
		max_iter=5,
		max_rpm=60,
		max_tokens=2048,
		tools=tools or [],
	)


def main() -> None:
	# Load .env and set provider to gemini if Gemini key is present
	load_dotenv()
	# Backoff if rate-limited
	# print(f"CREWAI_TELEMETRY before set: {os.getenv('CREWAI_TELEMETRY')}")
	os.environ.setdefault("LITELLM_RETRY_POLICY", "exponential_backoff")
	os.environ.setdefault("LITELLM_MAX_RETRIES", "3")
	# Disable CrewAI telemetry to avoid network timeouts during runs
	# This is redundant with the global setting at the top, but kept for clarity
	os.environ.setdefault("CREWAI_TELEMETRY", "false")
	# print(f"CREWAI_TELEMETRY after set: {os.getenv('CREWAI_TELEMETRY')}")
	
	mcp = MCPClient(SERVER_SSE_URL, SERVER_BASE_URL)
	mcp.connect()
	mcp.initialize()

	# Simple per-turn cache to avoid repeated tool calls with same arguments
	tool_cache: dict[tuple[str, str], str] = {}

	# Expose MCP tools to the LLM via CrewAI wrappers with caching
	@crew_tool("web_get")
	def _tool_web_get(url: str) -> str:
		"""Fetch raw HTML/text from the given URL using the server-side `web_get` MCP tool."""
		key = ("web_get", json.dumps({"url": url}, sort_keys=True))
		if key in tool_cache:
			print(f"[cached] web_get url={url}")
			return tool_cache[key]
		print(f"[tool] web_get url={url}")
		result = mcp.call_tool("web_get", url=url)
		tool_cache[key] = result
		return result

	@crew_tool("web_search")
	def _tool_web_search(query: str, max_results: int = 5) -> str:
		"""Perform a lightweight DuckDuckGo search via the server-side `web_search` MCP tool."""
		key = ("web_search", json.dumps({"query": query, "max_results": max_results}, sort_keys=True))
		if key in tool_cache:
			print(f"[cached] web_search query={query!r} max_results={max_results}")
			return tool_cache[key]
		print(f"[tool] web_search query={query!r} max_results={max_results}")
		result = mcp.call_tool("web_search", query=query, max_results=max_results)
		tool_cache[key] = result
		return result

	@crew_tool("get_beeceptor")
	def _tool_get_beeceptor() -> str:
		"""Fetch plain text data from the Beeceptor endpoint via the server-side MCP tool."""
		key = ("get_beeceptor", "{}")
		if key in tool_cache:
			print("[cached] get_beeceptor")
			return tool_cache[key]
		print("[tool] get_beeceptor")
		result = mcp.call_tool("get_beeceptor")
		tool_cache[key] = result
		return result

	@crew_tool("validate_contact")
	def _tool_validate_contact(input_string: str, validation_type: str) -> str:
		"""Validates a phone number or an email address using the API-Ninjas service.
		Input should be a string containing the phone number (e.g., '+12065550100') or email (e.g., 'test@example.com'),
		and the validation_type should be either 'phone' or 'email'.
		"""
		key = ("validate_contact", json.dumps({"input_string": input_string, "validation_type": validation_type}, sort_keys=True))
		if key in tool_cache:
			print(f"[cached] validate_contact input_string={input_string!r} validation_type={validation_type!r}")
			return tool_cache[key]
		print(f"[tool] validate_contact input_string={input_string!r} validation_type={validation_type!r}")
		result = validate_contact(input_string, validation_type)
		tool_cache[key] = result
		return result

	@crew_tool("simple_greet")
	def _tool_simple_greet(name: str = "there") -> str:
		"""A simple prompt that personalizes the greeting via the server-side `simple_greet` MCP tool."""
		key = ("simple_greet", name)
		if key in tool_cache:
			print(f"[cached] simple_greet name={name!r}")			
			return tool_cache[key]
		print(f"[tool] simple_greet name={name!r}")
		result = mcp.call_tool("simple_greet", name=name)
		tool_cache[key] = result
		return result

	@crew_tool("find_keywords")
	def _tool_find_keywords(text: str) -> str:
		"""Extract keywords from a block of text via the server-side `find_keywords` MCP tool."""
		key = ("find_keywords", text)
		if key in tool_cache:
			print(f"[cached] find_keywords text={len(text)}")
			return tool_cache[key]
		print(f"[tool] find_keywords text={len(text)}")
		result = mcp.call_tool("find_keywords", text=text)
		tool_cache[key] = result
		return result

	@crew_tool("summarize_text")
	def _tool_summarize_text(text: str) -> str:
		"""Summarize the given text using the server-side `summarize_text` MCP tool."""
		key = ("summarize_text", text)
		if key in tool_cache:
			print(f"[cached] summarize_text text={len(text)}")
			return tool_cache[key]
		print(f"[tool] summarize_text text={len(text)}")
		result = mcp.call_tool("summarize_text", text=text)
		tool_cache[key] = result
		return result

	agent_with_tools = build_agent(tools=[_tool_web_get, _tool_web_search, _tool_get_beeceptor, _tool_validate_contact, _tool_simple_greet, _tool_find_keywords, _tool_summarize_text])

	print("Agent ready. Examples: 'tool web_search query=python mcp', 'tool web_get url=https://example.com', 'read resource://greeting'")
	while True:
		try:
			user = input("You> ").strip()
		except (EOFError, KeyboardInterrupt):
			print("\nBye")
			break
		if not user:
			continue

		# Simple command routing to MCP
		if user.lower().startswith("read "):
			uri = user[5:].strip()
			print(mcp.read_resource(uri))
			continue
		if user.lower().startswith("tool "):
			# Format: tool NAME key=value key2=value2
			parts = user.split()
			name = parts[1]
			kwargs: Dict[str, Any] = {}
			for p in parts[2:]:
				if "=" in p:
					k, v = p.split("=", 1)
					kwargs[k] = v
			print(mcp.call_tool(name, **kwargs))
			continue

		# Build context from relevant resources
		files = mcp.list_project_files()
		context_chunks: list[str] = []
		# Rank files by user query and include top matches
		relevant = rank_files_by_query(files, user)
		for fname in relevant or []:
			uri = f"file:///{fname}"
			text = mcp.read_resource_text(uri)
			if text:
				context_chunks.append(f"From {fname}:\n" + text)
		# If available, prefer extracting 'Discussion Points' as a concise list
		desc = user
		if context_chunks:
			joined = "\n\n".join(context_chunks)
			discussion_points = _extract_markdown_points(joined, "Discussion Points:")
			if not discussion_points:
				# Also try without trailing colon
				discussion_points = _extract_markdown_points(joined, "Discussion Points")
				
			if discussion_points and ("discussion" in user.lower() or "points" in user.lower()):
				desc = (
					"Based on the project notes, list the discussion points as a numbered list.\n\n"
					+ "\n".join(f"{i+1}. {p}" for i, p in enumerate(discussion_points))
				)
			elif "keyword" in user.lower() or "keywords" in user.lower():
				desc = "Extract keywords from the following text:\n\n" + joined + "\n\nUser question: " + user
			else:
				# Use the summarize_text prompt for general context-based questions
				desc = "Summarize the following text:\n\n" + joined + "\n\nUser question: " + user
				
		# Let LLM respond directly for free-form Q&A using the agent with tools
		task = Task(description=desc, agent=agent_with_tools, expected_output="A concise answer.")
		crew = Crew(agents=[agent_with_tools], tasks=[task])
		result = crew.kickoff()
		print(getattr(result, "raw", result))


if __name__ == "__main__":
	main()
