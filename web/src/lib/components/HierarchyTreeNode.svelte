<script lang="ts">
	import {
		Library,
		Layers,
		SplitSquareHorizontal,
		ScrollText,
		Tag,
		FileText,
		ChevronRight,
		ChevronDown,
		Copy,
		Check
	} from 'lucide-svelte';
	import type { HierarchyNode } from '$lib/types';

	interface Props {
		node: HierarchyNode;
		depth?: number;
		isRTL?: boolean;
		copyLabel?: string;
		copiedLabel?: string;
	}

	let { node, depth = 0, isRTL = false, copyLabel = 'Copy', copiedLabel = 'Copied!' }: Props = $props();

	let isOpen = $state(depth < 2); // auto-expand first 2 levels
	let isCopied = $state(false);

	// Level → visual config
	const levelConfig: Record<string, { color: string; bg: string; border: string; label_ar: string; label_fr: string }> = {
		book:       { color: 'text-primary',    bg: 'bg-primary/8',    border: 'border-primary/20',    label_ar: 'كتاب',    label_fr: 'Livre' },
		section:    { color: 'text-indigo-600', bg: 'bg-indigo-50',    border: 'border-indigo-200',    label_ar: 'باب',     label_fr: 'Titre' },
		subsection: { color: 'text-violet-600', bg: 'bg-violet-50',    border: 'border-violet-200',    label_ar: 'قسم فرعي', label_fr: 'Sous-titre' },
		chapter:    { color: 'text-amber-600',  bg: 'bg-amber-50',     border: 'border-amber-200',     label_ar: 'فصل',     label_fr: 'Chapitre' },
		branch:     { color: 'text-rose-500',   bg: 'bg-rose-50',      border: 'border-rose-200',      label_ar: 'فرع',     label_fr: 'Section' },
		article:    { color: 'text-slate-700',  bg: 'bg-white',        border: 'border-sandstone-border', label_ar: 'مادة',  label_fr: 'Article' },
	};

	const cfg = $derived(levelConfig[node.level] ?? levelConfig.article);
	const hasChildren = $derived(node.children && node.children.length > 0);
	const isArticle = $derived(node.level === 'article');
	const indentPx = $derived(Math.min(depth * 20, 80));

	async function copyText() {
		const text = node.text_preview ?? node.title ?? '';
		try {
			await navigator.clipboard.writeText(text);
			isCopied = true;
			setTimeout(() => (isCopied = false), 2000);
		} catch {}
	}

	function toggle() {
		if (!isArticle) isOpen = !isOpen;
	}
</script>

<div
	class="group"
	style={`margin-${isRTL ? 'right' : 'left'}: ${indentPx}px`}
>
	<!-- Node row -->
	<div
		class={`flex items-start gap-2.5 rounded-xl border px-3 py-2.5 mb-1.5 transition-all
			${cfg.bg} ${cfg.border}
			${!isArticle ? 'cursor-pointer hover:brightness-95' : 'cursor-default'}`}
		role={!isArticle ? 'button' : undefined}
		tabindex={!isArticle ? 0 : undefined}
		onclick={toggle}
		onkeydown={(e) => e.key === 'Enter' && toggle()}
	>
		<!-- Expand/collapse chevron for containers -->
		<span class="mt-0.5 shrink-0 w-4 h-4">
			{#if !isArticle && hasChildren}
				{#if isOpen}
					<ChevronDown class={`h-4 w-4 ${cfg.color}`} />
				{:else}
					<ChevronRight class={`h-4 w-4 ${cfg.color} ${isRTL ? 'rotate-180' : ''}`} />
				{/if}
			{:else if isArticle}
				<FileText class="h-4 w-4 text-slate-400" />
			{/if}
		</span>

		<!-- Level icon -->
		<span class="mt-0.5 shrink-0">
			{#if node.level === 'book'}
				<Library class={`h-4 w-4 ${cfg.color}`} />
			{:else if node.level === 'section'}
				<Layers class={`h-4 w-4 ${cfg.color}`} />
			{:else if node.level === 'subsection'}
				<SplitSquareHorizontal class={`h-4 w-4 ${cfg.color}`} />
			{:else if node.level === 'chapter'}
				<ScrollText class={`h-4 w-4 ${cfg.color}`} />
			{:else if node.level === 'branch'}
				<Tag class={`h-4 w-4 ${cfg.color}`} />
			{/if}
		</span>

		<!-- Content -->
		<div class={`min-w-0 flex-1 ${isRTL ? 'text-right' : 'text-left'}`} dir={isRTL ? 'rtl' : 'ltr'}>
			{#if isArticle}
				<!-- Article leaf -->
				<div class="flex items-start justify-between gap-3">
					<div class="min-w-0 flex-1">
						<span class={`inline-block mb-1 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${cfg.bg} ${cfg.color} border ${cfg.border}`}>
							{isRTL ? cfg.label_ar : cfg.label_fr} {node.article_number ?? ''}
						</span>
						{#if node.text_preview}
							<p class="text-xs leading-relaxed text-slate-600">{node.text_preview}</p>
						{/if}
					</div>
					<button
						onclick={(e) => { e.stopPropagation(); copyText(); }}
						class={`shrink-0 flex items-center gap-1 rounded-lg px-2 py-1 text-[10px] font-medium transition-all
							${isCopied ? 'bg-green-100 text-green-700' : 'text-slate-400 hover:bg-slate-100 hover:text-slate-600'}`}
						title={copyLabel}
					>
						{#if isCopied}
							<Check class="h-3 w-3" />{copiedLabel}
						{:else}
							<Copy class="h-3 w-3" />
						{/if}
					</button>
				</div>
			{:else}
				<!-- Container heading -->
				<div class="flex items-center gap-2">
					<span class={`shrink-0 text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border ${cfg.bg} ${cfg.color} ${cfg.border}`}>
						{isRTL ? cfg.label_ar : cfg.label_fr}
					</span>
					<span class={`text-sm font-semibold leading-snug ${cfg.color}`}>
						{node.title ?? ''}
					</span>
					{#if hasChildren}
						<span class="ml-auto shrink-0 text-[10px] font-medium text-slate-400">
							{node.children.length}
						</span>
					{/if}
				</div>
			{/if}
		</div>
	</div>

	<!-- Recursive children -->
	{#if !isArticle && isOpen && hasChildren}
		<div class={`border-${isRTL ? 'r' : 'l'}-2 border-sandstone-border mb-1`}
			 style={`margin-${isRTL ? 'right' : 'left'}: 10px; padding-${isRTL ? 'right' : 'left'}: 8px`}>
			{#each node.children as child (child.level + (child.title ?? '') + (child.article_number ?? ''))}
				<svelte:self
					node={child}
					depth={depth + 1}
					{isRTL}
					{copyLabel}
					{copiedLabel}
				/>
			{/each}
		</div>
	{/if}
</div>
