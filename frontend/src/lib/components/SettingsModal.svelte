<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { X, Save, RotateCcw, Settings, User, Bot, Mail, Send, CheckCircle2, AlertCircle, Bug, Play } from 'lucide-svelte';

	export let show = false;

	const dispatch = createEventDispatcher();

	let userBackground = '';
	let classifyPrompt = '';
	let loading = false;
	let saving = false;
	let activeTab = 'user';
	let emailTesting = false;
	let emailResult = null;

	// Debug/Test API state
	let testInput = '';
	let testResult = null;
	let testing = false;

	const defaultClassifyPrompt = `Sei un assistente per una persona con ADHD che cattura pensieri velocemente.

USER BACKGROUND:
{user_background}

RECENT CONTEXT (ultimi 5 pensieri):
{recent_items}

INPUT UTENTE:
"{verbatim_input}"

TASK:
1. Classifica il tipo di pensiero
2. Estrai/inferisci il titolo corretto (es: se l'utente scrive "blade runner" -> "Blade Runner 2049" o "Blade Runner")
3. Suggerisci link utili (IMDb per film, Goodreads/Amazon per libri, Wikipedia per concetti, Spotify per musica)
4. Stima tempo necessario per consumare
5. Assegna priorità basata su interesse/urgenza

OUTPUT (JSON puro, senza markdown):
{
  "type": "film|book|concept|music|art|todo|other",
  "title": "titolo estratto/inferito",
  "description": "cosa significa questo pensiero (1-2 frasi)",
  "links": [
    {"url": "...", "type": "imdb|spotify|wikipedia|article|..."}
  ],
  "estimated_minutes": 30,
  "priority": 3,
  "tags": ["tag1", "tag2"],
  "consumption_suggestion": "come/quando consumarlo"
}

REGOLE:
- Sii generoso nell'interpretazione (preferisci classificare che "other")
- Se ambiguo, usa il background utente per disambiguare
- Trova almeno 1-2 link utili (IMDb, Spotify, Wikipedia, articoli, etc)
- Stima tempo realisticamente (film=120min, concept=15-30min, libro=varie ore)
- Priorità basata su: urgenza inferita, complessità, interesse utente
- Tag: max 3-4, semantici (es: "sci-fi", "philosophy", "ambient-music")
- RISPONDI SOLO CON IL JSON, niente altro testo prima o dopo`;

	onMount(async () => {
		if (show) await loadConfig();
	});

	$: if (show) loadConfig();

	async function loadConfig() {
		loading = true;
		try {
			const [bgRes, promptRes] = await Promise.all([
				fetch('/api/config/user_background'),
				fetch('/api/config/classify_prompt')
			]);

			const bgData = await bgRes.json();
			const promptData = await promptRes.json();

			userBackground = bgData.value || '';
			classifyPrompt = promptData.value || defaultClassifyPrompt;
		} catch (e) {
			console.error('Error loading config:', e);
		} finally {
			loading = false;
		}
	}

	async function saveConfig() {
		saving = true;
		try {
			await Promise.all([
				fetch('/api/config/user_background', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(userBackground)
				}),
				fetch('/api/config/classify_prompt', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(classifyPrompt)
				})
			]);

			dispatch('saved');
			close();
		} catch (e) {
			console.error('Error saving config:', e);
		} finally {
			saving = false;
		}
	}

	function resetPrompt() {
		classifyPrompt = defaultClassifyPrompt;
	}

	async function sendTestEmail() {
		emailTesting = true;
		emailResult = null;
		try {
			const res = await fetch('/api/email/test', { method: 'POST' });
			const data = await res.json();
			if (res.ok) {
				emailResult = { success: true, message: 'Email inviata con successo!' };
			} else {
				emailResult = { success: false, message: data.detail || 'Errore invio email' };
			}
		} catch (e) {
			emailResult = { success: false, message: 'Errore di connessione' };
		} finally {
			emailTesting = false;
		}
	}

	async function runApiTest() {
		if (!testInput.trim()) return;
		testing = true;
		testResult = null;
		try {
			const res = await fetch('/api/debug/test-classify', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ input: testInput })
			});
			testResult = await res.json();
		} catch (e) {
			testResult = { success: false, error: 'Errore di connessione: ' + e.message };
		} finally {
			testing = false;
		}
	}

	function close() {
		show = false;
		emailResult = null;
		dispatch('close');
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-static-element-interactions -->
	<div class="modal-backdrop animate-fade-in" on:click|self={close}>
		<div class="modal animate-scale-in">
			<!-- Header -->
			<div class="flex items-center justify-between p-6 border-b border-[var(--border)]">
				<div class="flex items-center gap-3">
					<div class="p-2 rounded-xl bg-[var(--accent)]/20">
						<Settings class="w-5 h-5 text-[var(--accent)]" />
					</div>
					<h2 class="text-xl font-bold">Impostazioni</h2>
				</div>
				<button class="btn btn-ghost btn-icon" on:click={close}>
					<X class="w-5 h-5" />
				</button>
			</div>

			<!-- Tabs -->
			<div class="flex border-b border-[var(--border)] overflow-x-auto">
				<button
					class="flex-1 px-4 sm:px-6 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap {activeTab === 'user'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'user')}
				>
					<User class="w-4 h-4 inline mr-1 sm:mr-2" />
					<span class="hidden sm:inline">Profilo Utente</span>
					<span class="sm:hidden">Profilo</span>
				</button>
				<button
					class="flex-1 px-4 sm:px-6 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap {activeTab === 'prompt'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'prompt')}
				>
					<Bot class="w-4 h-4 inline mr-1 sm:mr-2" />
					<span class="hidden sm:inline">System Prompt</span>
					<span class="sm:hidden">Prompt</span>
				</button>
				<button
					class="flex-1 px-4 sm:px-6 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap {activeTab === 'email'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'email')}
				>
					<Mail class="w-4 h-4 inline mr-1 sm:mr-2" />
					Email
				</button>
				<button
					class="flex-1 px-4 sm:px-6 py-3 text-sm font-medium transition-colors border-b-2 whitespace-nowrap {activeTab === 'debug'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'debug')}
				>
					<Bug class="w-4 h-4 inline mr-1 sm:mr-2" />
					<span class="hidden sm:inline">Debug API</span>
					<span class="sm:hidden">Debug</span>
				</button>
			</div>

			<!-- Content -->
			<div class="p-6">
				{#if loading}
					<div class="flex items-center justify-center py-12">
						<div class="w-8 h-8 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
					</div>
				{:else if activeTab === 'user'}
					<div class="space-y-4">
						<div>
							<label for="background" class="block text-sm font-medium mb-2 opacity-70">
								Il tuo profilo
							</label>
							<p class="text-xs opacity-50 mb-3">
								Descrivi i tuoi interessi, passioni, cose che ami e odi. Questo aiuta Claude a classificare meglio i tuoi pensieri.
							</p>
							<textarea
								id="background"
								bind:value={userBackground}
								class="textarea h-48"
								placeholder="Es: Amo cinema d'autore, sci-fi cerebrale tipo Blade Runner, musica elettronica ambient, filosofia continentale. Odio action stupidi e pop commerciale..."
							/>
						</div>
					</div>
				{:else if activeTab === 'prompt'}
					<div class="space-y-4">
						<div class="flex items-center justify-between">
							<div>
								<label for="prompt" class="block text-sm font-medium opacity-70">
									System Prompt per classificazione
								</label>
								<p class="text-xs opacity-50 mt-1">
									Modifica il prompt che Claude usa per classificare i tuoi pensieri
								</p>
							</div>
							<button class="btn btn-ghost btn-sm" on:click={resetPrompt} title="Ripristina default">
								<RotateCcw class="w-4 h-4" />
								Reset
							</button>
						</div>
						<textarea
							id="prompt"
							bind:value={classifyPrompt}
							class="textarea h-[400px] font-mono text-xs"
							placeholder="System prompt..."
						/>
						<p class="text-xs opacity-40">
							Variabili disponibili: {'{user_background}'}, {'{recent_items}'}, {'{verbatim_input}'}
						</p>
					</div>
				{:else if activeTab === 'email'}
					<div class="space-y-6">
						<div>
							<h3 class="text-sm font-medium mb-2">Weekly Digest</h3>
							<p class="text-xs opacity-50 mb-4">
								Ricevi un riepilogo settimanale via email con statistiche e ultimi pensieri catturati.
							</p>
						</div>

						<div class="card p-4 space-y-3">
							<div class="flex items-center justify-between gap-4">
								<div>
									<p class="text-sm font-medium">Test Email Digest</p>
									<p class="text-xs opacity-50">Invia subito una mail di test</p>
								</div>
								<button
									class="btn btn-primary btn-sm flex-shrink-0"
									on:click={sendTestEmail}
									disabled={emailTesting}
								>
									{#if emailTesting}
										<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
									{:else}
										<Send class="w-4 h-4" />
									{/if}
									Invia Test
								</button>
							</div>

							{#if emailResult}
								<div class="flex items-center gap-2 p-3 rounded-lg {emailResult.success ? 'bg-[var(--success)]/20' : 'bg-[var(--danger)]/20'}">
									{#if emailResult.success}
										<CheckCircle2 class="w-4 h-4 text-[var(--success)] flex-shrink-0" />
										<span class="text-sm text-[var(--success)]">{emailResult.message}</span>
									{:else}
										<AlertCircle class="w-4 h-4 text-[var(--danger)] flex-shrink-0" />
										<span class="text-sm text-[var(--danger)]">{emailResult.message}</span>
									{/if}
								</div>
							{/if}
						</div>

						<div class="text-xs opacity-40 space-y-2">
							<p>Variabili d'ambiente richieste nel server:</p>
							<code class="block p-3 bg-black/30 rounded text-[11px] leading-relaxed">
								EMAIL_ENABLED=true<br>
								EMAIL_USERNAME=tuaemail@gmail.com<br>
								EMAIL_PASSWORD=app_password<br>
								EMAIL_FROM=tuaemail@gmail.com<br>
								EMAIL_TO=destinatario@email.com<br>
								WEEKLY_DIGEST_DAY=sat<br>
								WEEKLY_DIGEST_TIME=08:00
							</code>
						</div>
					</div>
				{:else if activeTab === 'debug'}
					<div class="space-y-4">
						<div>
							<h3 class="text-sm font-medium mb-2">Test API Classification</h3>
							<p class="text-xs opacity-50 mb-4">
								Testa la chiamata API di classificazione e visualizza la risposta raw con metadata.
							</p>
						</div>

						<div class="flex gap-2">
							<input
								type="text"
								bind:value={testInput}
								class="input flex-1"
								placeholder="es: blade runner, faetooth milano..."
								on:keydown={(e) => e.key === 'Enter' && runApiTest()}
							/>
							<button
								class="btn btn-primary flex-shrink-0"
								on:click={runApiTest}
								disabled={testing || !testInput.trim()}
							>
								{#if testing}
									<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
								{:else}
									<Play class="w-4 h-4" />
								{/if}
								Test
							</button>
						</div>

						{#if testResult}
							<div class="space-y-3">
								<!-- Status -->
								<div class="flex items-center gap-2">
									{#if testResult.success}
										<CheckCircle2 class="w-4 h-4 text-[var(--success)]" />
										<span class="text-sm text-[var(--success)]">Chiamata riuscita</span>
									{:else}
										<AlertCircle class="w-4 h-4 text-[var(--danger)]" />
										<span class="text-sm text-[var(--danger)]">Errore</span>
									{/if}
									{#if testResult.provider}
										<span class="text-xs opacity-50">Provider: {testResult.provider}</span>
									{/if}
									{#if testResult.model}
										<span class="text-xs opacity-50">Model: {testResult.model}</span>
									{/if}
								</div>

								<!-- Error -->
								{#if testResult.error}
									<div class="p-3 bg-[var(--danger)]/20 rounded-lg">
										<p class="text-sm text-[var(--danger)] font-mono break-all">
											{testResult.error_type ? `[${testResult.error_type}] ` : ''}{testResult.error}
										</p>
									</div>
								{/if}

								<!-- Grounding Metadata -->
								{#if testResult.grounding_metadata}
									<div class="card p-3 space-y-2">
										<h4 class="text-xs font-medium opacity-70">🔍 Grounding Metadata</h4>
										{#if testResult.grounding_metadata.search_queries?.length}
											<div>
												<span class="text-xs opacity-50">Search queries:</span>
												<div class="flex flex-wrap gap-1 mt-1">
													{#each testResult.grounding_metadata.search_queries as query}
														<span class="px-2 py-0.5 bg-[var(--accent)]/20 rounded text-xs">{query}</span>
													{/each}
												</div>
											</div>
										{/if}
										{#if testResult.grounding_metadata.sources?.length}
											<div>
												<span class="text-xs opacity-50">Sources ({testResult.grounding_metadata.grounding_chunks} chunks):</span>
												<ul class="mt-1 space-y-1">
													{#each testResult.grounding_metadata.sources as source}
														<li class="text-xs">
															<a href={source.uri} target="_blank" class="text-[var(--accent)] hover:underline">
																{source.title || source.uri}
															</a>
														</li>
													{/each}
												</ul>
											</div>
										{/if}
									</div>
								{/if}

								<!-- Parsed JSON -->
								{#if testResult.parsed_json}
									<div class="card p-3 space-y-2">
										<h4 class="text-xs font-medium opacity-70">✅ Parsed JSON</h4>
										<pre class="text-xs font-mono bg-black/30 p-3 rounded overflow-x-auto max-h-48 overflow-y-auto">{JSON.stringify(testResult.parsed_json, null, 2)}</pre>
									</div>
								{/if}

								<!-- Raw Response -->
								{#if testResult.raw_response}
									<details class="card p-3">
										<summary class="text-xs font-medium opacity-70 cursor-pointer">📄 Raw Response</summary>
										<pre class="text-xs font-mono bg-black/30 p-3 rounded overflow-x-auto max-h-48 overflow-y-auto mt-2 whitespace-pre-wrap break-all">{testResult.raw_response}</pre>
									</details>
								{/if}

								<!-- Prompt Preview -->
								{#if testResult.prompt_preview}
									<details class="card p-3">
										<summary class="text-xs font-medium opacity-70 cursor-pointer">📝 Prompt Preview</summary>
										<pre class="text-xs font-mono bg-black/30 p-3 rounded overflow-x-auto max-h-48 overflow-y-auto mt-2 whitespace-pre-wrap">{testResult.prompt_preview}</pre>
									</details>
								{/if}
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex items-center justify-end gap-3 p-6 border-t border-[var(--border)]">
				<button class="btn btn-secondary" on:click={close}>Annulla</button>
				<button class="btn btn-primary" on:click={saveConfig} disabled={saving}>
					{#if saving}
						<div class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
					{:else}
						<Save class="w-4 h-4" />
					{/if}
					Salva
				</button>
			</div>
		</div>
	</div>
{/if}
