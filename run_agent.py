from create_agent import create_agent
from tools import get_information, get_specific_item
from authentication import get_tag_manager_client
from datetime import date
import tiktoken
import json

def process_and_truncate_tool_output(function_name: str, response: dict, max_chars: int = 10000) -> str:
	"""
    Processes raw tool output to make it concise and safe for model history.
    This is a critical function to prevent context window overflow.
    """
	# Example for 'get_container_version', which is often very large
	if function_name == 'get_container_version' and 'tag' in response:
		# Instead of the full dump, create a summary.
		summary = {
			"versionId": response.get("versionId"),
			"name": response.get("name"),
			"description": response.get("description"),
			"tagCount": len(response.get("tag", [])),
			"triggerCount": len(response.get("trigger", [])),
			"variableCount": len(response.get("variable", [])),
			"builtInVariableCount": len(response.get("builtInVariable", []))
		}
		# You could also add a few examples of tag names if needed
		# summary["tagExamples"] = [t.get('name') for t in response.get("tag", [])[:3]]

		content = json.dumps(summary)
	else:
		# For other functions, just dump the JSON
		content = json.dumps(response)

	# As a final safeguard, truncate the content if it's still too long
	if len(content) > max_chars:
		truncated_content = content[:max_chars] + '... [truncated due to length]'
		print(f"⚠️ WARNING: Tool output for '{function_name}' was truncated.")
		return truncated_content

	return content


def run_agent(question: str,
              messages: list = None,
              account_id: str = None,
              container_id: str = None,
              workspace_id: str = None,
              credentials_dict: dict = None):
	"""
    Runs the agent for a single turn, with robust history and output processing.
    """
	client, available_tools, tools_schema = create_agent()
	print(f"\n🙋 User Question: {question}")

	conversation_history = messages if messages is not None else []

	current_date = date.today().strftime("%Y-%m-%d")

	# --- THIS IS THE FIX ---
	# The system prompt now includes the workspace_id, giving the AI full context.
	if account_id and container_id and workspace_id:
		system_content = (
			f"You are a helpful assistant for Google Tag Manager.\n"
			f"Today's date is {current_date}.\n"
			f"The user's context is Account ID: {account_id}, Container ID: {container_id}, and Workspace ID: {workspace_id}.\n\n"
			"When tools return data, it will be a summary. Do not mention that it is a summary unless relevant. "
			"Directly use the information provided."
		)
	else:
		# Fallback if context is somehow incomplete
		system_content = (
			f"You are a helpful assistant for Google Tag Manager.\n"
			f"Today's date is {current_date}.\n"
			"You must ask the user for any missing Account, Container, or Workspace IDs before using tools."
		)

	system_prompt = {"role": "system", "content": system_content}
	conversation_history.append({"role": "user", "content": question})

	while True:
		messages_to_send = [system_prompt] + conversation_history
		try:
			response = client.chat.completions.create(
				model="openai/gpt-4o",
				messages=messages_to_send,
				tools=tools_schema,
				tool_choice="auto"
			)
			response_message = response.choices[0].message
			response_dict = {
				"role": response_message.role,
				"content": response_message.content or "",
				"tool_calls": [
					{
						"id": tc.id,
						"type": tc.type,
						"function": {"name": tc.function.name, "arguments": tc.function.arguments}
					} for tc in response_message.tool_calls
				] if response_message.tool_calls else None,
			}
			conversation_history.append(response_dict)
		except Exception as e:
			print(f"❌ Error communicating with the AI model: {e}")
			error_message = "Sorry, I encountered an error communicating with the AI model. This might be due to a large amount of data. Please try a more specific question."
			conversation_history.append({"role": "assistant", "content": error_message})
			return error_message, conversation_history

		if not response_message.tool_calls:
			final_answer = response_message.content
			print("🤖 Agent Answer (No Tool):", final_answer)
			return final_answer, conversation_history

		print("✅ Agent decided to use a tool.")
		tag_manager_client = get_tag_manager_client(credentials_dict)
		if not tag_manager_client:
			error_message = "Error: Could not authenticate with Google Tag Manager. Your session might have expired."
			conversation_history.append({"role": "assistant", "content": error_message})
			return error_message, conversation_history

		tool_calls = response_message.tool_calls
		for tool_call in tool_calls:
			function_name = tool_call.function.name
			function_to_call = available_tools.get(function_name)

			try:
				function_args = json.loads(tool_call.function.arguments)
				print(f"▶️ Calling function: {function_name} with args: {function_args}")
				raw_function_response = function_to_call(tag_manager_client, **function_args)

				processed_content = process_and_truncate_tool_output(function_name, raw_function_response)

			except Exception as e:
				print(f"❌ Error executing tool '{function_name}': {e}")
				processed_content = json.dumps({"error": str(e)})

			conversation_history.append({
				"tool_call_id": tool_call.id,
				"role": "tool",
				"name": function_name,
				"content": processed_content,
			})