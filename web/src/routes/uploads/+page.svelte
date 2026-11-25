<script lang="ts">
	import UploadView from '$lib/components/UploadView.svelte';
	import { appState } from '$lib/state.svelte';
</script>

<svelte:head>
	<title>{appState.language === 'ar' ? 'الوثائق المرفوعة' : 'Documents uploadés'} - Maroc Légal</title>
	<meta name="description" content="Upload and analyze Moroccan legal PDF documents" />
</svelte:head>

<UploadView language={appState.language} />
