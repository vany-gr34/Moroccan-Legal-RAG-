<script lang="ts">
	import HistoryView from '$lib/components/HistoryView.svelte';
	import { appState } from '$lib/state.svelte';
</script>

<svelte:head>
	<title>History - Maroc Légal</title>
</svelte:head>

<HistoryView language={appState.language} />
