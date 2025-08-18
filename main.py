import os
import json
import pypdf
import uvicorn
from fastapi import FastAPI
from fastmcp import FastMCP
from fastmcp.server.http import create_sse_app
from tools.tool import web_get, web_search, fetch_beeceptor_data

RESOURCE_DIR = "shared_files"

app = FastAPI()
mcp_server = FastMCP(name="File Resource Server")

@mcp_server.resource("resource://greeting")
def greet() -> str:
    """Simple greet resource to mirror the article example."""
    return "Hey This Is Harsh👋"

# Tool registrations
@mcp_server.tool(name="web_get")
def tool_web_get(url: str) -> str:
    """Fetch raw HTML/text from a URL and return the response text.

    Args:
        url: The fully qualified URL to fetch.
    """
    return web_get(url)


@mcp_server.tool(name="web_search")
def tool_web_search(query: str, max_results: int = 5) -> str:
    """Search the web using a lightweight DuckDuckGo endpoint.

    Args:
        query: The search query string.
        max_results: Max number of results to return (default 5).

    Returns:
        JSON string of results: [{"title": str, "href": str}]
    """
    return json.dumps(web_search(query, max_results=max_results))


@mcp_server.tool(name="get_beeceptor")
def tool_get_beeceptor() -> str:
    """Fetch plain text data from the Beeceptor endpoint and return it as text."""
    return fetch_beeceptor_data()

@mcp_server.resource("resource://files/list", mime_type="application/json")
def list_available_files() -> str:
    try:
        files = [f for f in os.listdir(RESOURCE_DIR) if os.path.isfile(os.path.join(RESOURCE_DIR, f))]
        return json.dumps(files)
    except FileNotFoundError:
        return json.dumps({"error": f"Resource directory '{RESOURCE_DIR}' not found."})

@mcp_server.resource("file:///{filename}")
def serve_file_content(filename: str) -> str:
    if ".." in filename or filename.startswith("/"):
        return "Error: Invalid filename."

    file_path = os.path.join(RESOURCE_DIR, filename)

    if not os.path.exists(file_path):
        return f"Error: File '{filename}' not found."

    if filename.lower().endswith(('.txt', '.log')):
        # Return text content for txt/log
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    elif filename.lower().endswith('.pdf'):
        try:
            # Return extracted text for PDF files
            text_content = ""
            with open(file_path, 'rb') as f:
                reader = pypdf.PdfReader(f)
                for page in reader.pages:
                    text_content += page.extract_text() or ""
            return text_content
        except Exception as e:
            return f"Error processing PDF file: {e}"
            
    return "Error: Unsupported file type."

@mcp_server.resource("images://{filename}")
def fetch_image_bytes(filename: str) -> bytes:
    """Returns image bytes from the shared resources directory.

    Use URIs like images://img.jpg. The client/inspector will receive base64-encoded blob data.
    """
    if ".." in filename or filename.startswith("/"):
        return b""

    file_path = os.path.join(RESOURCE_DIR, filename)

    if not os.path.exists(file_path):
        return b""

    with open(file_path, "rb") as f:
        return f.read()

# Provide distinct endpoints for SSE streaming and JSON-RPC message posts
sse_app = create_sse_app(mcp_server, message_path="/message/", sse_path="/sse")
app.mount("/mcp", sse_app)


if __name__ == "__main__":
    if not os.path.exists(RESOURCE_DIR):
        os.makedirs(RESOURCE_DIR)
        print(f"Created resource directory: '{RESOURCE_DIR}'. Please add files to it.")

    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    if transport == "stdio":
        print("Starting MCP server over stdio (set MCP_TRANSPORT=http to use HTTP/SSE)...")
        mcp_server.run(transport="stdio")
    else:
        print("Starting MCP server over HTTP/SSE at http://0.0.0.0:8000/mcp/")
        uvicorn.run(app, host="0.0.0.0", port=8000)