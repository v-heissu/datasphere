<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Home, MessageSquarePlus, Search, Settings, User } from 'lucide-svelte';
	import { initAuth, isAuthenticated, authLoading, currentUser } from '$lib/auth.js';
	import InstallPrompt from '$lib/components/InstallPrompt.svelte';
	import '../app.css';

	// Pages that don't need auth
	const publicPages = ['/login'];

	// Pages that don't show bottom nav
	const noNavPages = ['/login', '/share'];

	$: currentPath = $page.url.pathname;
	$: showBottomNav = $isAuthenticated && !noNavPages.includes(currentPath);
	$: isPublicPage = publicPages.includes(currentPath);

	onMount(() => {
		initAuth();
	});

	// Auth guard
	$: if (!$authLoading && !$isAuthenticated && !isPublicPage) {
		goto('/login');
	}

	// Handle pending share after login
	$: if ($isAuthenticated && typeof window !== 'undefined') {
		try {
			const pendingShare = sessionStorage.getItem('pending_share');
			if (pendingShare) {
				sessionStorage.removeItem('pending_share');
				const shareData = JSON.parse(pendingShare);
				if (shareData.title || shareData.text || shareData.url) {
					const params = new URLSearchParams();
					if (shareData.title) params.set('title', shareData.title);
					if (shareData.text) params.set('text', shareData.text);
					if (shareData.url) params.set('url', shareData.url);
					if (shareData.hasImage) params.set('hasImage', shareData.hasImage);
					goto(`/chat?${params.toString()}`);
				}
			}
		} catch (e) {
			console.error('Failed to process pending share:', e);
		}
	}

	// Navigation items
	const navItems = [
		{ path: '/', icon: Home, label: 'Home' },
		{ path: '/chat', icon: MessageSquarePlus, label: 'Nuovo' },
		{ path: '/search', icon: Search, label: 'Cerca' },
		{ path: '/settings', icon: Settings, label: 'Impostazioni' }
	];
</script>

{#if $authLoading && !isPublicPage}
	<!-- Loading screen -->
	<div class="min-h-screen flex items-center justify-center bg-[var(--bg-primary)]">
		<div class="text-center">
			<div class="inline-flex p-4 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600 mb-4 animate-pulse">
				<svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
				</svg>
			</div>
			<p class="text-[var(--text-secondary)]">Caricamento...</p>
		</div>
	</div>
{:else}
	<!-- Main content -->
	<div class="min-h-screen {showBottomNav ? 'pb-[calc(80px+env(safe-area-inset-bottom))]' : ''}">
		<slot />
	</div>

	<!-- Bottom Navigation -->
	{#if showBottomNav}
		<nav class="fixed bottom-0 left-0 right-0 z-50 bg-[var(--bg-secondary)]/95 backdrop-blur-lg border-t border-[var(--border)] pb-safe">
			<div class="flex items-center justify-around h-16 max-w-lg mx-auto px-2">
				{#each navItems as item}
					<a
						href={item.path}
						class="flex flex-col items-center justify-center flex-1 h-full gap-1 transition-colors touch-feedback
							{currentPath === item.path ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] hover:text-white'}"
					>
						<svelte:component this={item.icon} class="w-5 h-5" />
						<span class="text-[10px] font-medium">{item.label}</span>
					</a>
				{/each}
			</div>
		</nav>
	{/if}

	<!-- Install PWA Prompt -->
	{#if $isAuthenticated}
		<InstallPrompt />
	{/if}
{/if}

<style>
	/* Smooth page transitions */
	:global(body) {
		overflow-x: hidden;
	}

	/* iOS safe area for bottom nav */
	.pb-safe {
		padding-bottom: env(safe-area-inset-bottom);
	}
</style>
