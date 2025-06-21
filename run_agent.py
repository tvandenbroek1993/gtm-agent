from create_agent import create_agent
from authentication import get_tag_manager_client
from datetime import date
import json

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

    tag_manager_client = get_tag_manager_client(credentials_dict)

    conversation_history = messages if messages is not None else []

    system_content = (
	    f"You are a seasoned Google Tag Manager specialist.\n"
	    f"Today's date is {date.today().strftime("%Y-%m-%d")}.\n"
	    f"The user's context is Account ID: {account_id}, Container ID: {container_id}, and Workspace ID: {workspace_id}.\n"
        f"The output from the tools often consists of JSON data, put some effort in nice formatting for the end user in a non-technical way"
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

          # Initialize tool_calls_data before the try block for the response_dict
          tool_calls_data = None
          if response_message.tool_calls:
              try:
                  tool_calls_data = [
                      {
                          "id": tc.id,
                          "type": tc.type,
                          "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                      } for tc in response_message.tool_calls
                  ]
              except AttributeError as e:
                  print(f"⚠️ Warning: Malformed tool_call object received from AI: {e}")
                  # You might want to log the full response_message for debugging here
                  tool_calls_data = [] # Treat as no valid tool calls if malformed

          response_dict = {
             "role": response_message.role,
             "content": response_message.content or "",
             "tool_calls": tool_calls_data,
          }
          conversation_history.append(response_dict)

       except Exception as e:
          print(f"❌ Error communicating with the AI model or processing its response: {e}")
          error_message = "Sorry, I encountered an error communicating with the AI model or processing its response. This might be due to an unexpected response format. Please try a more specific question."
          conversation_history.append({"role": "assistant", "content": error_message})
          return error_message, conversation_history

       # Now, directly use response_message.tool_calls for the logic,
       # as it's the original object from the API response.
       if not response_message.tool_calls:
          final_answer = response_message.content
          print("🤖 Agent Answer (No Tool):", final_answer)
          return final_answer, conversation_history

       print("✅ Agent decided to use a tool.")
       # Ensure tool_calls is an iterable (it should be if response_message.tool_calls was not None)
       tool_calls = response_message.tool_calls
       if not isinstance(tool_calls, (list, tuple)):
           print(f"❌ Error: response_message.tool_calls is not a list/tuple, but: {type(tool_calls)}. Attempting to proceed with empty list.")
           tool_calls = []

       for tool_call in tool_calls:
          function_name = tool_call.function.name
          function_to_call = available_tools.get(function_name)

          if function_to_call is None:
              processed_content = function_to_call(tag_manager_client, **function_args)
              conversation_history.append({
                  "tool_call_id": tool_call.id if hasattr(tool_call, 'id') else 'unknown',
                  "role": "tool",
                  "name": function_name,
                  "content": processed_content,
              })
              continue

          try:
              function_args = json.loads(tool_call.function.arguments)
              print(f"▶️ Calling function: {function_name} with args: {function_args}")
              raw_content = function_to_call(tag_manager_client, **function_args)
              processed_content = json.dumps(raw_content, indent=2)
              print(f"✅ Tool output: {processed_content[:500]}...")

          except json.JSONDecodeError as e:
              print(f"❌ Error decoding arguments for tool '{function_name}': {e}. Arguments: {tool_call.function.arguments}")
              processed_content = json.dumps({"error": f"Invalid JSON arguments: {e}"})
          except Exception as e:
             print(f"❌ Error executing tool '{function_name}': {e}")
             processed_content = json.dumps({"error": str(e)})

          conversation_history.append({
              "tool_call_id": tool_call.id if hasattr(tool_call, 'id') else 'unknown',
              "role": "tool",
              "name": function_name,
              "content": processed_content,
          })