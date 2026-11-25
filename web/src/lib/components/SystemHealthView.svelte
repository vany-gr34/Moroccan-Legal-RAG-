<script lang="ts">
	import { Activity, Database, Server, Cpu, BrainCircuit, ScanText, Network, Layers, CheckCircle2, AlertCircle } from 'lucide-svelte';
	import type { Language } from '$lib/types';
	import { getTranslation } from '$lib/i18n';

	interface Props {
		language: Language;
	}

	let { language }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	// Mock data for services
	const services = $derived([
		{
			id: 'embedding',
			name: t('embeddingService'),
			status: 'online',
			icon: Network
		},
		{
			id: 'retrieval',
			name: t('retrievalService'),
			status: 'online',
			icon: Layers
		},
		{
			id: 'kb_connection',
			name: t('kbConnection'),
			status: 'online',
			icon: Database
		}
	]);

	// Mock data for infrastructure/models
	const infrastructure = $derived([
		{
			id: 'llm',
			name: t('llmModel'),
			value: 'Llama 3 70B Instruct',
			icon: BrainCircuit,
			active: true
		},
		{
			id: 'embedding_model',
			name: t('embeddingModel'),
			value: 'BGE-m3 (Multilingual)',
			icon: Activity,
			active: true
		},
		{
			id: 'ocr',
			name: t('ocrEngine'),
			value: 'Tesseract OCR v5.3',
			icon: ScanText,
			active: true
		},
		{
			id: 'gpu',
			name: t('gpuUsage'),
			value: 'NVIDIA A100 80GB (VRAM: 62GB / 80GB)',
			icon: Cpu,
			active: true
		}
	]);
</script>

<div class="flex-1 w-full max-w-4xl mx-auto px-4 py-8 space-y-8">
	<!-- Header -->
	<div class="flex items-center border-b border-sandstone-border pb-4">
		<h2 class="text-2xl font-bold text-slate-900 font-serif">{t('systemHealth')}</h2>
	</div>

	<!-- Services Status Section -->
	<div class="space-y-4">
		<h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">
			<Server class="h-5 w-5 text-primary" />
			{t('servicesStatus')}
		</h3>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			{#each services as service (service.id)}
				<div class="bg-white rounded-xl shadow-sm border border-sandstone-border p-5 flex flex-col gap-4">
					<div class="flex items-start justify-between">
						<div class="p-2 bg-primary/10 rounded-lg text-primary">
							<service.icon class="h-6 w-6" />
						</div>
						{#if service.status === 'online'}
							<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-success/10 text-success border border-success/20">
								<CheckCircle2 class={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'}`} />
								{t('statusOnline')}
							</span>
						{:else}
							<span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700 border border-amber-200">
								<AlertCircle class={`h-3 w-3 ${isRTL ? 'ml-1' : 'mr-1'}`} />
								{t('statusDegraded')}
							</span>
						{/if}
					</div>
					<h4 class="font-semibold text-slate-800">{service.name}</h4>
				</div>
			{/each}
		</div>
	</div>

	<!-- Infrastructure & Models Section -->
	<div class="space-y-4">
		<h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">
			<Cpu class="h-5 w-5 text-primary" />
			{t('infrastructure')}
		</h3>
		<div class="bg-white rounded-xl shadow-sm border border-sandstone-border overflow-hidden divide-y divide-sandstone-border">
			{#each infrastructure as item (item.id)}
				<div class="p-5 flex items-center justify-between hover:bg-slate-50 transition-colors">
					<div class="flex items-center gap-4">
						<div class="p-2 rounded-lg bg-sandstone text-slate-600">
							<item.icon class="h-5 w-5" />
						</div>
						<div>
							<h4 class="text-sm text-slate-500 font-medium">{item.name}</h4>
							<p class="text-base font-semibold text-slate-800 mt-0.5" dir="ltr">{item.value}</p>
						</div>
					</div>
					<div class="flex items-center">
						<div class="relative flex h-3 w-3">
							{#if item.active}
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-40"></span>
								<span class="relative inline-flex rounded-full h-3 w-3 bg-success"></span>
							{:else}
								<span class="relative inline-flex rounded-full h-3 w-3 bg-slate-300"></span>
							{/if}
						</div>
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>
