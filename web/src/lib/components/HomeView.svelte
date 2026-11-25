<script lang="ts">
	import {
		Search,
		UploadCloud,
		BookOpen,
		Scale,
		FileText,
		ShieldCheck,
		Sparkles
	} from 'lucide-svelte';
	import type { Language, LawsResponse } from '$lib/types';
	import { getTranslation } from '$lib/i18n';
	import { onMount } from 'svelte';
	import { PUBLIC_API_ENDPOIT } from '$env/static/public';

	interface Props {
		language: Language;
		onSearch: (query: string, domain: string) => void;
	}

	let { language, onSearch }: Props = $props();

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(language, key);
	const isRTL = $derived(language === 'ar');

	let query = $state('');
	let domain = $state('all');
	let activeDomainValues = $state<string[]>([]);

	onMount(async () => {
		try {
			const res = await fetch(PUBLIC_API_ENDPOIT + '/laws');
			if (res.ok) {
				const data: LawsResponse = await res.json();
				activeDomainValues = Array.from(new Set(data.laws.map((l) => l.domain)));
			}
		} catch (e) {
			console.error('Failed to fetch domains', e);
		}
	});

	const allPossibleDomains = $derived([
		{ id: 'all', label: t('allDomains') },
		{ id: 'criminal', label: t('domainCriminal') },
		{ id: 'traffic', label: t('domainTraffic') },
		{ id: 'family', label: t('domainFamily') },
		{ id: 'civil', label: t('domainCivil') },
		{ id: 'commercial', label: t('domainCommercial') },
		{ id: 'procedure', label: t('domainProcedure') },
		{ id: 'offenses', label: t('domainOffenses') }
	]);

	const domains = $derived([
		allPossibleDomains[0],
		...activeDomainValues.map(
			(val) => allPossibleDomains.find((d) => d.id === val) ?? { id: val, label: val }
		)
	]);

	function handleSubmit(e?: Event) {
		e?.preventDefault();
		if (query.trim()) {
			onSearch(query, domain);
		}
	}

	// ── Example queries from benchmark dataset ──
	const exampleQueries = $derived([
		language === 'ar'
			? 'ما هي الأفعال التي تعتبر جرائم إرهابية حسب القانون المغربي؟'
			: 'Actes considérés comme crimes terroristes au Maroc',
		language === 'ar'
			? 'ما هي الحالات التي يجب فيها توقيف المركبة حسب قانون السير؟'
			: "Cas d'immobilisation du véhicule",
		language === 'ar'
			? 'هل يمكن للمحكمة دعوة الأطراف إلى الوساطة لحل النزاع المدني؟'
			: 'Médiation judiciaire au Maroc',
		language === 'ar'
			? 'ما هي العائدات غير الخاضعة لضريبة الدخل؟'
			: 'Revenus exonérés de impôt sur le revenu',
		language === 'ar'
			? 'ماهي الشروط التي تجعل الطفل في وضعية صعبة حسب القانون الجنائي؟'
			: 'Enfant en situation difficile code pénal'
	]);

	function fillExample(q: string) {
		query = q;
	}

	const features = $derived([
		{
			icon: Scale,
			label: language === 'ar' ? 'القانون الجنائي والمدني' : 'Droit pénal et civil',
			desc: language === 'ar' ? 'تغطية شاملة للتشريعات' : 'Couverture complète des textes'
		},
		{
			icon: BookOpen,
			label: language === 'ar' ? 'مصادر موثوقة' : 'Sources vérifiées',
			desc: language === 'ar' ? 'مراجع رسمية معتمدة' : 'Références officielles certifiées'
		},
		{
			icon: FileText,
			label: language === 'ar' ? 'تحليل الوثائق' : 'Analyse documentaire',
			desc: language === 'ar' ? 'ارفع واستخرج المواد' : 'Importez et extrayez les articles'
		},
		{
			icon: ShieldCheck,
			label: language === 'ar' ? 'دقة وموثوقية' : 'Précision et fiabilité',
			desc: language === 'ar' ? 'إجابات مدعومة بالنصوص' : 'Réponses ancrées dans les textes'
		}
	]);
</script>

<!--
  The outer wrapper uses position:absolute + inset:0 to guarantee it
  fills the parent <main> completely, regardless of Svelte's scoped
  styles or flex-child width resolution quirks.
-->
<div class="home-root" dir={isRTL ? 'rtl' : 'ltr'}>
	<!-- Hero: grows to fill all available vertical space -->
	<section class="hero-section">
		<div class="hero-bg-pattern"></div>

		<div class="hero-inner">
			<!-- Badge -->
			<div class="hero-badge">
				<span class="badge-dot"></span>
				{language === 'ar' ? 'مدعوم بالذكاء الاصطناعي' : "Propulsé par l'IA"}
			</div>

			<!-- Heading -->
			<div class="hero-heading-group">
				<h1 class="hero-title">
					{language === 'ar' ? 'ابحث في القانون المغربي' : 'Explorez le droit marocain'}
				</h1>
				<p class="hero-subtitle">
					{language === 'ar'
						? 'اطرح أي سؤال قانوني وتلقَّ إجابات دقيقة مستخلصة من التشريعات الرسمية المغربية'
						: 'Posez toute question juridique et obtenez des réponses précises tirées des textes législatifs officiels'}
				</p>
			</div>

			<!-- Search card -->
			<form class="search-card" onsubmit={handleSubmit}>
				<div class="search-input-wrap">
					<div class="search-icon-side">
						<Search class="search-icon-svg" />
					</div>
					<textarea
						class={`search-textarea ${isRTL ? 'ta-rtl' : 'ta-ltr'}`}
						placeholder={t('searchPlaceholder')}
						bind:value={query}
						rows="3"
						onkeydown={(e) => {
							if (e.key === 'Enter' && !e.shiftKey) {
								e.preventDefault();
								handleSubmit();
							}
						}}
					></textarea>
					<div class="search-submit-side">
						<button
							type="submit"
							disabled={!query.trim()}
							class="search-btn"
							aria-label={language === 'ar' ? 'بحث' : 'Rechercher'}
						>
							<Search class="sbtn-icon" />
							<span>{language === 'ar' ? 'بحث' : 'Rechercher'}</span>
						</button>
					</div>
				</div>

				<!-- Domain filters -->
				<div class="domains-bar">
					<span class="domains-label">{t('domains')}</span>
					<div class="domains-chips">
						{#each domains as d (d.id)}
							<button
								type="button"
								onclick={() => (domain = d.id)}
								class={`domain-chip${domain === d.id ? ' domain-chip--active' : ''}`}
							>
								{d.label}
							</button>
						{/each}
					</div>
				</div>

				<!-- Example queries -->
				<div class="examples-bar">
					<div class="examples-chips">
						{#each exampleQueries as q}
							<button type="button" onclick={() => fillExample(q)} class="example-chip">
								<Sparkles size={11} class="example-chip-icon" />
								{q.length > 35 ? q.slice(0, 35) + '…' : q}
							</button>
						{/each}
					</div>
				</div>
			</form>

			<!-- Upload shortcut -->
			<a href="/uploads" class="upload-cta">
				<UploadCloud class="upload-cta-icon" />
				<span>{t('uploadDoc')}</span>
			</a>
		</div>
	</section>

	<!-- Features footer — stays pinned at the bottom -->
	<footer class="features-footer">
		<div class="features-grid">
			{#each features as f}
				<div class="feature-card">
					<div class="feature-icon-wrap">
						<svelte:component this={f.icon} class="feat-icon" />
					</div>
					<div class="feature-text">
						<p class="feature-label">{f.label}</p>
						<p class="feature-desc">{f.desc}</p>
					</div>
				</div>
			{/each}
		</div>
	</footer>
</div>

<style>
	/* ─────────────────────────────────────────────────────────
	   Root: fills the parent <main> completely.
	   position:absolute + inset:0 bypasses any flex-child width
	   ambiguity that Svelte scoped styles can cause.
	───────────────────────────────────────────────────────── */
	.home-root {
		position: absolute;
		inset: 0;
		display: flex;
		flex-direction: column;
		overflow-y: auto;
	}

	/* ─────────────────────────────────────────────────────────
	   Hero: fills all remaining vertical space
	───────────────────────────────────────────────────────── */
	.hero-section {
		flex: 1;
		position: relative;
		display: flex;
		align-items: center;
		justify-content: center;
		padding: 3.5rem 2rem 3rem;
		overflow: hidden;
		background: linear-gradient(160deg, #1a237e 0%, #283593 50%, #303f9f 100%);
	}

	/* Subtle grid overlay */
	.hero-bg-pattern {
		position: absolute;
		inset: 0;
		background-image:
			repeating-linear-gradient(
				0deg,
				transparent,
				transparent 60px,
				rgba(255, 255, 255, 0.03) 60px,
				rgba(255, 255, 255, 0.03) 61px
			),
			repeating-linear-gradient(
				90deg,
				transparent,
				transparent 60px,
				rgba(255, 255, 255, 0.03) 60px,
				rgba(255, 255, 255, 0.03) 61px
			);
		pointer-events: none;
	}

	/* Centred content column */
	.hero-inner {
		position: relative;
		width: 100%;
		max-width: 760px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: 1.75rem;
		z-index: 1;
	}

	/* ── Badge ── */
	.hero-badge {
		display: inline-flex;
		align-items: center;
		gap: 0.5rem;
		background: rgba(255, 255, 255, 0.12);
		border: 1px solid rgba(255, 255, 255, 0.22);
		color: rgba(255, 255, 255, 0.9);
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.07em;
		text-transform: uppercase;
		padding: 0.35rem 1rem;
		border-radius: 999px;
	}

	.badge-dot {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #69f0ae;
		box-shadow: 0 0 0 3px rgba(105, 240, 174, 0.25);
	}

	/* ── Heading ── */
	.hero-heading-group {
		text-align: center;
	}

	.hero-title {
		font-size: clamp(1.8rem, 5vw, 2.75rem);
		font-weight: 800;
		color: #fff;
		line-height: 1.15;
		margin: 0 0 0.75rem;
		font-family: var(--font-serif, serif);
		text-shadow: 0 2px 16px rgba(0, 0, 0, 0.25);
	}

	.hero-subtitle {
		font-size: clamp(0.88rem, 2vw, 1.05rem);
		color: rgba(255, 255, 255, 0.7);
		line-height: 1.75;
		max-width: 560px;
		margin: 0 auto;
	}

	/* ─────────────────────────────────────────────────────────
	   Search card
	───────────────────────────────────────────────────────── */
	.search-card {
		width: 100%;
		background: #fff;
		border-radius: 1.25rem;
		box-shadow:
			0 12px 48px rgba(0, 0, 0, 0.22),
			0 2px 8px rgba(0, 0, 0, 0.1);
		overflow: hidden;
	}

	.search-input-wrap {
		display: flex;
		align-items: flex-start;
		border-bottom: 1px solid var(--color-sandstone-border, #dcd3c1);
	}

	.search-icon-side {
		padding: 1.1rem 0 0 1.25rem;
		flex-shrink: 0;
		color: var(--color-primary, #1a237e);
		opacity: 0.45;
	}

	[dir='rtl'] .search-icon-side {
		padding: 1.1rem 1.25rem 0 0;
	}

	.search-icon-svg {
		width: 1.2rem;
		height: 1.2rem;
	}

	.search-textarea {
		flex: 1;
		padding: 1rem;
		font-size: 1rem;
		background: transparent;
		border: none;
		outline: none;
		resize: none;
		color: var(--color-primary, #1a237e);
		font-family: inherit;
		line-height: 1.6;
	}

	.ta-ltr {
		text-align: left;
	}
	.ta-rtl {
		text-align: right;
	}

	.search-textarea::placeholder {
		color: #94a3b8;
	}

	.search-submit-side {
		padding: 0.75rem 0.75rem 0.75rem 0;
		flex-shrink: 0;
		display: flex;
		align-items: flex-start;
	}

	[dir='rtl'] .search-submit-side {
		padding: 0.75rem 0 0.75rem 0.75rem;
	}

	.search-btn {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.6rem 1.2rem;
		background: var(--color-primary, #1a237e);
		color: #fff;
		border: none;
		border-radius: 0.75rem;
		font-size: 0.875rem;
		font-weight: 600;
		cursor: pointer;
		font-family: inherit;
	}

	.search-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.search-btn:not(:disabled):hover {
		background: #283593;
	}

	.sbtn-icon {
		width: 1rem;
		height: 1rem;
	}

	/* ── Domains bar ── */
	.domains-bar {
		display: flex;
		align-items: center;
		flex-wrap: wrap;
		gap: 0.6rem;
		padding: 0.85rem 1.25rem;
	}

	.domains-label {
		font-size: 0.72rem;
		font-weight: 700;
		color: #94a3b8;
		text-transform: uppercase;
		letter-spacing: 0.07em;
		white-space: nowrap;
	}

	.domains-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.domain-chip {
		padding: 0.28rem 0.85rem;
		border-radius: 999px;
		font-size: 0.78rem;
		font-weight: 500;
		border: 1.5px solid var(--color-sandstone-border, #dcd3c1);
		background: var(--color-sandstone, #f5f0e8);
		color: #475569;
		cursor: pointer;
		font-family: inherit;
	}

	.domain-chip--active {
		background: var(--color-primary, #1a237e);
		color: #fff;
		border-color: var(--color-primary, #1a237e);
	}

	.domain-chip:not(.domain-chip--active):hover {
		border-color: var(--color-primary, #1a237e);
		color: var(--color-primary, #1a237e);
	}

	/* ── Upload CTA ── */
	.upload-cta {
		display: inline-flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.65rem 1.75rem;
		border-radius: 999px;
		border: 1.5px solid rgba(255, 255, 255, 0.28);
		background: rgba(255, 255, 255, 0.09);
		color: rgba(255, 255, 255, 0.82);
		font-size: 0.875rem;
		font-weight: 500;
		text-decoration: none;
		font-family: inherit;
	}

	.upload-cta:hover {
		background: rgba(255, 255, 255, 0.17);
		border-color: rgba(255, 255, 255, 0.5);
		color: #fff;
	}

	.upload-cta-icon {
		width: 1.1rem;
		height: 1.1rem;
		opacity: 0.75;
	}

	/* ─────────────────────────────────────────────────────────
	   Features footer — always at the bottom
	───────────────────────────────────────────────────────── */
	.features-footer {
		flex-shrink: 0;
		background: #fff;
		border-top: 1px solid var(--color-sandstone-border, #dcd3c1);
		padding: 1.25rem 2rem;
	}

	.features-grid {
		max-width: 900px;
		margin: 0 auto;
		display: grid;
		grid-template-columns: repeat(2, 1fr);
		gap: 0.85rem;
	}

	@media (min-width: 640px) {
		.features-grid {
			grid-template-columns: repeat(4, 1fr);
		}
	}

	.feature-card {
		display: flex;
		align-items: flex-start;
		gap: 0.7rem;
		padding: 0.8rem;
		border-radius: 0.65rem;
		background: var(--color-sandstone, #f5f0e8);
		border: 1px solid var(--color-sandstone-border, #dcd3c1);
	}

	.feature-icon-wrap {
		flex-shrink: 0;
		width: 2rem;
		height: 2rem;
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: 0.5rem;
		background: var(--color-primary, #1a237e);
		color: #fff;
	}

	.feat-icon {
		width: 1.1rem;
		height: 1.1rem;
	}

	.feature-text {
		min-width: 0;
	}

	.feature-label {
		font-size: 0.78rem;
		font-weight: 700;
		color: var(--color-primary, #1a237e);
		line-height: 1.3;
		margin: 0 0 0.18rem;
	}

	.feature-desc {
		font-size: 0.7rem;
		color: #64748b;
		line-height: 1.4;
		margin: 0;
	}

	/* ── Example queries bar ── */
	.examples-bar {
		padding: 0.25rem 1.25rem 0.85rem;
	}

	.examples-chips {
		display: flex;
		flex-wrap: wrap;
		gap: 0.4rem;
	}

	.example-chip {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.3rem 0.75rem;
		border-radius: 999px;
		font-size: 0.72rem;
		font-weight: 600;
		border: 1px solid #dcd3c1;
		background: #fff;
		color: #1e293b;
		cursor: pointer;
		font-family: inherit;
		line-height: 1.4;
		white-space: nowrap;
	}

	.example-chip:hover {
		background: #f0ebe1;
		border-color: #1a237e;
		color: #1a237e;
	}

	.example-chip-icon {
		color: #94a3b8;
		flex-shrink: 0;
	}
</style>
