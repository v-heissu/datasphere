<script>
	import { createEventDispatcher } from 'svelte';
	import { Clock, RefreshCw, Check, ExternalLink, Sparkles } from 'lucide-svelte';

	export let picks = null;
	export let loading = false;

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
</script>

{#if picks && picks.picks && picks.picks.length > 0}
	<div class="card mb-8 border-[var(--accent)]/30 bg-gradient-to-br from-[var(--accent)]/5 to-transparent">
		<div class="p-6">
			<div class="flex items-center justify-between mb-5">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-xl bg-[var(--accent)]/20">
						<Sparkles class="w-5 h-5 text-[var(--accent)]" />
					</div>
					<div>
						<h2 class="text-xl font-bold">I tuoi picks di oggi</h2>
						{#if picks.message}
							<p class="text-sm opacity-60">{picks.message}</p>
						{/if}
					</div>
				</div>
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-1.5 text-sm opacity-60">
						<Clock class="w-4 h-4" />
						<span>~{picks.total_estimated_time}min</span>
					</div>
					<button
						class="btn btn-secondary btn-icon btn-sm"
						on:click={() => dispatch('regenerate')}
						disabled={loading}
						title="Rigenera picks"
					>
						<RefreshCw class="w-4 h-4 {loading ? 'animate-spin' : ''}" />
					</button>
				</div>
			</div>

			<div class="space-y-3">
				{#each picks.picks as pick, idx}
					{@const item = pick.item}
					{#if item}
						<div
							class="flex items-center gap-4 p-4 rounded-xl bg-[var(--bg-tertiary)] border border-[var(--border)] hover:border-[var(--accent)]/50 transition-all group"
						>
							<div
								class="w-10 h-10 rounded-xl bg-[var(--accent)]/20 text-[var(--accent)] flex items-center justify-center font-bold text-lg shrink-0"
							>
								{idx + 1}
							</div>

							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2 mb-1">
									<span>{typeIcon[item.item_type] || typeIcon.other}</span>
									<span class="font-semibold truncate">{item.title}</span>
									<span class="text-xs opacity-50 uppercase">{item.item_type}</span>
								</div>
								{#if pick.reason}
									<p class="text-xs opacity-50 truncate">{pick.reason}</p>
								{/if}
							</div>

							<div class="flex items-center gap-1.5 text-sm opacity-50 shrink-0">
								<Clock class="w-4 h-4" />
								<span>{item.estimated_minutes}min</span>
							</div>

							{#if item.enrichment?.links?.[0]?.url}
								<a
									href={item.enrichment.links[0].url}
									target="_blank"
									rel="noopener noreferrer"
									class="btn btn-secondary btn-sm btn-icon opacity-0 group-hover:opacity-100 transition-opacity"
									title="Apri link"
								>
									<ExternalLink class="w-4 h-4" />
								</a>
							{/if}

							<button
								class="btn btn-success btn-sm btn-icon"
								on:click={() => dispatch('consume', { id: item.id })}
								title="Fatto"
							>
								<Check class="w-4 h-4" />
							</button>
						</div>
					{/if}
				{/each}
			</div>
		</div>
	</div>
{:else}
	<div class="card mb-8 p-8 text-center">
		<div class="w-16 h-16 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center mx-auto mb-4">
			<Sparkles class="w-8 h-8 opacity-30" />
		</div>
		<p class="opacity-60">Nessun suggerimento per oggi.</p>
		<p class="text-sm opacity-40 mt-1">Cattura qualche pensiero su Telegram!</p>
	</div>
{/if}
