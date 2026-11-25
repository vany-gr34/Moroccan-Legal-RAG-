<script lang="ts">
	import type { RawSearchResult } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { appState } from '$lib/state.svelte';
	import { ChevronDown, ChevronUp, FileText } from 'lucide-svelte';

	interface Props {
		result: RawSearchResult;
		rank: number;
	}

	let { result, rank }: Props = $props();

	let expanded = $state(false);

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(appState.language, key);
	const isRTL = $derived(appState.language === 'ar');

	const truncatedText = $derived(
		result.text.length > 220 && !expanded ? result.text.slice(0, 220) + '…' : result.text
	);

	// Map similarity to a color tier
	const relevanceTier = $derived(
		result.similarity >= 0.5 ? 'high' : result.similarity >= 0.2 ? 'medium' : 'low'
	);

	const relevanceColor = $derived(
		relevanceTier === 'high'
			? 'bg-green-50 text-green-700 border-green-200'
			: relevanceTier === 'medium'
				? 'bg-amber-50 text-amber-700 border-amber-200'
				: 'bg-slate-50 text-slate-500 border-slate-200'
	);

	// ── Domain → color mapping for left border ──
	const domainBorderColor = $derived(
		(
			{
				criminal: '#b91c1c',
				traffic: '#b45309',
				family: '#7c3aed',
				civil: '#0369a1',
				commercial: '#0f766e',
				procedure: '#475569',
				violations: '#b91c1c'
			} as Record<string, string>
		)[result.domain] || 'transparent'
	);

	// Score as percentage (0–100)
	const scorePct = $derived(Math.round(result.similarity * 100));
</script>

<article
	class="group overflow-hidden rounded-xl border border-sandstone-border bg-surface-1 transition-all hover:shadow-md"
	style={domainBorderColor !== 'transparent'
		? `box-shadow: inset 3px 0 0 0 ${domainBorderColor}, 0 1px 3px rgba(0,0,0,0.06);`
		: ''}
>
	<!-- Card Header -->
	<div class="flex items-start justify-between gap-4 p-5 pb-3">
		<!-- Rank + Article Info -->
		<div class="flex min-w-0 items-start gap-3">
			<!-- Rank badge -->
			<div
				class="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-primary/10 text-xs font-bold text-primary"
				title="Result rank"
			>
				{rank}
			</div>
			<div class="min-w-0">
				<h3 class="text-lg leading-tight font-bold text-primary" dir="auto">
					{result.article_number}
				</h3>
				<p class="mt-0.5 text-sm leading-snug font-medium text-slate-600" dir="auto">
					{result.law_name}
				</p>
			</div>
		</div>

		<!-- Relevance Score + Visual Bar -->
		<div class="flex shrink-0 flex-col items-end gap-1.5">
			<span
				class="inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-bold {relevanceColor}"
			>
				{scorePct}%
			</span>
			<div class="score-bar" title="{scorePct}% pertinence">
				<div class="score-fill" style="width: {scorePct}%"></div>
			</div>
		</div>
	</div>

	<!-- Breadcrumb trail -->
	{#if result.section_title || result.chapter_title}
		<div class="px-5 pb-3">
			<div
				class="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[11px] leading-tight text-slate-400"
				dir="auto"
			>
				{#if result.section_title}
					<span class="max-w-50 truncate">{result.section_title}</span>
				{/if}
				{#if result.section_title && result.chapter_title}
					<span class="font-light opacity-40">/</span>
				{/if}
				{#if result.chapter_title}
					<span class="max-w-50 truncate">{result.chapter_title}</span>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Divider -->
	<div class="mx-5 h-px bg-sandstone-border"></div>

	<!-- Text Content -->
	<div class="px-5 py-4">
		<p class="text-sm leading-relaxed whitespace-pre-wrap text-slate-700" dir="auto">
			{truncatedText}
		</p>

		{#if result.text.length > 220}
			<button
				onclick={() => (expanded = !expanded)}
				class="mt-3 flex items-center gap-1 text-xs font-semibold text-primary transition-colors hover:text-blue-900"
			>
				{expanded ? t('readLess') : t('readMore')}
				{#if expanded}
					<ChevronUp size={14} />
				{:else}
					<ChevronDown size={14} />
				{/if}
			</button>
		{/if}
	</div>

	<!-- Card Footer -->
	<div
		class="flex items-center gap-2 border-t border-sandstone-border bg-surface-2/60 px-5 py-2.5 text-[11px] text-slate-400 transition-colors group-hover:bg-surface-2"
	>
		<FileText size={12} class="shrink-0" />
		<span class="truncate font-mono" dir="ltr">{result.source_file}</span>
	</div>
</article>

<style>
	/* ── Score bar ── */
	.score-bar {
		height: 3px;
		background: #e2e8f0;
		border-radius: 2px;
		width: 48px;
		overflow: hidden;
	}
	.score-fill {
		height: 100%;
		background: #1a237e;
		border-radius: 2px;
	}
</style>
