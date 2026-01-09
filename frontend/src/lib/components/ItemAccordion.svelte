<script>
	import { createEventDispatcher } from 'svelte';
	import { ExternalLink, Check, Archive, Trash2, RotateCcw, Copy, CheckCircle2, ChevronDown, Clock } from 'lucide-svelte';

	export let items = [];

	const dispatch = createEventDispatcher();

	const typeIcon = {
		film: '🎬',
		book: '📚',
		concept: '💡',
		music: '🎵',
		art: '🎨',
		todo: '✓',
		other: '📌'
	};

	const typeLabel = {
		film: 'Film',
		book: 'Libro',
		concept: 'Concetto',
		music: 'Musica',
		art: 'Arte',
		todo: 'Todo',
		other: 'Altro'
	};

	let expandedId = null;
	let copiedId = null;
	let confirmDeleteId = null;

	function toggle(id) {
		expandedId = expandedId === id ? null : id;
	}

	function formatDate(dateStr) {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('it-IT', { day: 'numeric', month: 'short' });
	}

	function handleDelete(id) {
		if (confirmDeleteId === id) {
			dispatch('action', { action: 'delete', id });
			confirmDeleteId = null;
		} else {
			confirmDeleteId = id;
			setTimeout(() => confirmDeleteId = null, 3000);
		}
	}

	async function copyItem(item) {
		const title = item.title || 'Senza titolo';
		const type = typeLabel[item.item_type] || 'Altro';
		const desc = item.description || '';
		const tags = item.tags?.join(', ') || '';
		const suggestion = item.enrichment?.consumption_suggestion || '';
		const links = item.enrichment?.links || [];
		const mainLink = links[0]?.url || '';

		let text = `${typeIcon[item.item_type] || '📌'} ${title}\n`;
		text += `Tipo: ${type}\n`;
		if (desc) text += `${desc}\n`;
		if (tags) text += `Tag: ${tags}\n`;
		if (item.estimated_minutes) text += `Tempo: ${item.estimated_minutes}min\n`;
		if (suggestion) text += `Suggerimento: ${suggestion}\n`;
		if (mainLink) text += `Link: ${mainLink}\n`;

		try {
			await navigator.clipboard.writeText(text.trim());
			copiedId = item.id;
			setTimeout(() => copiedId = null, 2000);
		} catch (e) {
			console.error('Copy failed:', e);
		}
	}
</script>

<div class="space-y-2">
	{#each items as item (item.id)}
		{@const isExpanded = expandedId === item.id}
		{@const links = item.enrichment?.links || []}

		<div class="card overflow-hidden">
			<!-- Header (always visible) -->
			<button
				class="w-full p-4 flex items-center gap-3 text-left hover:bg-white/5 transition-colors"
				on:click={() => toggle(item.id)}
			>
				<span class="text-lg flex-shrink-0">{typeIcon[item.item_type] || typeIcon.other}</span>

				<div class="flex-1 min-w-0">
					<h3 class="font-medium truncate">{item.title || 'Senza titolo'}</h3>
					{#if !isExpanded && item.description}
						<p class="text-xs opacity-50 truncate">{item.description}</p>
					{/if}
				</div>

				<div class="flex items-center gap-3 flex-shrink-0">
					<span class="text-xs opacity-50 hidden sm:inline">{formatDate(item.created_at)}</span>
					<div class="flex items-center gap-1 text-xs opacity-50">
						<Clock class="w-3 h-3" />
						{item.estimated_minutes || '?'}min
					</div>
					<ChevronDown class="w-4 h-4 opacity-40 transition-transform {isExpanded ? 'rotate-180' : ''}" />
				</div>
			</button>

			<!-- Expanded content -->
			{#if isExpanded}
				<div class="px-4 pb-4 pt-0 animate-fade-in border-t border-[var(--border)]">
					<!-- Description -->
					{#if item.description}
						<p class="text-sm opacity-70 mt-4 mb-4">{item.description}</p>
					{/if}

					<!-- Tags -->
					{#if item.tags?.length > 0}
						<div class="flex gap-1.5 mb-4 flex-wrap">
							{#each item.tags as tag}
								<span class="text-xs px-2 py-1 rounded-lg bg-white/5 border border-white/10">{tag}</span>
							{/each}
						</div>
					{/if}

					<!-- Links -->
					{#if links.length > 0}
						<div class="mb-4 space-y-1">
							{#each links as link}
								<a
									href={link.url}
									target="_blank"
									rel="noopener noreferrer"
									class="flex items-center gap-2 text-xs hover:opacity-100 opacity-70 transition-opacity"
								>
									<ExternalLink class="w-3 h-3 text-[var(--accent)]" />
									<span class="font-medium text-[var(--accent)]">{link.type}</span>
									<span class="truncate opacity-60">{link.url}</span>
								</a>
							{/each}
						</div>
					{/if}

					<!-- Consumption suggestion -->
					{#if item.enrichment?.consumption_suggestion}
						<p class="text-xs opacity-50 italic mb-4 border-l-2 border-white/20 pl-3">
							{item.enrichment.consumption_suggestion}
						</p>
					{/if}

					<!-- Actions -->
					<div class="flex items-center gap-2 pt-3 border-t border-[var(--border)]">
						{#if item.status === 'pending'}
							<button
								class="btn btn-success btn-sm flex-1"
								on:click|stopPropagation={() => dispatch('action', { action: 'consumed', id: item.id })}
							>
								<Check class="w-4 h-4" />
								Fatto
							</button>
							<button
								class="btn btn-secondary btn-sm btn-icon"
								title="Archivia"
								on:click|stopPropagation={() => dispatch('action', { action: 'archived', id: item.id })}
							>
								<Archive class="w-4 h-4" />
							</button>
						{:else}
							<button
								class="btn btn-secondary btn-sm flex-1"
								on:click|stopPropagation={() => dispatch('action', { action: 'pending', id: item.id })}
							>
								<RotateCcw class="w-4 h-4" />
								Ripristina
							</button>
						{/if}

						<button
							class="btn btn-ghost btn-sm btn-icon"
							title={copiedId === item.id ? 'Copiato!' : 'Copia'}
							on:click|stopPropagation={() => copyItem(item)}
						>
							{#if copiedId === item.id}
								<CheckCircle2 class="w-4 h-4 text-[var(--success)]" />
							{:else}
								<Copy class="w-4 h-4" />
							{/if}
						</button>

						<button
							class="btn btn-sm btn-icon {confirmDeleteId === item.id ? 'btn-danger' : 'btn-ghost'}"
							title={confirmDeleteId === item.id ? 'Conferma' : 'Elimina'}
							on:click|stopPropagation={() => handleDelete(item.id)}
						>
							<Trash2 class="w-4 h-4" />
						</button>
					</div>
				</div>
			{/if}
		</div>
	{/each}
</div>
