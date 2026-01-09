<script>
	import { onMount } from 'svelte';
	import { RefreshCw } from 'lucide-svelte';
	import StatsWidget from '$lib/components/StatsWidget.svelte';
	import ItemCard from '$lib/components/ItemCard.svelte';
	import DailyPicks from '$lib/components/DailyPicks.svelte';
	import { getItems, getStats, getDailyPicks, updateItem, regeneratePicks } from '$lib/api';
	import { items, stats, statusFilter, typeFilter, dailyPicks, loading, error } from '$lib/stores';

	const itemTypes = ['film', 'book', 'concept', 'music', 'art', 'todo', 'other'];

	let picksLoading = false;

	onMount(async () => {
		await Promise.all([loadItems(), loadStats(), loadDailyPicks()]);
	});

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

	async function handleAction(event) {
		const { action, id } = event.detail;

		try {
			await updateItem(id, { status: action });
			await Promise.all([loadItems(), loadStats()]);
		} catch (e) {
			console.error('Error updating item:', e);
		}
	}

	async function handleRegenerate() {
		picksLoading = true;
		try {
			$dailyPicks = await regeneratePicks();
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
</script>

<main class="min-h-screen bg-gray-50">
	<div class="container mx-auto px-4 py-8 max-w-6xl">
		<!-- Header -->
		<header class="mb-8">
			<h1 class="text-4xl font-bold text-gray-900 mb-2">La Tua Coda</h1>
			<p class="text-gray-600">Pensieri catturati, pronti da consumare</p>
		</header>

		<!-- Stats -->
		<StatsWidget stats={$stats} />

		<!-- Daily Picks -->
		{#if $statusFilter === 'pending'}
			<DailyPicks
				picks={$dailyPicks}
				loading={picksLoading}
				on:regenerate={handleRegenerate}
				on:consume={handleConsume}
			/>
		{/if}

		<!-- Filters -->
		<div class="flex flex-wrap gap-4 mb-6">
			<div class="flex gap-2">
				<button
					class="btn {$statusFilter === 'pending' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('pending')}
				>
					In Coda ({$stats.pending})
				</button>

				<button
					class="btn {$statusFilter === 'consumed' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('consumed')}
				>
					Consumati ({$stats.total_consumed})
				</button>

				<button
					class="btn {$statusFilter === 'archived' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('archived')}
				>
					Archiviati ({$stats.archived})
				</button>
			</div>

			<button class="btn btn-secondary" on:click={loadItems} disabled={$loading}>
				<RefreshCw class="w-4 h-4 {$loading ? 'animate-spin' : ''}" />
			</button>
		</div>

		<!-- Type filters -->
		<div class="flex gap-2 mb-6 flex-wrap items-center">
			<span class="text-sm text-gray-600">Tipo:</span>
			{#each itemTypes as type}
				<button
					class="badge {$typeFilter === type ? 'badge-active' : 'badge-default'}"
					on:click={() => handleTypeFilter(type)}
				>
					{type}
				</button>
			{/each}
			{#if $typeFilter}
				<button class="text-xs text-gray-500 hover:text-gray-700" on:click={() => handleTypeFilter(null)}>
					Reset
				</button>
			{/if}
		</div>

		<!-- Error message -->
		{#if $error}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-6">
				{$error}
			</div>
		{/if}

		<!-- Items grid -->
		{#if $loading && $items.length === 0}
			<div class="text-center py-12">
				<RefreshCw class="w-8 h-8 animate-spin mx-auto text-primary-500" />
				<p class="text-gray-500 mt-4">Caricamento...</p>
			</div>
		{:else if $items.length === 0}
			<div class="text-center py-12">
				<p class="text-gray-500 text-lg">
					{#if $statusFilter === 'pending'}
						Coda vuota! Mandami qualche pensiero su Telegram.
					{:else if $statusFilter === 'consumed'}
						Nessun item consumato ancora.
					{:else}
						Nessun item archiviato.
					{/if}
				</p>
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
				{#each $items as item (item.id)}
					<ItemCard {item} on:action={handleAction} />
				{/each}
			</div>
		{/if}
	</div>
</main>
