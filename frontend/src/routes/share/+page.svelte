<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { Loader2 } from 'lucide-svelte';
	import { isAuthenticated } from '$lib/auth.js';

	let redirecting = true;

	onMount(() => {
		// Check authentication first
		const unsubAuthscribe = isAuthenticated.subscribe(authenticated => {
			if (!authenticated) {
				// Store share data and redirect to login
				const params = $page.url.searchParams;
				const shareData = {
					title: params.get('title'),
					text: params.get('text'),
					url: params.get('url'),
					hasImage: params.get('hasImage')
				};

				// Store in sessionStorage for after login
				try {
					sessionStorage.setItem('pending_share', JSON.stringify(shareData));
				} catch (e) {
					console.error('Failed to store share data:', e);
				}

				goto('/login');
			} else {
				// Redirect to chat with share params
				const searchParams = $page.url.searchParams;
				goto(`/chat?${searchParams.toString()}`);
			}
		});

		return unsubAuthscribe;
	});
</script>

<svelte:head>
	<title>Condivisione - ThoughtCapture</title>
</svelte:head>

<main class="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
	<div class="text-center p-4">
		<Loader2 class="w-10 h-10 animate-spin mx-auto text-[var(--accent)] mb-4" />
		<p class="text-[var(--text-secondary)]">Elaborazione condivisione...</p>
	</div>
</main>
