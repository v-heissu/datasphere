<script>
	import { createEventDispatcher } from 'svelte';
	import { ExternalLink, Check, Archive, Trash2, RotateCcw, Copy, CheckCircle2 } from 'lucide-svelte';

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

	let copiedId = null;
	let confirmDeleteId = null;

	function formatDate(dateStr) {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		return date.toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' });
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
		const desc = item.description || '';
		const links = item.enrichment?.links || [];
		const mainLink = links[0]?.url || '';

		let text = `${typeIcon[item.item_type] || '📌'} ${title}`;
		if (desc) text += `\n${desc}`;
		if (mainLink) text += `\n${mainLink}`;

		try {
			await navigator.clipboard.writeText(text);
			copiedId = item.id;
			setTimeout(() => copiedId = null, 2000);
		} catch (e) {
			console.error('Copy failed:', e);
		}
	}

	function getMainLink(item) {
		return item.enrichment?.links?.[0]?.url || null;
	}
</script>

<div class="overflow-x-auto -mx-3 sm:mx-0">
	<table class="w-full min-w-[600px]">
		<thead>
			<tr class="border-b border-[var(--border)]">
				<th class="text-left p-3 text-xs font-semibold uppercase tracking-wider opacity-50">Tipo</th>
				<th class="text-left p-3 text-xs font-semibold uppercase tracking-wider opacity-50">Titolo</th>
				<th class="text-left p-3 text-xs font-semibold uppercase tracking-wider opacity-50 hidden sm:table-cell">Descrizione</th>
				<th class="text-center p-3 text-xs font-semibold uppercase tracking-wider opacity-50">Min</th>
				<th class="text-center p-3 text-xs font-semibold uppercase tracking-wider opacity-50 hidden sm:table-cell">Data</th>
				<th class="text-right p-3 text-xs font-semibold uppercase tracking-wider opacity-50">Azioni</th>
			</tr>
		</thead>
		<tbody>
			{#each items as item (item.id)}
				<tr class="border-b border-[var(--border)] hover:bg-white/5 transition-colors group">
					<td class="p-3">
						<span class="text-lg">{typeIcon[item.item_type] || typeIcon.other}</span>
					</td>
					<td class="p-3">
						<div class="flex items-center gap-2">
							<span class="font-medium">{item.title || 'Senza titolo'}</span>
							{#if getMainLink(item)}
								<a
									href={getMainLink(item)}
									target="_blank"
									rel="noopener noreferrer"
									class="text-[var(--accent)] opacity-60 hover:opacity-100"
								>
									<ExternalLink class="w-3.5 h-3.5" />
								</a>
							{/if}
						</div>
						{#if item.tags?.length > 0}
							<div class="flex gap-1 mt-1">
								{#each item.tags.slice(0, 3) as tag}
									<span class="text-[10px] px-1.5 py-0.5 rounded bg-white/10 opacity-50">{tag}</span>
								{/each}
							</div>
						{/if}
					</td>
					<td class="p-3 hidden sm:table-cell">
						<span class="text-sm opacity-60 line-clamp-2">{item.description || '-'}</span>
					</td>
					<td class="p-3 text-center">
						<span class="text-sm opacity-70">{item.estimated_minutes || '?'}</span>
					</td>
					<td class="p-3 text-center hidden sm:table-cell">
						<span class="text-xs opacity-50">{formatDate(item.created_at)}</span>
					</td>
					<td class="p-3">
						<div class="flex items-center justify-end gap-1">
							<button
								class="btn btn-ghost btn-icon btn-sm opacity-0 group-hover:opacity-60 hover:!opacity-100"
								title={copiedId === item.id ? 'Copiato!' : 'Copia'}
								on:click={() => copyItem(item)}
							>
								{#if copiedId === item.id}
									<CheckCircle2 class="w-3.5 h-3.5 text-[var(--success)]" />
								{:else}
									<Copy class="w-3.5 h-3.5" />
								{/if}
							</button>

							{#if item.status === 'pending'}
								<button
									class="btn btn-success btn-icon btn-sm"
									title="Fatto"
									on:click={() => dispatch('action', { action: 'consumed', id: item.id })}
								>
									<Check class="w-3.5 h-3.5" />
								</button>
								<button
									class="btn btn-secondary btn-icon btn-sm"
									title="Archivia"
									on:click={() => dispatch('action', { action: 'archived', id: item.id })}
								>
									<Archive class="w-3.5 h-3.5" />
								</button>
							{:else}
								<button
									class="btn btn-ghost btn-icon btn-sm"
									title="Ripristina"
									on:click={() => dispatch('action', { action: 'pending', id: item.id })}
								>
									<RotateCcw class="w-3.5 h-3.5" />
								</button>
							{/if}

							<button
								class="btn btn-icon btn-sm {confirmDeleteId === item.id ? 'btn-danger' : 'btn-ghost'}"
								title={confirmDeleteId === item.id ? 'Conferma' : 'Elimina'}
								on:click={() => handleDelete(item.id)}
							>
								<Trash2 class="w-3.5 h-3.5" />
							</button>
						</div>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>
