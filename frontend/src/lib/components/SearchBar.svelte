<script>
	import { createEventDispatcher } from 'svelte';
	import { Search, X, Loader2 } from 'lucide-svelte';
	import { searchQuery, searchLoading, isSearchMode } from '$lib/stores';

	const dispatch = createEventDispatcher();

	let inputElement;
	let expanded = false;
	let debounceTimer;

	function handleInput(e) {
		const value = e.target.value;
		$searchQuery = value;

		// Debounce search
		clearTimeout(debounceTimer);

		if (value.trim().length === 0) {
			$isSearchMode = false;
			dispatch('clear');
			return;
		}

		debounceTimer = setTimeout(() => {
			if (value.trim().length >= 2) {
				$isSearchMode = true;
				dispatch('search', { query: value.trim() });
			}
		}, 300);
	}

	function handleClear() {
		$searchQuery = '';
		$isSearchMode = false;
		expanded = false;
		dispatch('clear');
	}

	function handleExpand() {
		expanded = true;
		setTimeout(() => inputElement?.focus(), 100);
	}

	function handleBlur() {
		if ($searchQuery.trim().length === 0) {
			expanded = false;
		}
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			handleClear();
			inputElement?.blur();
		}
	}
</script>

<!-- Mobile: Expandable search -->
<div class="sm:hidden">
	{#if expanded || $isSearchMode}
		<div class="flex items-center gap-2 animate-fade-in">
			<div class="relative flex-1">
				<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
				<input
					bind:this={inputElement}
					type="search"
					placeholder="Cerca..."
					value={$searchQuery}
					on:input={handleInput}
					on:blur={handleBlur}
					on:keydown={handleKeydown}
					class="input pl-10 pr-10 py-2.5 text-sm"
					autocomplete="off"
					autocorrect="off"
					autocapitalize="off"
					spellcheck="false"
				/>
				{#if $searchLoading}
					<Loader2 class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--accent)] animate-spin" />
				{:else if $searchQuery}
					<button
						class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
						on:click={handleClear}
					>
						<X class="w-4 h-4 text-[var(--text-muted)]" />
					</button>
				{/if}
			</div>
			{#if $isSearchMode}
				<button
					class="btn btn-sm btn-ghost text-xs whitespace-nowrap"
					on:click={handleClear}
				>
					Annulla
				</button>
			{/if}
		</div>
	{:else}
		<button
			class="btn btn-ghost btn-icon"
			on:click={handleExpand}
			title="Cerca"
		>
			<Search class="w-5 h-5" />
		</button>
	{/if}
</div>

<!-- Desktop: Always visible search bar -->
<div class="hidden sm:block relative w-64 lg:w-80">
	<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)]" />
	<input
		type="search"
		placeholder="Cerca in tutti i campi..."
		value={$searchQuery}
		on:input={handleInput}
		on:keydown={handleKeydown}
		class="input pl-10 pr-10 py-2.5"
		autocomplete="off"
		autocorrect="off"
		autocapitalize="off"
		spellcheck="false"
	/>
	{#if $searchLoading}
		<Loader2 class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--accent)] animate-spin" />
	{:else if $searchQuery}
		<button
			class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
			on:click={handleClear}
		>
			<X class="w-4 h-4 text-[var(--text-muted)]" />
		</button>
	{/if}
</div>

<style>
	/* Remove default search input styling */
	input[type="search"]::-webkit-search-cancel-button,
	input[type="search"]::-webkit-search-decoration {
		-webkit-appearance: none;
		appearance: none;
	}
</style>
