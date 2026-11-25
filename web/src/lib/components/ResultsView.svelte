<script lang="ts">
	import type { Language, AskResponse, AskSource } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	interface Props {
		language: Language;
		domain: string;
		response: AskResponse;
		onSourceClick: (source: AskSource) => void;
		onBack: () => void;
		isHistoryView?: boolean;
	}

	let {
		language,
		domain,
		response,
		onSourceClick,
		onBack,
		isHistoryView = false
	}: Props = $props();

	const isRTL = $derived(language === 'ar');

	let activeTab = $state<'legal' | 'simple'>('legal');

	// Translated labels derived from language
	const tLegalAns = $derived(isRTL ? 'الإجابة القانونية المقترحة' : 'Suggested Legal Answer');
	const tLegalTab = $derived(isRTL ? 'لغة قانونية' : 'Legal language');
	const tSimpleTab = $derived(isRTL ? 'تفسير مبسط' : 'Simplified explanation');
	const tHelpful = $derived(
		isRTL ? 'هل كانت هذه المعلومة دقيقة ومفيدة؟' : 'Was this information accurate and helpful?'
	);
	const tYes = $derived(isRTL ? 'نعم' : 'Yes');
	const tNo = $derived(isRTL ? 'لا' : 'No');
	const tCopy = $derived(isRTL ? 'نسخ مع المصادر' : 'Copy with sources');
	const tSources = $derived(isRTL ? 'المصادر القانونية' : 'Legal Sources');
	const tRelevance = $derived(isRTL ? 'صلة:' : 'Relevance:');
	const tViewFull = $derived(isRTL ? 'عرض النص الكامل ←' : 'View full text →');
	const tViewMore = $derived(isRTL ? 'عرض مصادر إضافية' : 'View additional sources');

	// Session display (first 8 chars of UUID, uppercased)
	const displaySession = $derived(
		response.session_id ? response.session_id.slice(0, 8).toUpperCase() : '--------'
	);

	// ── Domain color mapping ──
	function domainColor(domain: string): string {
		const map: Record<string, string> = {
			criminal: '#b91c1c',
			traffic: '#b45309',
			family: '#7c3aed',
			civil: '#0369a1',
			commercial: '#0f766e',
			procedure: '#475569',
			violations: '#b91c1c',
			offenses: '#b91c1c'
		};
		return map[domain] || '#1A237E';
	}

	// ── Markdown renderer ─────────────────────────────────────────────────────
	marked.setOptions({ breaks: true, gfm: true });

	function renderMd(text: string): string {
		if (!text) return '';
		const raw = marked.parse(text) as string;
		return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } });
	}

	// Build the simple-tab markdown: short_answer + optional example block
	const simpleMarkdown = $derived(
		response.example
			? `${response.short_answer}\n\n---\n\n**${isRTL ? 'مثال' : 'Exemple'} :** ${response.example}`
			: response.short_answer
	);
</script>

<div class="flex h-full flex-1 flex-col overflow-hidden bg-surface-1">
	<!-- Query Context Header -->
	<div
		class="flex h-20 shrink-0 items-center justify-between border-b border-sandstone-border bg-surface-1 px-8"
	>
		<div class="flex min-w-0 flex-col">
			<span class="text-xs font-semibold tracking-widest text-slate-400 uppercase">
				{isRTL ? 'سؤالك الحالي' : 'Current Query'}
			</span>
			<h1 class="max-w-2xl truncate text-xl font-medium text-slate-900">{response.query}</h1>
		</div>
		<div class="flex shrink-0 gap-3">
			{#if isHistoryView}
				<span
					class="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-100 px-3 py-1.5 text-xs font-bold text-amber-700"
				>
					<svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
						/></svg
					>
					{isRTL ? 'من السجل' : 'From History'}
				</span>
			{:else}
				{@const color = domainColor(domain)}
				<div
					class="inline-flex items-center gap-2 rounded-lg border px-4 py-2"
					style={color !== '#1A237E'
						? `background: ${color}12; border-color: ${color}25; color: ${color};`
						: 'background: #f5f0e8; border-color: #dcd3c1; color: #475569;'}
				>
					<span class="text-xs font-semibold opacity-75">{isRTL ? 'المجال:' : 'Domain:'}</span>
					<span class="text-sm font-bold"
						>{domain === 'all' ? (isRTL ? 'الجميع' : 'All') : domain}</span
					>
				</div>
			{/if}
			<button
				onclick={onBack}
				class="rounded-lg bg-primary px-6 py-2 text-sm font-bold text-white shadow-sm transition-all hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)]"
			>
				{isHistoryView
					? isRTL
						? 'العودة للسجل'
						: 'Back to History'
					: isRTL
						? 'تعديل السؤال'
						: 'Edit Query'}
			</button>
		</div>
	</div>

	<!-- Main Content Grid -->
	<div class="flex flex-1 overflow-hidden">
		<!-- Sidebar: Knowledge Base Status -->
		<aside
			class="flex w-64 shrink-0 flex-col gap-6 overflow-y-auto border-e border-sandstone-border bg-surface-2 p-6"
		>
			<div>
				<h3 class="mb-4 text-xs font-bold tracking-wider text-slate-400 uppercase">
					{isRTL ? 'قاعدة البيانات النشطة' : 'Active Databases'}
				</h3>
				<ul class="space-y-2">
					{#each response.knowledge_base as kb}
						<li
							class="flex items-center gap-3 rounded-lg border border-sandstone-border bg-surface-1 px-3 py-2.5"
						>
							<div class="h-2 w-2 shrink-0 rounded-full bg-green-500"></div>
							<span class="text-sm font-medium text-slate-700">{kb}</span>
						</li>
					{/each}
					{#if response.knowledge_base.length === 0}
						<li class="px-1 text-sm text-slate-400 italic">
							{isRTL ? 'لا توجد قاعدة بيانات محددة' : 'No specific database'}
						</li>
					{/if}
				</ul>
			</div>
			<div class="mt-auto rounded-xl border border-primary/8 bg-primary/4 p-4">
				<p class="text-xs leading-relaxed text-slate-500">
					{isRTL
						? 'يتم تحديث النصوص القانونية بشكل آلي من الجريدة الرسمية للمملكة المغربية.'
						: 'Legal texts are automatically updated from the Official Gazette.'}
				</p>
			</div>
		</aside>

		<!-- Split Result Panels -->
		<main class="hidden flex-1 overflow-hidden bg-surface-0/40 md:flex">
			<!-- Left Panel: AI Answer -->
			<div class="w-3/5 overflow-y-auto border-e border-sandstone-border bg-surface-1 p-8">
				<div class="mb-6 flex flex-col justify-between gap-4 xl:flex-row xl:items-center">
					<h2 class="flex items-center gap-2 text-lg font-bold text-slate-900">
						<span class="h-6 w-2 shrink-0 rounded-full bg-success"></span>
						{tLegalAns}
					</h2>
					<div class="flex shrink-0 rounded-lg bg-surface-2 p-1">
						<button
							onclick={() => (activeTab = 'legal')}
							class={`rounded px-4 py-1 text-xs font-bold shadow-sm transition-all ${activeTab === 'legal' ? 'bg-surface-1 text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
						>
							{tLegalTab}
						</button>
						<button
							onclick={() => (activeTab = 'simple')}
							class={`rounded px-4 py-1 text-xs font-bold shadow-sm transition-all ${activeTab === 'simple' ? 'bg-surface-1 text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
						>
							{tSimpleTab}
						</button>
					</div>
				</div>

				<div
					class="md-answer max-w-none text-start font-serif leading-loose text-primary"
					dir={isRTL ? 'rtl' : 'ltr'}
				>
					{#if activeTab === 'legal'}
						{@html renderMd(response.long_answer)}
					{:else}
						{@html renderMd(simpleMarkdown)}
					{/if}
				</div>
				<div class="mt-6 rounded-sm border-s-4 border-blue-600 bg-blue-50 p-4 text-sm italic">
					{response.disclaimer || 'تنبيه: هذا الجواب للاسترشاد، ويفضل دائما العودة للجهات المختصة.'}
				</div>

				<!-- Feedback Section -->
				<div
					class="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-sandstone-border pt-6"
				>
					<span class="text-sm text-slate-500">{tHelpful}</span>
					<div class="flex items-center gap-3">
						<button
							class="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-slate-600 transition-colors hover:bg-surface-2"
						>
							<span>👍</span> <span class="text-sm font-medium">{tYes}</span>
						</button>
						<button
							class="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-slate-600 transition-colors hover:bg-surface-2"
						>
							<span>👎</span> <span class="text-sm font-medium">{tNo}</span>
						</button>
						<button
							class="rounded-lg border border-sandstone-border px-4 py-2 text-sm font-bold text-slate-600 transition-colors hover:bg-surface-2"
						>
							{tCopy}
						</button>
					</div>
				</div>
			</div>

			<!-- Right Panel: Source Articles -->
			<div class="w-2/5 overflow-y-auto bg-surface-2/30 p-6">
				<div class="mb-4 flex items-center justify-between">
					<h3 class="text-sm font-bold tracking-widest text-slate-400 uppercase">
						{tSources}
					</h3>
					<span class="rounded-full bg-surface-2 px-2.5 py-0.5 text-xs font-bold text-slate-400">
						{response.sources.length}
					</span>
				</div>

				<div class="space-y-3">
					{#each response.sources as source}
						{@const score = Math.round(source.relevance_score)}
						{@const scoreColor =
							score >= 70
								? 'bg-green-50 text-green-700 border-green-200'
								: score >= 40
									? 'bg-amber-50 text-amber-700 border-amber-200'
									: 'bg-slate-50 text-slate-500 border-slate-200'}
						<div
							onclick={() => onSourceClick(source)}
							role="button"
							tabindex="0"
							onkeydown={(e) => e.key === 'Enter' && onSourceClick(source)}
							class="group cursor-pointer overflow-hidden rounded-xl border border-sandstone-border bg-surface-1 transition-all hover:shadow-md"
						>
							<div
								class="flex items-center justify-between gap-3 border-b border-sandstone-border bg-surface-2/70 p-3"
							>
								<span class="truncate text-xs font-bold text-slate-800">
									{isRTL ? 'المادة' : 'Art.'}
									{source.article_number} — {source.law_name}
								</span>
								<span
									class="inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-bold {scoreColor}"
								>
									{score}%
								</span>
							</div>
							<div class="p-4">
								<p class="line-clamp-3 text-sm leading-relaxed text-slate-600" dir="auto">
									"{source.text_preview}"
								</p>
								<!-- Score bar -->
								<div class="mt-3 flex items-center justify-between gap-3">
									<div class="score-bar-sm" title="{score}% pertinence">
										<div class="score-fill-sm" style="width: {score}%"></div>
									</div>
									<span class="shrink-0 text-[10px] font-bold text-primary group-hover:underline">
										{tViewFull}
									</span>
								</div>
							</div>
						</div>
					{/each}

					{#if response.sources.length === 0}
						<div
							class="rounded-xl border border-dashed border-sandstone-border bg-surface-1 p-8 text-center text-sm text-slate-400"
						>
							{isRTL ? 'لم يتم العثور على مصادر مطابقة.' : 'No matching sources found.'}
						</div>
					{/if}
				</div>
			</div>
		</main>
	</div>

	<!-- Bottom Status Bar -->
	<footer
		class="flex h-8 shrink-0 items-center justify-between bg-primary px-6 text-[10px] text-white/50"
	>
		<div class="flex gap-5">
			<span class="flex items-center gap-1.5">
				<span class="h-1.5 w-1.5 shrink-0 rounded-full bg-green-400"></span>
				{isRTL ? `#${displaySession}` : `Session: #${displaySession}`}
			</span>
			<span>{(response.total_time_ms / 1000).toFixed(2)}s</span>
		</div>
		<div class="flex gap-5">
			<span class="hidden sm:inline"
				>{isRTL ? 'وزارة العدل - بيانات عامة' : 'MoJ — Public Data'}</span
			>
			<span class="font-semibold text-white/70">{isRTL ? 'متصل' : 'Online'}</span>
		</div>
	</footer>
</div>

<style>
	/* ── Markdown answer renderer ──────────────────────────────────────────── */
	.md-answer :global(h1),
	.md-answer :global(h2),
	.md-answer :global(h3),
	.md-answer :global(h4) {
		font-family: var(--font-serif, serif);
		font-weight: 700;
		color: #1a237e;
		margin-top: 1.5em;
		margin-bottom: 0.5em;
		line-height: 1.4;
	}
	.md-answer :global(h1) {
		font-size: 1.35rem;
		border-bottom: 2px solid #e8e0d0;
		padding-bottom: 0.3em;
	}
	.md-answer :global(h2) {
		font-size: 1.15rem;
	}
	.md-answer :global(h3) {
		font-size: 1rem;
		color: #374151;
	}

	.md-answer :global(p) {
		margin-bottom: 1em;
		line-height: 1.9;
		font-size: 1.05rem;
	}
	.md-answer :global(strong) {
		font-weight: 700;
		color: #1e293b;
	}
	.md-answer :global(em) {
		font-style: italic;
		color: #475569;
	}

	.md-answer :global(ul),
	.md-answer :global(ol) {
		margin-bottom: 1em;
		padding-inline-start: 1.5em;
		line-height: 1.85;
	}
	.md-answer :global(ul) {
		list-style-type: disc;
	}
	.md-answer :global(ol) {
		list-style-type: decimal;
	}
	.md-answer :global(li) {
		margin-bottom: 0.35em;
		font-size: 1rem;
	}
	.md-answer :global(li::marker) {
		color: #1a237e;
		font-weight: 600;
	}

	.md-answer :global(blockquote) {
		margin: 1.25em 0;
		padding: 0.75em 1.25em;
		border-inline-start: 4px solid #1a237e;
		background: #f0f4ff;
		border-radius: 0 0.5rem 0.5rem 0;
		color: #334155;
		font-style: italic;
	}

	.md-answer :global(code) {
		font-family: 'Courier New', monospace;
		font-size: 0.875em;
		background: #f1f5f9;
		color: #1a237e;
		padding: 0.15em 0.4em;
		border-radius: 0.3em;
		border: 1px solid #e2e8f0;
	}
	.md-answer :global(pre) {
		background: #1e293b;
		color: #e2e8f0;
		border-radius: 0.75rem;
		padding: 1rem 1.25rem;
		overflow-x: auto;
		margin: 1.25em 0;
		font-size: 0.875rem;
	}
	.md-answer :global(pre code) {
		background: none;
		border: none;
		padding: 0;
		color: inherit;
	}

	.md-answer :global(hr) {
		border: none;
		border-top: 1px solid #dcd3c1;
		margin: 1.5em 0;
	}

	.md-answer :global(a) {
		color: #1a237e;
		text-decoration: underline;
		text-underline-offset: 2px;
	}
	.md-answer :global(a:hover) {
		opacity: 0.75;
	}

	.md-answer :global(table) {
		width: 100%;
		border-collapse: collapse;
		margin: 1.25em 0;
		font-size: 0.9rem;
	}
	.md-answer :global(th) {
		background: #f5f0e8;
		font-weight: 700;
		padding: 0.5em 0.75em;
		border: 1px solid #dcd3c1;
		text-align: start;
	}
	.md-answer :global(td) {
		padding: 0.45em 0.75em;
		border: 1px solid #dcd3c1;
	}
	.md-answer :global(tr:nth-child(even) td) {
		background: #faf8f4;
	}

	/* ── Source score bar ── */
	.score-bar-sm {
		height: 3px;
		background: #e2e8f0;
		border-radius: 2px;
		flex: 1;
		max-width: 80px;
		overflow: hidden;
	}
	.score-fill-sm {
		height: 100%;
		background: #1a237e;
		border-radius: 2px;
	}
</style>
