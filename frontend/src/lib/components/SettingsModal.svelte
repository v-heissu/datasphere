<script>
	import { createEventDispatcher, onMount } from 'svelte';
	import { X, Save, RotateCcw, Settings, User, Bot } from 'lucide-svelte';

	export let show = false;

	const dispatch = createEventDispatcher();

	let userBackground = '';
	let classifyPrompt = '';
	let loading = false;
	let saving = false;
	let activeTab = 'user';

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

	function close() {
		show = false;
		dispatch('close');
	}

	function handleKeydown(e) {
		if (e.key === 'Escape') close();
	}
</script>

<svelte:window on:keydown={handleKeydown} />

{#if show}
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
			<div class="flex border-b border-[var(--border)]">
				<button
					class="flex-1 px-6 py-3 text-sm font-medium transition-colors border-b-2 {activeTab === 'user'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'user')}
				>
					<User class="w-4 h-4 inline mr-2" />
					Profilo Utente
				</button>
				<button
					class="flex-1 px-6 py-3 text-sm font-medium transition-colors border-b-2 {activeTab === 'prompt'
						? 'border-[var(--accent)] text-[var(--accent)]'
						: 'border-transparent opacity-60 hover:opacity-100'}"
					on:click={() => (activeTab = 'prompt')}
				>
					<Bot class="w-4 h-4 inline mr-2" />
					System Prompt
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
				{:else}
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
