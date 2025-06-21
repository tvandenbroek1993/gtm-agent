from google_tag_manager_agent.tools import *
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
MODEL_KEY = os.getenv("MODEL_KEY")

def create_agent():
    client = OpenAI(
       base_url="https://openrouter.ai/api/v1",
       api_key=MODEL_KEY,
    )

    available_tools = {
       "list_gtm_items": list_gtm_items,
       "get_gtm_item": get_gtm_item,
       "compare_gtm_versions": compare_gtm_versions,
       "update_gtm_tag_name": update_gtm_tag_name,
    }

    tools_schema = [
       {
          "type": "function",
          "function": {
             "name": "list_gtm_items",
             "description": "Get a LIST of all tags, variables, built-in variables, triggers, folders, or container versions from a GTM workspace or container. Use this to find the names and IDs of items.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "workspace_id": {"type": "string",
                                    "description": "The GTM workspace ID. REQUIRED for tags, variables, built_in_variables, triggers, and folders. NOT USED for 'versions'."},
                   "information_type": {
                      "type": "string",
                      "description": "The type of GTM items to list.",
                      "enum": ["tags", "variables", "built_in_variables", "triggers", "folders", "versions"]
                   }
                },
                "required": ["account_id", "container_id", "information_type"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "get_gtm_item",
             "description": "Get the full, detailed configuration of a SINGLE GTM item (tag, variable, trigger, folder, or container version) using its specific ID. Does NOT work for built-in variables.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "workspace_id": {"type": "string",
                                    "description": "The GTM workspace ID. REQUIRED for tags, variables, triggers, and folders. NOT USED for 'versions'."},
                   "information_type": {
                      "type": "string",
                      "description": "The type of the GTM item to get details for.",
                      "enum": ["tags", "variables", "triggers", "folders", "versions"]
                   },
                   "item_id": {
                      "type": "string",
                      "description": "The unique numerical ID of the specific GTM item to retrieve. Use 'published' as the item_id to get the currently live version when information_type is 'versions'."
                   }
                },
                "required": ["account_id", "container_id", "information_type", "item_id"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "compare_gtm_versions",
             "description": "Compares two Google Tag Manager container versions and reports additions, deletions, and modifications of tags, triggers, and variables. The output provides the new version ID, its timestamp, and lists of added, deleted, and modified tags, triggers, and variables.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "version_id_old": {"type": "string", "description": "The ID of the older GTM container version."},
                   "version_id_new": {"type": "string", "description": "The ID of the newer GTM container version."}
                },
                "required": ["account_id", "container_id", "version_id_old", "version_id_new"],
             },
          },
       },
       {
          "type": "function",
          "function": {
             "name": "update_gtm_tag_name",
             "description": "Updates the display name of a specific Google Tag Manager (GTM) tag within a workspace.",
             "parameters": {
                "type": "object",
                "properties": {
                   "account_id": {"type": "string", "description": "The GTM account ID."},
                   "container_id": {"type": "string", "description": "The GTM container ID."},
                   "workspace_id": {"type": "string", "description": "The GTM workspace ID where the tag is located."},
                   "tag_id": {"type": "string", "description": "The ID of the tag to be updated."},
                   "new_tag_name": {"type": "string", "description": "The new display name for the tag."}
                },
                "required": ["account_id", "container_id", "workspace_id", "tag_id", "new_tag_name"],
             },
          },
       },
    ]
    return client, available_tools, tools_schema