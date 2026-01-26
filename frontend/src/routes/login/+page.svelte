<script>
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { Brain, Eye, EyeOff, Loader2 } from 'lucide-svelte';
	import { login, register, isAuthenticated, authLoading, authError } from '$lib/auth.js';

	let mode = 'login'; // 'login' or 'register'
	let username = '';
	let password = '';
	let displayName = '';
	let showPassword = false;
	let loading = false;
	let error = null;

	onMount(() => {
		// Redirect if already authenticated
		const unsubscribe = isAuthenticated.subscribe(authenticated => {
			if (authenticated) {
				goto('/');
			}
		});

		return unsubscribe;
	});

	async function handleSubmit() {
		if (!username.trim() || !password.trim()) {
			error = 'Inserisci username e password';
			return;
		}

		if (mode === 'register' && password.length < 6) {
			error = 'La password deve essere almeno 6 caratteri';
			return;
		}

		loading = true;
		error = null;

		try {
			let result;
			if (mode === 'login') {
				result = await login(username.trim(), password);
			} else {
				result = await register(username.trim(), password, displayName.trim() || null);
			}

			if (result.success) {
				goto('/');
			} else {
				error = result.error;
			}
		} catch (e) {
			error = e.message || 'Errore durante l\'autenticazione';
		} finally {
			loading = false;
		}
	}

	function toggleMode() {
		mode = mode === 'login' ? 'register' : 'login';
		error = null;
	}
</script>

<svelte:head>
	<title>{mode === 'login' ? 'Accedi' : 'Registrati'} - ThoughtCapture</title>
</svelte:head>

<main class="min-h-screen flex flex-col items-center justify-center p-4 bg-[var(--bg-primary)]">
	<div class="w-full max-w-sm">
		<!-- Logo -->
		<div class="text-center mb-8">
			<div class="inline-flex p-4 rounded-2xl bg-gradient-to-br from-[var(--accent)] to-purple-600 mb-4">
				<Brain class="w-12 h-12 text-white" />
			</div>
			<h1 class="text-2xl font-bold text-white">ThoughtCapture</h1>
			<p class="text-sm text-[var(--text-secondary)] mt-1">
				Cattura i tuoi pensieri con AI
			</p>
		</div>

		<!-- Form Card -->
		<div class="card p-6">
			<h2 class="text-xl font-semibold text-white mb-6 text-center">
				{mode === 'login' ? 'Accedi' : 'Crea account'}
			</h2>

			<form on:submit|preventDefault={handleSubmit} class="space-y-4">
				<!-- Username -->
				<div>
					<label for="username" class="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
						Username
					</label>
					<input
						id="username"
						type="text"
						bind:value={username}
						placeholder="Il tuo username"
						class="input"
						autocomplete="username"
						autocapitalize="none"
						disabled={loading}
					/>
				</div>

				<!-- Display Name (solo per registrazione) -->
				{#if mode === 'register'}
					<div>
						<label for="displayName" class="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
							Nome visualizzato <span class="opacity-50">(opzionale)</span>
						</label>
						<input
							id="displayName"
							type="text"
							bind:value={displayName}
							placeholder="Come vuoi essere chiamato"
							class="input"
							autocomplete="name"
							disabled={loading}
						/>
					</div>
				{/if}

				<!-- Password -->
				<div>
					<label for="password" class="block text-sm font-medium text-[var(--text-secondary)] mb-1.5">
						Password
					</label>
					<div class="relative">
						{#if showPassword}
							<input
								id="password"
								type="text"
								bind:value={password}
								placeholder={mode === 'register' ? 'Minimo 6 caratteri' : 'La tua password'}
								class="input pr-12"
								autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
								disabled={loading}
							/>
						{:else}
							<input
								id="password"
								type="password"
								bind:value={password}
								placeholder={mode === 'register' ? 'Minimo 6 caratteri' : 'La tua password'}
								class="input pr-12"
								autocomplete={mode === 'login' ? 'current-password' : 'new-password'}
								disabled={loading}
							/>
						{/if}
						<button
							type="button"
							class="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[var(--text-muted)] hover:text-white transition-colors"
							on:click={() => showPassword = !showPassword}
						>
							{#if showPassword}
								<EyeOff class="w-5 h-5" />
							{:else}
								<Eye class="w-5 h-5" />
							{/if}
						</button>
					</div>
				</div>

				<!-- Error -->
				{#if error}
					<div class="p-3 rounded-lg bg-[var(--danger)]/10 border border-[var(--danger)]/30 text-[var(--danger)] text-sm">
						{error}
					</div>
				{/if}

				<!-- Submit Button -->
				<button
					type="submit"
					class="btn btn-primary w-full"
					disabled={loading}
				>
					{#if loading}
						<Loader2 class="w-5 h-5 animate-spin" />
						<span>{mode === 'login' ? 'Accesso...' : 'Registrazione...'}</span>
					{:else}
						<span>{mode === 'login' ? 'Accedi' : 'Crea account'}</span>
					{/if}
				</button>
			</form>

			<!-- Toggle Mode -->
			<div class="mt-6 text-center">
				<p class="text-sm text-[var(--text-secondary)]">
					{mode === 'login' ? 'Non hai un account?' : 'Hai già un account?'}
					<button
						type="button"
						class="text-[var(--accent)] hover:underline ml-1 font-medium"
						on:click={toggleMode}
					>
						{mode === 'login' ? 'Registrati' : 'Accedi'}
					</button>
				</p>
			</div>
		</div>

		<!-- Footer -->
		<p class="text-center text-xs text-[var(--text-muted)] mt-6">
			Pensieri catturati, pronti da consumare
		</p>
	</div>
</main>
