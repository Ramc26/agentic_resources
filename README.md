# Agentic Resources - MCP Server with CrewAI Agent

A comprehensive project demonstrating Model Context Protocol (MCP) primitives including Tools, Resources, and Prompts, integrated with a CrewAI-powered intelligent agent for research and retrieval tasks.

## 🚀 Project Overview

This project showcases a complete MCP server implementation with:
- **MCP Server** (`main.py`) - Exposes tools, resources, and prompts
- **CrewAI Agent** (`agent.py`) - Intelligent agent that uses MCP tools
- **MCP Inspector** - Web-based interface for testing MCP primitives
- **Validation Tools** - Phone number and email validation using API-Ninjas
- **File Processing** - Support for PDF, TXT, and image files

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   MCP Inspector │    │   FastAPI App   │    │   CrewAI Agent  │
│   (Web UI)      │◄──►│   (main.py)     │◄──►│   (agent.py)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  MCP Primitives │
                       │  (Tools,        │
                       │   Resources,    │
                       │   Prompts)      │
                       └─────────────────┘
```

## 🛠️ MCP Primitives

### 1. Tools (`@mcp.tool`)

Tools are callable functions that perform specific actions. They can be invoked by clients or agents.

#### Example Tool Definition:
```python
@mcp.tool(name="web_get")
def tool_web_get(url: str) -> str:
    """Fetch raw HTML/text from a URL and return the response text."""
    return web_get(url)
```

#### Available Tools:
- **`web_get`** - Fetch content from URLs
- **`web_search`** - Perform web searches using DuckDuckGo
- **`get_beeceptor`** - Fetch data from Beeceptor endpoint
- **`Verify Email and Phone`** - Validate phone numbers and emails using API-Ninjas

### 2. Resources (`@mcp.resource`)

Resources provide access to data or content that can be read by clients.

#### Example Resource Definition:
```python
@mcp.resource("resource://greeting")
def greet() -> str:
    """Simple greet resource to mirror the article example."""
    return "Hey This Is Harsh👋"
```

#### Available Resources:
- **`resource://greeting`** - Simple greeting message
- **`resource://files/list`** - List of available files in shared_files directory
- **`file:///{filename}`** - Content of specific files (supports PDF, TXT, LOG)
- **`images://{filename}`** - Image files as bytes

### 3. Prompts (`@mcp.prompt`)

Prompts are message templates that can be customized with parameters and used by clients or agents.

#### Example Prompt Definition:
```python
@mcp.prompt(name="simple_greet")
def simple_greet_prompt(name: str = "there") -> str:
    """A simple prompt that personalizes the greeting."""
    return f"Hello, {name}! How can I help you today?"
```

#### Available Prompts:
- **`simple_greet`** - Personalized greeting with name parameter
- **`summarize_text`** - Instructions to summarize text in two sentences
- **`find_keywords`** - Instructions to extract keywords from text

## 🤖 CrewAI Agent

The `agent.py` file implements an intelligent agent using CrewAI that can:
- Use MCP tools for web searches and data retrieval
- Access MCP resources for file content
- Utilize MCP prompts for structured responses
- Perform multi-step reasoning with context from local files
- Cache tool calls to avoid repetition

### Agent Features:
- **Multi-step reasoning** with `max_iter=5`
- **Tool caching** to prevent duplicate calls
- **Context-aware responses** using local file content
- **Intelligent tool selection** based on query requirements

### Agent Tools:
The agent has access to all MCP tools plus additional CrewAI-wrapped versions:
- `_tool_web_get`, `_tool_web_search`, `_tool_get_beeceptor`
- `_tool_validate_contact`, `_tool_simple_greet`
- `_tool_find_keywords`, `_tool_summarize_text`

## 📁 Project Structure

```
agentic_resources/
├── main.py                 # MCP server with FastAPI
├── agent.py               # CrewAI agent implementation
├── client.py              # MCP client for testing
├── pyproject.toml         # Project dependencies
├── uv.lock               # Locked dependency versions
├── tools/
│   ├── tool.py           # Web tools implementation
│   └── validation_tool.py # Phone/email validation
├── resources/
│   ├── mcp_client.py     # MCP client wrapper
│   ├── selectors.py      # File ranking logic
│   └── markdown_utils.py # Markdown processing
└── shared_files/          # Directory for project files
```

## 🚀 Setup Instructions

### 1. Initialize Project
```bash
# Clone or create project directory
cd agentic_resources

# Initialize with uv
uv init

# Install dependencies
uv sync
```

### 2. Environment Configuration
Create a `.env` file with your API keys:
```bash
# Required for CrewAI agent
OPENAI_API_KEY=your_openai_api_key_here
LITELLM_MODEL=gpt-4o-mini

# Required for validation tools
API_NINJAS_KEY=your_api_ninjas_key_here

# Optional: MCP server configuration
MCP_SERVER_BASE_URL=http://127.0.0.1:8000
MCP_TRANSPORT=http
```

### 3. Add Files to shared_files/
Place your project files (PDFs, TXTs, images) in the `shared_files/` directory for the agent to access.

## 🏃‍♂️ Running the Project

### Start MCP Server
```bash
uv run python main.py
```
This starts the FastAPI server with MCP endpoints at `http://localhost:8000`

### Start CrewAI Agent
```bash
uv run python agent.py
```
This starts the intelligent agent that can use MCP tools and resources.

### Start MCP Inspector (Web UI)
```bash
uv run fastmcp dev main.py
```
This opens a web interface at `http://localhost:6274` for testing MCP primitives.

## 🧪 Testing

### Test MCP Tools via Inspector
1. Open MCP Inspector in your browser
2. Navigate to the "Tools" tab
3. Test tools like `web_search` or `validate_contact`
4. Check the "Resources" tab for available data

### Test Agent Capabilities
1. Start the agent with `python agent.py`
2. Ask questions like:
   - "What files do you have access to?"
   - "Summarize the content of project_notes.txt"
   - "Search for information about Python MCP"
   - "Validate the email test@example.com"

### Test File Processing
1. Add files to `shared_files/` directory
2. Use agent commands:
   - `read resource://files/list` - List available files
   - `read file:///your_file.pdf` - Read specific file content

## 🔧 Development

### Adding New Tools
```python
@mcp.tool(name="your_tool_name")
def your_tool_function(param1: str, param2: int) -> str:
    """Tool description for documentation."""
    # Your tool logic here
    return "Tool result"
```

### Adding New Resources
```python
@mcp.resource("resource://your_resource")
def your_resource_function() -> str:
    """Resource description."""
    return "Resource content"
```

### Adding New Prompts
```python
@mcp.prompt(name="your_prompt_name")
def your_prompt_function(param: str) -> str:
    """Prompt description."""
    return f"Your prompt template with {param}"
```

## 🌟 Key Features

- **Telemetry Disabled** - No external tracking or timeouts
- **Tool Caching** - Prevents duplicate API calls
- **File Type Support** - PDF text extraction, image handling
- **Intelligent Routing** - Agent chooses appropriate tools automatically
- **Context Awareness** - Uses local files for relevant responses
- **Multi-step Reasoning** - Complex queries broken into logical steps

## 🐛 Troubleshooting

### Common Issues:
1. **Port conflicts** - Ensure port 8000 is available
2. **API key errors** - Check `.env` file configuration
3. **File not found** - Verify files exist in `shared_files/`
4. **Tool errors** - Check tool dependencies and API limits

### Debug Mode:
The agent runs with `verbose=True` by default, showing detailed tool usage and decision-making processes.

## 📚 Dependencies

- **FastAPI** - Web framework for MCP server
- **FastMCP** - MCP server implementation
- **CrewAI** - Agent framework for intelligent automation
- **LiteLLM** - LLM abstraction layer
- **PyPDF** - PDF text extraction
- **httpx** - HTTP client for tools
- **uv** - Fast Python package manager

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your MCP primitives or agent improvements
4. Test thoroughly with the provided tools
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

---

**Happy Building! 🚀**

For more information about MCP, visit: https://modelcontextprotocol.io/
For CrewAI documentation: https://docs.crewai.com/

---

## 👨‍💻 Developer

**Ram Bikkina**<br>
🌐 [RamTechSuite](https://ramc26.github.io/RamTechSuite)
<div style="display: flex; justify-content: center; align-items: center; background: black;">
<pre style="color: #ffcb8b; font-family: monospace; margin: 0; background: transparent;">
          __________-------____                 ____-------__________
          \------____-------___--__---------__--___-------____------/
           \//////// / / / / / \   _-------_   / \ \ \ \ \ \\\\\\\\/
             \////-/-/------/_/_| /___   ___\ |_\_\------\-\-\\\\/
               --//// / /  /  //|| (O)\ /(O) ||\\  \  \ \ \\\\--
                    ---__/  // /| \_  /V\  _/ |\ \\  \__---
                         -//  / /\_ ------- _/\ \  \\-
                           \_/_/ /\---------/\ \_\_/
                               ----\   |   /----
                                    | -|- |
                                   /   |   \
                                   ---- \___|
                              <b style="font-size:1rem">Happy Prototyping!</b>
</pre>
</div>



