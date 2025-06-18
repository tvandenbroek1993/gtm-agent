# authentication.py

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_tag_manager_client(user_credentials_dict):
	"""
	Creates a GTM client object from a user's credentials dictionary.
	"""
	try:
		# Create credentials object from the dictionary provided by the Flask session
		credentials = Credentials(**user_credentials_dict)
		tag_manager_client = build('tagmanager', 'v2', credentials=credentials)
		print("--> [Helper] Successfully created Tag Manager client for the logged-in user.")
		return tag_manager_client
	except Exception as e:
		print(f"--> [Helper] Error creating Tag Manager client from user credentials: {e}")
		return None


def get_accounts_list(credentials_dict):
	"""Fetches a list of all GTM Accounts the user can access."""
	try:
		client = get_tag_manager_client(credentials_dict)
		if not client:
			raise ConnectionError("Failed to get Tag Manager client.")

		response = client.accounts().list().execute()
		return response.get('account', [])
	except (HttpError, ConnectionError, Exception) as e:
		print(f"Error fetching accounts: {e}")
		return None


def get_containers_list(account_id, credentials_dict):
	"""Fetches a list of containers for a given GTM Account ID."""
	try:
		client = get_tag_manager_client(credentials_dict)
		if not client:
			raise ConnectionError("Failed to get Tag Manager client.")

		parent_path = f"accounts/{account_id}"
		response = client.accounts().containers().list(parent=parent_path).execute()
		return response.get('container', [])
	except (HttpError, ConnectionError, Exception) as e:
		print(f"Error fetching containers for account {account_id}: {e}")
		return None


def get_workspaces_list(account_id, container_id, credentials_dict):
	"""Fetches a list of workspaces for a given GTM Container ID."""
	try:
		client = get_tag_manager_client(credentials_dict)
		if not client:
			raise ConnectionError("Failed to get Tag Manager client.")

		parent_path = f"accounts/{account_id}/containers/{container_id}"
		response = client.accounts().containers().workspaces().list(parent=parent_path).execute()
		return response.get('workspace', [])
	except (HttpError, ConnectionError, Exception) as e:
		print(f"Error fetching workspaces for container {container_id}: {e}")
		return None