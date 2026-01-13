<script>
	import { onMount, onDestroy } from 'svelte';
	import { RefreshCw, Settings, Brain, Inbox, CheckCircle2, Archive, LayoutGrid, List, AlignJustify } from 'lucide-svelte';
	import StatsWidget from '$lib/components/StatsWidget.svelte';
	import ItemCard from '$lib/components/ItemCard.svelte';
	import ItemTable from '$lib/components/ItemTable.svelte';
	import ItemAccordion from '$lib/components/ItemAccordion.svelte';
	import DailyPicks from '$lib/components/DailyPicks.svelte';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import SearchBar from '$lib/components/SearchBar.svelte';
	import { getItems, getStats, getDailyPicks, updateItem, deleteItem, regeneratePicks, searchItems } from '$lib/api';
	import { items, stats, statusFilter, typeFilter, dailyPicks, loading, error, searchQuery, searchResults, searchLoading, isSearchMode } from '$lib/stores';

	const itemTypes = ['film', 'book', 'concept', 'music', 'art', 'todo', 'other'];
	const AUTO_REFRESH_INTERVAL = 30000; // 30 seconds

	// View mode: 'cards' | 'table' | 'accordion'
	let viewMode = 'cards';

	const typeIcons = {
		film: '🎬',
		book: '📚',
		concept: '💡',
		music: '🎵',
		art: '🎨',
		todo: '✓',
		other: '📌'
	};

	let picksLoading = false;
	let showSettings = false;
	let toast = null;
	let refreshInterval = null;
	let lastRefresh = Date.now();

	onMount(async () => {
		await Promise.all([loadItems(), loadStats(), loadDailyPicks()]);
		startAutoRefresh();

		// Refresh on visibility change (tab becomes active)
		document.addEventListener('visibilitychange', handleVisibilityChange);

		// Refresh on window focus
		window.addEventListener('focus', handleWindowFocus);
	});

	onDestroy(() => {
		stopAutoRefresh();
		if (typeof document !== 'undefined') {
			document.removeEventListener('visibilitychange', handleVisibilityChange);
		}
		if (typeof window !== 'undefined') {
			window.removeEventListener('focus', handleWindowFocus);
		}
	});

	function startAutoRefresh() {
		stopAutoRefresh();
		refreshInterval = setInterval(() => {
			if (!document.hidden && !$loading) {
				silentRefresh();
			}
		}, AUTO_REFRESH_INTERVAL);
	}

	function stopAutoRefresh() {
		if (refreshInterval) {
			clearInterval(refreshInterval);
			refreshInterval = null;
		}
	}

	function handleVisibilityChange() {
		if (!document.hidden) {
			// Tab became visible - refresh if more than 10 seconds since last refresh
			const timeSinceRefresh = Date.now() - lastRefresh;
			if (timeSinceRefresh > 10000) {
				silentRefresh();
			}
		}
	}

	function handleWindowFocus() {
		// Refresh if more than 10 seconds since last refresh
		const timeSinceRefresh = Date.now() - lastRefresh;
		if (timeSinceRefresh > 10000 && !$loading) {
			silentRefresh();
		}
	}

	async function silentRefresh() {
		// Refresh without showing loading state (background refresh)
		lastRefresh = Date.now();
		try {
			const [newItems, newStats, newPicks] = await Promise.all([
				getItems($statusFilter, $typeFilter),
				getStats(),
				getDailyPicks()
			]);
			$items = newItems;
			$stats = newStats;
			$dailyPicks = newPicks;
		} catch (e) {
			console.error('Silent refresh error:', e);
		}
	}

	async function loadItems() {
		$loading = true;
		$error = null;
		try {
			$items = await getItems($statusFilter, $typeFilter);
		} catch (e) {
			$error = e.message;
			console.error('Error loading items:', e);
		} finally {
			$loading = false;
		}
	}

	async function loadStats() {
		try {
			$stats = await getStats();
		} catch (e) {
			console.error('Error loading stats:', e);
		}
	}

	async function loadDailyPicks() {
		try {
			$dailyPicks = await getDailyPicks();
		} catch (e) {
			console.error('Error loading daily picks:', e);
		}
	}

	function showToast(message, type = 'success') {
		toast = { message, type };
		setTimeout(() => toast = null, 3000);
	}

	async function handleAction(event) {
		const { action, id } = event.detail;

		try {
			if (action === 'delete') {
				await deleteItem(id);
				showToast('Item eliminato');
			} else {
				await updateItem(id, { status: action });
				const actionLabels = {
					consumed: 'Completato',
					archived: 'Archiviato',
					pending: 'Ripristinato'
				};
				showToast(actionLabels[action] || 'Aggiornato');
			}
			await Promise.all([loadItems(), loadStats()]);
		} catch (e) {
			console.error('Error updating item:', e);
			showToast('Errore: ' + e.message, 'error');
		}
	}

	async function handleRegenerate() {
		picksLoading = true;
		try {
			$dailyPicks = await regeneratePicks();
			showToast('Picks rigenerati');
		} catch (e) {
			console.error('Error regenerating picks:', e);
		} finally {
			picksLoading = false;
		}
	}

	async function handleConsume(event) {
		const { id } = event.detail;

		try {
			await updateItem(id, { status: 'consumed' });
			showToast('Completato!');
			await Promise.all([loadItems(), loadStats(), loadDailyPicks()]);
		} catch (e) {
			console.error('Error consuming item:', e);
		}
	}

	function handleStatusFilter(newStatus) {
		$statusFilter = newStatus;
		loadItems();
	}

	function handleTypeFilter(type) {
		$typeFilter = $typeFilter === type ? null : type;
		loadItems();
	}

	async function handleSearch(event) {
		const { query } = event.detail;
		$searchLoading = true;
		try {
			const response = await searchItems(query);
			$searchResults = response.results;
		} catch (e) {
			console.error('Error searching:', e);
			showToast('Errore nella ricerca', 'error');
		} finally {
			$searchLoading = false;
		}
	}

	function handleSearchClear() {
		$searchResults = null;
		$searchQuery = '';
		$isSearchMode = false;
	}
</script>

<svelte:head>
	<title>ThoughtCapture</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<main class="min-h-screen pb-safe">
	<div class="container mx-auto px-3 sm:px-4 py-4 sm:py-8 max-w-6xl">
		<!-- Header -->
		<header class="mb-6 sm:mb-10 flex items-center justify-between gap-3">
			<div class="flex items-center gap-2 sm:gap-3 flex-shrink-0">
				<div class="p-2 sm:p-2.5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600">
					<Brain class="w-5 h-5 sm:w-7 sm:h-7 text-white" />
				</div>
				<div class="hidden sm:block">
					<h1 class="text-xl sm:text-3xl font-bold bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
						ThoughtCapture
					</h1>
					<p class="text-xs sm:text-sm opacity-50">Pensieri catturati, pronti da consumare</p>
				</div>
			</div>

			<!-- Search Bar -->
			<div class="flex-1 sm:flex-initial flex justify-end sm:justify-center">
				<SearchBar on:search={handleSearch} on:clear={handleSearchClear} />
			</div>

			<button
				class="btn btn-ghost btn-icon flex-shrink-0"
				on:click={() => showSettings = true}
				title="Impostazioni"
			>
				<Settings class="w-5 h-5" />
			</button>
		</header>

		<!-- Stats (hide in search mode) -->
		{#if !$isSearchMode}
			<StatsWidget stats={$stats} />
		{/if}

		<!-- Daily Picks (hide in search mode) -->
		{#if $statusFilter === 'pending' && !$isSearchMode}
			<DailyPicks
				picks={$dailyPicks}
				loading={picksLoading}
				on:regenerate={handleRegenerate}
				on:consume={handleConsume}
			/>
		{/if}

		<!-- Search Results Header -->
		{#if $isSearchMode}
			<div class="mb-6 sm:mb-8">
				<div class="flex items-center justify-between mb-4">
					<h2 class="text-lg sm:text-xl font-semibold">
						Risultati per "{$searchQuery}"
						{#if $searchResults}
							<span class="text-[var(--text-muted)] font-normal ml-2">({$searchResults.length})</span>
						{/if}
					</h2>
				</div>
			</div>
		{/if}

		<!-- Status Filters - Scrollable on mobile (hide in search mode) -->
		<div class="flex items-center gap-2 mb-4 sm:mb-6 overflow-x-auto pb-2 -mx-3 px-3 sm:mx-0 sm:px-0 sm:overflow-visible sm:flex-wrap {$isSearchMode ? 'hidden' : ''}">
			<button
				class="btn btn-sm sm:btn {$statusFilter === 'pending' ? 'btn-primary' : 'btn-secondary'} whitespace-nowrap flex-shrink-0"
				on:click={() => handleStatusFilter('pending')}
			>
				<Inbox class="w-4 h-4" />
				<span class="hidden sm:inline">In Coda</span>
				<span class="sm:hidden">Coda</span>
				<span class="opacity-60">({$stats.pending})</span>
			</button>

			<button
				class="btn btn-sm sm:btn {$statusFilter === 'consumed' ? 'btn-primary' : 'btn-secondary'} whitespace-nowrap flex-shrink-0"
				on:click={() => handleStatusFilter('consumed')}
			>
				<CheckCircle2 class="w-4 h-4" />
				<span class="hidden sm:inline">Consumati</span>
				<span class="sm:hidden">Fatti</span>
				<span class="opacity-60">({$stats.total_consumed})</span>
			</button>

			<button
				class="btn btn-sm sm:btn {$statusFilter === 'archived' ? 'btn-primary' : 'btn-secondary'} whitespace-nowrap flex-shrink-0"
				on:click={() => handleStatusFilter('archived')}
			>
				<Archive class="w-4 h-4" />
				<span class="hidden sm:inline">Archiviati</span>
				<span class="sm:hidden">Archivio</span>
				<span class="opacity-60">({$stats.archived})</span>
			</button>

			<!-- View mode toggle -->
			<div class="flex items-center gap-1 ml-auto border border-[var(--border)] rounded-lg p-0.5 flex-shrink-0">
				<button
					class="btn btn-sm btn-icon {viewMode === 'cards' ? 'btn-primary' : 'btn-ghost'}"
					on:click={() => viewMode = 'cards'}
					title="Cards"
				>
					<LayoutGrid class="w-4 h-4" />
				</button>
				<button
					class="btn btn-sm btn-icon {viewMode === 'table' ? 'btn-primary' : 'btn-ghost'}"
					on:click={() => viewMode = 'table'}
					title="Tabella"
				>
					<List class="w-4 h-4" />
				</button>
				<button
					class="btn btn-sm btn-icon {viewMode === 'accordion' ? 'btn-primary' : 'btn-ghost'}"
					on:click={() => viewMode = 'accordion'}
					title="Accordion"
				>
					<AlignJustify class="w-4 h-4" />
				</button>
			</div>

			<button
				class="btn btn-ghost btn-icon flex-shrink-0"
				on:click={loadItems}
				disabled={$loading}
				title="Ricarica"
			>
				<RefreshCw class="w-4 h-4 {$loading ? 'animate-spin' : ''}" />
			</button>
		</div>

		<!-- Type filters - Scrollable on mobile (hide in search mode) -->
		<div class="flex gap-2 mb-6 sm:mb-8 overflow-x-auto pb-2 -mx-3 px-3 sm:mx-0 sm:px-0 sm:overflow-visible sm:flex-wrap items-center {$isSearchMode ? 'hidden' : ''}">
			<span class="text-xs sm:text-sm opacity-50 flex-shrink-0">Tipo:</span>
			{#each itemTypes as type}
				<button
					class="badge {$typeFilter === type ? 'badge-active' : ''} flex-shrink-0"
					on:click={() => handleTypeFilter(type)}
				>
					<span class="mr-1">{typeIcons[type]}</span>
					<span class="hidden sm:inline">{type}</span>
				</button>
			{/each}
			{#if $typeFilter}
				<button
					class="text-xs opacity-40 active:opacity-100 transition-opacity ml-2 flex-shrink-0 py-2"
					on:click={() => handleTypeFilter(null)}
				>
					Reset
				</button>
			{/if}
		</div>

		<!-- Error message -->
		{#if $error && !$isSearchMode}
			<div class="card border-[var(--danger)]/50 bg-[var(--danger)]/10 px-4 py-3 mb-6 text-[var(--danger)] text-sm">
				{$error}
			</div>
		{/if}

		<!-- Search Results -->
		{#if $isSearchMode}
			{#if $searchLoading}
				<div class="text-center py-12 sm:py-16">
					<RefreshCw class="w-8 h-8 sm:w-10 sm:h-10 animate-spin mx-auto text-[var(--accent)] opacity-50" />
					<p class="opacity-40 mt-4 text-sm sm:text-base">Ricerca in corso...</p>
				</div>
			{:else if $searchResults && $searchResults.length === 0}
				<div class="text-center py-12 sm:py-16">
					<div class="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center mx-auto mb-4">
						<svg class="w-8 h-8 sm:w-10 sm:h-10 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
						</svg>
					</div>
					<p class="opacity-50 text-base sm:text-lg">Nessun risultato trovato</p>
					<p class="text-xs sm:text-sm opacity-30 mt-2">Prova con termini diversi</p>
				</div>
			{:else if $searchResults}
				<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
					{#each $searchResults as item (item.id)}
						<ItemCard {item} on:action={handleAction} />
					{/each}
				</div>
			{/if}
		{:else}
			<!-- Normal Items grid -->
			{#if $loading && $items.length === 0}
				<div class="text-center py-12 sm:py-16">
					<RefreshCw class="w-8 h-8 sm:w-10 sm:h-10 animate-spin mx-auto text-[var(--accent)] opacity-50" />
					<p class="opacity-40 mt-4 text-sm sm:text-base">Caricamento...</p>
				</div>
			{:else if $items.length === 0}
				<div class="text-center py-12 sm:py-16">
					<div class="w-16 h-16 sm:w-20 sm:h-20 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center mx-auto mb-4">
						{#if $statusFilter === 'pending'}
							<Inbox class="w-8 h-8 sm:w-10 sm:h-10 opacity-20" />
						{:else if $statusFilter === 'consumed'}
							<CheckCircle2 class="w-8 h-8 sm:w-10 sm:h-10 opacity-20" />
						{:else}
							<Archive class="w-8 h-8 sm:w-10 sm:h-10 opacity-20" />
						{/if}
					</div>
					<p class="opacity-50 text-base sm:text-lg">
						{#if $statusFilter === 'pending'}
							Coda vuota!
						{:else if $statusFilter === 'consumed'}
							Nessun item consumato.
						{:else}
							Nessun item archiviato.
						{/if}
					</p>
					{#if $statusFilter === 'pending'}
						<p class="text-xs sm:text-sm opacity-30 mt-2">Manda qualche pensiero su Telegram</p>
					{/if}
				</div>
			{:else}
				{#if viewMode === 'cards'}
					<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
						{#each $items as item (item.id)}
							<ItemCard {item} on:action={handleAction} />
						{/each}
					</div>
				{:else if viewMode === 'table'}
					<ItemTable items={$items} on:action={handleAction} />
				{:else if viewMode === 'accordion'}
					<ItemAccordion items={$items} on:action={handleAction} />
				{/if}
			{/if}
		{/if}
	</div>
</main>

<!-- Settings Modal -->
<SettingsModal bind:show={showSettings} on:saved={loadItems} />

<!-- Toast -->
{#if toast}
	<div class="toast {toast.type === 'error' ? 'border-[var(--danger)]' : 'border-[var(--success)]'}">
		<span class={toast.type === 'error' ? 'text-[var(--danger)]' : 'text-[var(--success)]'}>
			{toast.message}
		</span>
	</div>
{/if}
