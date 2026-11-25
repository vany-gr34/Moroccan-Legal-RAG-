<script lang="ts">
	import {
		UploadCloud,
		FileText,
		Trash2,
		Eye,
		CheckCircle2,
		Clock,
		AlertCircle,
		Loader2,
		FilePlus2,
		BookOpen,
		X,
		RefreshCw,
		Hourglass
	} from 'lucide-svelte';
	import type { Language, UploadedFile } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { listUploads, deleteUpload, uploadPdf, getUploadStatus } from '$lib/upload';
	import { onMount, onDestroy } from 'svelte';
	import { goto } from '$app/navigation';

	interface Props {
		language: Language;
	}

	let { language }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	// ── List state ───────────────────────────────────────────────────────────
	let uploads = $state<UploadedFile[]>([]);
	let isLoading = $state(true);
	let listError = $state<string | null>(null);

	// ── Dropzone / upload state ───────────────────────────────────────────────
	let isDragging = $state(false);
	let selectedFile = $state<File | null>(null);

	type UploadPhase =
		| 'idle'
		| 'uploading' // POST /upload in flight
		| 'processing' // polling status
		| 'done'
		| 'error';

	let uploadPhase = $state<UploadPhase>('idle');
	let uploadError = $state<string | null>(null);
	let processingFileId = $state<string | null>(null);
	let processingProgress = $state(0); // 0-100 cosmetic progress
	let processingArticleCount = $state(0);

	// ── Delete confirmation ───────────────────────────────────────────────────
	let deleteConfirm = $state<string | null>(null);

	// ── Polling timer ─────────────────────────────────────────────────────────
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	// Track which file_ids in the list are still processing so we auto-refresh
	let processingIds = $state<Set<string>>(new Set());
	let listPollInterval: ReturnType<typeof setInterval> | null = null;

	let fileInput: HTMLInputElement;

	onMount(async () => {
		await loadUploads();
	});

	onDestroy(() => {
		clearPollInterval();
		clearListPoll();
	});

	// ── Load list ─────────────────────────────────────────────────────────────
	async function loadUploads() {
		isLoading = true;
		listError = null;
		try {
			const data = await listUploads();
			uploads = data.files;
			// Start list-level polling for any files still processing
			const processing = new Set(data.files.filter((f) => f.processing).map((f) => f.file_id));
			processingIds = processing;
			if (processing.size > 0) startListPoll();
		} catch (e: any) {
			listError = e.message;
		} finally {
			isLoading = false;
		}
	}

	// ── List-level polling (refresh list every 3 s while files are processing) ─
	function startListPoll() {
		clearListPoll();
		listPollInterval = setInterval(async () => {
			try {
				const data = await listUploads();
				uploads = data.files;
				const stillProcessing = new Set(
					data.files.filter((f) => f.processing).map((f) => f.file_id)
				);
				processingIds = stillProcessing;
				if (stillProcessing.size === 0) clearListPoll();
			} catch {}
		}, 3000);
	}

	function clearListPoll() {
		if (listPollInterval !== null) {
			clearInterval(listPollInterval);
			listPollInterval = null;
		}
	}

	// ── Upload-flow polling ───────────────────────────────────────────────────
	function clearPollInterval() {
		if (pollInterval !== null) {
			clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	/**
	 * After POST /upload returns, poll GET /uploads/{file_id}/status
	 * every 2.5 s until status=="done" or "error".
	 */
	function startPolling(fileId: string) {
		processingFileId = fileId;
		uploadPhase = 'processing';
		processingProgress = 5;

		// Cosmetic progress: creep toward 90% over ~30s
		const progressTimer = setInterval(() => {
			if (processingProgress < 90) processingProgress += 2;
		}, 700);

		clearPollInterval();
		pollInterval = setInterval(async () => {
			try {
				const status = await getUploadStatus(fileId);
				if (status.status === 'done') {
					clearPollInterval();
					clearInterval(progressTimer);
					processingProgress = 100;
					processingArticleCount = status.article_count;
					uploadPhase = 'done';
					selectedFile = null;
					if (fileInput) fileInput.value = '';
					await loadUploads();
					// Auto-reset after 4 s
					setTimeout(() => {
						if (uploadPhase === 'done') {
							uploadPhase = 'idle';
							processingFileId = null;
							processingProgress = 0;
						}
					}, 4000);
				} else if (status.status === 'error') {
					clearPollInterval();
					clearInterval(progressTimer);
					processingProgress = 0;
					uploadPhase = 'error';
					uploadError = status.error ?? (isRTL ? 'حدث خطأ أثناء المعالجة' : 'Processing failed');
					await loadUploads();
				}
			} catch {
				// network blip — keep polling
			}
		}, 2500);
	}

	// ── Handlers ─────────────────────────────────────────────────────────────
	function onDragOver(e: DragEvent) {
		e.preventDefault();
		isDragging = true;
	}
	function onDragLeave() {
		isDragging = false;
	}
	function onDrop(e: DragEvent) {
		e.preventDefault();
		isDragging = false;
		const file = e.dataTransfer?.files[0];
		if (file?.type === 'application/pdf') selectedFile = file;
	}
	function onFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		selectedFile = input.files?.[0] ?? null;
	}
	function clearFile() {
		selectedFile = null;
		uploadPhase = 'idle';
		uploadError = null;
		if (fileInput) fileInput.value = '';
	}

	async function handleUpload() {
		if (!selectedFile) return;
		uploadPhase = 'uploading';
		uploadError = null;
		try {
			const response = await uploadPdf(selectedFile);
			// File saved — now poll for background processing
			startPolling(response.file_id);
		} catch (e: any) {
			uploadPhase = 'error';
			uploadError = e.message;
		}
	}

	async function handleDelete(fileId: string) {
		if (deleteConfirm !== fileId) {
			deleteConfirm = fileId;
			return;
		}
		try {
			await deleteUpload(fileId);
			uploads = uploads.filter((u) => u.file_id !== fileId);
		} catch (e: any) {
			listError = e.message;
		} finally {
			deleteConfirm = null;
		}
	}

	function formatDate(dateString: string) {
		return new Date(dateString).toLocaleDateString(isRTL ? 'ar-MA' : 'fr-FR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	function formatFileSize(bytes?: number) {
		if (!bytes) return '';
		if (bytes < 1024) return `${bytes} B`;
		if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
		return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
	}
</script>

<div class="mx-auto w-full max-w-4xl flex-1 space-y-6 px-4 py-8">
	<!-- Page header -->
	<div class="flex items-start justify-between border-b border-sandstone-border pb-5">
		<div>
			<h1 class="font-serif text-2xl font-bold text-slate-900">{t('uploadPageTitle')}</h1>
			<p class="mt-1 text-sm text-slate-500">{t('uploadPageSubtitle')}</p>
		</div>
		<div
			class="inline-flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-bold text-primary"
		>
			<FilePlus2 class="h-3.5 w-3.5" />
			<span>PDF</span>
		</div>
	</div>

	<!-- ── Upload dropzone ─────────────────────────────────────────────────── -->
	<div
		role="button"
		tabindex="0"
		aria-label="Upload zone"
		class={`group relative flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-10 text-center
			${isDragging ? 'border-primary bg-primary/5' : 'border-sandstone-border bg-surface-1 hover:border-primary/40 hover:bg-surface-2'}
			${uploadPhase === 'done' ? 'border-green-400 bg-green-50' : ''}
			${uploadPhase === 'error' ? 'border-red-300 bg-red-50/60' : ''}
			${uploadPhase === 'processing' || uploadPhase === 'uploading' ? 'pointer-events-none cursor-default border-primary/40 bg-primary/5' : ''}`}
		ondragover={onDragOver}
		ondragleave={onDragLeave}
		ondrop={onDrop}
		onclick={() => uploadPhase === 'idle' && !selectedFile && fileInput?.click()}
		onkeydown={(e) =>
			e.key === 'Enter' && uploadPhase === 'idle' && !selectedFile && fileInput?.click()}
	>
		<input
			bind:this={fileInput}
			type="file"
			accept="application/pdf"
			class="sr-only"
			onchange={onFileChange}
		/>

		<!-- ── Phase: done ── -->
		{#if uploadPhase === 'done'}
			<div class="flex flex-col items-center gap-3">
				<div class="rounded-full bg-green-100 p-4">
					<CheckCircle2 class="h-8 w-8 text-green-600" />
				</div>
				<p class="text-base font-bold text-green-700">{t('uploadSuccess')}</p>
				{#if processingArticleCount > 0}
					<p class="text-sm text-green-600">
						{processingArticleCount}
						{t('articlesFound')}
					</p>
				{/if}
			</div>

			<!-- ── Phase: uploading (POST in flight) ── -->
		{:else if uploadPhase === 'uploading'}
			<div class="flex flex-col items-center gap-3">
				<div class="rounded-full bg-primary/10 p-4">
					<Loader2 class="h-8 w-8 animate-spin text-primary" />
				</div>
				<p class="font-semibold text-primary">
					{isRTL ? 'جارٍ رفع الملف...' : 'Envoi du fichier...'}
				</p>
			</div>

			<!-- ── Phase: processing (background polling) ── -->
		{:else if uploadPhase === 'processing'}
			<div class="flex w-full max-w-sm flex-col items-center gap-4">
				<div class="relative">
					<div class="rounded-full bg-primary/10 p-4">
						<Hourglass class="h-8 w-8 text-primary" style="animation: spin 3s linear infinite;" />
					</div>
					<div
						class="absolute -inset-e-1 -top-1 flex h-5 w-5 items-center justify-center rounded-full bg-primary"
					>
						<span class="text-[9px] font-bold text-white">{processingProgress}%</span>
					</div>
				</div>
				<div class="space-y-1 text-center">
					<p class="font-semibold text-primary">{t('uploading')}</p>
					<p class="text-xs text-slate-400">
						{isRTL
							? 'استخراج النصوص، التنظيف، التحليل... يرجى الانتظار'
							: 'Extraction, nettoyage, analyse… veuillez patienter'}
					</p>
				</div>
				<!-- Progress bar -->
				<div class="h-1.5 w-full overflow-hidden rounded-full bg-primary/15">
					<div class="h-full rounded-full bg-primary" style="width: {processingProgress}%"></div>
				</div>
			</div>

			<!-- ── Phase: error ── -->
		{:else if uploadPhase === 'error'}
			<div class="flex flex-col items-center gap-3">
				<div class="rounded-full bg-red-100 p-4">
					<AlertCircle class="h-8 w-8 text-red-500" />
				</div>
				<p class="font-semibold text-red-700">{t('uploadError')}</p>
				{#if uploadError}
					<p class="max-w-xs rounded-lg bg-red-50 px-4 py-2 text-xs text-red-600">{uploadError}</p>
				{/if}
				<button
					onclick={(e) => {
						e.stopPropagation();
						clearFile();
					}}
					class="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-surface-1 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-surface-2"
				>
					<RefreshCw class="h-4 w-4" />
					{isRTL ? 'حاول مجددًا' : 'Réessayer'}
				</button>
			</div>

			<!-- ── Phase: file selected, not yet uploading ── -->
		{:else if selectedFile}
			<div class="flex w-full flex-col items-center gap-4">
				<div class="rounded-full bg-primary/10 p-3">
					<FileText class="h-8 w-8 text-primary" />
				</div>
				<div class="space-y-1 text-center">
					<p class="text-xs font-medium tracking-wider text-slate-400 uppercase">
						{t('selectedFile')}
					</p>
					<p class="text-sm font-bold text-slate-800">{selectedFile.name}</p>
					<p class="text-xs text-slate-400">{formatFileSize(selectedFile.size)}</p>
				</div>
				<div class="flex gap-3">
					<button
						onclick={(e) => {
							e.stopPropagation();
							clearFile();
						}}
						class="inline-flex items-center gap-1.5 rounded-lg border border-sandstone-border bg-surface-1 px-4 py-2 text-sm font-medium text-slate-600 hover:bg-surface-2"
					>
						<X class="h-4 w-4" />
						{t('cancel')}
					</button>
					<button
						onclick={(e) => {
							e.stopPropagation();
							handleUpload();
						}}
						class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-5 py-2 text-sm font-semibold text-white shadow-sm hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)]"
					>
						<UploadCloud class="h-4 w-4" />
						{t('uploadStart')}
					</button>
				</div>
			</div>

			<!-- ── Phase: idle ── -->
		{:else}
			<div class="flex flex-col items-center gap-3">
				<div class="rounded-full bg-primary/10 p-4">
					<UploadCloud class="h-8 w-8 text-primary" />
				</div>
				<div class="space-y-1">
					<p class="text-base font-semibold text-slate-800">
						{isDragging ? t('dropzoneActive') : t('dropzoneTitle')}
					</p>
					<p class="text-sm text-slate-400">{t('dropzoneSubtitle')}</p>
				</div>
			</div>
		{/if}
	</div>

	<!-- ── Uploads list ───────────────────────────────────────────────────── -->
	<div class="overflow-hidden rounded-2xl border border-sandstone-border bg-surface-1">
		<div
			class="flex items-center justify-between border-b border-sandstone-border bg-surface-2 px-6 py-4"
		>
			<h3 class="font-semibold text-slate-900">{t('uploadsListTitle')}</h3>
			<div class="flex items-center gap-3">
				{#if processingIds.size > 0}
					<span class="flex items-center gap-1.5 text-xs text-primary">
						<Loader2 class="h-3 w-3 animate-spin" />
						{isRTL ? 'يتم المعالجة...' : 'Traitement en cours...'}
					</span>
				{/if}
				{#if !isLoading}
					<span class="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-bold text-primary">
						{uploads.length}
					</span>
				{/if}
			</div>
		</div>

		{#if isLoading}
			<div class="divide-y divide-sandstone-border">
				{#each [1, 2, 3] as _}
					<div class="flex items-center gap-4 px-6 py-5">
						<div class="h-11 w-11 shrink-0 rounded-xl bg-surface-3"></div>
						<div class="min-w-0 flex-1 space-y-2">
							<div class="h-4 w-48 rounded bg-surface-3"></div>
							<div class="h-3 w-32 rounded bg-surface-3"></div>
						</div>
						<div class="h-8 w-20 rounded-lg bg-surface-3"></div>
					</div>
				{/each}
			</div>
		{:else if listError}
			<div class="flex items-center gap-3 p-8 text-red-600">
				<AlertCircle class="h-5 w-5 shrink-0" />
				<span class="text-sm">{listError}</span>
			</div>
		{:else if uploads.length === 0}
			<div class="flex flex-col items-center gap-4 py-16 text-center">
				<div
					class="flex h-14 w-14 items-center justify-center rounded-2xl border border-sandstone-border bg-surface-2"
				>
					<BookOpen class="h-7 w-7 text-primary/40" />
				</div>
				<div>
					<p class="text-sm font-semibold text-slate-600">{t('noUploads')}</p>
					<p class="mt-1 text-xs text-slate-400">
						{isRTL ? 'ارفع ملف PDF للبدء' : 'Uploadez un PDF pour commencer'}
					</p>
				</div>
			</div>
		{:else}
			<div class="divide-y divide-sandstone-border">
				{#each uploads as upload (upload.file_id)}
					<div
						class="group flex items-center justify-between gap-4 px-6 py-5 transition-colors hover:bg-surface-2"
					>
						<!-- Left: icon + info -->
						<div class="flex min-w-0 flex-1 items-start gap-4">
							<div
								class={`shrink-0 rounded-xl p-2.5
								${upload.processed ? 'bg-success/10 text-success' : ''}
								${upload.processing ? 'bg-primary/10 text-primary' : ''}
								${upload.error ? 'bg-red-50 text-red-400' : ''}
								${!upload.processed && !upload.processing && !upload.error ? 'bg-surface-3 text-slate-400' : ''}`}
							>
								{#if upload.processing}
									<Loader2 class="h-6 w-6 animate-spin" />
								{:else}
									<FileText class="h-6 w-6" />
								{/if}
							</div>

							<div class="min-w-0 flex-1">
								<p class="truncate font-semibold text-slate-800" title={upload.original_filename}>
									{upload.original_filename}
								</p>
								<div class="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-400">
									<span class="flex items-center gap-1">
										<Clock class="h-3 w-3" />
										{formatDate(upload.uploaded_at)}
									</span>
									{#if upload.size_bytes}
										<span>{formatFileSize(upload.size_bytes)}</span>
									{/if}
									{#if upload.processed && upload.article_count > 0}
										<span class="font-medium text-primary">
											{upload.article_count}
											{t('articlesFound')}
										</span>
									{/if}
									{#if upload.error}
										<span class="text-red-500">{upload.error}</span>
									{/if}
								</div>
							</div>
						</div>

						<!-- Right: status badge + actions -->
						<div class="flex shrink-0 items-center gap-2">
							<!-- Status badge -->
							{#if upload.processing}
								<span
									class="hidden items-center gap-1 rounded-full border border-primary/20 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary sm:inline-flex"
								>
									<Loader2 class="h-3 w-3 animate-spin" />
									{isRTL ? 'يعالج...' : 'Traitement...'}
								</span>
							{:else if upload.error}
								<span
									class="hidden items-center gap-1 rounded-full border border-red-200 bg-red-50 px-2.5 py-1 text-xs font-medium text-red-600 sm:inline-flex"
								>
									<AlertCircle class="h-3 w-3" />
									{isRTL ? 'خطأ' : 'Erreur'}
								</span>
							{:else if upload.processed}
								<span
									class="hidden items-center gap-1 rounded-full border border-success/20 bg-success/10 px-2.5 py-1 text-xs font-medium text-success sm:inline-flex"
								>
									<CheckCircle2 class="h-3 w-3" />
									{t('processed')}
								</span>
							{:else}
								<span
									class="hidden items-center gap-1 rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-600 sm:inline-flex"
								>
									<AlertCircle class="h-3 w-3" />
									{t('unprocessed')}
								</span>
							{/if}

							<!-- View articles -->
							{#if upload.processed}
								<button
									onclick={() =>
										goto(
											`/uploads/${upload.file_id}?filename=${encodeURIComponent(upload.original_filename)}`
										)}
									class="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:bg-[#283593] active:bg-[#1a237e] active:shadow-[inset_0_2px_4px_rgba(0,0,0,0.15)]"
								>
									<Eye class="h-3.5 w-3.5" />
									{t('viewArticles')}
								</button>
							{/if}

							<!-- Delete with 2-step confirm -->
							{#if deleteConfirm === upload.file_id}
								<div
									class="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5"
								>
									<span class="text-xs font-medium text-red-700"
										>{isRTL ? 'تأكيد؟' : 'Confirmer ?'}</span
									>
									<button
										onclick={() => handleDelete(upload.file_id)}
										class="text-xs font-bold text-red-600 hover:text-red-800"
										>{isRTL ? 'نعم' : 'Oui'}</button
									>
									<button
										onclick={() => (deleteConfirm = null)}
										class="text-slate-400 hover:text-slate-600"><X class="h-3 w-3" /></button
									>
								</div>
							{:else}
								<button
									onclick={() => handleDelete(upload.file_id)}
									class="rounded-lg p-1.5 text-slate-300 hover:bg-red-50 hover:text-red-500"
									title={t('deleteUpload')}
									disabled={upload.processing}
								>
									<Trash2 class="h-4 w-4" />
								</button>
							{/if}
						</div>
					</div>
				{/each}
			</div>
		{/if}
	</div>
</div>
