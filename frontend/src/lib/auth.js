/**
 * Authentication store and utilities for ThoughtCapture PWA
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

// Storage keys
const TOKEN_KEY = 'tc_access_token';
const REFRESH_KEY = 'tc_refresh_token';
const USER_KEY = 'tc_user';

// Auth state stores
export const accessToken = writable(null);
export const refreshToken = writable(null);
export const currentUser = writable(null);
export const authLoading = writable(true);
export const authError = writable(null);

// Derived store: is user authenticated?
export const isAuthenticated = derived(
	[accessToken, currentUser],
	([$accessToken, $currentUser]) => !!$accessToken && !!$currentUser
);

// Initialize auth state from localStorage
export function initAuth() {
	if (!browser) return;

	try {
		const storedToken = localStorage.getItem(TOKEN_KEY);
		const storedRefresh = localStorage.getItem(REFRESH_KEY);
		const storedUser = localStorage.getItem(USER_KEY);

		if (storedToken) {
			accessToken.set(storedToken);
		}
		if (storedRefresh) {
			refreshToken.set(storedRefresh);
		}
		if (storedUser) {
			try {
				currentUser.set(JSON.parse(storedUser));
			} catch (e) {
				console.error('Failed to parse stored user:', e);
			}
		}
	} catch (e) {
		console.error('Failed to init auth:', e);
	} finally {
		authLoading.set(false);
	}
}

// Save auth state to localStorage
function saveAuth(tokens, user) {
	if (!browser) return;

	try {
		if (tokens.access_token) {
			localStorage.setItem(TOKEN_KEY, tokens.access_token);
			accessToken.set(tokens.access_token);
		}
		if (tokens.refresh_token) {
			localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
			refreshToken.set(tokens.refresh_token);
		}
		if (user) {
			localStorage.setItem(USER_KEY, JSON.stringify(user));
			currentUser.set(user);
		}
	} catch (e) {
		console.error('Failed to save auth:', e);
	}
}

// Clear auth state
export function clearAuth() {
	if (!browser) return;

	try {
		localStorage.removeItem(TOKEN_KEY);
		localStorage.removeItem(REFRESH_KEY);
		localStorage.removeItem(USER_KEY);
	} catch (e) {
		console.error('Failed to clear auth:', e);
	}

	accessToken.set(null);
	refreshToken.set(null);
	currentUser.set(null);
	authError.set(null);
}

// API base URL
const API_BASE = '/api';

// Make authenticated request
export async function authFetch(endpoint, options = {}) {
	const token = get(accessToken);

	const headers = {
		'Content-Type': 'application/json',
		...options.headers
	};

	if (token) {
		headers['Authorization'] = `Bearer ${token}`;
	}

	const response = await fetch(`${API_BASE}${endpoint}`, {
		...options,
		headers
	});

	// Handle 401 - try to refresh token
	if (response.status === 401 && get(refreshToken)) {
		const refreshed = await tryRefreshToken();
		if (refreshed) {
			// Retry with new token
			headers['Authorization'] = `Bearer ${get(accessToken)}`;
			return fetch(`${API_BASE}${endpoint}`, {
				...options,
				headers
			});
		} else {
			// Refresh failed, logout
			clearAuth();
			throw new Error('Session expired');
		}
	}

	return response;
}

// Try to refresh the access token
async function tryRefreshToken() {
	const refresh = get(refreshToken);
	if (!refresh) return false;

	try {
		const response = await fetch(`${API_BASE}/auth/refresh`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ refresh_token: refresh })
		});

		if (response.ok) {
			const data = await response.json();
			saveAuth(data, data.user);
			return true;
		}
	} catch (e) {
		console.error('Token refresh failed:', e);
	}

	return false;
}

// Parse API error response
function parseApiError(error) {
	if (!error.detail) return 'Errore sconosciuto';

	// FastAPI validation errors are arrays
	if (Array.isArray(error.detail)) {
		const firstError = error.detail[0];
		if (firstError?.msg) {
			// Make error message more user-friendly
			const field = firstError.loc?.[1] || 'campo';
			const msg = firstError.msg;
			if (msg.includes('pattern')) {
				return `Username può contenere solo lettere, numeri, _, @, . e -`;
			}
			if (msg.includes('at least')) {
				return `${field} troppo corto`;
			}
			return `${field}: ${msg}`;
		}
		return error.detail.map(e => e.msg || e).join(', ');
	}

	// Simple string error
	return String(error.detail);
}

// Register a new user
export async function register(username, password, displayName = null) {
	authLoading.set(true);
	authError.set(null);

	try {
		const response = await fetch(`${API_BASE}/auth/register`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				username,
				password,
				display_name: displayName
			})
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Registrazione fallita' }));
			throw new Error(parseApiError(error));
		}

		const data = await response.json();
		saveAuth(data, data.user);

		return { success: true, user: data.user };
	} catch (e) {
		authError.set(e.message);
		return { success: false, error: e.message };
	} finally {
		authLoading.set(false);
	}
}

// Login user
export async function login(username, password) {
	authLoading.set(true);
	authError.set(null);

	try {
		const response = await fetch(`${API_BASE}/auth/login`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ username, password })
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Login fallito' }));
			throw new Error(parseApiError(error));
		}

		const data = await response.json();
		saveAuth(data, data.user);

		return { success: true, user: data.user };
	} catch (e) {
		authError.set(e.message);
		return { success: false, error: e.message };
	} finally {
		authLoading.set(false);
	}
}

// Logout user
export function logout() {
	clearAuth();
	if (browser) {
		window.location.href = '/login';
	}
}

// Get current user from API
export async function fetchCurrentUser() {
	try {
		const response = await authFetch('/auth/me');

		if (response.ok) {
			const user = await response.json();
			currentUser.set(user);
			if (browser) {
				localStorage.setItem(USER_KEY, JSON.stringify(user));
			}
			return user;
		}
	} catch (e) {
		console.error('Failed to fetch current user:', e);
	}

	return null;
}

// Initialize on module load
if (browser) {
	initAuth();
}
