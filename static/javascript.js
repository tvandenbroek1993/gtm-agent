document.addEventListener('DOMContentLoaded', async () => {
    // --- DOM Elements ---
    const accountSelect = document.getElementById('account-select');
    const containerSelect = document.getElementById('container-select');
    const workspaceSelect = document.getElementById('workspace-select');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const chatContainer = document.getElementById('chat-container');
    const loginModal = document.getElementById('login-modal');
    const userProfileDiv = document.getElementById('user-profile');

    // --- State Management ---
    let selectedContext = {
        accountId: null,
        containerId: null,
        workspaceId: null,
    };
    let chatHistory = [];

    // --- API Configuration ---
    // Use this URL for your deployed backend
//    const API_BASE_URL = 'https://gtm-agent-354636185201.europe-west1.run.app';
    const API_BASE_URL = 'http://127.0.0.1:5000'
    // Use this URL for local testing
    // const API_BASE_URL = 'http://127.0.0.1:5000';

    // --- API Functions ---
    async function fetchApi(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                // If unauthorized, trigger login
                if (response.status === 401) {
                    showLoginModal();
                }
                const errorBody = await response.json().catch(() => ({ error: `Request failed with status ${response.status}` }));
                throw new Error(errorBody.error);
            }
            return await response.json();
        } catch (error) {
            console.error(`API call to ${url} failed:`, error);
            throw error;
        }
    }
    const getAccountInfo = () => fetchApi(`${API_BASE_URL}/api/accounts`).catch(() => {
        addMessageToChat('Error: Could not load accounts. You may need to log in again.', 'agent');
        return [];
    });
    const getContainerInfo = (accountId) => fetchApi(`${API_BASE_URL}/api/containers?accountId=${accountId}`).catch(() => {
        addMessageToChat(`Error: Could not load containers.`, 'agent');
        return [];
    });
    const getWorkspaceInfo = (accountId, containerId) => fetchApi(`${API_BASE_URL}/api/workspaces?accountId=${accountId}&containerId=${containerId}`).catch(() => {
        addMessageToChat('Error: Could not load workspaces.', 'agent');
        return [];
    });
    async function runAgent(question, history, context) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ question, history, context })
            });
            if (!response.ok) throw new Error('Agent request failed');
            return await response.json();
        } catch (error) {
            console.error("Agent run failed:", error);
            const errorMessage = "I'm sorry, I couldn't connect to the agent.";
            return { answer: errorMessage, history: [...history, { role: 'user', content: question }, { role: 'agent', content: errorMessage }] };
        }
    }

    // --- UI Functions ---
    function populateSelect(select, items, valueField, nameField, placeholder) {
        select.innerHTML = `<option value="">${placeholder}</option>`;
        if (items) {
            items.forEach(item => {
                const option = document.createElement('option');
                option.value = item[valueField];
                option.textContent = item[nameField];
                select.appendChild(option);
            });
        }
        select.disabled = !items || items.length === 0;
    }

    function resetSelect(select, placeholder) {
        select.innerHTML = `<option>${placeholder}</option>`;
        select.disabled = true;
    }

    function addMessageToChat(message, sender) {
        const wrapper = document.createElement('div');
        chatContainer.appendChild(wrapper);

        const agentIcon = `<div class="bg-gray-700 text-purple-400 rounded-full h-8 w-8 flex-shrink-0 flex items-center justify-center"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clip-rule="evenodd" /></svg></div>`;
        const userIcon = `<div class="bg-gray-700 text-white rounded-full h-8 w-8 flex-shrink-0 flex items-center justify-center order-2"><svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg></div>`;

        if (sender === 'loading') {
            wrapper.id = 'loading-indicator';
            wrapper.className = 'flex items-start gap-3 mb-5';
            wrapper.innerHTML = `${agentIcon}<div class="bg-gray-700 p-4 rounded-lg shadow-md chat-bubble flex items-center"><div class="loader"></div></div>`;
        } else {
            const isUser = sender === 'user';
            wrapper.className = `flex items-start gap-3 mb-5 ${isUser ? 'justify-end' : ''}`;
            const bubbleHTML = `<div class="chat-bubble ${isUser ? 'chat-bubble-user order-1' : 'chat-bubble-agent'}"><p class="text-sm">${message.replace(/\n/g, '<br>')}</p></div>`;
            wrapper.innerHTML = (isUser ? '' : agentIcon) + bubbleHTML + (isUser ? userIcon : '');
        }

        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    function removeLoadingIndicator() {
        const el = document.getElementById('loading-indicator');
        if (el) el.remove();
    }

    function showLoginModal() {
        loginModal.classList.remove('hidden');
        userProfileDiv.classList.add('hidden');
        // Disable all controls
        accountSelect.disabled = true;
        containerSelect.disabled = true;
        workspaceSelect.disabled = true;
        chatInput.disabled = true;
        sendBtn.disabled = true;
        chatInput.placeholder = 'Please log in to begin...';
    }


    // --- Main Logic ---
    async function handleSendMessage() {
        const question = chatInput.value.trim();
        if (!question || sendBtn.disabled) return;
        addMessageToChat(question, 'user');
        chatInput.value = '';
        chatInput.disabled = true;
        sendBtn.disabled = true;
        addMessageToChat('', 'loading');

        const contextForAgent = {
            ...selectedContext,
            accountName: accountSelect.options[accountSelect.selectedIndex].text,
            containerName: containerSelect.options[containerSelect.selectedIndex].text,
            workspaceName: workspaceSelect.options[workspaceSelect.selectedIndex].text,
        };

        const { answer, history } = await runAgent(question, chatHistory, contextForAgent);
        chatHistory = history;

        removeLoadingIndicator();
        addMessageToChat(answer, 'agent');

        chatInput.disabled = false;
        sendBtn.disabled = false;
        chatInput.focus();
    }

    // --- Event Listeners ---
    accountSelect.addEventListener('change', async (e) => {
        const accountId = e.target.value;
        chatHistory = [];
        resetSelect(containerSelect, 'Select an account first');
        resetSelect(workspaceSelect, 'Select a container first');
        if (!accountId) {
            localStorage.removeItem('selectedAccountId');
            localStorage.removeItem('selectedAccountName');
            localStorage.removeItem('selectedContainerId');
            localStorage.removeItem('selectedContainerName');
            localStorage.removeItem('selectedWorkspaceId');
            localStorage.removeItem('selectedWorkspaceName');
            return;
        };
        selectedContext = { accountId: accountId, containerId: null, workspaceId: null };
        const containers = await getContainerInfo(accountId);
        populateSelect(containerSelect, containers, 'containerId', 'name', 'Select a container');
        localStorage.setItem('selectedAccountId', accountId);
        localStorage.setItem('selectedAccountName', accountSelect.options[accountSelect.selectedIndex].text);
        localStorage.removeItem('selectedContainerId');
        localStorage.removeItem('selectedContainerName');
        localStorage.removeItem('selectedWorkspaceId');
        localStorage.removeItem('selectedWorkspaceName');
    });

    containerSelect.addEventListener('change', async (e) => {
        const containerId = e.target.value;
        chatHistory = [];
        resetSelect(workspaceSelect, 'Select a container first');
        if (!containerId) return;
        selectedContext.containerId = containerId;
        const workspaces = await getWorkspaceInfo(selectedContext.accountId, containerId);
        populateSelect(workspaceSelect, workspaces, 'workspaceId', 'name', 'Select a workspace');
        localStorage.setItem('selectedContainerId', containerId);
        localStorage.setItem('selectedContainerName', containerSelect.options[containerSelect.selectedIndex].text);
        localStorage.removeItem('selectedWorkspaceId');
        localStorage.removeItem('selectedWorkspaceName');
    });

    workspaceSelect.addEventListener('change', (e) => {
        const workspaceId = e.target.value;
        chatHistory = [];
        chatInput.disabled = true;
        sendBtn.disabled = true;
        if (!workspaceId) return;
        selectedContext.workspaceId = workspaceId;
        chatInput.disabled = false;
        sendBtn.disabled = false;
        const workspaceName = workspaceSelect.options[workspaceSelect.selectedIndex].text.trim();
        chatInput.placeholder = `Ask about workspace "${workspaceName}"`;
        chatInput.focus();
        localStorage.setItem('selectedWorkspaceId', workspaceId);
        localStorage.setItem('selectedWorkspaceName', workspaceName);
    });

    sendBtn.addEventListener('click', handleSendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            handleSendMessage();
        }
    });

    // --- Initialization & Authentication ---
    async function initializeAuthenticatedState() {
        addMessageToChat("Welcome! Please select your GTM Account, Container, and Workspace to begin.", "agent");

        const accounts = await getAccountInfo();
        populateSelect(accountSelect, accounts, 'accountId', 'name', 'Select an account');

        // Restore previous session from local storage
        const savedAccountId = localStorage.getItem('selectedAccountId');
        if (savedAccountId) {
            accountSelect.value = savedAccountId;
            selectedContext.accountId = savedAccountId;
            const containers = await getContainerInfo(savedAccountId);
            populateSelect(containerSelect, containers, 'containerId', 'name', 'Select a container');

            const savedContainerId = localStorage.getItem('selectedContainerId');
            if (savedContainerId) {
                containerSelect.value = savedContainerId;
                selectedContext.containerId = savedContainerId;
                const workspaces = await getWorkspaceInfo(savedAccountId, savedContainerId);
                populateSelect(workspaceSelect, workspaces, 'workspaceId', 'name', 'Select a workspace');

                const savedWorkspaceId = localStorage.getItem('selectedWorkspaceId');
                if (savedWorkspaceId) {
                    workspaceSelect.value = savedWorkspaceId;
                    selectedContext.workspaceId = savedWorkspaceId;
                    chatInput.disabled = false;
                    sendBtn.disabled = false;
                    const savedWorkspaceName = localStorage.getItem('selectedWorkspaceName');
                    chatInput.placeholder = `Ask about workspace "${savedWorkspaceName}"`;
                }
            }
        }
    }

    async function checkAuthStatus() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/auth/status`);
            const data = await response.json();

            if (data.is_authenticated) {
                loginModal.classList.add('hidden');
                document.getElementById('user-name').textContent = data.user.name;
                document.getElementById('user-email').textContent = data.user.email;
                document.getElementById('user-picture').src = data.user.picture;
                userProfileDiv.classList.remove('hidden');
                await initializeAuthenticatedState();
            } else {
                showLoginModal();
            }
        } catch (error) {
            console.error('Error checking auth status:', error);
            showLoginModal();
            addMessageToChat('Could not verify authentication status. Please try logging in.', 'agent');
        }
    }

    // --- Entry Point ---
    checkAuthStatus();
});