import os
import flask
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests
import requests
from functools import wraps
from run_agent import run_agent
from authentication import *
from dotenv import load_dotenv

load_dotenv()
ENVIRONMENT = os.environ.get("ENVIRONMENT", "production")

app = Flask(__name__)

CORS(app, supports_credentials=True)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "a-very-secret-key-for-dev")

CLIENT_SECRETS_CONFIG = {
    "web": {
        "client_id": os.environ.get("OAUTH_CLIENT_ID"),
        "client_secret": os.environ.get("OAUTH_CLIENT_SECRET"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [os.environ.get("REDIRECT_URI")]
    }
}

SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/tagmanager.readonly',
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/tagmanager.edit.containerversions'
    ''
]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'credentials' not in flask.session:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    flow = Flow.from_client_config(
        client_config=CLIENT_SECRETS_CONFIG,
        scopes=SCOPES,
        redirect_uri=os.environ.get("REDIRECT_URI")
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline', include_granted_scopes='true'
    )
    flask.session['state'] = state
    return flask.redirect(authorization_url)


@app.route('/logout')
def logout():
    flask.session.clear()
    return flask.redirect(flask.url_for('home'))


@app.route('/oauth2callback')
def oauth2callback():
    state = flask.session.get('state')
    if not state or state != request.args.get('state'):
        return "State mismatch. Possible CSRF attack.", 400
    flow = Flow.from_client_config(
        client_config=CLIENT_SECRETS_CONFIG,
        scopes=SCOPES,
        redirect_uri=os.environ.get("REDIRECT_URI")
    )
    try:
        authorization_response = request.url
        if not authorization_response.startswith('https://'):
             authorization_response = authorization_response.replace('http://', 'https://', 1)
        flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        return f"Failed to fetch token: {str(e)}", 400

    credentials = flow.credentials
    authed_session = google.auth.transport.requests.AuthorizedSession(credentials)
    user_info_response = authed_session.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user_info = user_info_response.json()
    flask.session['credentials'] = {
        'token': credentials.token, 'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri, 'client_id': credentials.client_id,
        'client_secret': credentials.client_secret, 'scopes': credentials.scopes
    }
    flask.session['user_info'] = {
        'email': user_info.get('email'), 'name': user_info.get('name'),
        'picture': user_info.get('picture')
    }
    return flask.redirect(flask.url_for('home'))

@app.route('/api/auth/status')
def auth_status():
    """Endpoint for the frontend to check if the user is authenticated."""
    if 'credentials' in flask.session and 'user_info' in flask.session:
        return jsonify({
            "is_authenticated": True,
            "user": flask.session['user_info']
        })
    return jsonify({"is_authenticated": False})

@app.route('/api/accounts', methods=['GET'])
@login_required
def api_get_accounts():
    accounts = get_accounts_list(flask.session['credentials'])
    if accounts is None:
       return jsonify({"error": "Failed to retrieve accounts."}), 500
    return jsonify(accounts)

@app.route('/api/containers', methods=['GET'])
@login_required
def api_get_containers():
    account_id = request.args.get('accountId')
    if not account_id:
       return jsonify({"error": "accountId parameter is required"}), 400
    containers = get_containers_list(account_id, flask.session['credentials'])
    if containers is None:
       return jsonify({"error": "Failed to retrieve containers."}), 500
    return jsonify(containers)

@app.route('/api/workspaces', methods=['GET'])
@login_required
def api_get_workspaces():
    account_id = request.args.get('accountId')
    container_id = request.args.get('containerId')
    if not all([account_id, container_id]):
       return jsonify({"error": "accountId and containerId parameters are required"}), 400
    workspaces = get_workspaces_list(account_id, container_id, flask.session['credentials'])
    if workspaces is None:
       return jsonify({"error": "Failed to retrieve workspaces."}), 500
    return jsonify(workspaces)


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.json
    question = data.get('question')
    history = data.get('history', [])
    context = data.get('context', {})
    if not all([question, context.get('accountId'), context.get('containerId'), context.get('workspaceId')]):
       return jsonify({"error": "Missing required fields"}), 400

    answer, updated_history = run_agent(
       question=question,
       messages=history,
       account_id=context.get('accountId'),
       container_id=context.get('containerId'),
       workspace_id=context.get('workspaceId'),
       credentials_dict=flask.session['credentials']
    )
    return jsonify({"answer": answer, "history": updated_history})

@app.route("/")
def home():
    """Serves the main HTML page."""
    return render_template("index.html")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    use_ssl = ENVIRONMENT != "production" and os.path.exists("../cert.pem") and os.path.exists("../key.pem")
    ssl_context = ("../cert.pem", "../key.pem") if use_ssl else None
    if ENVIRONMENT == "production":
        print("🚀 Starting GTM Agent in production mode..")
        app.run(host="0.0.0.0", port=port)
    else:
        use_ssl = ENVIRONMENT != "production" and os.path.exists("cert.pem") and os.path.exists("key.pem")
        ssl_context = ("cert.pem", "key.key") if use_ssl else None
        print(f"🤖 GTM Agent is running. Visit {'https://' if use_ssl else 'http://'}127.0.0.1:5000 to test.")
        app.run(port=5000, debug=True, ssl_context=ssl_context)