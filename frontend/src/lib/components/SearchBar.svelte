<script>
	import { createEventDispatcher } from 'svelte';
	import { Search, X, Loader2, Film, Book, Lightbulb, Music, Palette, CheckSquare, HelpCircle } from 'lucide-svelte';
	import { searchQuery, searchLoading, isSearchMode } from '$lib/stores';
	import { getSearchSuggestions } from '$lib/api';

	const dispatch = createEventDispatcher();

	let inputElement;
	let desktopInputElement;
	let expanded = false;
	let debounceTimer;
	let suggestTimer;
	let suggestions = [];
	let showSuggestions = false;
	let selectedIndex = -1;
	let loadingSuggestions = false;

	const typeIcons = {
		film: Film,
		book: Book,
		concept: Lightbulb,
		music: Music,
		art: Palette,
		todo: CheckSquare,
		other: HelpCircle
	};

	function handleInput(e) {
		const value = e.target.value;
		$searchQuery = value;
		selectedIndex = -1;

		// Clear timers
		clearTimeout(debounceTimer);
		clearTimeout(suggestTimer);

		if (value.trim().length === 0) {
			$isSearchMode = false;
			suggestions = [];
			showSuggestions = false;
			dispatch('clear');
			return;
		}

		// Fetch suggestions quickly (150ms)
		if (value.trim().length >= 2) {
			suggestTimer = setTimeout(async () => {
				loadingSuggestions = true;
				try {
					const result = await getSearchSuggestions(value.trim());
					suggestions = result.suggestions || [];
					showSuggestions = suggestions.length > 0;
				} catch (e) {
					suggestions = [];
				} finally {
					loadingSuggestions = false;
				}
			}, 150);
		}

		// Debounce full search (400ms)
		debounceTimer = setTimeout(() => {
			if (value.trim().length >= 2) {
				$isSearchMode = true;
				showSuggestions = false;
				dispatch('search', { query: value.trim() });
			}
		}, 400);
	}

	function handleClear() {
		$searchQuery = '';
		$isSearchMode = false;
		expanded = false;
		suggestions = [];
		showSuggestions = false;
		selectedIndex = -1;
		dispatch('clear');
	}

	function handleExpand() {
		expanded = true;
		setTimeout(() => inputElement?.focus(), 100);
	}

	function handleBlur() {
		// Delay to allow click on suggestions
		setTimeout(() => {
			showSuggestions = false;
			if ($searchQuery.trim().length === 0) {
				expanded = false;
			}
		}, 200);
	}

	function handleFocus() {
		if (suggestions.length > 0 && $searchQuery.trim().length >= 2) {
			showSuggestions = true;
		}
	}

	function selectSuggestion(suggestion) {
		$searchQuery = suggestion.title || '';
		showSuggestions = false;
		suggestions = [];
		$isSearchMode = true;
		dispatch('search', { query: suggestion.title });
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') {
			if (showSuggestions) {
				showSuggestions = false;
			} else {
				handleClear();
				inputElement?.blur();
				desktopInputElement?.blur();
			}
			return;
		}

		if (!showSuggestions || suggestions.length === 0) return;

		if (e.key === 'ArrowDown') {
			e.preventDefault();
			selectedIndex = Math.min(selectedIndex + 1, suggestions.length - 1);
		} else if (e.key === 'ArrowUp') {
			e.preventDefault();
			selectedIndex = Math.max(selectedIndex - 1, -1);
		} else if (e.key === 'Enter' && selectedIndex >= 0) {
			e.preventDefault();
			selectSuggestion(suggestions[selectedIndex]);
		}
	}
</script>

<!-- Mobile: Expandable search -->
<div class="sm:hidden">
	{#if expanded || $isSearchMode}
		<div class="flex items-center gap-2 animate-fade-in">
			<div class="relative flex-1">
				<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] z-10" />
				<input
					bind:this={inputElement}
					type="search"
					placeholder="Cerca ovunque..."
					value={$searchQuery}
					on:input={handleInput}
					on:blur={handleBlur}
					on:focus={handleFocus}
					on:keydown={handleKeydown}
					class="input pl-10 pr-10 py-2.5 text-sm"
					autocomplete="off"
					autocorrect="off"
					autocapitalize="off"
					spellcheck="false"
				/>
				{#if $searchLoading || loadingSuggestions}
					<Loader2 class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--accent)] animate-spin" />
				{:else if $searchQuery}
					<button
						class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
						on:click={handleClear}
					>
						<X class="w-4 h-4 text-[var(--text-muted)]" />
					</button>
				{/if}

				<!-- Mobile Suggestions Dropdown -->
				{#if showSuggestions && suggestions.length > 0}
					<div class="absolute top-full left-0 right-0 mt-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-xl z-50 overflow-hidden max-h-64 overflow-y-auto">
						{#each suggestions as suggestion, i}
							<button
								class="w-full px-4 py-3 text-left hover:bg-[var(--bg-hover)] transition-colors flex items-start gap-3 {selectedIndex === i ? 'bg-[var(--bg-hover)]' : ''}"
								on:mousedown|preventDefault={() => selectSuggestion(suggestion)}
							>
								<svelte:component this={typeIcons[suggestion.item_type] || HelpCircle} class="w-4 h-4 mt-0.5 text-[var(--accent)] flex-shrink-0" />
								<div class="flex-1 min-w-0">
									<div class="font-medium text-sm truncate">{suggestion.title}</div>
									{#if suggestion.description}
										<div class="text-xs text-[var(--text-muted)] line-clamp-2 mt-0.5">{suggestion.description}</div>
									{/if}
								</div>
							</button>
						{/each}
					</div>
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
	<Search class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-muted)] z-10" />
	<input
		bind:this={desktopInputElement}
		type="search"
		placeholder="Cerca ovunque..."
		value={$searchQuery}
		on:input={handleInput}
		on:blur={handleBlur}
		on:focus={handleFocus}
		on:keydown={handleKeydown}
		class="input pl-10 pr-10 py-2.5"
		autocomplete="off"
		autocorrect="off"
		autocapitalize="off"
		spellcheck="false"
	/>
	{#if $searchLoading || loadingSuggestions}
		<Loader2 class="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--accent)] animate-spin" />
	{:else if $searchQuery}
		<button
			class="absolute right-2 top-1/2 -translate-y-1/2 p-1.5 rounded-lg hover:bg-[var(--bg-hover)] transition-colors"
			on:click={handleClear}
		>
			<X class="w-4 h-4 text-[var(--text-muted)]" />
		</button>
	{/if}

	<!-- Desktop Suggestions Dropdown -->
	{#if showSuggestions && suggestions.length > 0}
		<div class="absolute top-full left-0 right-0 mt-1 bg-[var(--bg-secondary)] border border-[var(--border)] rounded-xl shadow-xl z-50 overflow-hidden max-h-80 overflow-y-auto">
			{#each suggestions as suggestion, i}
				<button
					class="w-full px-4 py-3 text-left hover:bg-[var(--bg-hover)] transition-colors flex items-start gap-3 border-b border-[var(--border)] last:border-b-0 {selectedIndex === i ? 'bg-[var(--bg-hover)]' : ''}"
					on:mousedown|preventDefault={() => selectSuggestion(suggestion)}
				>
					<svelte:component this={typeIcons[suggestion.item_type] || HelpCircle} class="w-4 h-4 mt-0.5 text-[var(--accent)] flex-shrink-0" />
					<div class="flex-1 min-w-0">
						<div class="font-medium text-sm">{suggestion.title}</div>
						{#if suggestion.description}
							<div class="text-xs text-[var(--text-muted)] line-clamp-2 mt-0.5">{suggestion.description}</div>
						{/if}
					</div>
					<span class="text-[10px] uppercase tracking-wider text-[var(--text-muted)] opacity-60 flex-shrink-0">{suggestion.item_type}</span>
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	/* Remove default search input styling */
	input[type="search"]::-webkit-search-cancel-button,
	input[type="search"]::-webkit-search-decoration {
		-webkit-appearance: none;
		appearance: none;
	}

	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
