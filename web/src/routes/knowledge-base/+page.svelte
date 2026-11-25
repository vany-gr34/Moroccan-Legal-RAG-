<script lang="ts">
	import KnowledgeBaseView from '$lib/components/KnowledgeBaseView.svelte';
	import { appState } from '$lib/state.svelte';
</script>

<svelte:head>
	<title>Knowledge Base - Maroc Légal</title>
</svelte:head>

<KnowledgeBaseView language={appState.language} />
