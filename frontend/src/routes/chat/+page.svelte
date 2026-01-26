<script>
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { Send, Image, X, Loader2, Camera, CheckCircle, AlertCircle } from 'lucide-svelte';
	import { isAuthenticated } from '$lib/auth.js';
	import { sendMessage, sendImage } from '$lib/api.js';

	let messageText = '';
	let imageFile = null;
	let imagePreview = null;
	let caption = '';
	let sending = false;
	let result = null;
	let error = null;
	let fileInput;

	// Type icons for results
	const typeIcons = {
		film: '🎬',
		book: '📚',
		concept: '💡',
		music: '🎵',
		art: '🎨',
		todo: '✓',
		other: '📌'
	};

	onMount(() => {
		// Check authentication
		const unsubscribe = isAuthenticated.subscribe(authenticated => {
			if (!authenticated) {
				goto('/login');
			}
		});

		// Handle share target data from URL
		const params = $page.url.searchParams;
		const sharedTitle = params.get('title');
		const sharedText = params.get('text');
		const sharedUrl = params.get('url');
		const hasImage = params.get('hasImage');

		if (sharedTitle || sharedText || sharedUrl) {
			let text = '';
			if (sharedTitle) text += sharedTitle;
			if (sharedText) text += (text ? '\n' : '') + sharedText;
			if (sharedUrl) text += (text ? '\n' : '') + sharedUrl;
			messageText = text.trim();
		}

		// Focus input
		setTimeout(() => {
			const input = document.getElementById('message-input');
			if (input) input.focus();
		}, 100);

		return unsubscribe;
	});

	function handleImageSelect(e) {
		const file = e.target.files?.[0];
		if (!file) return;

		if (!file.type.startsWith('image/')) {
			error = 'Seleziona un file immagine';
			return;
		}

		if (file.size > 10 * 1024 * 1024) {
			error = 'Immagine troppo grande (max 10MB)';
			return;
		}

		imageFile = file;
		error = null;

		// Create preview
		const reader = new FileReader();
		reader.onload = (e) => {
			imagePreview = e.target.result;
		};
		reader.readAsDataURL(file);
	}

	function clearImage() {
		imageFile = null;
		imagePreview = null;
		caption = '';
		if (fileInput) {
			fileInput.value = '';
		}
	}

	async function handleSend() {
		if (sending) return;

		// Validate input
		if (!imageFile && !messageText.trim()) {
			error = 'Scrivi un messaggio o seleziona un\'immagine';
			return;
		}

		sending = true;
		error = null;
		result = null;

		try {
			let response;

			if (imageFile) {
				// Send image
				response = await sendImage(imageFile, caption.trim() || null);
			} else {
				// Send text
				response = await sendMessage(messageText.trim());
			}

			if (response.success) {
				result = response.item;

				// Clear inputs after success
				messageText = '';
				clearImage();

				// Auto-clear result after 5 seconds
				setTimeout(() => {
					result = null;
				}, 5000);
			} else {
				error = response.error || 'Errore durante l\'invio';
			}
		} catch (e) {
			error = e.message || 'Errore durante l\'invio';
		} finally {
			sending = false;
		}
	}

	function handleKeyDown(e) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSend();
		}
	}
</script>

<svelte:head>
	<title>Nuovo pensiero - ThoughtCapture</title>
</svelte:head>

<main class="min-h-screen flex flex-col bg-[var(--bg-primary)]">
	<!-- Header -->
	<header class="sticky top-0 z-10 bg-[var(--bg-primary)]/95 backdrop-blur border-b border-[var(--border)] px-4 py-3 pt-safe">
		<h1 class="text-lg font-semibold text-center">Nuovo pensiero</h1>
	</header>

	<!-- Content -->
	<div class="flex-1 flex flex-col p-4 max-w-lg mx-auto w-full">
		<!-- Instructions -->
		<div class="mb-6 text-center">
			<p class="text-sm text-[var(--text-secondary)]">
				Scrivi un pensiero o condividi un'immagine.<br/>
				L'AI lo classificherà automaticamente.
			</p>
		</div>

		<!-- Result Card -->
		{#if result}
			<div class="card p-4 mb-4 border-[var(--success)]/50 animate-scale-in">
				<div class="flex items-start gap-3">
					<div class="p-2 rounded-lg bg-[var(--success)]/20">
						<CheckCircle class="w-5 h-5 text-[var(--success)]" />
					</div>
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-1">
							<span class="text-lg">{typeIcons[result.type] || '📌'}</span>
							<span class="font-medium text-white truncate">{result.title || 'Salvato'}</span>
						</div>
						{#if result.description}
							<p class="text-sm text-[var(--text-secondary)] line-clamp-2">{result.description}</p>
						{/if}
						<div class="flex items-center gap-3 mt-2 text-xs text-[var(--text-muted)]">
							<span class="capitalize">{result.type}</span>
							{#if result.estimated_minutes}
								<span>{result.estimated_minutes} min</span>
							{/if}
							{#if result.priority}
								<span>P{result.priority}</span>
							{/if}
						</div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Error -->
		{#if error}
			<div class="card p-4 mb-4 border-[var(--danger)]/50 bg-[var(--danger)]/10 animate-scale-in">
				<div class="flex items-center gap-3">
					<AlertCircle class="w-5 h-5 text-[var(--danger)] flex-shrink-0" />
					<p class="text-sm text-[var(--danger)]">{error}</p>
				</div>
			</div>
		{/if}

		<!-- Image Preview -->
		{#if imagePreview}
			<div class="relative mb-4 rounded-2xl overflow-hidden bg-[var(--bg-secondary)]">
				<img src={imagePreview} alt="Preview" class="w-full max-h-64 object-contain" />
				<button
					class="absolute top-2 right-2 p-2 rounded-full bg-black/60 text-white hover:bg-black/80 transition-colors"
					on:click={clearImage}
				>
					<X class="w-5 h-5" />
				</button>
			</div>

			<!-- Caption for image -->
			<div class="mb-4">
				<input
					type="text"
					bind:value={caption}
					placeholder="Aggiungi una descrizione (opzionale)"
					class="input"
					disabled={sending}
				/>
			</div>
		{/if}

		<!-- Input Area -->
		<div class="flex-1 flex flex-col justify-end">
			{#if !imageFile}
				<textarea
					id="message-input"
					bind:value={messageText}
					on:keydown={handleKeyDown}
					placeholder="Scrivi il tuo pensiero..."
					class="input resize-none min-h-[120px] mb-4"
					disabled={sending}
				></textarea>
			{/if}

			<!-- Actions -->
			<div class="flex items-center gap-3">
				<!-- Image button -->
				<input
					type="file"
					accept="image/*"
					class="hidden"
					bind:this={fileInput}
					on:change={handleImageSelect}
				/>

				<button
					class="btn btn-secondary btn-icon"
					on:click={() => fileInput.click()}
					disabled={sending}
					title="Aggiungi immagine"
				>
					{#if imageFile}
						<Camera class="w-5 h-5" />
					{:else}
						<Image class="w-5 h-5" />
					{/if}
				</button>

				<!-- Send button -->
				<button
					class="btn btn-primary flex-1"
					on:click={handleSend}
					disabled={sending || (!messageText.trim() && !imageFile)}
				>
					{#if sending}
						<Loader2 class="w-5 h-5 animate-spin" />
						<span>Elaborando...</span>
					{:else}
						<Send class="w-5 h-5" />
						<span>Invia</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
</main>
