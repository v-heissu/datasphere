<script>
	import { createEventDispatcher } from 'svelte';
	import { Clock, RefreshCw, Check, ExternalLink } from 'lucide-svelte';

	export let picks = null;
	export let loading = false;

	const dispatch = createEventDispatcher();
</script>

{#if picks && picks.picks && picks.picks.length > 0}
	<div class="card mb-8 border-2 border-primary-200 bg-primary-50/30">
		<div class="p-4">
			<div class="flex items-center justify-between mb-4">
				<div>
					<h2 class="text-xl font-bold text-gray-900">I tuoi picks di oggi</h2>
					{#if picks.message}
						<p class="text-sm text-gray-600">{picks.message}</p>
					{/if}
				</div>
				<div class="flex items-center gap-4">
					<div class="flex items-center gap-1 text-sm text-gray-500">
						<Clock class="w-4 h-4" />
						<span>~{picks.total_estimated_time}min totali</span>
					</div>
					<button
						class="btn btn-secondary btn-sm"
						on:click={() => dispatch('regenerate')}
						disabled={loading}
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
							class="flex items-center gap-4 p-3 bg-white rounded-lg border border-gray-200 hover:border-primary-300 transition-colors"
						>
							<div
								class="w-8 h-8 rounded-full bg-primary-100 text-primary-600 flex items-center justify-center font-bold"
							>
								{idx + 1}
							</div>

							<div class="flex-1 min-w-0">
								<div class="flex items-center gap-2">
									<span class="font-medium text-gray-900 truncate">{item.title}</span>
									<span class="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded"
										>{item.item_type}</span
									>
								</div>
								{#if pick.reason}
									<p class="text-xs text-gray-500 truncate">{pick.reason}</p>
								{/if}
							</div>

							<div class="flex items-center gap-2 text-sm text-gray-500">
								<Clock class="w-4 h-4" />
								<span>{item.estimated_minutes}min</span>
							</div>

							{#if item.enrichment?.links?.[0]?.url}
								<a
									href={item.enrichment.links[0].url}
									target="_blank"
									rel="noopener noreferrer"
									class="btn btn-secondary btn-sm"
								>
									<ExternalLink class="w-4 h-4" />
								</a>
							{/if}

							<button
								class="btn btn-success btn-sm"
								on:click={() => dispatch('consume', { id: item.id })}
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
	<div class="card mb-8 p-6 text-center">
		<p class="text-gray-500">Nessun suggerimento per oggi.</p>
		<p class="text-sm text-gray-400 mt-1">Cattura qualche pensiero su Telegram!</p>
	</div>
{/if}
