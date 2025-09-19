"""
MCP schema validation utilities.
"""

from typing import Dict, List, Any


def assert_tool_schema(tool: Dict[str, Any]) -> None:
    """Validate that a tool conforms to MCP spec requirements."""
    required_keys = ("name", "description", "inputSchema", "outputSchema")
    
    for key in required_keys:
        if key not in tool:
            raise ValueError(f"Tool missing required key: {key}")
    
    # Validate outputSchema structure
    oschema = tool["outputSchema"]
    if not isinstance(oschema, dict):
        raise ValueError("outputSchema must be an object")
    
    if "properties" not in oschema:
        raise ValueError("outputSchema must have 'properties'")
    
    if "content" not in oschema["properties"]:
        raise ValueError("outputSchema.properties must include 'content'")
    
    content_schema = oschema["properties"]["content"]
    if not isinstance(content_schema, dict):
        raise ValueError("outputSchema.properties.content must be an object")
    
    if content_schema.get("type") != "array":
        raise ValueError("outputSchema.properties.content must be an array")


def validate_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Validate all tools in a list."""
    for i, tool in enumerate(tools):
        try:
            assert_tool_schema(tool)
        except ValueError as e:
            raise ValueError(f"Tool {i} ({tool.get('name', 'unnamed')}): {e}")
    
    return tools
