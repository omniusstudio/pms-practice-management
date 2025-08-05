/**
 * Auth0 Frontend Integration Example
 * 
 * This example shows how to integrate the Auth0 authentication
 * endpoints with a frontend application.
 */

class Auth0Client {
    constructor(apiBaseUrl = 'http://localhost:8000/api') {
        this.apiBaseUrl = apiBaseUrl;
        this.user = null;
    }

    /**
     * Initiate login by redirecting to Auth0
     */
    login(nextUrl = '/dashboard') {
        const loginUrl = `${this.apiBaseUrl}/auth/login?next=${encodeURIComponent(nextUrl)}`;
        window.location.href = loginUrl;
    }

    /**
     * Logout user and redirect to Auth0 logout
     */
    async logout() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/logout`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                const data = await response.json();
                window.location.href = data.logout_url;
            } else {
                console.error('Logout failed:', response.statusText);
            }
        } catch (error) {
            console.error('Logout error:', error);
        }
    }

    /**
     * Get current user information
     */
    async getCurrentUser() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/auth/user`, {
                method: 'GET',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            if (response.ok) {
                this.user = await response.json();
                return this.user;
            } else if (response.status === 401) {
                this.user = null;
                return null;
            } else {
                throw new Error(`Failed to get user: ${response.statusText}`);
            }
        } catch (error) {
            console.error('Get user error:', error);
            this.user = null;
            return null;
        }
    }

    /**
     * Check if user is authenticated
     */
    async isAuthenticated() {
        const user = await this.getCurrentUser();
        return user !== null;
    }

    /**
     * Make authenticated API requests
     */
    async apiRequest(endpoint, options = {}) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const config = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(url, config);
            
            if (response.status === 401) {
                // Redirect to login if unauthorized
                this.login(window.location.pathname);
                return null;
            }

            if (!response.ok) {
                throw new Error(`API request failed: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API request error:', error);
            throw error;
        }
    }
}

// Usage example
const auth = new Auth0Client();

// Check authentication status on page load
document.addEventListener('DOMContentLoaded', async () => {
    const user = await auth.getCurrentUser();
    
    if (user) {
        console.log('User is authenticated:', user);
        // Update UI for authenticated user
        updateUIForAuthenticatedUser(user);
    } else {
        console.log('User is not authenticated');
        // Update UI for unauthenticated user
        updateUIForUnauthenticatedUser();
    }
});

// Example UI update functions
function updateUIForAuthenticatedUser(user) {
    // Show user info
    const userInfo = document.getElementById('user-info');
    if (userInfo) {
        userInfo.innerHTML = `
            <div class="user-profile">
                <h3>Welcome, ${user.name || user.email}</h3>
                <p>Email: ${user.email}</p>
                <button onclick="auth.logout()">Logout</button>
            </div>
        `;
    }

    // Show authenticated content
    const authContent = document.getElementById('authenticated-content');
    if (authContent) {
        authContent.style.display = 'block';
    }

    // Hide login button
    const loginButton = document.getElementById('login-button');
    if (loginButton) {
        loginButton.style.display = 'none';
    }
}

function updateUIForUnauthenticatedUser() {
    // Hide authenticated content
    const authContent = document.getElementById('authenticated-content');
    if (authContent) {
        authContent.style.display = 'none';
    }

    // Show login button
    const loginButton = document.getElementById('login-button');
    if (loginButton) {
        loginButton.style.display = 'block';
        loginButton.onclick = () => auth.login();
    }

    // Clear user info
    const userInfo = document.getElementById('user-info');
    if (userInfo) {
        userInfo.innerHTML = '';
    }
}

// Example of making authenticated API calls
async function fetchPatients() {
    try {
        const patients = await auth.apiRequest('/patients');
        console.log('Patients:', patients);
        return patients;
    } catch (error) {
        console.error('Failed to fetch patients:', error);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Auth0Client;
}