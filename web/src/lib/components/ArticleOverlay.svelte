<script lang="ts">
	import { X, ExternalLink } from 'lucide-svelte';
	import type { Language, SourceArticle } from '$lib/types';
	import { getTranslation } from '$lib/i18n';

	interface Props {
		language: Language;
		article: SourceArticle;
		onClose: () => void;
	}

	let { language, article, onClose }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	const maxLength = 300;
	let isExpanded = $state(false);
	const shouldTruncate = $derived(article.content?.length > maxLength);
</script>

<div class="fixed inset-0 z-50 flex">
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
		onclick={onClose}
		role="button"
		tabindex="0"
		aria-label="Close overlay"
		onkeydown={(e) => e.key === 'Escape' && onClose()}
	></div>

	<!-- Slide-over panel -->
	<div
		class={`fixed inset-y-0 ${isRTL ? 'left-0' : 'right-0'} w-full max-w-md bg-white shadow-2xl flex flex-col z-10 transform transition-transform duration-300 ease-in-out translate-x-0`}
	>
		<!-- Header -->
		<div class="flex items-center justify-between p-4 bg-primary text-white">
			<div class="flex items-center space-x-3">
				<h2 class="text-lg font-bold font-serif">{t('appTitle')}</h2>
			</div>
			<button
				onclick={onClose}
				class="p-2 -mr-2 text-white/70 hover:text-white rounded-md hover:bg-white/10 transition-colors rtl:-mr-0 rtl:-ml-2"
			>
				<X class="h-6 w-6" />
			</button>
		</div>

		<!-- Body -->
		<div class="flex-1 overflow-y-auto p-6 md:p-8 bg-sandstone">
			<div class="space-y-6">
				<div class="border-b border-sandstone-border pb-4">
					<h3 class="text-2xl font-bold font-serif text-slate-900 mb-2">{article.title}</h3>
					<p class="text-sm font-medium text-slate-500">{article.law}</p>
				</div>
				<div class="prose prose-blue max-w-none font-serif text-lg leading-relaxed whitespace-pre-wrap text-primary">
					{#if shouldTruncate && !isExpanded}
						{article.content.slice(0, maxLength)}...
					{:else}
						{article.content}
					{/if}
				</div>
				{#if shouldTruncate}
					<button
						onclick={() => isExpanded = !isExpanded}
						class="text-sm font-bold text-primary hover:opacity-80 transition-opacity"
					>
						{isExpanded ? (isRTL ? 'عرض أقل' : 'Read less') : (isRTL ? 'قراءة المزيد' : 'Read more')}
					</button>
				{/if}
			</div>
		</div>

		<!-- Footer -->
		<div class="p-4 bg-white border-t border-sandstone-border shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.05)]">
			<p class="text-sm text-slate-500 mb-4">{t('sourceDocument')} {article.law} - الصفحة 34</p>
			<button
				class="w-full flex items-center justify-center py-3 px-4 bg-primary hover:opacity-90 text-white rounded-lg font-medium transition-colors shadow-sm"
			>
				<ExternalLink class={`h-4 w-4 ${isRTL ? 'ml-2' : 'mr-2'}`} />
				{t('openFullDocument')}
			</button>
		</div>
	</div>
</div>
