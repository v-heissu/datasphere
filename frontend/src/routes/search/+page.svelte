<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Search, X, Loader2, RefreshCw } from 'lucide-svelte';
	import { isAuthenticated } from '$lib/auth.js';
	import { searchItems, getSearchSuggestions } from '$lib/api.js';
	import ItemCard from '$lib/components/ItemCard.svelte';

	let query = '';
	let results = [];
	let suggestions = [];
	let loading = false;
	let showSuggestions = false;
	let debounceTimer;

	const typeIcons = {
		film: '🎬',
		book: '📚',
		concept: '💡',
		music: '🎵',
		art: '🎨',
		todo: '✓',
		other: '📌'
	};

	onMount(() => {
		const unsubscribe = isAuthenticated.subscribe(authenticated => {
			if (!authenticated) {
				goto('/login');
			}
		});

		// Focus search input
		setTimeout(() => {
			const input = document.getElementById('search-input');
			if (input) input.focus();
		}, 100);

		return unsubscribe;
	});

	function handleInput(e) {
		query = e.target.value;

		// Debounce suggestions
		clearTimeout(debounceTimer);

		if (query.length < 2) {
			suggestions = [];
			showSuggestions = false;
			return;
		}

		debounceTimer = setTimeout(async () => {
			try {
				const response = await getSearchSuggestions(query);
				suggestions = response.suggestions || [];
				showSuggestions = suggestions.length > 0;
			} catch (e) {
				console.error('Suggestions error:', e);
			}
		}, 300);
	}

	async function handleSearch(searchQuery = query) {
		if (!searchQuery.trim()) return;

		query = searchQuery;
		showSuggestions = false;
		loading = true;

		try {
			const response = await searchItems(searchQuery);
			results = response.results || [];
		} catch (e) {
			console.error('Search error:', e);
			results = [];
		} finally {
			loading = false;
		}
	}

	function handleKeyDown(e) {
		if (e.key === 'Enter') {
			e.preventDefault();
			handleSearch();
		} else if (e.key === 'Escape') {
			showSuggestions = false;
		}
	}

	function selectSuggestion(suggestion) {
		handleSearch(suggestion.title);
	}

	function clearSearch() {
		query = '';
		results = [];
		suggestions = [];
		showSuggestions = false;
	}

	async function handleAction(event) {
		const { action, id } = event.detail;

		// Refresh search after action
		if (query) {
			await handleSearch();
		}
	}
</script>

<svelte:head>
	<title>Cerca - ThoughtCapture</title>
</svelte:head>

<main class="min-h-screen bg-[var(--bg-primary)]">
	<!-- Header with search -->
	<header class="sticky top-0 z-20 bg-[var(--bg-primary)]/95 backdrop-blur border-b border-[var(--border)] px-4 py-3 pt-safe">
		<div class="relative max-w-lg mx-auto">
			<div class="relative">
				<Search class="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-[var(--text-muted)]" />
				<input
					id="search-input"
					type="search"
					value={query}
					on:input={handleInput}
					on:keydown={handleKeyDown}
					on:focus={() => suggestions.length > 0 && (showSuggestions = true)}
					placeholder="Cerca pensieri..."
					class="input pl-12 pr-12"
				/>
				{#if query}
					<button
						class="absolute right-4 top-1/2 -translate-y-1/2 p-1 text-[var(--text-muted)] hover:text-white transition-colors"
						on:click={clearSearch}
					>
						<X class="w-5 h-5" />
					</button>
				{/if}
			</div>

			<!-- Suggestions dropdown -->
			{#if showSuggestions}
				<div class="absolute top-full left-0 right-0 mt-2 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-2xl overflow-hidden z-30">
					{#each suggestions as suggestion}
						<button
							class="w-full px-4 py-3 text-left hover:bg-[var(--bg-tertiary)] transition-colors flex items-center gap-3 border-b border-[var(--border)] last:border-b-0"
							on:click={() => selectSuggestion(suggestion)}
						>
							<span class="text-lg">{typeIcons[suggestion.item_type] || '📌'}</span>
							<div class="flex-1 min-w-0">
								<p class="text-white font-medium truncate">{suggestion.title}</p>
								{#if suggestion.description}
									<p class="text-xs text-[var(--text-muted)] truncate">{suggestion.description}</p>
								{/if}
							</div>
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</header>

	<!-- Content -->
	<div class="p-4 max-w-lg mx-auto">
		{#if loading}
			<div class="text-center py-12">
				<Loader2 class="w-10 h-10 animate-spin mx-auto text-[var(--accent)] mb-4" />
				<p class="text-[var(--text-secondary)]">Ricerca...</p>
			</div>
		{:else if query && results.length === 0}
			<div class="text-center py-12">
				<div class="w-16 h-16 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center mx-auto mb-4">
					<Search class="w-8 h-8 opacity-20" />
				</div>
				<p class="text-[var(--text-secondary)]">Nessun risultato per "{query}"</p>
				<p class="text-sm text-[var(--text-muted)] mt-2">Prova con termini diversi</p>
			</div>
		{:else if results.length > 0}
			<div class="mb-4">
				<p class="text-sm text-[var(--text-muted)]">{results.length} risultat{results.length === 1 ? 'o' : 'i'}</p>
			</div>
			<div class="space-y-4">
				{#each results as item (item.id)}
					<ItemCard {item} on:action={handleAction} />
				{/each}
			</div>
		{:else}
			<div class="text-center py-12">
				<div class="w-16 h-16 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center mx-auto mb-4">
					<Search class="w-8 h-8 opacity-20" />
				</div>
				<p class="text-[var(--text-secondary)]">Cerca tra i tuoi pensieri</p>
				<p class="text-sm text-[var(--text-muted)] mt-2">Titoli, descrizioni, tag...</p>
			</div>
		{/if}
	</div>
</main>
