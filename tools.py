import json
import logging
import datetime  # Added import for datetime
from googleapiclient.errors import HttpError

# from googleapiclient.discovery import build # Assuming 'build' might be needed if tag_manager_client isn't pre-built
# from your_credential_module import load_credentials # Assuming 'load_credentials' exists

logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
	handlers=[
		logging.StreamHandler()
	]
)
logger = logging.getLogger(__name__)


# --- Start of assumed helper function (remove_null_keys) ---
# This function is used in tools.py but not defined in the provided snippets.
# A basic implementation is included here for completeness.
def remove_null_keys(data):
	"""
	Recursively removes keys with None values from dictionaries and lists within data.
	"""
	if isinstance(data, dict):
		return {k: remove_null_keys(v) for k, v in data.items() if v is not None}
	elif isinstance(data, list):
		return [remove_null_keys(elem) for elem in data if elem is not None]
	else:
		return data


# --- End of assumed helper function ---

def _handle_api_error(e: HttpError, operation_name: str):
	"""
	Handles Google API HttpError, extracting more details.
	"""
	logger.error(f"--> [API Error] Failed to retrieve {operation_name}.")
	logger.error(f"--> [API Error] HTTP Status Code: {e.resp.status}")
	logger.error(f"--> [API Error] Response Content: {e.content.decode('utf-8')}")
	try:
		error_details = e.error_details
		if error_details:
			logger.error(f"--> [API Error] Details from error_details: {error_details}")
		# Attempt to parse the content as JSON for more structured error messages
		import json
		error_json = json.loads(e.content.decode('utf-8'))
		if 'error' in error_json and 'message' in error_json['error']:
			logger.error(f"--> [API Error] Message from JSON content: {error_json['error']['message']}")
		if 'error' in error_json and 'errors' in error_json['error']:
			for err in error_json['error']['errors']:
				logger.error(
					f"--> [API Error] Specific error: Domain={err.get('domain')}, Reason={err.get('reason')}, Message={err.get('message')}")
	except (json.JSONDecodeError, KeyError):
		logger.error(
			"--> [API Error] Could not parse detailed error from response content (not JSON or unexpected format).")
	return {"error": f"API Error during {operation_name}: {e.resp.status} - {e.content.decode('utf-8')}"}


def _handle_unexpected_error(e: Exception, operation_name: str):
	"""
	Handles unexpected general exceptions.
	"""
	logger.exception(f"--> [Unexpected Error] An unexpected error occurred during {operation_name}.")
	return {"error": f"An unexpected error occurred during {operation_name}: {str(e)}"}


def list_gtm_items(tag_manager_client, account_id: str, container_id: str, workspace_id: str = None,
                   information_type: str = None):
	"""
	Retrieves a list of tags, variables, triggers, folders, built-in variables,
	or container versions from a specified GTM workspace or container,
	based on the information_type parameter.

	Args:
		tag_manager_client: An authorized Google Tag Manager API client object.
		account_id (str): The GTM account ID.
		container_id (str): The GTM container ID.
		workspace_id (str): The GTM workspace ID. (Not used for 'versions' type)
		information_type (str): The type of GTM item to list.
								 Accepts: "tags", "variables", "built_in_variables",
										  "triggers", "folders", "versions".

	Returns:
		list: A list of dictionaries, where each dictionary represents an item of the
			  specified `information_type`. Returns a dictionary with an "error" or
			  "message" key if no items are found or an error occurs.
	"""
	# Define API methods for each information type
	method_tags = tag_manager_client.accounts().containers().workspaces().tags().list
	method_variables = tag_manager_client.accounts().containers().workspaces().variables().list
	method_built_in_variables = tag_manager_client.accounts().containers().workspaces().built_in_variables().list
	method_triggers = tag_manager_client.accounts().containers().workspaces().triggers().list
	method_folders = tag_manager_client.accounts().containers().workspaces().folders().list
	method_versions = tag_manager_client.accounts().containers().version_headers().list

	# Map information types to their respective API method, response key, and item ID key
	info_map = {
		'tags': {'method': method_tags, 'key': 'tag', 'item_id_key': 'tagId'},
		'variables': {'method': method_variables, 'key': 'variable', 'item_id_key': 'variableId'},
		'built_in_variables': {
			'method': method_built_in_variables, 'key': 'builtInVariable', 'item_id_key': 'builtInVariableId'},
		'triggers': {'method': method_triggers, 'key': 'trigger', 'item_id_key': 'triggerId'},
		'folders': {'method': method_folders, 'key': 'folder', 'item_id_key': 'folderId'},
		'versions': {'method': method_versions, 'key': 'containerVersionHeader', 'item_id_key': 'containerVersionId'}
	}

	try:
		if information_type not in info_map:
			return {"error": f"Invalid information_type: {information_type}. "
			                 "Accepted types are: {', '.join(info_map.keys())}"}

		if information_type == 'versions':
			parent_path = f"accounts/{account_id}/containers/{container_id}"
		else:
			# Added a check for workspace_id when not listing versions
			if workspace_id is None:
				return {"error": "workspace_id is required for information_type other than 'versions'."}
			parent_path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}"

		config = info_map[information_type]

		all_items = []
		next_page_token = None
		# Loop to handle pagination and retrieve all items
		while True:
			response = config['method'](parent=parent_path, pageToken=next_page_token).execute()
			current_items = response.get(config['key'], [])
			all_items.extend(current_items)

			next_page_token = response.get("nextPageToken")
			if not next_page_token:
				break  # No more pages

		processed_items = []
		for item in all_items:
			# Construct a dictionary with 'name', 'id', and 'type' (if available)
			info = {
				'name': item.get('name'),
				'id': item.get(config['item_id_key'])
			}
			if 'type' in item:  # 'type' is not always present (e.g., for folders)
				info['type'] = item['type']
			processed_items.append(info)

		# Use the external helper function to remove keys with None values
		processed_items = remove_null_keys(processed_items)
		print(f"--> [GTM] Successfully listed {len(processed_items)} {information_type} items.")
		return processed_items

	except HttpError as e:
		return _handle_api_error(e, f"listing GTM {information_type}")
	except Exception as e:
		return _handle_unexpected_error(e, f"listing GTM {information_type}")


def get_gtm_item(tag_manager_client, account_id: str, container_id: str, workspace_id: str = None,
                 information_type: str = None, item_id: str = None):
	"""
	Retrieves a specific tag, variable, trigger, folder, or container version
	from a specified GTM workspace or container, based on the information_type
	and item_id parameters. Built-in variables do not support a direct 'get' operation.

	Args:
		tag_manager_client: An authorized Google Tag Manager API client object.
		account_id (str): The GTM account ID.
		container_id (str): The GTM container ID.
		workspace_id (str): The GTM workspace ID. (Not used for 'versions' type)
		information_type (str): The type of GTM item to retrieve.
								 Accepts: "tags", "variables", "triggers",
										  "folders", "versions".
		item_id (str): The ID of the specific item to retrieve.

	Returns:
		dict: A dictionary representing the retrieved item. Returns a dictionary
			  with an "error" or "message" key if the item is not found,
			  the information_type is invalid, or an error occurs.
	"""
	# Define API methods for each information type's 'get' operation
	method_tags_get = tag_manager_client.accounts().containers().workspaces().tags().get
	method_variables_get = tag_manager_client.accounts().containers().workspaces().variables().get
	method_triggers_get = tag_manager_client.accounts().containers().workspaces().triggers().get
	method_folders_get = tag_manager_client.accounts().containers().workspaces().folders().get
	method_versions_get = tag_manager_client.accounts().containers().versions().get

	# Map information types to their respective API method and path segment
	info_map = {
		'tags': {'method': method_tags_get, 'path_segment': 'tags'},
		'variables': {'method': method_variables_get, 'path_segment': 'variables'},
		'triggers': {'method': method_triggers_get, 'path_segment': 'triggers'},
		'folders': {'method': method_folders_get, 'path_segment': 'folders'},
		'versions': {'method': method_versions_get, 'path_segment': 'versions'}
	}

	try:
		if information_type not in info_map:
			return {"error": f"Invalid information_type: {information_type}. "
			                 "Accepted types are: {', '.join(info_map.keys())}"}

		if information_type == 'built_in_variables':
			return {"message": "Built-in variables do not support a direct 'get' operation. "
			                   "You can only list them."}

		config = info_map[information_type]

		# Construct the API path based on information type
		if information_type == 'versions':
			# For versions, the path is accounts/{account}/containers/{container}/versions/{version}
			# The item_id directly maps to the version ID here.
			item_path = f"accounts/{account_id}/containers/{container_id}/versions/{item_id}"
			# For versions.get, the item_id is passed as a query parameter
			response = config['method'](path=item_path, containerVersionId=item_id).execute()
		else:
			# Added a check for workspace_id when not getting versions
			if workspace_id is None:
				return {"error": "workspace_id is required for information_type other than 'versions'."}
			# For other types, the path is accounts/{account}/containers/{container}/workspaces/{workspace}/{type}/{itemId}
			item_path = (f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/"
			             f"{config['path_segment']}/{item_id}")
			response = config['method'](path=item_path).execute()

		if response:
			return response
		else:
			return {"message": f"No {information_type} found with ID: {item_id}"}

	except HttpError as e:
		return _handle_api_error(e, f"retrieving GTM {information_type}")
	except Exception as e:
		return _handle_unexpected_error(e, f"retrieving GTM {information_type}")


def compare_gtm_versions(tag_manager_client, account_id: str, container_id: str, version_id_old: str,
                         version_id_new: str):
	"""
	Compares two Google Tag Manager container versions and reports additions,
	deletions, and modifications of tags, triggers, and variables.

	Args:
		tag_manager_client: An authorized Google Tag Manager API client object.
		account_id (str): The GTM account ID.
		container_id (str): The GTM container ID.
		version_id_old (str): The ID of the older GTM container version.
		version_id_new (str): The ID of the newer GTM container version.

	Returns:
		dict: A dictionary detailing the differences between the two versions,
			  including a timestamp for the new version and lists of added,
			  deleted, and modified tags, triggers, and variables.
			  Returns a dictionary with an "error" key if an error occurs.
	"""
	# 'gtm' client is now passed as an argument 'tag_manager_client'
	gtm = tag_manager_client

	def get_version(version_id):
		"""Helper to fetch a specific GTM container version."""
		path = f"accounts/{account_id}/containers/{container_id}/versions/{version_id}"
		# Use the get method, similar to how it's used in get_gtm_item for versions
		return gtm.accounts().containers().versions().get(path=path, containerVersionId=version_id).execute()

	def sort_obj(obj):
		"""Recursively sorts dictionaries and lists for consistent comparison."""
		if isinstance(obj, dict):
			return {k: sort_obj(v) for k, v in sorted(obj.items())}
		if isinstance(obj, list):
			# Sort list of dictionaries by their JSON representation to ensure consistent ordering
			return sorted([sort_obj(i) for i in obj], key=lambda x: json.dumps(x, sort_keys=True))
		return obj

	def serialize(obj):
		"""Serializes an object to a consistent JSON string for comparison."""
		return json.dumps(sort_obj(obj), sort_keys=True)

	def clean(item):
		"""Removes GTM-specific metadata keys that should not be part of the comparison."""
		# 'path' and 'fingerprint' are also dynamic and should be excluded for comparison
		return {k: v for k, v in item.items() if k not in ['accountId', 'containerId', 'path', 'fingerprint']}

	def fingerprint_to_date(fp):
		"""Converts GTM fingerprint (timestamp) to a readable date string."""
		try:
			return datetime.datetime.fromtimestamp(int(fp) / 1000).strftime("%Y-%m-%d %H:%M:%S")
		except (ValueError, TypeError):
			logger.warning(f"Invalid fingerprint value: {fp}. Returning N/A for timestamp.")
			return "N/A"

	try:
		logger.info(
			f"--> [GTM] Comparing versions: old={version_id_old}, new={version_id_new} for container {container_id}")
		version_old = get_version(version_id_old)
		version_new = get_version(version_id_new)

		# Handle cases where versions might not be found
		if not version_old or 'error' in version_old:
			return {
				"error": f"Could not retrieve old version {version_id_old}. Details: {version_old.get('error', 'Unknown error')}"}
		if not version_new or 'error' in version_new:
			return {
				"error": f"Could not retrieve new version {version_id_new}. Details: {version_new.get('error', 'Unknown error')}"}

		result = {
			"version_new_id": version_new.get("containerVersionId"),
			"timestamp_new": fingerprint_to_date(version_new.get("fingerprint"))
		}

		# Iterate through tags, triggers, and variables to find differences
		for key in ["tag", "trigger", "variable"]:
			id_key = f"{key}Id"
			old_items = {i["name"]: i for i in version_old.get(key, [])}
			new_items = {i["name"]: i for i in version_new.get(key, [])}

			added = [{"name": i["name"], "id": i.get(id_key, "N/A")} for name, i in new_items.items() if
			         name not in old_items]
			deleted = [{"name": i["name"], "id": i.get(id_key, "N/A")} for name, i in old_items.items() if
			           name not in new_items]

			modified = []
			for name in old_items.keys() & new_items.keys():
				# Compare cleaned and serialized versions of the items
				if serialize(clean(old_items[name])) != serialize(clean(new_items[name])):
					modified.append({
						"name": name,
						"old_id": old_items[name].get(id_key, "N/A"),
						"new_id": new_items[name].get(id_key, "N/A")
					})

			# Add the differences to the result only if there are any changes for the specific item type
			if any([added, deleted, modified]):
				result[key] = {}
				if added: result[key]["added"] = added
				if deleted: result[key]["deleted"] = deleted
				if modified: result[key]["modified"] = modified

		logger.info(
			f"--> [GTM] Successfully compared versions. Found differences: {bool(result.get('tag') or result.get('trigger') or result.get('variable'))}")
		return result

	except HttpError as e:
		return _handle_api_error(e, "comparing GTM versions")
	except Exception as e:
		return _handle_unexpected_error(e, "comparing GTM versions")


def update_gtm_tag_name(tag_manager_client, account_id: str, container_id: str, workspace_id: str,
                        tag_id: str, new_tag_name: str):
    """
    Updates the display name of a specific GTM tag within a workspace.

    Args:
       tag_manager_client: An authorized Google Tag Manager API client object.
       account_id (str): The GTM account ID.
       container_id (str): The GTM container ID.
       workspace_id (str): The GTM workspace ID where the tag is located.
       tag_id (str): The ID of the tag to be updated.
       new_tag_name (str): The new display name for the tag.

    Returns:
       dict: A dictionary representing the updated tag if successful,
            otherwise a dictionary with an "error" key.
    """
    try:
        # 1. Get the existing tag to retain its current configuration
        # This is crucial because the update method replaces the entire resource.
        # We only want to change the 'name' field and keep all other fields as they are.
        existing_tag = get_gtm_item(
            tag_manager_client=tag_manager_client,
            account_id=account_id,
            container_id=container_id,
            workspace_id=workspace_id,
            information_type='tags',
            item_id=tag_id
        )

        if "error" in existing_tag:
            logger.error(f"--> [GTM] Could not retrieve existing tag {tag_id} to update its name: {existing_tag['error']}")
            return {"error": f"Failed to retrieve existing tag: {existing_tag['error']}"}

        if "message" in existing_tag:
            logger.warning(f"--> [GTM] Tag {tag_id} not found: {existing_tag['message']}")
            return {"error": f"Tag {tag_id} not found: {existing_tag['message']}"}

        # 2. Update the 'name' field in the existing tag object
        existing_tag['name'] = new_tag_name

        # 3. Construct the API path for the tag update
        path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/tags/{tag_id}"

        # 4. Call the tags().update() method
        updated_tag = tag_manager_client.accounts().containers().workspaces().tags().update(path=path,body=existing_tag).execute()

        logger.info(f"--> [GTM] Successfully updated tag '{tag_id}' name to '{new_tag_name}'.")
        return updated_tag

    except HttpError as e:
        return _handle_api_error(e, f"updating GTM tag name for tag ID {tag_id}")
    except Exception as e:
        return _handle_unexpected_error(e, f"updating GTM tag name for tag ID {tag_id}")