<script>
	import { onMount } from 'svelte';
	import { RefreshCw, Settings, Brain, Inbox, CheckCircle2, Archive } from 'lucide-svelte';
	import StatsWidget from '$lib/components/StatsWidget.svelte';
	import ItemCard from '$lib/components/ItemCard.svelte';
	import DailyPicks from '$lib/components/DailyPicks.svelte';
	import SettingsModal from '$lib/components/SettingsModal.svelte';
	import { getItems, getStats, getDailyPicks, updateItem, deleteItem, regeneratePicks } from '$lib/api';
	import { items, stats, statusFilter, typeFilter, dailyPicks, loading, error } from '$lib/stores';

	const itemTypes = ['film', 'book', 'concept', 'music', 'art', 'todo', 'other'];

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
</script>

<svelte:head>
	<title>ThoughtCapture - La Tua Coda</title>
	<link rel="preconnect" href="https://fonts.googleapis.com" />
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
	<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
</svelte:head>

<main class="min-h-screen">
	<div class="container mx-auto px-4 py-8 max-w-6xl">
		<!-- Header -->
		<header class="mb-10 flex items-start justify-between">
			<div>
				<div class="flex items-center gap-3 mb-2">
					<div class="p-2.5 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600">
						<Brain class="w-7 h-7 text-white" />
					</div>
					<h1 class="text-3xl font-bold bg-gradient-to-r from-white to-white/70 bg-clip-text text-transparent">
						ThoughtCapture
					</h1>
				</div>
				<p class="opacity-50 ml-14">Pensieri catturati, pronti da consumare</p>
			</div>
			<button
				class="btn btn-ghost btn-icon"
				on:click={() => showSettings = true}
				title="Impostazioni"
			>
				<Settings class="w-5 h-5" />
			</button>
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
		<div class="flex flex-wrap items-center gap-3 mb-6">
			<div class="flex gap-2">
				<button
					class="btn {$statusFilter === 'pending' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('pending')}
				>
					<Inbox class="w-4 h-4" />
					In Coda
					<span class="opacity-60">({$stats.pending})</span>
				</button>

				<button
					class="btn {$statusFilter === 'consumed' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('consumed')}
				>
					<CheckCircle2 class="w-4 h-4" />
					Consumati
					<span class="opacity-60">({$stats.total_consumed})</span>
				</button>

				<button
					class="btn {$statusFilter === 'archived' ? 'btn-primary' : 'btn-secondary'}"
					on:click={() => handleStatusFilter('archived')}
				>
					<Archive class="w-4 h-4" />
					Archiviati
					<span class="opacity-60">({$stats.archived})</span>
				</button>
			</div>

			<button
				class="btn btn-ghost btn-icon ml-auto"
				on:click={loadItems}
				disabled={$loading}
				title="Ricarica"
			>
				<RefreshCw class="w-4 h-4 {$loading ? 'animate-spin' : ''}" />
			</button>
		</div>

		<!-- Type filters -->
		<div class="flex gap-2 mb-8 flex-wrap items-center">
			<span class="text-sm opacity-50">Tipo:</span>
			{#each itemTypes as type}
				<button
					class="badge {$typeFilter === type ? 'badge-active' : ''}"
					on:click={() => handleTypeFilter(type)}
				>
					<span class="mr-1">{typeIcons[type]}</span>
					{type}
				</button>
			{/each}
			{#if $typeFilter}
				<button
					class="text-xs opacity-40 hover:opacity-100 transition-opacity ml-2"
					on:click={() => handleTypeFilter(null)}
				>
					Reset
				</button>
			{/if}
		</div>

		<!-- Error message -->
		{#if $error}
			<div class="card border-[var(--danger)]/50 bg-[var(--danger)]/10 px-4 py-3 mb-6 text-[var(--danger)]">
				{$error}
			</div>
		{/if}

		<!-- Items grid -->
		{#if $loading && $items.length === 0}
			<div class="text-center py-16">
				<RefreshCw class="w-10 h-10 animate-spin mx-auto text-[var(--accent)] opacity-50" />
				<p class="opacity-40 mt-4">Caricamento...</p>
			</div>
		{:else if $items.length === 0}
			<div class="text-center py-16">
				<div class="w-20 h-20 rounded-full bg-[var(--bg-secondary)] flex items-center justify-center mx-auto mb-4">
					{#if $statusFilter === 'pending'}
						<Inbox class="w-10 h-10 opacity-20" />
					{:else if $statusFilter === 'consumed'}
						<CheckCircle2 class="w-10 h-10 opacity-20" />
					{:else}
						<Archive class="w-10 h-10 opacity-20" />
					{/if}
				</div>
				<p class="opacity-50 text-lg">
					{#if $statusFilter === 'pending'}
						Coda vuota!
					{:else if $statusFilter === 'consumed'}
						Nessun item consumato ancora.
					{:else}
						Nessun item archiviato.
					{/if}
				</p>
				{#if $statusFilter === 'pending'}
					<p class="text-sm opacity-30 mt-2">Manda qualche pensiero su Telegram</p>
				{/if}
			</div>
		{:else}
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
				{#each $items as item (item.id)}
					<ItemCard {item} on:action={handleAction} />
				{/each}
			</div>
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
