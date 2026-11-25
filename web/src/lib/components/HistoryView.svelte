<script lang="ts">
	import { Search, Trash2, ChevronRight, ChevronLeft, MessageSquare, Loader2, RefreshCw, Plus } from 'lucide-svelte';
	import type { Language, SessionSummary, SessionsResponse } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { appState } from '$lib/state.svelte';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { PUBLIC_API_ENDPOIT } from '$env/static/public';

	interface Props {
		language: Language;
	}

	let { language }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	// ── State ────────────────────────────────────────────────────────────────
	let sessions = $state<SessionSummary[]>([]);
	let isLoading = $state(true);
	let errorMsg = $state<string | null>(null);
	let searchQuery = $state('');
	let deletingId = $state<string | null>(null);

	// ── Data fetching ─────────────────────────────────────────────────────────
	async function loadSessions() {
		isLoading = true;
		errorMsg = null;
		try {
			const res = await fetch(`${PUBLIC_API_ENDPOIT}/conversations`);
			if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
			const data: SessionsResponse = await res.json();
			sessions = data.sessions;
		} catch (e: any) {
			errorMsg = e.message || t('historyError');
		} finally {
			isLoading = false;
		}
	}

	onMount(loadSessions);

	// ── Filtering ─────────────────────────────────────────────────────────────
	const filteredSessions = $derived(
		searchQuery.trim()
			? sessions.filter((s) =>
					s.first_query.toLowerCase().includes(searchQuery.trim().toLowerCase())
				)
			: sessions
	);

	// ── Date grouping ─────────────────────────────────────────────────────────
	function getDateGroup(isoTs: string): string {
		const d = new Date(isoTs);
		const now = new Date();
		const todayStr = now.toDateString();
		const yestDate = new Date(now);
		yestDate.setDate(yestDate.getDate() - 1);
		const yestStr = yestDate.toDateString();
		if (d.toDateString() === todayStr) return t('today');
		if (d.toDateString() === yestStr) return t('yesterday');
		return t('eariler');
	}

	const groupedSessions = $derived(() => {
		const groups: Record<string, SessionSummary[]> = {};
		for (const s of filteredSessions) {
			const group = getDateGroup(s.last_active);
			if (!groups[group]) groups[group] = [];
			groups[group].push(s);
		}
		const order = [t('today'), t('yesterday'), t('eariler')];
		return order
			.filter((g) => groups[g]?.length)
			.map((g) => ({ group: g, items: groups[g] }));
	});

	// ── Formatting ────────────────────────────────────────────────────────────
	function formatTime(isoTs: string): string {
		return new Date(isoTs).toLocaleTimeString(language === 'ar' ? 'ar-MA' : 'fr-MA', {
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatDate(isoTs: string): string {
		return new Date(isoTs).toLocaleDateString(language === 'ar' ? 'ar-MA' : 'fr-MA', {
			day: 'numeric',
			month: 'short'
		});
	}

	function isToday(isoTs: string): boolean {
		return new Date(isoTs).toDateString() === new Date().toDateString();
	}

	// ── Actions ───────────────────────────────────────────────────────────────

	/** Navigate to the results page to view the stored Q&A from DB */
	function handleView(session: SessionSummary) {
		goto(`/results?session_id=${encodeURIComponent(session.session_id)}`);
	}

	async function handleDeleteSession(session: SessionSummary) {
		deletingId = session.session_id;
		try {
			const res = await fetch(`${PUBLIC_API_ENDPOIT}/conversations/${session.session_id}`, {
				method: 'DELETE'
			});
			if (!res.ok) throw new Error(`${res.status}`);
			sessions = sessions.filter((s) => s.session_id !== session.session_id);
		} catch (e: any) {
			errorMsg = `${isRTL ? 'فشل الحذف:' : 'Delete failed:'} ${e.message}`;
		} finally {
			deletingId = null;
		}
	}

	async function handleClearAll() {
		const confirmed = confirm(
			language === 'ar'
				? 'هل أنت متأكد من مسح جميع سجلات المحادثات؟'
				: "Êtes-vous sûr de vouloir effacer tout l'historique ?"
		);
		if (!confirmed) return;
		for (const session of [...sessions]) {
			await fetch(`${PUBLIC_API_ENDPOIT}/conversations/${session.session_id}`, {
				method: 'DELETE'
			});
		}
		sessions = [];
	}

	function handleNewQuestion() {
		goto('/');
	}
</script>

<div class="flex-1 w-full max-w-4xl mx-auto px-4 py-8 space-y-6" dir={isRTL ? 'rtl' : 'ltr'}>
	<!-- Header -->
	<div class="flex items-center justify-between border-b border-sandstone-border pb-4">
		<h2 class="text-2xl font-bold text-slate-900 font-serif">{t('history')}</h2>
		<div class="flex items-center gap-2">
			<!-- New question shortcut -->
			<button
				onclick={handleNewQuestion}
				class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/10 rounded-md transition-colors border border-primary/30"
			>
				<Plus class="h-4 w-4" />
				{t('newSession')}
			</button>
			<!-- Refresh -->
			<button
				onclick={loadSessions}
				class="p-2 text-slate-500 hover:bg-slate-100 rounded-md transition-colors"
				title={isRTL ? 'تحديث' : 'Refresh'}
			>
				<RefreshCw class="h-4 w-4" />
			</button>
			<!-- Clear all -->
			{#if sessions.length > 0}
				<button
					onclick={handleClearAll}
					class="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50 rounded-md transition-colors"
				>
					<Trash2 class="h-4 w-4" />
					{t('clearHistory')}
				</button>
			{/if}
		</div>
	</div>

	<!-- Search -->
	<div class="relative mb-6">
		<div
			class={`absolute inset-y-0 ${isRTL ? 'right-0 pr-3' : 'left-0 pl-3'} flex items-center pointer-events-none`}
		>
			<Search class="h-5 w-5 text-slate-400" />
		</div>
		<input
			type="text"
			bind:value={searchQuery}
			class={`block w-full rounded-lg border border-sandstone-border py-3 ${isRTL ? 'pr-10 pl-3' : 'pl-10 pr-3'} text-sm placeholder-slate-400 focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary bg-white`}
			placeholder={t('searchHistory')}
		/>
	</div>

	<!-- Loading -->
	{#if isLoading}
		<div class="flex flex-col items-center justify-center py-20 text-slate-400 gap-4">
			<Loader2 class="h-10 w-10 animate-spin text-primary/60" />
			<p class="text-sm">{t('historyLoading')}</p>
		</div>

	<!-- Error -->
	{:else if errorMsg}
		<div class="flex flex-col items-center justify-center py-16 gap-4 text-center">
			<div class="p-4 bg-red-50 rounded-xl border border-red-200 max-w-md">
				<p class="text-red-700 text-sm">{errorMsg}</p>
				<button
					onclick={loadSessions}
					class="mt-3 px-4 py-2 text-sm bg-red-100 hover:bg-red-200 text-red-700 rounded-lg transition-colors font-medium"
				>
					{isRTL ? 'إعادة المحاولة' : 'Réessayer'}
				</button>
			</div>
		</div>

	<!-- Empty -->
	{:else if filteredSessions.length === 0}
		<div class="flex flex-col items-center justify-center py-20 text-slate-400 gap-4">
			<div class="w-16 h-16 rounded-full bg-sandstone flex items-center justify-center">
				<MessageSquare class="h-8 w-8 text-slate-300" />
			</div>
			<p class="text-base font-medium text-slate-500">
				{searchQuery
					? isRTL
						? 'لا توجد نتائج مطابقة'
						: 'Aucun résultat trouvé'
					: t('historyEmpty')}
			</p>
			{#if !searchQuery}
				<button
					onclick={handleNewQuestion}
					class="px-5 py-2.5 bg-primary text-white rounded-full text-sm font-semibold hover:opacity-90 transition-opacity"
				>
					{t('newSessionTitle')}
				</button>
			{/if}
		</div>

	<!-- Session list -->
	{:else}
		<div class="space-y-8">
			{#each groupedSessions() as grp (grp.group)}
				<div class="space-y-3">
					<h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider px-1">
						{grp.group}
					</h3>
					<div
						class="bg-white rounded-xl shadow-sm border border-sandstone-border overflow-hidden divide-y divide-sandstone-border"
					>
						{#each grp.items as session (session.session_id)}
							<div
								class="p-4 flex items-center justify-between hover:bg-slate-50 transition-colors group/item cursor-pointer"
								role="button"
								tabindex="0"
								onclick={() => handleView(session)}
								onkeydown={(e) => e.key === 'Enter' && handleView(session)}
							>
								<!-- Left: info -->
								<div class="flex items-start gap-4 min-w-0 flex-1">
									<div
										class="mt-0.5 shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center"
									>
										<MessageSquare class="h-4 w-4 text-primary" />
									</div>
									<div class="min-w-0 flex-1">
										<!-- Query text -->
										<h4
											class="text-slate-800 font-medium group-hover/item:text-primary transition-colors line-clamp-2 text-sm leading-snug"
											dir="auto"
										>
											{session.first_query}
										</h4>
										<!-- Meta -->
										<div class="flex items-center flex-wrap text-xs text-slate-400 mt-1.5 gap-2">
											<span class="font-mono">
												{isToday(session.last_active)
													? formatTime(session.last_active)
													: formatDate(session.last_active)}
											</span>
											<span>·</span>
											<span class="bg-slate-100 px-2 py-0.5 rounded text-slate-600">
												{isRTL ? 'مصدر' : 'sources'}: {Math.floor(session.turn_count / 2)}
											</span>
										</div>
									</div>
								</div>

								<!-- Right: actions -->
								<div class="flex items-center gap-1 shrink-0 ms-3">
									<!-- Delete (stop click from bubbling to row) -->
									<button
										onclick={(e) => { e.stopPropagation(); handleDeleteSession(session); }}
										disabled={deletingId === session.session_id}
										class="p-2 text-slate-300 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover/item:opacity-100"
										title={t('deleteSession')}
									>
										{#if deletingId === session.session_id}
											<Loader2 class="h-4 w-4 animate-spin" />
										{:else}
											<Trash2 class="h-4 w-4" />
										{/if}
									</button>

									<!-- View chevron -->
									<span class="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-primary opacity-0 group-hover/item:opacity-100 transition-opacity">
										{t('view')}
										{#if isRTL}
											<ChevronLeft class="h-3.5 w-3.5" />
										{:else}
											<ChevronRight class="h-3.5 w-3.5" />
										{/if}
									</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>
