<script lang="ts">
	import ResultsView from '$lib/components/ResultsView.svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { appState } from '$lib/state.svelte';
	import type { AskRequest, AskResponse, AskSource } from '$lib/types';
	import { PUBLIC_API_ENDPOIT } from '$env/static/public';
	import { Loader2 } from 'lucide-svelte';

	// Two modes:
	//   ?q=...&domain=...        → ask a new question via /ask
	//   ?session_id=...          → load a stored result from /conversations/{id}/response
	let query = $derived($page.url.searchParams.get('q') || '');
	let domain = $derived($page.url.searchParams.get('domain') || 'all');
	let historySessionId = $derived($page.url.searchParams.get('session_id') || null);

	let isLoading = $state(false);
	let errorMsg = $state<string | null>(null);
	let rawResponse = $state<AskResponse | null>(null);

	const isRTL = $derived(appState.language === 'ar');

	$effect(() => {
		if (historySessionId) {
			loadFromHistory(historySessionId);
		} else if (query) {
			fetchAnswer();
		}
	});

	/** Load a stored Q&A result from the DB by session_id */
	async function loadFromHistory(sessionId: string) {
		isLoading = true;
		errorMsg = null;
		rawResponse = null;
		try {
			const res = await fetch(`${PUBLIC_API_ENDPOIT}/conversations/${sessionId}/response`);
			if (!res.ok) {
				const errText = await res.text();
				throw new Error(`${res.statusText} - ${errText}`);
			}
			rawResponse = await res.json();
		} catch (err: any) {
			errorMsg = err.message || 'Failed to load conversation from history.';
		} finally {
			isLoading = false;
		}
	}

	/** Ask a new question via /ask */
	async function fetchAnswer() {
		isLoading = true;
		errorMsg = null;
		rawResponse = null;

		const requestBody: AskRequest = { query, top_k: 5 };
		if (domain && domain !== 'all') {
			requestBody.domain = domain;
		}

		try {
			const res = await fetch(PUBLIC_API_ENDPOIT + '/ask', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(requestBody)
			});

			if (!res.ok) {
				const errText = await res.text();
				throw new Error(`API error: ${res.statusText} - ${errText}`);
			}

			rawResponse = await res.json();
		} catch (err: any) {
			errorMsg = err.message || 'An error occurred while fetching the answer.';
		} finally {
			isLoading = false;
		}
	}

	function handleBack() {
		// If we came from history, go back to history; otherwise go home
		if (historySessionId) {
			goto('/history');
		} else {
			goto('/');
		}
	}

	function handleSourceClick(article: AskSource) {
		appState.selectedArticle = {
			id: `${article.article_number}-${article.law_name}`,
			title: `${isRTL ? 'المادة' : 'Article'} ${article.article_number} - ${article.law_name}`,
			content: article.text_full || article.text_preview,
			law: article.law_name,
			snippet: article.text_preview,
			relevance: article.relevance_score
		};
	}
</script>

<svelte:head>
	<title>
		{historySessionId
			? isRTL
				? 'عرض المحادثة - المغرب القانوني'
				: 'View Result - Maroc Légal'
			: 'Results - Maroc Légal'}
	</title>
</svelte:head>

{#if isLoading}
	<div
		class="flex h-full flex-1 flex-col items-center justify-center gap-4 bg-surface-0 text-primary"
	>
		<div class="flex flex-col items-center gap-3">
			<Loader2 class="h-10 w-10 animate-spin text-primary/60" />
			<p class="text-base font-medium text-slate-600">
				{historySessionId
					? isRTL
						? 'جاري تحميل المحادثة...'
						: 'Loading conversation...'
					: isRTL
						? 'جاري تحليل سؤالك...'
						: 'Analyzing your query...'}
			</p>
		</div>
		<!-- Skeleton hints -->
		<div class="mt-4 w-80 space-y-3">
			<div class="h-4 w-full rounded bg-surface-3"></div>
			<div class="h-4 w-3/4 rounded bg-surface-3"></div>
			<div class="h-4 w-5/6 rounded bg-surface-3"></div>
		</div>
	</div>
{:else if errorMsg}
	<div class="flex h-full flex-1 items-center justify-center bg-surface-0 p-8">
		<div class="max-w-lg rounded-xl border border-red-200 bg-red-50 p-6 text-center text-red-700">
			<div class="mb-3 flex justify-center">
				<div class="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
					<svg class="h-6 w-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"
						><path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
						/></svg
					>
				</div>
			</div>
			<h2 class="mb-1 text-lg font-bold">{isRTL ? 'حدث خطأ' : 'Error'}</h2>
			<p class="text-sm opacity-80">{errorMsg}</p>
			<button
				onclick={handleBack}
				class="mt-4 rounded-lg bg-red-100 px-5 py-2 text-sm font-medium transition-colors hover:bg-red-200"
			>
				{isRTL ? 'العودة' : 'Go back'}
			</button>
		</div>
	</div>
{:else if rawResponse}
	<ResultsView
		language={appState.language}
		domain={domain || rawResponse.query}
		response={rawResponse}
		onSourceClick={handleSourceClick}
		onBack={handleBack}
		isHistoryView={!!historySessionId}
	/>
{:else}
	<div class="flex h-full flex-col items-center justify-center bg-surface-0 p-8">
		<div
			class="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl border border-sandstone-border bg-surface-1"
		>
			<svg class="h-7 w-7 text-primary/30" fill="none" stroke="currentColor" viewBox="0 0 24 24"
				><path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="1.5"
					d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
				/></svg
			>
		</div>
		<p class="mb-3 text-base font-medium text-slate-500">
			{isRTL ? 'لم يتم تقديم أي سؤال.' : 'No query provided.'}
		</p>
		<button onclick={handleBack} class="text-sm font-semibold text-primary hover:underline">
			{isRTL ? 'العودة للصفحة الرئيسية' : 'Go back to home'}
		</button>
	</div>
{/if}
