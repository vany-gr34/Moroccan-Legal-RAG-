<script lang="ts">
	import {
		UploadCloud,
		FileText,
		Activity,
		Clock,
		CheckCircle2,
		AlertCircle,
		Loader2,
		Database,
		BookOpen,
		Layers
	} from 'lucide-svelte';
	import type { Language, Law, LawsResponse } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { onMount } from 'svelte';
	import { PUBLIC_API_ENDPOIT } from '$env/static/public';

	interface Props {
		language: Language;
	}

	let { language }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	let laws = $state<Law[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			const res = await fetch(PUBLIC_API_ENDPOIT + '/laws');
			if (!res.ok) {
				throw new Error('Failed to fetch knowledge bases');
			}
			const data: LawsResponse = await res.json();
			laws = data.laws;
		} catch (e: any) {
			error = e.message;
		} finally {
			isLoading = false;
		}
	});

	function formatDate(dateString: string) {
		const date = new Date(dateString);
		return date.toLocaleDateString(isRTL ? 'ar-MA' : 'fr-FR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	// ── Derived stats ──
	const totalLaws = $derived(laws.length);
	const totalArticles = $derived(laws.reduce((sum, l) => sum + l.article_count, 0));
	const uniqueDomains = $derived(new Set(laws.map((l) => l.domain)).size);

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
</script>

<div class="mx-auto w-full max-w-5xl flex-1 space-y-6 px-4 py-8">
	<!-- ══ Header row ═════════════════════════════════════════════════════ -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="font-serif text-2xl font-bold text-slate-900">{t('manageKB')}</h1>
			<p class="mt-1 text-sm text-slate-500">
				{isRTL
					? 'إدارة القوانين والمواد القانونية المدرجة'
					: 'Gérez les lois et articles juridiques indexés'}
			</p>
		</div>
		<button
			class="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-sm transition-all hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)]"
		>
			<UploadCloud size={16} />
			{t('uploadNewDoc')}
		</button>
	</div>

	<!-- ══ Stats strip ════════════════════════════════════════════════════ -->
	{#if !isLoading && !error && laws.length > 0}
		<div class="grid grid-cols-3 gap-4">
			<div
				class="flex items-center gap-4 rounded-xl border border-sandstone-border bg-surface-1 p-4"
			>
				<div
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary"
				>
					<BookOpen size={20} />
				</div>
				<div>
					<p class="text-2xl leading-none font-bold text-slate-900">{totalLaws}</p>
					<p class="mt-1 text-xs text-slate-500">{isRTL ? 'قانون' : 'Lois indexées'}</p>
				</div>
			</div>
			<div
				class="flex items-center gap-4 rounded-xl border border-sandstone-border bg-surface-1 p-4"
			>
				<div
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-success/10 text-success"
				>
					<FileText size={20} />
				</div>
				<div>
					<p class="text-2xl leading-none font-bold text-slate-900">{totalArticles}</p>
					<p class="mt-1 text-xs text-slate-500">{isRTL ? 'مادة قانونية' : 'Articles'}</p>
				</div>
			</div>
			<div
				class="flex items-center gap-4 rounded-xl border border-sandstone-border bg-surface-1 p-4"
			>
				<div
					class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-600"
				>
					<Layers size={20} />
				</div>
				<div>
					<p class="text-2xl leading-none font-bold text-slate-900">{uniqueDomains}</p>
					<p class="mt-1 text-xs text-slate-500">{isRTL ? 'مجال قانوني' : 'Domaines'}</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- ══ Upload Zone (compact card) ══════════════════════════════════════ -->
	<div
		class="group flex cursor-pointer items-center justify-center gap-4 rounded-xl border-2 border-dashed border-sandstone-border bg-surface-1 px-6 py-5 text-center transition-all hover:border-primary/40 hover:bg-surface-2"
	>
		<div
			class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 transition-transform group-hover:scale-110"
		>
			<UploadCloud class="h-5 w-5 text-primary" />
		</div>
		<div class="text-start">
			<p class="text-sm font-semibold text-slate-800">{t('uploadNewDoc')}</p>
			<p class="text-xs text-slate-500">{t('dragDropDoc')}</p>
		</div>
	</div>

	<!-- ══ Documents Grid ══════════════════════════════════════════════════ -->
	<div>
		<div class="mb-4 flex items-center justify-between">
			<h3 class="text-sm font-bold tracking-wider text-slate-600 uppercase">
				{t('documentsList')}
				<span class="ms-1.5 font-normal text-slate-400">({laws.length})</span>
			</h3>
		</div>

		{#if isLoading}
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				{#each [1, 2, 3, 4] as _}
					<div class="rounded-xl border border-sandstone-border bg-surface-1 p-5">
						<div class="flex items-start gap-4">
							<div class="h-10 w-10 shrink-0 rounded-lg bg-surface-3"></div>
							<div class="min-w-0 flex-1 space-y-2.5">
								<div class="h-4 w-3/5 rounded bg-surface-3"></div>
								<div class="h-3 w-full rounded bg-surface-3"></div>
								<div class="flex gap-3">
									<div class="h-3 w-16 rounded bg-surface-3"></div>
									<div class="h-3 w-12 rounded bg-surface-3"></div>
									<div class="h-5 w-14 rounded-full bg-surface-3"></div>
								</div>
							</div>
						</div>
					</div>
				{/each}
			</div>
		{:else if error}
			<div
				class="flex flex-col items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-10 text-center"
			>
				<div class="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
					<AlertCircle class="h-6 w-6 text-red-500" />
				</div>
				<p class="text-sm font-medium text-red-600">{error}</p>
			</div>
		{:else if laws.length === 0}
			<div
				class="flex flex-col items-center gap-4 rounded-xl border border-dashed border-sandstone-border bg-surface-1 p-14 text-center"
			>
				<div
					class="flex h-14 w-14 items-center justify-center rounded-2xl border border-sandstone-border bg-surface-2"
				>
					<Database class="h-7 w-7 text-primary/40" />
				</div>
				<div>
					<p class="text-base font-semibold text-slate-700">
						{isRTL ? 'لا توجد قوانين بعد' : 'Aucune loi indexée'}
					</p>
					<p class="mt-1 text-sm text-slate-500">
						{isRTL
							? 'ارفع وثيقة PDF جديدة لبدء بناء قاعدة المعرفة.'
							: 'Uploadez un nouveau document PDF pour commencer à alimenter la base.'}
					</p>
				</div>
			</div>
		{:else}
			<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
				{#each laws as doc (doc.law_name)}
					{@const color = domainColor(doc.domain)}
					<article
						class="rounded-xl border border-sandstone-border bg-surface-1 p-5 transition-all hover:border-primary/20 hover:shadow-md"
					>
						<!-- Card row: icon + info + status -->
						<div class="flex items-start gap-4">
							<div
								class="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
								style={`background: ${color}14; color: ${color};`}
							>
								<FileText size={20} />
							</div>
							<div class="min-w-0 flex-1">
								<div class="flex items-start justify-between gap-3">
									<div class="min-w-0">
										<h4 class="line-clamp-2 text-sm leading-snug font-bold text-slate-900">
											{doc.law_name}
										</h4>
										<!-- Domain + metadata inline -->
										<div class="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">
											<span
												class="inline-flex items-center rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wide uppercase"
												style={`background: ${color}14; color: ${color};`}
											>
												{doc.domain}
											</span>
											<span class="inline-flex items-center gap-1 text-xs text-slate-400">
												<Clock size={11} />
												{formatDate(doc.ingested_at)}
											</span>
											{#if doc.article_count > 0}
												<span class="inline-flex items-center gap-1 text-xs text-slate-400">
													<Activity size={11} />
													{doc.article_count}
													{t('articlesCount')}
												</span>
											{/if}
										</div>
									</div>
									<!-- Status pill -->
									<span
										class="inline-flex shrink-0 items-center gap-1 rounded-full border border-success/20 bg-success/10 px-2.5 py-1 text-[10px] font-semibold whitespace-nowrap text-success"
									>
										<CheckCircle2 size={9} />
										{t('statusActive')}
									</span>
								</div>
							</div>
						</div>

						<!-- Footer with toggle -->
						<div
							class="mt-4 flex items-center justify-between border-t border-sandstone-border pt-3"
						>
							<span class="text-[11px] text-slate-400">
								{isRTL ? 'حالة التضمين' : 'Indexation'}
							</span>
							<div
								class="flex h-5 w-9 cursor-pointer items-center rounded-full bg-primary p-0.5 transition-colors"
								role="switch"
								aria-checked="true"
								tabindex="0"
							>
								<div
									class="h-3.5 w-3.5 rounded-full bg-white shadow-sm"
									style="margin-inline-start: auto;"
								></div>
							</div>
						</div>
					</article>
				{/each}
			</div>
		{/if}
	</div>
</div>
