<script lang="ts">
	import UploadDetailView from '$lib/components/UploadDetailView.svelte';
	import { appState } from '$lib/state.svelte';
	import { page } from '$app/stores';

	const fileId = $derived($page.params.file_id ?? '');
	const filename = $derived($page.url.searchParams.get('filename') ?? undefined);
</script>

<svelte:head>
	<title>{appState.language === 'ar' ? 'المواد القانونية' : 'Articles juridiques'} - Maroc Légal</title>
	<meta name="description" content="View extracted legal articles from uploaded document" />
</svelte:head>

<UploadDetailView language={appState.language} fileId={fileId} filename={filename} />
