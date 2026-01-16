/**
 * API client for ThoughtCapture PWA
 * All API calls go through authFetch for authentication support
 */

import { authFetch } from './auth.js';

const API_BASE = '/api';

// Helper for non-authenticated requests
async function fetchAPI(endpoint, options = {}) {
	const url = `${API_BASE}${endpoint}`;

	const response = await fetch(url, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			...options.headers
		}
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	return response.json();
}

// Helper for authenticated requests
async function fetchAuthAPI(endpoint, options = {}) {
	const response = await authFetch(endpoint, options);

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	return response.json();
}

// ==================== Items ====================

export async function getItems(status = 'pending', itemType = null, limit = 50) {
	const params = new URLSearchParams({ status, limit: limit.toString() });
	if (itemType) params.append('item_type', itemType);

	return fetchAuthAPI(`/items?${params}`);
}

export async function getItem(itemId) {
	return fetchAuthAPI(`/items/${itemId}`);
}

export async function updateItem(itemId, updates) {
	return fetchAuthAPI(`/items/${itemId}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
}

export async function deleteItem(itemId) {
	return fetchAuthAPI(`/items/${itemId}`, {
		method: 'DELETE'
	});
}

// ==================== Stats & Picks ====================

export async function getStats() {
	return fetchAuthAPI('/stats');
}

export async function getDailyPicks() {
	return fetchAuthAPI('/daily-picks');
}

export async function regeneratePicks() {
	return fetchAuthAPI('/daily-picks/regenerate', { method: 'POST' });
}

// ==================== Search ====================

export async function searchItems(query, status = null, itemType = null, limit = 50) {
	const params = new URLSearchParams({ q: query, limit: limit.toString() });
	if (status) params.append('status', status);
	if (itemType) params.append('item_type', itemType);

	return fetchAuthAPI(`/search?${params}`);
}

export async function getSearchSuggestions(query, limit = 8) {
	const params = new URLSearchParams({ q: query, limit: limit.toString() });
	return fetchAuthAPI(`/search/suggest?${params}`);
}

// ==================== Config ====================

export async function getConfig(key) {
	return fetchAuthAPI(`/config/${key}`);
}

export async function setConfig(key, value) {
	return fetchAuthAPI(`/config/${key}`, {
		method: 'POST',
		body: JSON.stringify(value)
	});
}

export async function getAllConfig() {
	return fetchAuthAPI('/config');
}

// ==================== Messages (Direct - replaces Telegram) ====================

export async function sendMessage(text) {
	return fetchAuthAPI('/messages', {
		method: 'POST',
		body: JSON.stringify({ text })
	});
}

export async function sendImage(imageFile, caption = null) {
	const formData = new FormData();
	formData.append('image', imageFile);
	if (caption) {
		formData.append('caption', caption);
	}

	const response = await authFetch('/messages/image', {
		method: 'POST',
		headers: {}, // Let browser set Content-Type for FormData
		body: formData
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
		throw new Error(error.detail || `HTTP ${response.status}`);
	}

	return response.json();
}

// ==================== Push Notifications ====================

export async function getVapidPublicKey() {
	return fetchAPI('/push/vapid-public-key');
}

export async function subscribePush(subscription) {
	return fetchAuthAPI('/push/subscribe', {
		method: 'POST',
		body: JSON.stringify(subscription)
	});
}

export async function unsubscribePush(endpoint) {
	return fetchAuthAPI('/push/unsubscribe', {
		method: 'DELETE',
		body: JSON.stringify({ endpoint })
	});
}

// ==================== Health ====================

export async function checkHealth() {
	return fetchAPI('/health');
}
