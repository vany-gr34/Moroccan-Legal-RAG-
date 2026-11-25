<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import Navbar from '$lib/components/Navbar.svelte';
	import ArticleOverlay from '$lib/components/ArticleOverlay.svelte';
	import { appState } from '$lib/state.svelte';

	let { children } = $props();

	// Sync RTL direction with the document when language changes
	$effect(() => {
		document.documentElement.dir = appState.language === 'ar' ? 'rtl' : 'ltr';
		document.documentElement.lang = appState.language;
	});
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
	<meta name="theme-color" content="#1A237E" />
</svelte:head>

<div class="h-screen flex flex-col bg-sandstone text-primary overflow-hidden">
	<Navbar />

	<main class="flex-1 flex flex-col relative overflow-y-auto">
		{@render children()}
	</main>

	{#if appState.selectedArticle}
		<ArticleOverlay
			language={appState.language}
			article={appState.selectedArticle}
			onClose={() => (appState.selectedArticle = null)}
		/>
	{/if}
</div>
