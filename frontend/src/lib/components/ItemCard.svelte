<script>
	import { createEventDispatcher } from 'svelte';
	import { ExternalLink, Check, Archive, Clock, ChevronDown, ChevronUp, Trash2, RotateCcw, Copy, CheckCircle2 } from 'lucide-svelte';

	export let item;

	const dispatch = createEventDispatcher();
	let copied = false;

	const typeLabel = {
		film: 'Film',
		book: 'Libro',
		concept: 'Concetto',
		music: 'Musica',
		art: 'Arte',
		todo: 'Todo',
		other: 'Altro'
	};

	const typeIcon = {
		film: '🎬',
		book: '📚',
		concept: '💡',
		music: '🎵',
		art: '🎨',
		todo: '✓',
		other: '📌'
	};

	let showDetails = false;
	let confirmDelete = false;

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

	function handleDelete() {
		if (confirmDelete) {
			dispatch('action', { action: 'delete', id: item.id });
			confirmDelete = false;
		} else {
			confirmDelete = true;
			setTimeout(() => confirmDelete = false, 3000);
		}
	}

	async function copyCard() {
		const title = item.title || 'Senza titolo';
		const type = typeLabel[item.item_type] || 'Altro';
		const desc = item.description || '';
		const tags = item.tags?.join(', ') || '';
		const suggestion = item.enrichment?.consumption_suggestion || '';
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
			copied = true;
			setTimeout(() => copied = false, 2000);
		} catch (e) {
			console.error('Copy failed:', e);
		}
	}

	$: daysAgo = getDaysAgo(item.created_at);
	$: links = item.enrichment?.links || [];
	$: itemType = item.item_type || 'other';
</script>

<div class="card type-{itemType} animate-fade-in group">
	<div class="p-4 sm:p-5">
		<!-- Header -->
		<div class="flex items-start justify-between gap-3 mb-3">
			<div class="flex-1 min-w-0">
				<div class="flex items-center gap-2 mb-1.5">
					<span class="text-base sm:text-lg">{typeIcon[itemType] || typeIcon.other}</span>
					<span class="text-xs font-semibold uppercase tracking-wider opacity-70">
						{typeLabel[itemType] || typeLabel.other}
					</span>
					{#if daysAgo > 7}
						<span class="text-xs px-2 py-0.5 rounded-full bg-orange-500/20 text-orange-400 font-medium">
							{daysAgo}g fa
						</span>
					{/if}
				</div>
				<h3 class="font-bold text-base sm:text-lg leading-snug">{item.title || 'Senza titolo'}</h3>
			</div>
			<div class="flex items-center gap-1.5 shrink-0">
				<button
					class="btn btn-ghost btn-icon btn-sm sm:opacity-0 sm:group-hover:opacity-60 hover:!opacity-100 transition-opacity"
					title={copied ? 'Copiato!' : 'Copia'}
					on:click={copyCard}
				>
					{#if copied}
						<CheckCircle2 class="w-4 h-4 text-[var(--success)]" />
					{:else}
						<Copy class="w-4 h-4" />
					{/if}
				</button>
				<div class="flex items-center gap-1 text-xs sm:text-sm opacity-60">
					<Clock class="w-3.5 h-3.5 sm:w-4 sm:h-4" />
					<span>{item.estimated_minutes || '?'}min</span>
				</div>
			</div>
		</div>

		<!-- Description -->
		{#if item.description}
			<p class="text-sm opacity-70 mb-3 leading-relaxed line-clamp-3">{item.description}</p>
		{/if}

		<!-- Original query (verbatim) - hidden on mobile for space -->
		{#if item.verbatim_input}
			<p class="hidden sm:block text-xs opacity-40 mb-3 italic border-l-2 border-white/10 pl-3 line-clamp-2">
				"{item.verbatim_input}"
			</p>
		{/if}

		<!-- Tags -->
		{#if item.tags && item.tags.length > 0}
			<div class="flex gap-1.5 mb-3 flex-wrap">
				{#each item.tags.slice(0, 4) as tag}
					<span class="text-xs px-2 py-0.5 rounded-lg bg-white/5 border border-white/10">{tag}</span>
				{/each}
				{#if item.tags.length > 4}
					<span class="text-xs px-2 py-0.5 opacity-40">+{item.tags.length - 4}</span>
				{/if}
			</div>
		{/if}

		<!-- Links (collapsible) -->
		{#if links.length > 0}
			<div class="mb-4">
				<button
					class="text-xs opacity-60 hover:opacity-100 flex items-center gap-1 transition-opacity"
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
					<div class="mt-3 space-y-2 animate-fade-in">
						{#each links as link}
							<a
								href={link.url}
								target="_blank"
								rel="noopener noreferrer"
								class="flex items-center gap-2 text-xs hover:opacity-100 opacity-70 transition-opacity group/link"
							>
								<ExternalLink class="w-3 h-3 flex-shrink-0 text-[var(--accent)]" />
								<span class="font-medium text-[var(--accent)]">{link.type}</span>
								<span class="truncate opacity-60 group-hover/link:opacity-100">{link.url}</span>
							</a>
						{/each}
					</div>
				{/if}
			</div>
		{/if}

		<!-- Consumption suggestion -->
		{#if item.enrichment?.consumption_suggestion}
			<p class="text-xs opacity-50 italic mb-4 border-l-2 border-white/20 pl-3">
				{item.enrichment.consumption_suggestion}
			</p>
		{/if}

		<!-- Actions -->
		<div class="flex items-center gap-2 pt-4 border-t border-white/10">
			{#if item.status === 'pending'}
				<button
					class="btn btn-success btn-sm flex-1"
					on:click={() => dispatch('action', { action: 'consumed', id: item.id })}
				>
					<Check class="w-4 h-4" />
					Fatto
				</button>
				<button
					class="btn btn-secondary btn-sm btn-icon"
					title="Archivia"
					on:click={() => dispatch('action', { action: 'archived', id: item.id })}
				>
					<Archive class="w-4 h-4" />
				</button>
				<button
					class="btn btn-sm btn-icon {confirmDelete ? 'btn-danger' : 'btn-ghost'}"
					title={confirmDelete ? 'Conferma eliminazione' : 'Elimina'}
					on:click={handleDelete}
				>
					<Trash2 class="w-4 h-4" />
				</button>
			{:else if item.status === 'consumed'}
				<div class="flex-1 flex items-center gap-2 text-sm text-[var(--success)]">
					<Check class="w-4 h-4" />
					<span>Consumato {formatDate(item.consumed_at)}</span>
				</div>
				<button
					class="btn btn-sm btn-icon btn-ghost"
					title="Ripristina"
					on:click={() => dispatch('action', { action: 'pending', id: item.id })}
				>
					<RotateCcw class="w-4 h-4" />
				</button>
				<button
					class="btn btn-sm btn-icon {confirmDelete ? 'btn-danger' : 'btn-ghost'}"
					title={confirmDelete ? 'Conferma eliminazione' : 'Elimina'}
					on:click={handleDelete}
				>
					<Trash2 class="w-4 h-4" />
				</button>
			{:else if item.status === 'archived'}
				<button
					class="btn btn-secondary btn-sm flex-1"
					on:click={() => dispatch('action', { action: 'pending', id: item.id })}
				>
					<RotateCcw class="w-4 h-4" />
					Ripristina
				</button>
				<button
					class="btn btn-sm btn-icon {confirmDelete ? 'btn-danger' : 'btn-ghost'}"
					title={confirmDelete ? 'Conferma eliminazione' : 'Elimina'}
					on:click={handleDelete}
				>
					<Trash2 class="w-4 h-4" />
				</button>
			{/if}
		</div>
	</div>
</div>
