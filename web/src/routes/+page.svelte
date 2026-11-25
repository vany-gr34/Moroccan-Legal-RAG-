<script lang="ts">
	import HomeView from '$lib/components/HomeView.svelte';
	import { goto } from '$app/navigation';
	import { appState } from '$lib/state.svelte';

	function handleSearch(query: string, domain: string) {
		const searchParams = new URLSearchParams({ q: query, domain });
		goto(`/results?${searchParams.toString()}`);
	}
</script>

<svelte:head>
	<title>المغرب القانوني · Maroc Légal</title>
	<meta
		name="description"
		content="منصة ذكية للبحث في القانون المغربي · Plateforme intelligente de recherche juridique marocaine"
	/>
</svelte:head>

<HomeView language={appState.language} onSearch={handleSearch} />

