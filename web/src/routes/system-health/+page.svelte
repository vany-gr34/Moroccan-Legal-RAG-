<script lang="ts">
	import SystemHealthView from '$lib/components/SystemHealthView.svelte';
	import { appState } from '$lib/state.svelte';
</script>

<svelte:head>
	<title>System Health - Maroc Légal</title>
</svelte:head>

<SystemHealthView language={appState.language} />
