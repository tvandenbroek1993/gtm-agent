from tools import *
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
MODEL_KEY = os.getenv("MODEL_KEY")

def create_agent():
    """Initializes the OpenAI client and defines the agent's tools and their schemas."""
    client = OpenAI(
       base_url="https://openrouter.ai/api/v1",
       api_key=MODEL_KEY,
    )

    available_tools = {
       "get_information": get_information,
       "get_specific_item": get_specific_item,
       "list_container_versions": list_container_versions,
       "get_container_version": get_container_version
    }

    tools_schema = [
       {
          "type": "function",
          "function": {
             "name": "get_information",
             "description": "Get a LIST of all tags, variables, built-in variables, triggers, or folders. Use this to find the names and IDs of items within a specific workspace.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "workspace_id": {"type": "string", "description": "The GTM workspace ID."},
                   "information_type": {
                      "type": "string",
                      "description": "The type of items to list.",
                      "enum": ["tags", "variables", "built_in_variables", "triggers", "folders"]
                   }
                },
                "required": ["account_id", "container_id", "workspace_id", "information_type"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "get_specific_item",
             "description": "Get the full, detailed configuration of a SINGLE tag, variable, trigger, or folder from a workspace using its specific ID. Does NOT work for built-in variables.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "workspace_id": {"type": "string", "description": "The GTM workspace ID."},
                   "item_type": {
                      "type": "string",
                      "description": "The type of the item to get. Must be singular.",
                      "enum": ["tag", "variable", "trigger", "folder"]
                   },
                   "item_id": {
                      "type": "string",
                      "description": "The unique numerical ID of the specific item to retrieve."
                   }
                },
                "required": ["account_id", "container_id", "workspace_id", "item_type", "item_id"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "list_container_versions",
             "description": "Get a list of all version headers for a GTM Container. This is useful for seeing the history of a container and finding specific version IDs.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM Account ID."},
                   "container_id": {"type": "string", "description": "The GTM Container ID."},
                   "include_deleted": {
                      "type": "boolean",
                      "description": "Optional. Set to true to also retrieve deleted (archived) versions. Defaults to false."
                   }
                },
                "required": ["account_id", "container_id"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "get_container_version",
             "description": "Get the full, detailed configuration of a SINGLE container version using its specific version ID. Use 'published' as the version_id to get the currently live version.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM Account ID."},
                   "container_id": {"type": "string", "description": "The GTM Container ID."},
                   "version_id": {
                      "type": "string",
                      "description": "The unique ID of the specific container version to retrieve. Use 'published' to get the current live version. Retrieved from the list container versions tool"
                   }
                },
                "required": ["account_id", "container_id", "version_id"],
             },
          },
       }
    ]
    return client, available_tools, tools_schema
