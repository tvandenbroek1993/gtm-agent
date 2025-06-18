import json

from googleapiclient.errors import HttpError


def get_information(tag_manager_client, account_id: str, container_id: str, workspace_id: str, information_type: str):
    """
    Retrieves a list of tags, variables, triggers, folders, or built-in variables
    from a specified GTM workspace based on the information_type parameter.
    """
    print(
        f"--> [Tool] Getting list of type '{information_type}' for account: {account_id}, container: {container_id}, workspace: {workspace_id}")
    try:
        parent_path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}"
        response_data = None
        data_key = None

        if information_type == 'tags':
            response_data = tag_manager_client.accounts().containers().workspaces().tags().list(
                parent=parent_path).execute()
            data_key = 'tag'
        elif information_type == 'variables':
            response_data = tag_manager_client.accounts().containers().workspaces().variables().list(
                parent=parent_path).execute()
            data_key = 'variable'
        elif information_type == 'built_in_variables':
            response_data = tag_manager_client.accounts().containers().workspaces().built_in_variables().list(
                parent=parent_path).execute()
            data_key = 'builtInVariable'  # Corrected key
        elif information_type == 'triggers':
            response_data = tag_manager_client.accounts().containers().workspaces().triggers().list(
                parent=parent_path).execute()
            data_key = 'trigger'
        elif information_type == 'folders':
            response_data = tag_manager_client.accounts().containers().workspaces().folders().list(
                parent=parent_path).execute()
            data_key = 'folder'  # Corrected key
        else:
            error_msg = f"Invalid information type specified: '{information_type}'. Please use 'tags', 'variables', 'built_in_variables', 'triggers', or 'folders'."
            print(f"--> [Tool] Error: {error_msg}")
            return {"error": error_msg}

        if not isinstance(response_data, dict):
            return {"error": f"Unexpected API response format for {information_type}: {type(response_data)}"}

        items = response_data.get(data_key, [])
        if not items:
            return {"message": f"No {information_type} found in the specified workspace."}

        processed_items = []
        for item in items:
            info = {
                'name': item.get('name'),
                'type': item.get('type')
            }

            # Built-in variables do not have an ID, so we handle them separately.
            if information_type != 'built_in_variables':
                info['id'] = item.get(f'{data_key}Id')

            if information_type == 'tags':
                info['firingTriggers'] = item.get('firingTriggerId', [])
            processed_items.append(info)

        print(f"--> [Tool] Successfully found {len(processed_items)} {information_type}.")
        return processed_items

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error fetching list of {information_type}: {error_details}")
        return {"error": f"API Error: {error_details.get('error', {}).get('message', 'Unknown error')}"}
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in get_information: {e}")
        return {"error": str(e)}


def get_specific_item(tag_manager_client, account_id: str, container_id: str, workspace_id: str, item_type: str, item_id: str):
    """
    Gets the full details of a single GTM item (tag, variable, trigger, or folder) using its ID.
    NOTE: This function does not support 'built_in_variables' as they cannot be retrieved individually.
    """
    print(f"--> [Tool] Getting details for {item_type} with ID {item_id}")

    # Create a mapping from a consistent singular item_type to the required plural path
    item_type_map = {
        'tag': 'tags',
        'variable': 'variables',
        'trigger': 'triggers',
        'folder': 'folders'
    }

    # Get the correct plural path, or None if the item_type is invalid
    item_path_name = item_type_map.get(item_type)

    if not item_path_name:
        error_msg = f"Invalid item type for get_specific_item: '{item_type}'. Supported types are 'tag', 'variable', 'trigger', 'folder'."
        print(f"--> [Tool] Error: {error_msg}")
        return {"error": error_msg}

    try:
        # Construct the full, correct API resource path
        path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/{item_path_name}/{item_id}"

        response = None
        if item_type == 'tag':
            response = tag_manager_client.accounts().containers().workspaces().tags().get(path=path).execute()
        elif item_type == 'variable':
            response = tag_manager_client.accounts().containers().workspaces().variables().get(path=path).execute()
        elif item_type == 'trigger':
            response = tag_manager_client.accounts().containers().workspaces().triggers().get(path=path).execute()
        elif item_type == 'folder':
            response = tag_manager_client.accounts().containers().workspaces().folders().get(path=path).execute()

        print(f"--> [Tool] Successfully retrieved details for {item_type} ID {item_id}.")
        return response

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error fetching item {item_id}: {error_details}")
        return {
            "error": f"API Error: {error_details.get('error', {}).get('message', 'Could not find the specified item.')}"
        }
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in get_specific_item: {e}")
        return {"error": str(e)}


def list_container_versions(tag_manager_client, account_id: str, container_id: str, include_deleted: bool = False):
    """
    Lists all Container Versions of a GTM Container.

    Args:
        tag_manager_client: The authenticated Google Tag Manager service object.
        account_id: The GTM Account ID.
        container_id: The GTM Container ID.
        include_deleted: Also retrieve deleted (archived) versions when true.

    Returns:
        A dictionary containing a list of container version headers or an error message.
    """
    print(
        f"--> [Tool] Getting container versions for account: {account_id}, container: {container_id}"
    )
    try:
        parent_path = f"accounts/{account_id}/containers/{container_id}"

        # Note: This implementation fetches all pages at once.
        # For very large numbers of versions, you might implement pagination with the pageToken.
        all_versions = []
        next_page_token = None

        while True:
            response = tag_manager_client.accounts().containers().version_headers().list(
                parent=parent_path,
                includeDeleted=include_deleted,
                pageToken=next_page_token
            ).execute()

            versions = response.get("containerVersionHeader", [])
            if versions:
                all_versions.extend(versions)

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        if not all_versions:
            return {"message": "No container versions found."}

        print(f"--> [Tool] Successfully found {len(all_versions)} container versions.")
        return {"containerVersionHeader": all_versions}

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error fetching container versions: {error_details}")
        return {"error": f"API Error: {error_details.get('error', {}).get('message', 'Unknown error')}"}
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in list_container_versions: {e}")
        return {"error": str(e)}


def get_container_version(tag_manager_client, account_id: str, container_id: str, version_id: str):
    """
    Gets a specific GTM Container Version by its ID.

    Args:
        tag_manager_client: The authenticated Google Tag Manager service object.
        account_id: The GTM Account ID.
        container_id: The GTM Container ID.
        version_id: The GTM ContainerVersion ID. Specify 'published' to retrieve the
                    currently published version.

    Returns:
        A dictionary containing the full container version object or an error message.
    """
    print(f"--> [Tool] Getting details for container version ID '{version_id}'")

    try:
        # Construct the full, correct API resource path
        path = f"accounts/{account_id}/containers/{container_id}/versions/{version_id}"

        response = tag_manager_client.accounts().containers().versions().get(
            path=path
        ).execute()

        print(f"--> [Tool] Successfully retrieved details for version ID '{version_id}'.")
        return response

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error fetching container version '{version_id}': {error_details}")
        return {
            "error": f"API Error: {error_details.get('error', {}).get('message', 'Could not find the specified version.')}"
        }
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in get_container_version: {e}")
        return {"error": str(e)}


def create_gtm_item(tag_manager_client, account_id: str, container_id: str, workspace_id: str, item_type: str, item_body: dict):
    """
    Creates a new GTM item (tag, variable, or trigger) within a specified workspace.

    Args:
        tag_manager_client: The initialized Google Tag Manager API client.
        account_id (str): The GTM account ID.
        container_id (str): The GTM container ID.
        workspace_id (str): The GTM workspace ID where the item will be created.
        item_type (str): The type of item to create ('tag', 'variable', or 'trigger').
        item_body (dict): A dictionary containing the configuration for the item to be created.
                          This should match the structure required by the GTM API for the given item_type.

    Returns:
        dict: The created item's resource representation if successful, or an error dictionary.
    """
    print(f"--> [Tool] Attempting to create a new {item_type} in workspace {workspace_id}...")

    # Create a mapping from a consistent singular item_type to the required plural path
    item_type_map = {
        'tag': 'tags',
        'variable': 'variables',
        'trigger': 'triggers'
    }

    # Get the correct plural path, or None if the item_type is invalid
    item_path_name = item_type_map.get(item_type)

    if not item_path_name:
        error_msg = f"Invalid item type for create_gtm_item: '{item_type}'. Supported types are 'tag', 'variable', 'trigger'."
        print(f"--> [Tool] Error: {error_msg}")
        return {"error": error_msg}

    try:
        # Construct the parent path where the item will be created
        parent_path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}"

        response = None
        if item_type == 'tag':
            response = tag_manager_client.accounts().containers().workspaces().tags().create(parent=parent_path, body=item_body).execute()
        elif item_type == 'variable':
            response = tag_manager_client.accounts().containers().workspaces().variables().create(parent=parent_path, body=item_body).execute()
        elif item_type == 'trigger':
            response = tag_manager_client.accounts().containers().workspaces().triggers().create(parent=parent_path, body=item_body).execute()

        if response:
            print(f"--> [Tool] Successfully created {item_type}: {response.get('name', 'Unnamed Item')}")
            return response
        else:
            return {"error": f"Failed to create {item_type}: No response from API."}

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error creating {item_type}: {error_details}")
        return {
            "error": f"API Error: {error_details.get('error', {}).get('message', f'Could not create the specified {item_type}.')}"
        }
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in create_gtm_item: {e}")
        return {"error": str(e)}


def update_gtm_item(tag_manager_client, account_id: str, container_id: str, workspace_id: str, item_type: str, item_id: str, item_body: dict, fingerprint: str = None):
    """
    Updates an existing GTM item (tag, variable, or trigger) within a specified workspace.
    The 'fingerprint' of the existing item is highly recommended to prevent conflicts.

    Args:
        tag_manager_client: The initialized Google Tag Manager API client.
        account_id (str): The GTM account ID.
        container_id (str): The GTM container ID.
        workspace_id (str): The GTM workspace ID where the item resides.
        item_type (str): The type of item to update ('tag', 'variable', or 'trigger').
        item_id (str): The ID of the specific item to update.
        item_body (dict): A dictionary containing the *full* updated configuration for the item.
                          This should match the structure required by the GTM API for the given item_type.
        fingerprint (str, optional): The fingerprint of the item to be updated.
                                     If provided, the update will only succeed if this
                                     fingerprint matches the current fingerprint of the item
                                     in storage, preventing "lost updates".
                                     It's strongly recommended to fetch the item first to get its current fingerprint.

    Returns:
        dict: The updated item's resource representation if successful, or an error dictionary.
    """
    print(f"--> [Tool] Attempting to update {item_type} with ID {item_id} in workspace {workspace_id}...")

    # Create a mapping from a consistent singular item_type to the required plural path
    item_type_map = {
        'tag': 'tags',
        'variable': 'variables',
        'trigger': 'triggers'
    }

    # Get the correct plural path, or None if the item_type is invalid
    item_path_name = item_type_map.get(item_type)

    if not item_path_name:
        error_msg = f"Invalid item type for update_gtm_item: '{item_type}'. Supported types are 'tag', 'variable', 'trigger'."
        print(f"--> [Tool] Error: {error_msg}")
        return {"error": error_msg}

    try:
        # Construct the full, correct API resource path for update
        path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/{item_path_name}/{item_id}"

        # Prepare arguments for the update method
        update_kwargs = {"path": path, "body": item_body}
        if fingerprint:
            update_kwargs["fingerprint"] = fingerprint

        response = None
        if item_type == 'tag':
            response = tag_manager_client.accounts().containers().workspaces().tags().update(**update_kwargs).execute()
        elif item_type == 'variable':
            response = tag_manager_client.accounts().containers().workspaces().variables().update(**update_kwargs).execute()
        elif item_type == 'trigger':
            response = tag_manager_client.accounts().containers().workspaces().triggers().update(**update_kwargs).execute()

        if response:
            print(f"--> [Tool] Successfully updated {item_type}: {response.get('name', 'Unnamed Item')} (ID: {item_id}).")
            return response
        else:
            return {"error": f"Failed to update {item_type}: No response from API."}

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error updating {item_type} ID {item_id}: {error_details}")
        return {
            "error": f"API Error: {error_details.get('error', {}).get('message', f'Could not update the specified {item_type}.')}"
        }
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in update_gtm_item: {e}")
        return {"error": str(e)}


def delete_gtm_item(tag_manager_client, account_id: str, container_id: str, workspace_id: str, item_type: str, item_id: str):
    """
    Deletes a specific GTM item (tag, variable, or trigger) from a workspace using its ID.

    Args:
        tag_manager_client: The initialized Google Tag Manager API client.
        account_id (str): The GTM account ID.
        container_id (str): The GTM container ID.
        workspace_id (str): The GTM workspace ID from which the item will be deleted.
        item_type (str): The type of item to delete ('tag', 'variable', or 'trigger').
        item_id (str): The ID of the specific item to delete.

    Returns:
        dict: An empty dictionary if successful, or an error dictionary.
    """
    print(f"--> [Tool] Attempting to delete {item_type} with ID {item_id} from workspace {workspace_id}...")

    # Create a mapping from a consistent singular item_type to the required plural path
    item_type_map = {
        'tag': 'tags',
        'variable': 'variables',
        'trigger': 'triggers'
    }

    # Get the correct plural path, or None if the item_type is invalid
    item_path_name = item_type_map.get(item_type)

    if not item_path_name:
        error_msg = f"Invalid item type for delete_gtm_item: '{item_type}'. Supported types are 'tag', 'variable', 'trigger'."
        print(f"--> [Tool] Error: {error_msg}")
        return {"error": error_msg}

    try:
        # Construct the full, correct API resource path for deletion
        path = f"accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}/{item_path_name}/{item_id}"

        response = None
        if item_type == 'tag':
            response = tag_manager_client.accounts().containers().workspaces().tags().delete(path=path).execute()
        elif item_type == 'variable':
            response = tag_manager_client.accounts().containers().workspaces().variables().delete(path=path).execute()
        elif item_type == 'trigger':
            response = tag_manager_client.accounts().containers().workspaces().triggers().delete(path=path).execute()

        # According to the documentation, a successful delete returns an empty JSON object {}
        if response == {}:
            print(f"--> [Tool] Successfully deleted {item_type} with ID {item_id}.")
            return {}  # Return an empty dictionary on success as per API spec
        else:
            # This case ideally shouldn't be hit if the API adheres to its spec,
            # but it's a safeguard.
            print(f"--> [Tool] Unexpected response after deleting {item_type} ID {item_id}: {response}")
            return {"message": f"Delete request sent, but received an unexpected response for {item_type} ID {item_id}."}

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        print(f"--> [Tool] API Error deleting {item_type} ID {item_id}: {error_details}")
        return {
            "error": f"API Error: {error_details.get('error', {}).get('message', f'Could not delete the specified {item_type}.')}"
        }
    except Exception as e:
        print(f"--> [Tool] An unexpected error occurred in delete_gtm_item: {e}")
        return {"error": str(e)}