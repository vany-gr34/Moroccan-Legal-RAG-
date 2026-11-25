<script lang="ts">
	import { getTranslation } from '$lib/i18n';
	import { appState } from '$lib/state.svelte';
	import type { RawSearchRequest, RawSearchResponse, LawsResponse } from '$lib/types';
	import RawResultCard from '$lib/components/RawResultCard.svelte';
	import { Search, Loader2, Database, Zap, BarChart3, Clock, Sparkles } from 'lucide-svelte';
	import { PUBLIC_API_ENDPOIT } from '$env/static/public';
	import { onMount } from 'svelte';

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(appState.language, key);
	const isRTL = $derived(appState.language === 'ar');

	let query = $state('');
	let domain = $state('');
	let top_k = $state(5);
	let strategy = $state<'dense' | 'bm25' | 'rrf'>('rrf');

	let isLoading = $state(false);
	let response = $state<RawSearchResponse | null>(null);
	let errorMsg = $state<string | null>(null);
	let hasSearched = $state(false);

	let activeDomainValues = $state<string[]>([]);
	let isFetchingDomains = $state(true);

	// ── Example queries from benchmark dataset ──
	const exampleQueries = $derived([
		isRTL
			? 'ما هي الأفعال التي تعتبر جرائم إرهابية حسب القانون المغربي؟'
			: 'Actes considérés comme crimes terroristes au Maroc',
		isRTL
			? 'ما هي الحالات التي يجب فيها توقيف المركبة حسب قانون السير؟'
			: "Cas d'immobilisation du véhicule code de la route",
		isRTL
			? 'هل يمكن للمحكمة دعوة الأطراف إلى الوساطة لحل النزاع المدني؟'
			: 'Médiation judiciaire au Maroc',
		isRTL
			? 'ما هي المعلومات التي يجب تضمينها في التصريح بالتسجيل في السجل التجاري؟'
			: "Déclaration d'immatriculation registre du commerce",
		isRTL
			? 'متى تفتتح السنة القضائية في المغرب ومن يرأس الجلسة؟'
			: "Ouverture de l'année judiciaire au Maroc",
		isRTL
			? 'ما هي العائدات غير الخاضعة لضريبة الدخل حسب المدونة العامة للضرائب؟'
			: "Revenus exonérés de l'impôt sur le revenu",
		isRTL
			? 'ماهي الشروط التي تجعل الطفل في وضعية صعبة حسب القانون الجنائي؟'
			: 'Enfant en situation difficile code pénal',
		isRTL
			? 'ما هي آجال الأداء في المعاملات التجارية بين التجار؟'
			: 'Délais de paiement transactions commerciales'
	]);

	onMount(async () => {
		try {
			const res = await fetch(PUBLIC_API_ENDPOIT + '/laws');
			if (res.ok) {
				const data: LawsResponse = await res.json();
				activeDomainValues = Array.from(new Set(data.laws.map((l) => l.domain)));
			}
		} catch (e) {
			console.error('Failed to fetch domains', e);
		} finally {
			isFetchingDomains = false;
		}
	});

	// ── Domain color mapping ──
	const domainColor = (value: string): string => {
		const map: Record<string, string> = {
			'': '#1A237E',
			criminal: '#b91c1c',
			traffic: '#b45309',
			family: '#7c3aed',
			civil: '#0369a1',
			commercial: '#0f766e',
			procedure: '#475569',
			violations: '#b91c1c'
		};
		return map[value] || '#1A237E';
	};

	const allPossibleDomains = $derived([
		{ value: '', label: t('allDomains'), icon: '🗂️' },
		{ value: 'criminal', label: t('domainCriminal'), icon: '⚖️' },
		{ value: 'traffic', label: t('domainTraffic'), icon: '🚦' },
		{ value: 'family', label: t('domainFamily'), icon: '👨‍👩‍👧' },
		{ value: 'civil', label: t('domainCivil'), icon: '📋' },
		{ value: 'commercial', label: t('domainCommercial'), icon: '🏪' },
		{ value: 'procedure', label: t('domainProcedure'), icon: '📁' },
		{ value: 'violations', label: t('domainOffenses'), icon: '🚫' }
	]);

	const domains = $derived([
		allPossibleDomains[0],
		...activeDomainValues.map(
			(val) =>
				allPossibleDomains.find((d) => d.value === val) ?? { value: val, label: val, icon: '📁' }
		)
	]);

	const strategies = $derived([
		{
			value: 'rrf',
			label: 'Hybrid (RRF)',
			description: isRTL ? 'دمج النتائج المعنوية والكلمات المفتاحية' : 'Best of both worlds',
			icon: Zap
		},
		{
			value: 'dense',
			label: 'Dense',
			description: isRTL ? 'بحث دلالي معنوي' : 'Semantic search',
			icon: BarChart3
		},
		{
			value: 'bm25',
			label: 'BM25',
			description: isRTL ? 'مطابقة الكلمات المفتاحية' : 'Keyword matching',
			icon: Search
		}
	]);

	const selectedDomain = $derived(domains.find((d) => d.value === domain) ?? domains[0]);
	const selectedStrategy = $derived(strategies.find((s) => s.value === strategy) ?? strategies[0]);

	async function performSearch() {
		if (!query.trim()) return;

		isLoading = true;
		errorMsg = null;
		response = null;
		hasSearched = true;

		const requestBody: RawSearchRequest = { query, top_k, strategy };
		if (domain) requestBody.domain = domain;

		try {
			const res = await fetch(PUBLIC_API_ENDPOIT + '/search', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(requestBody)
			});
			if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
			response = await res.json();
		} catch (err: any) {
			errorMsg = err.message || 'An error occurred while fetching the results.';
		} finally {
			isLoading = false;
		}
	}

	function fillExample(q: string) {
		query = q;
	}
</script>

<svelte:head>
	<title>{t('exploreData')} - Maroc Légal</title>
</svelte:head>

<div class="flex flex-1 overflow-hidden">
	<!-- ══ Left Sidebar: Search Controls ══════════════════════════════════ -->
	<aside
		class="flex w-72 shrink-0 flex-col overflow-y-auto border-e border-sandstone-border bg-surface-2"
	>
		<!-- Header -->
		<div class="shrink-0 border-b border-sandstone-border bg-surface-1 px-6 pt-6 pb-4">
			<div class="mb-1 flex items-center gap-3">
				<div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary">
					<Database class="text-white" size={16} />
				</div>
				<h1 class="text-base font-bold text-primary">{t('exploreData')}</h1>
			</div>
			<p class="text-start text-xs text-slate-500">
				{isRTL ? 'استكشاف النصوص القانونية الخام' : 'Browse raw legal texts from the KB'}
			</p>
		</div>

		<form
			class="flex flex-1 flex-col gap-5 px-5 py-5"
			onsubmit={(e) => {
				e.preventDefault();
				performSearch();
			}}
		>
			<!-- Query Input -->
			<div class="flex flex-col gap-1.5">
				<label
					for="explore-query"
					class="text-xs font-bold tracking-wider text-slate-600 uppercase"
				>
					{t('yourQuestion')}
				</label>
				<div class="relative">
					<textarea
						id="explore-query"
						bind:value={query}
						rows="4"
						dir="auto"
						placeholder={isRTL
							? 'اكتب سؤالاً قانونياً بالعربية...'
							: 'Enter your legal question...'}
						class="w-full resize-none rounded-xl border border-sandstone-border bg-white p-3 text-sm text-slate-800 transition-all placeholder:text-slate-400 focus:border-primary focus:ring-2 focus:ring-primary/30 focus:outline-none"
					></textarea>
					{#if query.length > 0}
						<span
							class="absolute bottom-2 {isRTL
								? 'left-2'
								: 'right-2'} text-[10px] font-medium text-slate-400"
						>
							{query.length}
						</span>
					{/if}
				</div>
				<!-- Keyboard shortcut hint -->
				<span class="text-[10px] text-slate-400 {isRTL ? 'text-start' : 'text-start'}">
					{isRTL
						? '↵ للإرسال · Shift+↵ لسطر جديد'
						: '↵ pour chercher · Shift+↵ pour nouvelle ligne'}
				</span>
			</div>

			<!-- Domain / KB Selection -->
			<div class="flex flex-col gap-2">
				<span class="text-xs font-bold tracking-wider text-slate-600 uppercase">{t('domains')}</span
				>
				<div class="flex flex-col gap-1">
					{#each domains as d}
						{@const color = domainColor(d.value)}
						<button
							type="button"
							onclick={() => (domain = d.value)}
							class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-start text-sm transition-all
								{domain === d.value
								? 'font-semibold text-white shadow-sm'
								: 'text-slate-700 hover:bg-surface-1 hover:text-primary'}"
							style={domain === d.value ? `background: ${color}` : ''}
						>
							<span class="text-base leading-none">{d.icon}</span>
							<span>{d.label}</span>
							{#if domain === d.value}
								<span class="ms-auto text-[10px] text-white/60">✓</span>
							{/if}
						</button>
					{/each}
				</div>
			</div>

			<!-- Strategy Selector -->
			<div class="flex flex-col gap-2">
				<span class="text-xs font-bold tracking-wider text-slate-600 uppercase"
					>{t('strategy')}</span
				>
				<div class="flex flex-col gap-1.5">
					{#each strategies as s}
						{@const Icon = s.icon}
						<button
							type="button"
							onclick={() => (strategy = s.value as typeof strategy)}
							class="flex items-start gap-3 rounded-lg border px-3 py-2.5 text-start text-sm transition-all
								{strategy === s.value
								? 'border-primary bg-white text-primary shadow-sm'
								: 'border-sandstone-border bg-surface-1 text-slate-600 hover:border-primary/40 hover:bg-surface-2'}"
						>
							<Icon size={15} class="mt-0.5 shrink-0" />
							<div class="flex flex-col leading-tight">
								<span class="text-xs font-semibold">{s.label}</span>
								<span class="mt-0.5 text-[11px] opacity-70">{s.description}</span>
							</div>
						</button>
					{/each}
				</div>
			</div>

			<!-- Top K -->
			<div class="flex flex-col gap-1.5">
				<label for="explore-topk" class="text-xs font-bold tracking-wider text-slate-600 uppercase">
					{t('topK')} <span class="font-normal normal-case opacity-60">(1–20)</span>
				</label>
				<div
					class="flex items-center gap-3 rounded-lg border border-sandstone-border bg-surface-1 px-3 py-2"
				>
					<input
						type="range"
						id="explore-topk"
						bind:value={top_k}
						min="1"
						max="20"
						class="flex-1 accent-primary"
					/>
					<span class="w-6 shrink-0 text-center text-sm font-bold text-primary">{top_k}</span>
				</div>
			</div>

			<!-- Submit Button -->
			<button
				type="submit"
				disabled={isLoading || !query.trim()}
				class="mt-auto flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 font-bold text-white shadow-sm transition-all hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)] disabled:cursor-not-allowed disabled:opacity-40"
			>
				{#if isLoading}
					<Loader2 size={16} class="animate-spin" />
					<span>{isRTL ? 'جارٍ البحث...' : 'Searching...'}</span>
				{:else}
					<Search size={16} />
					<span>{t('searchButton')}</span>
				{/if}
			</button>
		</form>
	</aside>

	<!-- ══ Main Area: Results ══════════════════════════════════════════════ -->
	<main class="flex flex-1 flex-col overflow-hidden bg-white">
		{#if response}
			<!-- Results Topbar -->
			<div
				class="flex h-14 shrink-0 items-center justify-between gap-4 border-b border-sandstone-border bg-surface-1 px-6"
			>
				<div class="flex min-w-0 items-center gap-3">
					<span class="shrink-0 text-xs font-bold tracking-widest text-slate-400 uppercase">
						{isRTL ? 'بحثت عن:' : 'Query:'}
					</span>
					<p class="truncate text-sm font-medium text-slate-800" dir="auto">{response.query}</p>
				</div>
				<div class="flex shrink-0 items-center gap-3 text-xs">
					<span
						class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 font-bold text-primary"
					>
						<Database size={12} />
						{response.total_results}
						{isRTL ? 'نتيجة' : 'results'}
					</span>
					<span
						class="inline-flex items-center gap-1.5 rounded-lg border border-sandstone-border bg-surface-2 px-3 py-1 text-slate-500"
					>
						<Clock size={12} />
						{(response.search_time_ms / 1000).toFixed(2)}s
					</span>
					<span
						class="hidden items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1 font-semibold text-amber-700 uppercase sm:inline-flex"
					>
						<Zap size={12} />
						{response.strategy}
					</span>
				</div>
			</div>

			<!-- Results Scroll Area -->
			<div class="flex-1 overflow-y-auto p-6">
				{#if response.results.length === 0}
					<div class="flex h-full flex-col items-center justify-center gap-4 py-20 text-center">
						<div class="flex h-14 w-14 items-center justify-center rounded-full bg-slate-100">
							<Search size={24} class="text-slate-400" />
						</div>
						<p class="max-w-sm text-slate-500">
							{isRTL
								? 'لا توجد نتائج. جرّب كلمات مختلفة أو غيّر استراتيجية البحث.'
								: 'No results found. Try different keywords or change the search strategy.'}
						</p>
					</div>
				{:else}
					<div class="mx-auto grid max-w-4xl gap-4">
						{#each response.results as result, i (result.id)}
							<div class="animate-in" style="animation-delay: {i * 40}ms">
								<RawResultCard {result} rank={i + 1} />
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{:else if isLoading}
			<!-- Loading skeleton -->
			<div class="flex-1 overflow-y-auto p-6">
				<div class="mx-auto grid max-w-4xl gap-4">
					{#each Array(top_k > 5 ? 5 : top_k) as _, i}
						<div
							class="animate-pulse rounded-xl border border-sandstone-border bg-sandstone/60 p-5"
						>
							<div class="mb-3 flex items-start justify-between">
								<div class="space-y-2">
									<div class="h-6 w-32 rounded bg-sandstone-border"></div>
									<div class="h-4 w-48 rounded bg-sandstone-border"></div>
								</div>
								<div class="h-6 w-20 rounded-full bg-sandstone-border"></div>
							</div>
							<div class="mb-1.5 h-3 w-full rounded bg-sandstone-border"></div>
							<div class="mb-1.5 h-3 w-4/5 rounded bg-sandstone-border"></div>
							<div class="h-3 w-3/5 rounded bg-sandstone-border"></div>
						</div>
					{/each}
				</div>
			</div>
		{:else if errorMsg}
			<div class="flex flex-1 items-center justify-center p-8">
				<div
					class="w-full max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 text-sm text-red-700"
				>
					<p class="mb-1 font-bold">{isRTL ? 'حدث خطأ' : 'Error'}</p>
					<p class="opacity-80">{errorMsg}</p>
				</div>
			</div>
		{:else}
			<!-- Welcome State -->
			<div class="flex flex-1 flex-col items-center justify-center bg-surface-0/50 p-8 text-center">
				<div
					class="mb-6 flex h-20 w-20 items-center justify-center rounded-2xl border border-sandstone-border bg-surface-1 shadow-sm"
				>
					<Database size={36} class="text-primary/40" />
				</div>
				<h2 class="mb-3 text-2xl font-bold text-slate-700">
					{isRTL ? 'استكشف قاعدة المعرفة' : 'Explore the Knowledge Base'}
				</h2>
				<p class="mb-8 max-w-md leading-relaxed text-slate-500">
					{isRTL
						? 'اختر مجالاً قانونياً من القائمة على اليسار، أدخل سؤالك أو نصاً، ثم اضغط بحث للاطلاع على المواد القانونية ذات الصلة.'
						: 'Select a legal domain from the sidebar, enter your question or text, then click Search to browse matching legal articles from the raw database.'}
				</p>

				<!-- Example queries as clickable chips -->
				<div class="mb-6 max-w-lg">
					<p class="mb-3 text-xs font-semibold tracking-wider text-slate-400 uppercase">
						{isRTL ? 'أسئلة مقترحة' : 'Suggested queries'}
					</p>
					<div class="flex flex-wrap justify-center gap-2">
						{#each exampleQueries as q}
							<button
								type="button"
								onclick={() => fillExample(q)}
								class="inline-flex items-center gap-1.5 rounded-full border border-sandstone-border bg-surface-1 px-3.5 py-1.5 text-xs font-medium text-slate-600 transition-all hover:border-primary/40 hover:bg-surface-2 hover:text-primary"
							>
								<Sparkles size={11} class="opacity-50" />
								{q.length > 40 ? q.slice(0, 40) + '…' : q}
							</button>
						{/each}
					</div>
				</div>

				<div class="grid w-full max-w-sm grid-cols-3 gap-3">
					{#each [{ icon: '⚖️', label: isRTL ? 'اختر المجال' : 'Select Domain' }, { icon: '✍️', label: isRTL ? 'أدخل سؤالك' : 'Enter Query' }, { icon: '🔍', label: isRTL ? 'ابحث وتصفح' : 'Search & Browse' }] as step}
						<div
							class="flex flex-col items-center gap-2 rounded-xl border border-sandstone-border bg-surface-1 p-3"
						>
							<span class="text-2xl">{step.icon}</span>
							<span class="text-center text-xs font-medium text-slate-600">{step.label}</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</main>
</div>

<style>
	@keyframes animate-in {
		from {
			opacity: 0;
			transform: translateY(8px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
	.animate-in {
		animation: animate-in 0.25s ease-out both;
	}
</style>
