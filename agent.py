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

SERVER_BASE_URL = os.getenv("MCP_SERVER_BASE_URL", "http://127.0.0.1:8000")
SERVER_SSE_URL = urljoin(SERVER_BASE_URL, "/mcp/sse")


def _extract_markdown_points(markdown_text: str, section_header: str) -> list[str]:
	return extract_markdown_points(markdown_text, section_header)


def build_agent(tools: list | None = None) -> Agent:
	# Use Gemini via CrewAI's LLM wrapper (LiteLLM under the hood)
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
			" reading MCP resources for project context, or simply responding.\n\n"
			"Tool use policy: If you need external/current information, always use one of the tools."
			" If you do not need a tool, do NOT emit any Action step—respond directly with Final Answer."
			" Never output 'Action: None'."
		),
		backstory=(
			"Connected to an MCP server exposing tools and resources. Prefer tools for current events/web,"
			" and prefer resources for local project knowledge. Follow the tool format strictly."
		),
		llm=llm,
		allow_delegation=False,
		verbose=True,
		memory=True,
		max_iter=1,
		max_rpm=60,
		max_tokens=2048,
		tools=tools or [],
	)


def main() -> None:
	# Load .env and set provider to gemini if Gemini key is present
	load_dotenv()
	# Backoff if rate-limited
	os.environ.setdefault("LITELLM_RETRY_POLICY", "exponential_backoff")
	os.environ.setdefault("LITELLM_MAX_RETRIES", "3")
	# Disable CrewAI telemetry to avoid network timeouts during runs
	os.environ.setdefault("CREWAI_TELEMETRY", "false")
	mcp = MCPClient(SERVER_SSE_URL, SERVER_BASE_URL)
	mcp.connect()
	mcp.initialize()

	# Expose MCP tools to the LLM via CrewAI wrappers
	@crew_tool("web_get")
	def _tool_web_get(url: str) -> str:
		"""Fetch raw HTML/text from the given URL using the server-side `web_get` MCP tool."""
		return mcp.call_tool("web_get", url=url)

	@crew_tool("web_search")
	def _tool_web_search(query: str, max_results: int = 5) -> str:
		"""Perform a lightweight DuckDuckGo search via the server-side `web_search` MCP tool."""
		return mcp.call_tool("web_search", query=query, max_results=max_results)

	@crew_tool("get_beeceptor")
	def _tool_get_beeceptor() -> str:
		"""Fetch plain text data from the Beeceptor endpoint via the server-side MCP tool."""
		return mcp.call_tool("get_beeceptor")

	agent = build_agent(tools=[_tool_web_get, _tool_web_search, _tool_get_beeceptor])

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
			else:
				desc = (
					"Use the following project context if helpful. Answer succinctly and list key points when asked.\n\n"
					+ joined
					+ "\n\nUser question: "
					+ user
				)

		# Let LLM respond directly for free-form Q&A using Crew
		task = Task(description=desc, agent=agent, expected_output="A concise answer.")
		crew = Crew(agents=[agent], tasks=[task])
		result = crew.kickoff()
		print(getattr(result, "raw", result))


if __name__ == "__main__":
	main()


