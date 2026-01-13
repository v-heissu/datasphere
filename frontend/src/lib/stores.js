import { writable, derived } from 'svelte/store';

// Items store
export const items = writable([]);
export const stats = writable({
	total_captured: 0,
	total_consumed: 0,
	pending: 0,
	archived: 0,
	streak_days: 0,
	consumption_rate: 0,
	dashboard_url: ''
});

// Filter stores
export const statusFilter = writable('pending');
export const typeFilter = writable(null);

// Loading states
export const loading = writable(false);
export const error = writable(null);

// Daily picks
export const dailyPicks = writable(null);

// Search
export const searchQuery = writable('');
export const searchResults = writable(null);
export const searchLoading = writable(false);
export const isSearchMode = writable(false);

// Derived store for filtered items count by type
export const itemCountByType = derived(items, ($items) => {
	const counts = {};
	for (const item of $items) {
		const type = item.item_type || 'other';
		counts[type] = (counts[type] || 0) + 1;
	}
	return counts;
});
