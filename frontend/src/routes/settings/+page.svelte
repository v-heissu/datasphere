<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { User, LogOut, Bell, BellOff, Info, ChevronRight, Loader2 } from 'lucide-svelte';
	import { isAuthenticated, currentUser, logout } from '$lib/auth.js';
	import { getVapidPublicKey, subscribePush, unsubscribePush } from '$lib/api.js';

	let user = null;
	let pushSupported = false;
	let pushEnabled = false;
	let pushLoading = false;

	onMount(() => {
		const unsubscribe = isAuthenticated.subscribe(authenticated => {
			if (!authenticated) {
				goto('/login');
			}
		});

		const unsubUser = currentUser.subscribe(u => {
			user = u;
		});

		// Check push notification support
		checkPushSupport();

		return () => {
			unsubscribe();
			unsubUser();
		};
	});

	async function checkPushSupport() {
		if (!('serviceWorker' in navigator) || !('PushManager' in window)) {
			pushSupported = false;
			return;
		}

		pushSupported = true;

		// Check if already subscribed
		try {
			const registration = await navigator.serviceWorker.ready;
			const subscription = await registration.pushManager.getSubscription();
			pushEnabled = !!subscription;
		} catch (e) {
			console.error('Error checking push subscription:', e);
		}
	}

	async function togglePush() {
		if (pushLoading) return;
		pushLoading = true;

		try {
			const registration = await navigator.serviceWorker.ready;

			if (pushEnabled) {
				// Unsubscribe
				const subscription = await registration.pushManager.getSubscription();
				if (subscription) {
					await subscription.unsubscribe();
					await unsubscribePush(subscription.endpoint);
				}
				pushEnabled = false;
			} else {
				// Subscribe
				const vapidKey = await getVapidPublicKey();

				if (!vapidKey.publicKey) {
					alert('Push notifications non configurate sul server');
					return;
				}

				// Request permission
				const permission = await Notification.requestPermission();
				if (permission !== 'granted') {
					alert('Permesso notifiche negato');
					return;
				}

				// Subscribe
				const subscription = await registration.pushManager.subscribe({
					userVisibleOnly: true,
					applicationServerKey: urlBase64ToUint8Array(vapidKey.publicKey)
				});

				await subscribePush(subscription.toJSON());
				pushEnabled = true;
			}
		} catch (e) {
			console.error('Push toggle error:', e);
			alert('Errore: ' + e.message);
		} finally {
			pushLoading = false;
		}
	}

	function urlBase64ToUint8Array(base64String) {
		const padding = '='.repeat((4 - base64String.length % 4) % 4);
		const base64 = (base64String + padding)
			.replace(/-/g, '+')
			.replace(/_/g, '/');

		const rawData = window.atob(base64);
		const outputArray = new Uint8Array(rawData.length);

		for (let i = 0; i < rawData.length; ++i) {
			outputArray[i] = rawData.charCodeAt(i);
		}
		return outputArray;
	}

	function handleLogout() {
		if (confirm('Vuoi davvero uscire?')) {
			logout();
		}
	}

	function formatDate(dateStr) {
		if (!dateStr) return 'Mai';
		try {
			return new Date(dateStr).toLocaleDateString('it-IT', {
				day: 'numeric',
				month: 'long',
				year: 'numeric',
				hour: '2-digit',
				minute: '2-digit'
			});
		} catch {
			return dateStr;
		}
	}
</script>

<svelte:head>
	<title>Impostazioni - ThoughtCapture</title>
</svelte:head>

<main class="min-h-screen bg-[var(--bg-primary)]">
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-[var(--bg-primary)]/95 backdrop-blur border-b border-[var(--border)] px-4 py-3 pt-safe">
		<h1 class="text-lg font-semibold text-center">Impostazioni</h1>
	</header>

	<div class="p-4 max-w-lg mx-auto space-y-6">
		<!-- User Section -->
		{#if user}
			<section class="card p-4">
				<div class="flex items-center gap-4">
					<div class="w-14 h-14 rounded-full bg-gradient-to-br from-[var(--accent)] to-purple-600 flex items-center justify-center">
						<User class="w-7 h-7 text-white" />
					</div>
					<div class="flex-1 min-w-0">
						<h2 class="font-semibold text-white text-lg">{user.display_name || user.username}</h2>
						<p class="text-sm text-[var(--text-muted)]">@{user.username}</p>
					</div>
				</div>

				<div class="mt-4 pt-4 border-t border-[var(--border)] space-y-2">
					<div class="flex justify-between text-sm">
						<span class="text-[var(--text-secondary)]">Registrato</span>
						<span class="text-[var(--text-muted)]">{formatDate(user.created_at)}</span>
					</div>
					{#if user.last_login}
						<div class="flex justify-between text-sm">
							<span class="text-[var(--text-secondary)]">Ultimo accesso</span>
							<span class="text-[var(--text-muted)]">{formatDate(user.last_login)}</span>
						</div>
					{/if}
				</div>
			</section>
		{/if}

		<!-- Notifications Section -->
		<section class="card overflow-hidden">
			<h3 class="px-4 py-3 text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-tertiary)]">
				Notifiche
			</h3>

			{#if pushSupported}
				<button
					class="w-full flex items-center justify-between p-4 hover:bg-[var(--bg-tertiary)] transition-colors"
					on:click={togglePush}
					disabled={pushLoading}
				>
					<div class="flex items-center gap-3">
						{#if pushEnabled}
							<Bell class="w-5 h-5 text-[var(--success)]" />
						{:else}
							<BellOff class="w-5 h-5 text-[var(--text-muted)]" />
						{/if}
						<div class="text-left">
							<p class="font-medium text-white">Notifiche push</p>
							<p class="text-xs text-[var(--text-muted)]">
								{pushEnabled ? 'Attive' : 'Disattivate'}
							</p>
						</div>
					</div>

					{#if pushLoading}
						<Loader2 class="w-5 h-5 animate-spin text-[var(--text-muted)]" />
					{:else}
						<div class="w-12 h-6 rounded-full transition-colors {pushEnabled ? 'bg-[var(--success)]' : 'bg-[var(--bg-tertiary)]'}">
							<div class="w-5 h-5 rounded-full bg-white shadow-md transform transition-transform mt-0.5 {pushEnabled ? 'translate-x-6' : 'translate-x-0.5'}"></div>
						</div>
					{/if}
				</button>
			{:else}
				<div class="p-4 flex items-center gap-3 text-[var(--text-muted)]">
					<BellOff class="w-5 h-5" />
					<span class="text-sm">Notifiche push non supportate</span>
				</div>
			{/if}
		</section>

		<!-- App Info Section -->
		<section class="card overflow-hidden">
			<h3 class="px-4 py-3 text-sm font-medium text-[var(--text-secondary)] bg-[var(--bg-tertiary)]">
				App
			</h3>

			<div class="divide-y divide-[var(--border)]">
				<div class="flex items-center justify-between p-4">
					<div class="flex items-center gap-3">
						<Info class="w-5 h-5 text-[var(--text-muted)]" />
						<span class="text-white">Versione</span>
					</div>
					<span class="text-[var(--text-muted)]">1.0.0 PWA</span>
				</div>

				<a
					href="/"
					class="flex items-center justify-between p-4 hover:bg-[var(--bg-tertiary)] transition-colors"
				>
					<div class="flex items-center gap-3">
						<svg class="w-5 h-5 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h7" />
						</svg>
						<span class="text-white">Dashboard</span>
					</div>
					<ChevronRight class="w-5 h-5 text-[var(--text-muted)]" />
				</a>
			</div>
		</section>

		<!-- Logout -->
		<button
			class="w-full btn btn-danger"
			on:click={handleLogout}
		>
			<LogOut class="w-5 h-5" />
			<span>Esci</span>
		</button>

		<!-- Footer -->
		<p class="text-center text-xs text-[var(--text-muted)] pt-4">
			ThoughtCapture PWA<br/>
			Pensieri catturati, pronti da consumare
		</p>
	</div>
</main>
