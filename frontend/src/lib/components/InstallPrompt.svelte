<script>
	import { onMount } from 'svelte';
	import { browser } from '$app/environment';
	import { X, Download, Share } from 'lucide-svelte';

	let deferredPrompt = null;
	let showBanner = false;
	let isIOS = false;
	let isStandalone = false;

	onMount(() => {
		if (!browser) return;

		// Check if already installed (standalone mode)
		isStandalone = window.matchMedia('(display-mode: standalone)').matches ||
			window.navigator.standalone === true;

		if (isStandalone) return;

		// Check if iOS
		isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;

		// Check if dismissed recently
		const dismissed = localStorage.getItem('install_dismissed');
		if (dismissed) {
			const dismissedTime = parseInt(dismissed, 10);
			// Don't show for 7 days after dismissal
			if (Date.now() - dismissedTime < 7 * 24 * 60 * 60 * 1000) {
				return;
			}
		}

		// For iOS, show instructions banner
		if (isIOS) {
			setTimeout(() => {
				showBanner = true;
			}, 3000);
			return;
		}

		// For Android/Desktop, listen for install prompt
		window.addEventListener('beforeinstallprompt', handleInstallPrompt);

		return () => {
			window.removeEventListener('beforeinstallprompt', handleInstallPrompt);
		};
	});

	function handleInstallPrompt(e) {
		e.preventDefault();
		deferredPrompt = e;
		showBanner = true;
	}

	async function handleInstall() {
		if (!deferredPrompt) return;

		deferredPrompt.prompt();
		const { outcome } = await deferredPrompt.userChoice;

		if (outcome === 'accepted') {
			showBanner = false;
		}

		deferredPrompt = null;
	}

	function dismiss() {
		showBanner = false;
		localStorage.setItem('install_dismissed', Date.now().toString());
	}
</script>

{#if showBanner && !isStandalone}
	<div class="fixed bottom-20 left-4 right-4 z-40 max-w-md mx-auto animate-slide-up">
		<div class="bg-[var(--bg-secondary)] border border-[var(--border)] rounded-2xl p-4 shadow-2xl">
			<button
				class="absolute top-2 right-2 p-1.5 text-[var(--text-muted)] hover:text-white transition-colors"
				on:click={dismiss}
			>
				<X class="w-5 h-5" />
			</button>

			<div class="flex items-start gap-4 pr-6">
				<div class="p-3 rounded-xl bg-gradient-to-br from-[var(--accent)] to-purple-600 flex-shrink-0">
					<Download class="w-6 h-6 text-white" />
				</div>

				<div class="flex-1">
					<h3 class="font-semibold text-white mb-1">Installa ThoughtCapture</h3>

					{#if isIOS}
						<p class="text-sm text-[var(--text-secondary)] mb-3">
							Tocca <Share class="w-4 h-4 inline text-[var(--accent)]" /> e poi "Aggiungi a Home"
						</p>
						<button
							class="btn btn-secondary btn-sm"
							on:click={dismiss}
						>
							Ho capito
						</button>
					{:else}
						<p class="text-sm text-[var(--text-secondary)] mb-3">
							Aggiungi l'app alla home per un accesso rapido
						</p>
						<button
							class="btn btn-primary btn-sm"
							on:click={handleInstall}
						>
							Installa
						</button>
					{/if}
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	@keyframes slide-up {
		from {
			opacity: 0;
			transform: translateY(20px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-slide-up {
		animation: slide-up 0.3s ease-out;
	}
</style>
