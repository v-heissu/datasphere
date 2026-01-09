<script>
	import { createEventDispatcher } from 'svelte';
	import { ExternalLink, Check, Archive, Clock, ChevronDown, ChevronUp } from 'lucide-svelte';

	export let item;

	const dispatch = createEventDispatcher();

	const typeEmoji = {
		film: 'Film',
		book: 'Libro',
		concept: 'Concetto',
		music: 'Musica',
		art: 'Arte',
		todo: 'Todo',
		other: 'Altro'
	};

	const typeColor = {
		film: 'border-l-purple-500 bg-purple-50',
		book: 'border-l-blue-500 bg-blue-50',
		concept: 'border-l-yellow-500 bg-yellow-50',
		music: 'border-l-pink-500 bg-pink-50',
		art: 'border-l-green-500 bg-green-50',
		todo: 'border-l-red-500 bg-red-50',
		other: 'border-l-gray-500 bg-gray-50'
	};

	let showDetails = false;

	function formatDate(dateStr) {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('it-IT', {
			day: 'numeric',
			month: 'short',
			year: 'numeric'
		});
	}

	function getDaysAgo(dateStr) {
		if (!dateStr) return 0;
		const date = new Date(dateStr);
		const now = new Date();
		const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24));
		return diff;
	}

	$: daysAgo = getDaysAgo(item.created_at);
	$: links = item.enrichment?.links || [];
</script>

<div
	class="card border-l-4 {typeColor[item.item_type] ||
		typeColor.other} hover:shadow-md transition-shadow"
>
	<div class="p-4">
		<!-- Header -->
		<div class="flex items-start justify-between mb-3">
			<div class="flex-1">
				<div class="flex items-center gap-2 mb-1">
					<span
						class="text-xs font-medium px-2 py-0.5 rounded-full bg-white/50 text-gray-600 border"
					>
						{typeEmoji[item.item_type] || typeEmoji.other}
					</span>
					{#if daysAgo > 7}
						<span class="text-xs text-orange-500 font-medium"> {daysAgo}g fa </span>
					{/if}
				</div>
				<h3 class="font-bold text-gray-900 text-lg">{item.title || 'Senza titolo'}</h3>
				<p class="text-xs text-gray-500">{formatDate(item.created_at)}</p>
			</div>
			<div class="flex items-center gap-2 text-sm text-gray-500">
				<Clock class="w-4 h-4" />
				<span>{item.estimated_minutes || '?'}min</span>
			</div>
		</div>

		<!-- Description -->
		{#if item.description}
			<p class="text-sm text-gray-700 mb-3">{item.description}</p>
		{/if}

		<!-- Tags -->
		{#if item.tags && item.tags.length > 0}
			<div class="flex gap-1 mb-3 flex-wrap">
				{#each item.tags as tag}
					<span class="text-xs px-2 py-0.5 bg-white/70 rounded border text-gray-600">{tag}</span>
				{/each}
			</div>
		{/if}

		<!-- Links (collapsible) -->
		{#if links.length > 0}
			<div class="mb-3">
				<button
					class="text-xs text-primary-600 hover:underline flex items-center gap-1"
					on:click={() => (showDetails = !showDetails)}
				>
					{#if showDetails}
						<ChevronUp class="w-3 h-3" />
					{:else}
						<ChevronDown class="w-3 h-3" />
					{/if}
					{links.length} link{links.length > 1 ? 's' : ''}
				</button>

				{#if showDetails}
					<div class="mt-2 space-y-1">
						{#each links as link}
							<a
								href={link.url}
								target="_blank"
								rel="noopener noreferrer"
								class="flex items-center gap-2 text-xs text-primary-600 hover:underline truncate"
							>
								<ExternalLink class="w-3 h-3 flex-shrink-0" />
								<span class="text-gray-500 font-medium">{link.type}:</span>
								<span class="truncate">{link.url}</span>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Consumption suggestion -->
		{#if item.enrichment?.consumption_suggestion}
			<p class="text-xs text-gray-500 italic mb-3">
				"{item.enrichment.consumption_suggestion}"
			</p>
		{/if}

		<!-- Actions -->
		<div class="flex gap-2 pt-2 border-t border-gray-200">
			{#if item.status === 'pending'}
				<button
					class="btn btn-success btn-sm flex-1"
					on:click={() => dispatch('action', { action: 'consumed', id: item.id })}
				>
					<Check class="w-4 h-4" />
					Fatto
				</button>
				<button
					class="btn btn-secondary btn-sm"
					on:click={() => dispatch('action', { action: 'archived', id: item.id })}
				>
					<Archive class="w-4 h-4" />
				</button>
			{:else if item.status === 'consumed'}
				<span class="text-green-600 text-sm flex items-center gap-1">
					<Check class="w-4 h-4" />
					Consumato {formatDate(item.consumed_at)}
				</span>
			{:else if item.status === 'archived'}
				<button
					class="btn btn-secondary btn-sm"
					on:click={() => dispatch('action', { action: 'pending', id: item.id })}
				>
					Ripristina
				</button>
			{/if}
		</div>
	</div>
</div>
