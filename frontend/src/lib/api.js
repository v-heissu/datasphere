/**
 * API client for ADHD Thought Capture
 */

const API_BASE = '/api';

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

export async function getItems(status = 'pending', itemType = null, limit = 50) {
	const params = new URLSearchParams({ status, limit: limit.toString() });
	if (itemType) params.append('item_type', itemType);

	return fetchAPI(`/items?${params}`);
}

export async function getItem(itemId) {
	return fetchAPI(`/items/${itemId}`);
}

export async function updateItem(itemId, updates) {
	return fetchAPI(`/items/${itemId}`, {
		method: 'PATCH',
		body: JSON.stringify(updates)
	});
}

export async function deleteItem(itemId) {
	return fetchAPI(`/items/${itemId}`, {
		method: 'DELETE'
	});
}

export async function getStats() {
	return fetchAPI('/stats');
}

export async function getDailyPicks() {
	return fetchAPI('/daily-picks');
}

export async function regeneratePicks() {
	return fetchAPI('/daily-picks/regenerate', { method: 'POST' });
}

export async function getConfig(key) {
	return fetchAPI(`/config/${key}`);
}

export async function setConfig(key, value) {
	return fetchAPI(`/config/${key}`, {
		method: 'POST',
		body: JSON.stringify(value)
	});
}

export async function getAllConfig() {
	return fetchAPI('/config');
}

export async function searchItems(query, status = null, itemType = null, limit = 50) {
	const params = new URLSearchParams({ q: query, limit: limit.toString() });
	if (status) params.append('status', status);
	if (itemType) params.append('item_type', itemType);

	return fetchAPI(`/search?${params}`);
}
