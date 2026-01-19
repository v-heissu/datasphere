<script>
	import { onMount } from 'svelte';
	import { X, ChevronRight, ChevronLeft, Brain, MessageSquare, Image, Search, Sparkles, Download, Check } from 'lucide-svelte';
	import { browser } from '$app/environment';

	export let show = false;
	export let onClose = () => {};

	let currentStep = 0;
	let deferredPrompt = null;
	let canInstall = false;
	let installed = false;

	const steps = [
		{
			icon: Brain,
			title: 'Benvenuto in ThoughtCapture!',
			description: 'La tua app per catturare pensieri al volo. Perfetta per chi ha mille idee e poco tempo.',
			color: 'var(--accent)'
		},
		{
			icon: MessageSquare,
			title: 'Cattura i tuoi pensieri',
			description: 'Scrivi qualsiasi cosa: un film da vedere, un libro, un\'idea, un todo. L\'AI lo classificherà automaticamente.',
			color: '#10b981'
		},
		{
			icon: Image,
			title: 'Condividi immagini',
			description: 'Vedi una locandina interessante? Scatta una foto o seleziona dalla galleria. L\'AI riconoscerà il contenuto.',
			color: '#f59e0b'
		},
		{
			icon: Search,
			title: 'Cerca e ritrova',
			description: 'Cerca tra i tuoi pensieri salvati. Filtra per tipo, stato, o usa la ricerca full-text.',
			color: '#3b82f6'
		},
		{
			icon: Sparkles,
			title: 'Daily Picks',
			description: 'Ogni giorno ricevi suggerimenti personalizzati su cosa consumare, basati sulle tue priorità.',
			color: '#ec4899'
		}
	];

	const totalSteps = steps.length + 1; // +1 for install step

	onMount(() => {
		if (browser) {
			// Check if already installed
			if (window.matchMedia('(display-mode: standalone)').matches) {
				installed = true;
			}

			// Listen for install prompt
			window.addEventListener('beforeinstallprompt', (e) => {
				e.preventDefault();
				deferredPrompt = e;
				canInstall = true;
			});
		}
	});

	async function handleInstall() {
		if (!deferredPrompt) return;

		deferredPrompt.prompt();
		const { outcome } = await deferredPrompt.userChoice;

		if (outcome === 'accepted') {
			installed = true;
			canInstall = false;
		}
		deferredPrompt = null;
	}

	function nextStep() {
		if (currentStep < totalSteps - 1) {
			currentStep++;
		} else {
			completeOnboarding();
		}
	}

	function prevStep() {
		if (currentStep > 0) {
			currentStep--;
		}
	}

	function completeOnboarding() {
		if (browser) {
			localStorage.setItem('onboarding_completed', 'true');
		}
		onClose();
	}

	function skip() {
		completeOnboarding();
	}

	$: isLastStep = currentStep === totalSteps - 1;
	$: isInstallStep = currentStep === steps.length;
</script>

{#if show}
	<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
		<div class="relative w-full max-w-md bg-[var(--bg-secondary)] rounded-2xl border border-[var(--border)] overflow-hidden animate-scale-in">
			<!-- Close button -->
			<button
				class="absolute top-3 right-3 p-2 rounded-lg hover:bg-white/10 transition-colors z-10"
				on:click={skip}
				title="Salta"
			>
				<X class="w-5 h-5 opacity-60" />
			</button>

			<!-- Content -->
			<div class="p-6 pt-12">
				{#if !isInstallStep}
					{@const step = steps[currentStep]}
					<div class="text-center">
						<!-- Icon -->
						<div
							class="w-20 h-20 rounded-2xl mx-auto mb-6 flex items-center justify-center"
							style="background: {step.color}20;"
						>
							<svelte:component this={step.icon} class="w-10 h-10" style="color: {step.color}" />
						</div>

						<!-- Title -->
						<h2 class="text-xl font-bold mb-3">{step.title}</h2>

						<!-- Description -->
						<p class="text-sm opacity-70 leading-relaxed mb-8">
							{step.description}
						</p>
					</div>
				{:else}
					<!-- Install Step -->
					<div class="text-center">
						<div
							class="w-20 h-20 rounded-2xl mx-auto mb-6 flex items-center justify-center bg-[var(--accent)]/20"
						>
							<Download class="w-10 h-10 text-[var(--accent)]" />
						</div>

						<h2 class="text-xl font-bold mb-3">Installa l'app</h2>

						<p class="text-sm opacity-70 leading-relaxed mb-6">
							Installa ThoughtCapture sul tuo dispositivo per un'esperienza migliore e accesso rapido.
						</p>

						{#if installed}
							<div class="flex items-center justify-center gap-2 text-[var(--success)] mb-6">
								<Check class="w-5 h-5" />
								<span class="font-medium">App già installata!</span>
							</div>
						{:else if canInstall}
							<button
								class="btn btn-primary w-full mb-4"
								on:click={handleInstall}
							>
								<Download class="w-5 h-5" />
								<span>Installa ora</span>
							</button>
						{:else}
							<!-- iOS instructions -->
							<div class="bg-[var(--bg-tertiary)] rounded-xl p-4 text-left mb-6">
								<p class="text-xs font-medium mb-2 opacity-80">Su iPhone/iPad:</p>
								<ol class="text-xs opacity-60 space-y-1">
									<li>1. Tocca il pulsante <strong>Condividi</strong> (quadrato con freccia)</li>
									<li>2. Scorri e seleziona <strong>"Aggiungi a Home"</strong></li>
									<li>3. Tocca <strong>"Aggiungi"</strong></li>
								</ol>
							</div>
						{/if}

						<p class="text-xs opacity-40">
							Puoi sempre installare dopo dalle impostazioni
						</p>
					</div>
				{/if}
			</div>

			<!-- Footer with navigation -->
			<div class="px-6 pb-6">
				<!-- Progress dots -->
				<div class="flex items-center justify-center gap-1.5 mb-6">
					{#each Array(totalSteps) as _, idx}
						<button
							class="w-2 h-2 rounded-full transition-all {idx === currentStep ? 'bg-[var(--accent)] w-6' : 'bg-white/20 hover:bg-white/30'}"
							on:click={() => currentStep = idx}
						/>
					{/each}
				</div>

				<!-- Navigation buttons -->
				<div class="flex items-center gap-3">
					{#if currentStep > 0}
						<button
							class="btn btn-secondary btn-icon"
							on:click={prevStep}
						>
							<ChevronLeft class="w-5 h-5" />
						</button>
					{/if}

					<button
						class="btn btn-primary flex-1"
						on:click={nextStep}
					>
						{#if isLastStep}
							<span>Inizia!</span>
							<Check class="w-5 h-5" />
						{:else}
							<span>Avanti</span>
							<ChevronRight class="w-5 h-5" />
						{/if}
					</button>
				</div>

				<!-- Skip link -->
				<button
					class="w-full text-center text-xs opacity-40 hover:opacity-70 transition-opacity mt-4 py-2"
					on:click={skip}
				>
					Salta introduzione
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes fade-in {
		from { opacity: 0; }
		to { opacity: 1; }
	}

	@keyframes scale-in {
		from {
			opacity: 0;
			transform: scale(0.95);
		}
		to {
			opacity: 1;
			transform: scale(1);
		}
	}

	.animate-fade-in {
		animation: fade-in 0.2s ease-out;
	}

	.animate-scale-in {
		animation: scale-in 0.3s ease-out;
	}
</style>
