<script lang="ts">
	import {
		ArrowRight,
		ArrowLeft,
		BookOpen,
		Copy,
		Check,
		Search,
		Loader2,
		AlertCircle,
		ChevronDown,
		ChevronRight,
		ChevronsDownUp,
		ChevronsUpDown,
		Gavel,
		Library,
		Layers,
		SplitSquareHorizontal,
		ScrollText,
		Tag,
		FileSymlink,
		RefreshCw,
		Database,
		Zap,
		CheckCircle2,
		ToggleLeft,
		ToggleRight
	} from 'lucide-svelte';
	import type { Language, UploadArticle } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { getUploadArticles, embedUpload } from '$lib/upload';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	interface Props {
		language: Language;
		fileId: string;
		filename?: string;
	}

	let { language, fileId, filename }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	// ── Flat list state ───────────────────────────────────────────────────────
	let articles = $state<UploadArticle[]>([]);
	let flatLoading = $state(false);
	let flatError = $state<string | null>(null);
	let flatLoaded = $state(false);

	// ── Metadata ──────────────────────────────────────────────────────────────
	let articleCount = $state(0);
	let lawName = $state('');
	let domain = $state('');

	// ── Flat list UI ──────────────────────────────────────────────────────────
	let filterQuery = $state('');
	let copiedIndex = $state<number | null>(null);
	let expandedSet = $state<Set<number>>(new Set());

	const filteredArticles = $derived(
		filterQuery.trim()
			? articles.filter((a) => {
					const q = filterQuery.toLowerCase();
					const ctx = a.context ?? {};
					return (
						a.text?.toLowerCase().includes(q) ||
						a.article_number?.toLowerCase().includes(q) ||
						ctx.book?.toLowerCase().includes(q) ||
						ctx.chapter?.toLowerCase().includes(q) ||
						ctx.section?.toLowerCase().includes(q) ||
						a.law_name?.toLowerCase().includes(q)
					);
				})
			: articles
	);

	// ── Load flat list on mount (default tab) ─────────────────────────────────
	onMount(async () => {
		await loadFlatList();
	});

	async function loadFlatList() {
		if (flatLoaded) return;
		flatLoading = true;
		flatError = null;
		try {
			const data = await getUploadArticles(fileId);
			articles = data.articles;
			if (data.articles.length > 0) {
				lawName = data.articles[0].law_name ?? '';
				domain = data.articles[0].domain ?? '';
			}
			flatLoaded = true;
		} catch (e: any) {
			flatError = e.message;
		} finally {
			flatLoading = false;
		}
	}

	// ── Flat list helpers ─────────────────────────────────────────────────────
	async function copyText(text: string, idx: number) {
		try {
			await navigator.clipboard.writeText(text);
			copiedIndex = idx;
			setTimeout(() => {
				if (copiedIndex === idx) copiedIndex = null;
			}, 2000);
		} catch {}
	}

	function toggleExpand(idx: number) {
		const next = new Set(expandedSet);
		next.has(idx) ? next.delete(idx) : next.add(idx);
		expandedSet = next;
	}

	function expandAll() {
		expandedSet = new Set(filteredArticles.map((_, i) => i));
	}
	function collapseAll() {
		expandedSet = new Set();
	}

	function truncate(text: string, length = 280) {
		return text.length > length ? text.slice(0, length) + '…' : text;
	}

	function buildBreadcrumb(article: UploadArticle) {
		const ctx = article.context ?? {};
		const crumbs: { label: string; type: string }[] = [];
		if (ctx.book) crumbs.push({ label: ctx.book, type: 'book' });
		if (ctx.section) crumbs.push({ label: ctx.section, type: 'section' });
		if (ctx.subsection) crumbs.push({ label: ctx.subsection, type: 'subsection' });
		if (ctx.chapter) crumbs.push({ label: ctx.chapter, type: 'chapter' });
		if (ctx.branch) crumbs.push({ label: ctx.branch, type: 'branch' });
		return crumbs;
	}

	// ── Embed state ───────────────────────────────────────────────────────────
	type EmbedPhase = 'idle' | 'embedding' | 'done' | 'error';
	let embedPhase = $state<EmbedPhase>('idle');
	let embedDomain = $state('uploaded');
	let embedClear = $state(true);
	let embedResult = $state<{ ingested: number; message: string } | null>(null);
	let embedError = $state<string | null>(null);

	const LEGAL_DOMAINS = [
		{ id: 'uploaded', label_ar: 'مرفوع', label_fr: 'Uploadé' },
		{ id: 'civil', label_ar: 'مدني', label_fr: 'Civil' },
		{ id: 'criminal', label_ar: 'جنائي', label_fr: 'Pénal' },
		{ id: 'commercial', label_ar: 'تجاري', label_fr: 'Commercial' },
		{ id: 'family', label_ar: 'الأسرة', label_fr: 'Famille' },
		{ id: 'traffic', label_ar: 'السير', label_fr: 'Circulation' },
		{ id: 'procedure', label_ar: 'المسطرة', label_fr: 'Procédure' }
	];

	async function handleEmbed() {
		embedPhase = 'embedding';
		embedError = null;
		embedResult = null;
		try {
			const res = await embedUpload(fileId, embedDomain, embedClear);
			embedResult = { ingested: res.ingested, message: res.message };
			embedPhase = 'done';
		} catch (e: any) {
			embedError = e.message;
			embedPhase = 'error';
		}
	}
</script>

<div class="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-8">
	<!-- ── Page header ──────────────────────────────────────────────────────── -->
	<div class="flex items-start gap-3">
		<button
			onclick={() => goto('/uploads')}
			class="mt-1 shrink-0 rounded-lg p-2 text-slate-400 hover:bg-surface-2 hover:text-primary"
		>
			{#if isRTL}<ArrowRight class="h-5 w-5" />{:else}<ArrowLeft class="h-5 w-5" />{/if}
		</button>

		<div class="min-w-0 flex-1 border-b border-sandstone-border pb-4">
			<div class="flex items-center gap-2 text-sm text-slate-400">
				<a href="/uploads" class="hover:text-primary">{t('uploads')}</a>
				<ChevronRight class="h-3.5 w-3.5" />
				<span class="truncate font-medium text-slate-600">{filename ?? fileId}</span>
			</div>
			<h1 class="mt-1 font-serif text-2xl font-bold text-slate-900">{t('articlesPageTitle')}</h1>

			{#if lawName || domain}
				<div class="mt-2 flex flex-wrap items-center gap-2">
					{#if lawName}
						<span
							class="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary"
						>
							<Gavel class="h-3.5 w-3.5" />{lawName}
						</span>
					{/if}
					{#if domain}
						<span
							class="rounded-full border border-sandstone-border bg-surface-2 px-3 py-1 text-xs font-medium text-slate-600"
						>
							{domain}
						</span>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- ── Stats ────────────────────────────────────────────────────────────── -->
	<div class="grid grid-cols-2 gap-4">
		<div class="rounded-xl border border-sandstone-border bg-surface-1 p-4">
			<p class="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
				{t('totalArticles')}
			</p>
			<p class="mt-1 text-2xl font-bold text-primary">{articleCount || articles.length}</p>
		</div>
		<div class="rounded-xl border border-sandstone-border bg-surface-1 p-4">
			<p class="text-[10px] font-semibold tracking-wider text-slate-400 uppercase">
				{isRTL ? 'الملف' : 'Fichier'}
			</p>
			<p class="mt-1 truncate text-xs font-semibold text-slate-700" title={filename}>
				{filename ?? fileId}
			</p>
		</div>
	</div>

	<!-- ── Embed panel ──────────────────────────────────────────────────────── -->
	<div
		class={`overflow-hidden rounded-2xl border
		${embedPhase === 'done' ? 'border-green-200 bg-green-50' : ''}
		${embedPhase === 'error' ? 'border-red-200 bg-red-50/60' : ''}
		${embedPhase === 'idle' || embedPhase === 'embedding' ? 'border-sandstone-border bg-surface-1' : ''}`}
	>
		<!-- Panel header -->
		<div class="flex items-center gap-3 border-b border-inherit px-5 py-4">
			<div
				class={`rounded-lg p-2
				${embedPhase === 'done' ? 'bg-green-100 text-green-600' : 'bg-primary/10 text-primary'}`}
			>
				<Database class="h-5 w-5" />
			</div>
			<div class="min-w-0 flex-1">
				<p class="font-semibold text-slate-800">{t('embedToDb')}</p>
				<p class="text-xs text-slate-400">
					{isRTL
						? 'أدرج المواد المعالجة في قاعدة البيانات المتجهية لتصبح قابلة للبحث'
						: 'Intègre les articles traités dans la base vectorielle pour les rendre cherchables'}
				</p>
			</div>
			<!-- Success badge -->
			{#if embedPhase === 'done' && embedResult}
				<span
					class="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-bold text-green-700"
				>
					<CheckCircle2 class="h-3.5 w-3.5" />
					{embedResult.ingested}
					{t('embedIngested')}
				</span>
			{/if}
		</div>

		<!-- Panel body -->
		<div class="space-y-4 px-5 py-4">
			{#if embedPhase === 'done'}
				<div class="flex items-start gap-3 rounded-xl border border-green-200 bg-green-100/60 p-4">
					<CheckCircle2 class="mt-0.5 h-5 w-5 shrink-0 text-green-600" />
					<div>
						<p class="font-semibold text-green-800">{t('embedSuccess')}</p>
						<p class="mt-0.5 text-sm text-green-700">{embedResult?.message}</p>
					</div>
				</div>
				<button
					onclick={() => {
						embedPhase = 'idle';
						embedResult = null;
					}}
					class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-primary"
				>
					<RefreshCw class="h-3.5 w-3.5" />
					{isRTL ? 'إعادة الإدراج' : 'Ré-intégrer'}
				</button>
			{:else if embedPhase === 'error'}
				<div class="flex items-start gap-3 rounded-xl border border-red-200 bg-red-100/60 p-4">
					<AlertCircle class="mt-0.5 h-5 w-5 shrink-0 text-red-500" />
					<div>
						<p class="font-semibold text-red-700">{t('embedError')}</p>
						<p class="mt-0.5 text-sm break-all text-red-600">{embedError}</p>
					</div>
				</div>
				<button
					onclick={() => {
						embedPhase = 'idle';
						embedError = null;
					}}
					class="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-primary"
				>
					<RefreshCw class="h-3.5 w-3.5" />
					{isRTL ? 'حاول مجددًا' : 'Réessayer'}
				</button>
			{:else}
				<div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
					<div class="space-y-1.5">
						<label
							for="embed-domain"
							class="text-xs font-semibold tracking-wider text-slate-400 uppercase"
						>
							{t('embedDomain')}
						</label>
						<select
							id="embed-domain"
							bind:value={embedDomain}
							disabled={embedPhase === 'embedding'}
							class="w-full rounded-xl border border-sandstone-border bg-surface-2 px-3 py-2 text-sm font-medium text-slate-700 outline-none focus:border-primary/40 focus:ring-2 focus:ring-primary/10 disabled:opacity-50"
						>
							{#each LEGAL_DOMAINS as d}
								<option value={d.id}>{isRTL ? d.label_ar : d.label_fr}</option>
							{/each}
						</select>
					</div>

					<div
						class="flex items-center justify-between rounded-xl border border-sandstone-border bg-surface-2 px-4 py-2.5"
					>
						<div>
							<p class="text-xs font-semibold text-slate-700">{t('embedClear')}</p>
							<p class="text-[10px] text-slate-400">
								{isRTL ? 'يُنصح به لتجنب التكرار' : 'Recommandé pour éviter les doublons'}
							</p>
						</div>
						<button
							onclick={() => (embedClear = !embedClear)}
							disabled={embedPhase === 'embedding'}
							class="ms-3 shrink-0 disabled:opacity-50"
						>
							{#if embedClear}
								<ToggleRight class="h-7 w-7 text-primary" />
							{:else}
								<ToggleLeft class="h-7 w-7 text-slate-300" />
							{/if}
						</button>
					</div>
				</div>

				<button
					onclick={handleEmbed}
					disabled={embedPhase === 'embedding'}
					class="flex w-full items-center justify-center gap-2.5 rounded-xl bg-primary px-5 py-3 text-sm font-bold text-white shadow-sm hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)] disabled:cursor-not-allowed disabled:opacity-60"
				>
					{#if embedPhase === 'embedding'}
						<Loader2 class="h-4 w-4 animate-spin" />
						{t('embedding')}
					{:else}
						<Zap class="h-4 w-4" />
						{t('embedToDb')}
					{/if}
				</button>

				{#if embedPhase === 'embedding'}
					<p class="text-center text-xs text-slate-400">
						{isRTL
							? 'يتم توليد التضمينات وتخزين المواد في قاعدة البيانات...'
							: 'Génération des embeddings et stockage dans la base de données...'}
					</p>
				{/if}
			{/if}
		</div>
	</div>

	<!-- ══ Flat List ═════════════════════════════════════════════════════════════ -->
	{#if flatLoading}
		<div class="flex items-center justify-center py-24 text-slate-400">
			<Loader2 class="h-10 w-10 animate-spin" />
		</div>
	{:else if flatError}
		<div
			class="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-5 text-red-700"
		>
			<AlertCircle class="h-5 w-5 shrink-0" />
			<span class="text-sm">{flatError}</span>
		</div>
	{:else}
		<!-- Toolbar: search + expand/collapse all -->
		<div class="flex items-center gap-3">
			<div class="relative flex-1">
				<Search
					class={`absolute top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400 ${isRTL ? 'inset-inline-end-3' : 'inset-inline-start-3'}`}
				/>
				<input
					type="text"
					bind:value={filterQuery}
					placeholder={t('filterArticles')}
					class={`w-full rounded-xl border border-sandstone-border bg-surface-1 py-2.5 text-sm outline-none placeholder:text-slate-400 focus:border-primary/40 focus:ring-2 focus:ring-primary/10
						${isRTL ? 'ps-9 pe-4 text-start' : 'ps-9 pe-4'}`}
				/>
			</div>
			<button
				onclick={expandAll}
				class="inline-flex items-center gap-1.5 rounded-xl border border-sandstone-border bg-surface-1 px-3 py-2.5 text-xs font-medium text-slate-600 hover:bg-surface-2"
				title={isRTL ? 'توسيع الكل' : 'Tout développer'}
			>
				<ChevronsUpDown class="h-4 w-4" />
			</button>
			<button
				onclick={collapseAll}
				class="inline-flex items-center gap-1.5 rounded-xl border border-sandstone-border bg-surface-1 px-3 py-2.5 text-xs font-medium text-slate-600 hover:bg-surface-2"
				title={isRTL ? 'طي الكل' : 'Tout réduire'}
			>
				<ChevronsDownUp class="h-4 w-4" />
			</button>
		</div>

		{#if filteredArticles.length === 0}
			<div class="flex flex-col items-center gap-3 py-20 text-slate-400">
				<BookOpen class="h-12 w-12 opacity-30" />
				<p class="text-sm">
					{filterQuery ? (isRTL ? 'لا توجد نتائج' : 'Aucun résultat') : t('noArticles')}
				</p>
			</div>
		{:else}
			<div class="space-y-3">
				{#each filteredArticles as article, i (i)}
					{@const isExpanded = expandedSet.has(i)}
					{@const isCopied = copiedIndex === i}
					{@const crumbs = buildBreadcrumb(article)}
					{@const hasFootnotes = (article.footnotes?.length ?? 0) > 0}

					<article
						class="overflow-hidden rounded-2xl border border-sandstone-border bg-surface-1 hover:shadow-md"
					>
						<!-- Hierarchy breadcrumb strip -->
						{#if crumbs.length > 0}
							<div class="border-b border-sandstone-border bg-surface-2 px-5 py-2">
								<ol class="flex flex-wrap items-center gap-1 text-xs text-slate-500">
									{#each crumbs as crumb, ci}
										<li class="flex min-w-0 items-center gap-1">
											{#if ci > 0}
												<ChevronRight class="h-3 w-3 shrink-0 text-slate-300" />
											{/if}
											{#if crumb.type === 'book'}
												<Library class="h-3 w-3 shrink-0 text-primary/60" />
											{:else if crumb.type === 'section'}
												<Layers class="h-3 w-3 shrink-0 text-indigo-400" />
											{:else if crumb.type === 'subsection'}
												<SplitSquareHorizontal class="h-3 w-3 shrink-0 text-violet-400" />
											{:else if crumb.type === 'chapter'}
												<ScrollText class="h-3 w-3 shrink-0 text-amber-500" />
											{:else}
												<Tag class="h-3 w-3 shrink-0 text-rose-400" />
											{/if}
											<span
												class="max-w-[24ch] truncate leading-tight font-medium"
												title={crumb.label}>{crumb.label}</span
											>
										</li>
									{/each}
								</ol>
							</div>
						{/if}

						<!-- Article body -->
						<div class="flex items-start justify-between gap-4 p-5">
							<div class="flex min-w-0 flex-1 items-start gap-3">
								<!-- Number badge -->
								<div class="min-w-14 shrink-0 rounded-xl bg-primary/10 px-3 py-2 text-center">
									<p class="text-[9px] font-semibold tracking-widest text-primary/60 uppercase">
										{isRTL ? 'الفصل' : 'Art.'}
									</p>
									<p class="mt-0.5 text-base leading-none font-bold text-primary">
										{article.article_number ?? i + 1}
									</p>
								</div>

								<!-- Text -->
								<div class="min-w-0 flex-1">
									<p
										class="text-start text-sm leading-[1.85] text-slate-700"
										dir={isRTL ? 'rtl' : 'ltr'}
									>
										{isExpanded ? article.text : truncate(article.text)}
									</p>

									{#if article.text.length > 280}
										<button
											onclick={() => toggleExpand(i)}
											class="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-primary/70 hover:text-primary"
										>
											{#if isExpanded}
												<ChevronDown class="h-3.5 w-3.5" />{t('readLess')}
											{:else}
												<ChevronRight class="h-3.5 w-3.5" />{t('readMore')}
											{/if}
										</button>
									{/if}

									<!-- Footnotes -->
									{#if hasFootnotes && isExpanded}
										<div
											class="mt-4 space-y-1 rounded-lg border border-sandstone-border bg-surface-2/60 p-3"
										>
											<p
												class="flex items-center gap-1.5 text-[10px] font-semibold tracking-wider text-slate-400 uppercase"
											>
												<FileSymlink class="h-3 w-3" />
												{isRTL ? 'الهوامش' : 'Notes de bas de page'}
											</p>
											{#each article.footnotes ?? [] as fn, fi}
												<p
													class="text-xs leading-relaxed text-slate-500"
													dir={isRTL ? 'rtl' : 'ltr'}
												>
													<span class="font-bold text-primary/70">{fi + 1}.</span>
													{fn}
												</p>
											{/each}
										</div>
									{/if}
								</div>
							</div>

							<!-- Copy button -->
							<button
								onclick={() => copyText(article.text, i)}
								class={`flex shrink-0 items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-all
										${isCopied ? 'bg-green-100 text-green-700' : 'bg-slate-100 text-slate-400 hover:bg-primary/10 hover:text-primary'}`}
							>
								{#if isCopied}
									<Check class="h-3.5 w-3.5" /><span class="hidden sm:inline">{t('copied')}</span>
								{:else}
									<Copy class="h-3.5 w-3.5" />
								{/if}
							</button>
						</div>

						<div
							class="h-px w-full bg-linear-to-r from-primary/20 via-primary/5 to-transparent"
						></div>
					</article>
				{/each}
			</div>
		{/if}
	{/if}
</div>
