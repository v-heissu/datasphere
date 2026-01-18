<script>
	import { createEventDispatcher } from 'svelte';
	import { Clock, RefreshCw, Check, ExternalLink, Sparkles, ChevronLeft, ChevronRight } from 'lucide-svelte';

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

	// Carousel state for mobile
	let currentIndex = 0;
	let touchStartX = 0;
	let touchEndX = 0;
	let carouselContainer;

	$: totalPicks = picks?.picks?.length || 0;
	$: canGoBack = currentIndex > 0;
	$: canGoForward = currentIndex < totalPicks - 1;

	function goTo(index) {
		if (index >= 0 && index < totalPicks) {
			currentIndex = index;
		}
	}

	function handleTouchStart(e) {
		touchStartX = e.touches[0].clientX;
	}

	function handleTouchMove(e) {
		touchEndX = e.touches[0].clientX;
	}

	function handleTouchEnd() {
		const diff = touchStartX - touchEndX;
		const threshold = 50;

		if (Math.abs(diff) > threshold) {
			if (diff > 0 && canGoForward) {
				currentIndex++;
			} else if (diff < 0 && canGoBack) {
				currentIndex--;
			}
		}
	}
</script>

{#if picks && picks.picks && picks.picks.length > 0}
	<div class="card mb-6 sm:mb-8 border-[var(--accent)]/30 bg-gradient-to-br from-[var(--accent)]/5 to-transparent overflow-hidden">
		<!-- Header -->
		<div class="p-4 sm:p-6 pb-3 sm:pb-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2 sm:gap-3">
					<div class="p-1.5 sm:p-2 rounded-lg sm:rounded-xl bg-[var(--accent)]/20">
						<Sparkles class="w-4 h-4 sm:w-5 sm:h-5 text-[var(--accent)]" />
					</div>
					<div>
						<h2 class="text-base sm:text-xl font-bold">I tuoi picks di oggi</h2>
						{#if picks.message}
							<p class="text-xs sm:text-sm opacity-60 line-clamp-1">{picks.message}</p>
						{/if}
					</div>
				</div>
				<div class="flex items-center gap-2 sm:gap-4">
					<div class="hidden sm:flex items-center gap-1.5 text-sm opacity-60">
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
		</div>

		<!-- Mobile Carousel -->
		<div class="sm:hidden relative">
			<!-- Carousel container -->
			<div
				bind:this={carouselContainer}
				class="overflow-hidden"
				on:touchstart={handleTouchStart}
				on:touchmove={handleTouchMove}
				on:touchend={handleTouchEnd}
			>
				<div
					class="flex transition-transform duration-300 ease-out"
					style="transform: translateX(-{currentIndex * 100}%)"
				>
					{#each picks.picks as pick, idx}
						{@const item = pick.item}
						{#if item}
							<div class="w-full flex-shrink-0 px-4 pb-4">
								<div class="bg-[var(--bg-tertiary)] rounded-xl border border-[var(--border)] p-4">
									<!-- Type badge and time -->
									<div class="flex items-center justify-between mb-3">
										<div class="flex items-center gap-2">
											<span class="text-xl">{typeIcon[item.item_type] || typeIcon.other}</span>
											<span class="text-xs font-semibold uppercase tracking-wide opacity-60">{item.item_type}</span>
										</div>
										<div class="flex items-center gap-1.5 text-xs opacity-50">
											<Clock class="w-3.5 h-3.5" />
											<span>{item.estimated_minutes}min</span>
										</div>
									</div>

									<!-- Title - full, can wrap -->
									<h3 class="font-bold text-lg mb-2 leading-snug">{item.title}</h3>

									<!-- Description - 2 lines -->
									{#if item.description}
										<p class="text-sm opacity-60 mb-3 line-clamp-2">{item.description}</p>
									{/if}

									<!-- Reason -->
									{#if pick.reason}
										<p class="text-xs opacity-40 italic mb-4 border-l-2 border-[var(--accent)]/30 pl-2">{pick.reason}</p>
									{/if}

									<!-- Actions -->
									<div class="flex items-center gap-2">
										{#if item.enrichment?.links?.[0]?.url}
											<a
												href={item.enrichment.links[0].url}
												target="_blank"
												rel="noopener noreferrer"
												class="btn btn-secondary btn-sm flex-1"
											>
												<ExternalLink class="w-4 h-4" />
												<span>Apri</span>
											</a>
										{/if}
										<button
											class="btn btn-success btn-sm flex-1"
											on:click={() => dispatch('consume', { id: item.id })}
										>
											<Check class="w-4 h-4" />
											<span>Fatto</span>
										</button>
									</div>
								</div>
							</div>
						{/if}
					{/each}
				</div>
			</div>

			<!-- Dots indicator -->
			{#if totalPicks > 1}
				<div class="flex items-center justify-center gap-1.5 pb-4">
					{#each picks.picks as _, idx}
						<button
							class="w-2 h-2 rounded-full transition-all {idx === currentIndex ? 'bg-[var(--accent)] w-4' : 'bg-white/20'}"
							on:click={() => goTo(idx)}
						/>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Desktop List -->
		<div class="hidden sm:block px-6 pb-6">
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
									<span class="font-semibold">{item.title}</span>
									<span class="text-xs opacity-50 uppercase">{item.item_type}</span>
								</div>
								{#if pick.reason}
									<p class="text-xs opacity-50 line-clamp-1">{pick.reason}</p>
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
	<div class="card mb-6 sm:mb-8 p-6 sm:p-8 text-center">
		<div class="w-12 h-12 sm:w-16 sm:h-16 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center mx-auto mb-3 sm:mb-4">
			<Sparkles class="w-6 h-6 sm:w-8 sm:h-8 opacity-30" />
		</div>
		<p class="opacity-60 text-sm sm:text-base">Nessun suggerimento per oggi.</p>
		<p class="text-xs opacity-40 mt-1">Aggiungi qualche pensiero!</p>
	</div>
{/if}
