<script lang="ts">
	import {
		Search,
		BarChart2,
		Database,
		Clock,
		UploadCloud,
		Activity,
		Menu,
		X,
		Scale
	} from 'lucide-svelte';
	import { getTranslation } from '$lib/i18n';
	import { appState } from '$lib/state.svelte';
	import { page } from '$app/stores';
	import favicon from '$lib/assets/favicon.svg';

	const t = (key: Parameters<typeof getTranslation>[1]) => getTranslation(appState.language, key);
	const isRTL = $derived(appState.language === 'ar');

	function setLanguage(lang: 'ar' | 'fr') {
		appState.language = lang;
		mobileOpen = false;
	}

	let mobileOpen = $state(false);

	const navLinks = $derived([
		{
			href: '/',
			label: t('askQuestion'),
			icon: Search,
			exact: false,
			active: $page.url.pathname === '/' || $page.url.pathname === '/results'
		},
		{
			href: '/explore',
			label: t('exploreData'),
			icon: BarChart2,
			exact: true,
			active: $page.url.pathname === '/explore'
		},
		{
			href: '/knowledge-base',
			label: t('manageKB'),
			icon: Database,
			exact: true,
			active: $page.url.pathname === '/knowledge-base'
		},
		{
			href: '/history',
			label: t('history'),
			icon: Clock,
			exact: true,
			active: $page.url.pathname === '/history'
		},
		{
			href: '/uploads',
			label: t('uploads'),
			icon: UploadCloud,
			exact: false,
			active: $page.url.pathname.startsWith('/uploads')
		}
		// {
		// 	href: '/system-health',
		// 	label: t('systemHealth'),
		// 	icon: Activity,
		// 	exact: true,
		// 	active: $page.url.pathname === '/system-health'
		// }
	]);
</script>

<nav class="navbar" aria-label="Navigation principale">
	<!-- ── Left: Logo + desktop nav ─────────────────────── -->
	<div class="nav-left">
		<!-- Logo -->
		<a href="/" class="logo" aria-label="Accueil">
			<div class="logo-icon">
				<img src={favicon} alt="Maroc Légal" width="28" height="28" />
			</div>
			<div class="logo-text">
				<span class="logo-title">{t('appTitle')}</span>
				<!-- <span class="logo-sub">{t('appSubtitle')}</span> -->
			</div>
		</a>

		<!-- Divider -->
		<div class="nav-divider" aria-hidden="true"></div>

		<!-- Desktop links -->
		<div class="nav-links" role="menubar">
			{#each navLinks as link}
				<a
					href={link.href}
					class={`nav-link${link.active ? ' nav-link--active' : ''}`}
					role="menuitem"
					aria-current={link.active ? 'page' : undefined}
				>
					<svelte:component this={link.icon} class="nav-link-icon" />
					<span class="nav-link-label">{link.label}</span>
				</a>
			{/each}
		</div>
	</div>

	<!-- ── Right: lang switch + avatar + mobile toggle ─── -->
	<div class="nav-right">
		<!-- Language segmented control -->
		<div class="lang-switch" role="group" aria-label="Langue">
			<button
				class={`lang-btn${appState.language === 'ar' ? ' lang-btn--active' : ''}`}
				onclick={() => setLanguage('ar')}
				aria-pressed={appState.language === 'ar'}
			>
				AR
			</button>
			<button
				class={`lang-btn${appState.language === 'fr' ? ' lang-btn--active' : ''}`}
				onclick={() => setLanguage('fr')}
				aria-pressed={appState.language === 'fr'}
			>
				FR
			</button>
		</div>

		<!-- Mobile hamburger -->
		<button
			class="mobile-toggle"
			onclick={() => (mobileOpen = !mobileOpen)}
			aria-label={mobileOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
			aria-expanded={mobileOpen}
		>
			{#if mobileOpen}
				<X class="h-5 w-5" />
			{:else}
				<Menu class="h-5 w-5" />
			{/if}
		</button>
	</div>
</nav>

<!-- ── Mobile drawer ──────────────────────────────────── -->
{#if mobileOpen}
	<!-- Backdrop -->
	<div
		class="mobile-backdrop"
		role="button"
		tabindex="-1"
		aria-label="Fermer le menu"
		onclick={() => (mobileOpen = false)}
		onkeydown={(e) => e.key === 'Escape' && (mobileOpen = false)}
	></div>

	<!-- Drawer panel -->
	<div class="mobile-drawer" role="dialog" aria-modal="true" aria-label="Navigation mobile">
		<div class="drawer-header">
			<div class="logo-icon">
				<img src={favicon} alt="Maroc Légal" width="24" height="24" />
			</div>
			<span class="logo-title">{t('appTitle')}</span>
			<button class="drawer-close" onclick={() => (mobileOpen = false)} aria-label="Fermer">
				<X class="h-5 w-5" />
			</button>
		</div>

		<nav class="drawer-links" role="menu">
			{#each navLinks as link}
				<a
					href={link.href}
					class={`drawer-link${link.active ? ' drawer-link--active' : ''}`}
					role="menuitem"
					aria-current={link.active ? 'page' : undefined}
					onclick={() => (mobileOpen = false)}
				>
					<svelte:component this={link.icon} class="drawer-link-icon" />
					<span>{link.label}</span>
				</a>
			{/each}
		</nav>

		<div class="drawer-footer">
			<div class="lang-switch">
				<button
					class={`lang-btn${appState.language === 'ar' ? ' lang-btn--active' : ''}`}
					onclick={() => setLanguage('ar')}>AR</button
				>
				<button
					class={`lang-btn${appState.language === 'fr' ? ' lang-btn--active' : ''}`}
					onclick={() => setLanguage('fr')}>FR</button
				>
			</div>
		</div>
	</div>
{/if}

<style>
	/* ─────────────────────────────────────────────────────────
	   Navbar shell
	───────────────────────────────────────────────────────── */
	.navbar {
		position: relative;
		z-index: 50;
		display: flex;
		align-items: center;
		justify-content: space-between;
		height: 56px;
		padding: 0 1.25rem;
		background: #1a237e;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
		box-shadow:
			0 1px 0 rgba(0, 0, 0, 0.18),
			0 4px 16px rgba(0, 0, 0, 0.12);
		flex-shrink: 0;
	}

	/* ─────────────────────────────────────────────────────────
	   Logo
	───────────────────────────────────────────────────────── */
	.nav-left {
		display: flex;
		align-items: center;
		gap: 1rem;
		min-width: 0;
	}

	.logo {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		text-decoration: none;
		flex-shrink: 0;
	}

	.logo-icon {
		width: 34px;
		height: 34px;
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.12);
		border: 1px solid rgba(255, 255, 255, 0.18);
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.logo-icon img {
		width: 22px;
		height: 22px;
		object-fit: contain;
	}

	.logo-text {
		display: flex;
		flex-direction: column;
		line-height: 1;
	}

	.logo-title {
		font-size: 0.95rem;
		font-weight: 800;
		color: #fff;
		letter-spacing: -0.01em;
	}

	.logo-sub {
		font-size: 0.6rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.5);
		text-transform: uppercase;
		letter-spacing: 0.08em;
		margin-top: 1px;
	}

	/* ─────────────────────────────────────────────────────────
	   Divider
	───────────────────────────────────────────────────────── */
	.nav-divider {
		width: 1px;
		height: 22px;
		background: rgba(255, 255, 255, 0.15);
		flex-shrink: 0;
		display: none;
	}

	@media (min-width: 768px) {
		.nav-divider {
			display: block;
		}
	}

	/* ─────────────────────────────────────────────────────────
	   Desktop nav links
	───────────────────────────────────────────────────────── */
	.nav-links {
		display: none;
		align-items: center;
		gap: 0.15rem;
	}

	@media (min-width: 768px) {
		.nav-links {
			display: flex;
		}
	}

	.nav-link {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.4rem 0.75rem;
		border-radius: 6px;
		font-size: 0.8rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.6);
		text-decoration: none;
		white-space: nowrap;
		border: 1px solid transparent;
	}

	.nav-link:hover {
		color: rgba(255, 255, 255, 0.92);
		background: rgba(255, 255, 255, 0.07);
	}

	.nav-link--active {
		color: #fff;
		background: rgba(255, 255, 255, 0.13);
		border-color: rgba(255, 255, 255, 0.14);
		font-weight: 600;
	}

	.nav-link--active:hover {
		background: rgba(255, 255, 255, 0.16);
	}

	/* Icon inside link */
	:global(.nav-link-icon) {
		width: 0.95rem;
		height: 0.95rem;
		flex-shrink: 0;
	}

	.nav-link-label {
		/* hide label on smaller desktop, show icon only */
	}

	@media (min-width: 768px) and (max-width: 1024px) {
		.nav-link-label {
			display: none;
		}
		.nav-link {
			padding: 0.4rem 0.55rem;
		}
	}

	/* ─────────────────────────────────────────────────────────
	   Right side
	───────────────────────────────────────────────────────── */
	.nav-right {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		flex-shrink: 0;
	}

	/* ── Language segmented control ── */
	.lang-switch {
		display: flex;
		background: rgba(0, 0, 0, 0.2);
		border: 1px solid rgba(255, 255, 255, 0.1);
		border-radius: 6px;
		padding: 2px;
		gap: 2px;
	}

	.lang-btn {
		padding: 0.25rem 0.65rem;
		border-radius: 4px;
		font-size: 0.72rem;
		font-weight: 700;
		letter-spacing: 0.04em;
		border: none;
		cursor: pointer;
		font-family: inherit;
		color: rgba(255, 255, 255, 0.5);
		background: transparent;
	}

	.lang-btn:hover {
		color: rgba(255, 255, 255, 0.85);
		background: rgba(255, 255, 255, 0.07);
	}

	.lang-btn--active {
		background: #fff;
		color: #1a237e;
		font-weight: 800;
	}

	.lang-btn--active:hover {
		background: #f0f0f0;
		color: #1a237e;
	}

	/* ── Avatar ── */
	.avatar {
		display: none;
		width: 32px;
		height: 32px;
		border-radius: 50%;
		background: rgba(255, 255, 255, 0.12);
		border: 1.5px solid rgba(255, 255, 255, 0.2);
		color: #fff;
		font-size: 0.7rem;
		font-weight: 800;
		align-items: center;
		justify-content: center;
		letter-spacing: 0.02em;
		cursor: default;
		flex-shrink: 0;
	}

	@media (min-width: 768px) {
		.avatar {
			display: flex;
		}
	}

	/* ── Mobile hamburger ── */
	.mobile-toggle {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 34px;
		height: 34px;
		border-radius: 6px;
		border: 1px solid rgba(255, 255, 255, 0.15);
		background: rgba(255, 255, 255, 0.07);
		color: rgba(255, 255, 255, 0.85);
		cursor: pointer;
	}

	.mobile-toggle:hover {
		background: rgba(255, 255, 255, 0.13);
		border-color: rgba(255, 255, 255, 0.25);
		color: #fff;
	}

	@media (min-width: 768px) {
		.mobile-toggle {
			display: none;
		}
	}

	/* ─────────────────────────────────────────────────────────
	   Mobile backdrop + drawer
	───────────────────────────────────────────────────────── */
	.mobile-backdrop {
		position: fixed;
		inset: 0;
		z-index: 40;
		background: rgba(0, 0, 0, 0.45);
	}

	.mobile-drawer {
		position: fixed;
		top: 56px;
		left: 0;
		right: 0;
		z-index: 45;
		background: #1e2a8a;
		border-bottom: 1px solid rgba(255, 255, 255, 0.1);
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
		display: flex;
		flex-direction: column;
	}

	.drawer-header {
		display: flex;
		align-items: center;
		gap: 0.6rem;
		padding: 0.85rem 1.25rem;
		border-bottom: 1px solid rgba(255, 255, 255, 0.08);
	}

	.drawer-close {
		margin-left: auto;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 30px;
		height: 30px;
		border-radius: 6px;
		border: 1px solid rgba(255, 255, 255, 0.15);
		background: rgba(255, 255, 255, 0.07);
		color: rgba(255, 255, 255, 0.75);
		cursor: pointer;
	}

	.drawer-links {
		display: flex;
		flex-direction: column;
		padding: 0.6rem 0.75rem;
		gap: 0.25rem;
	}

	.drawer-link {
		display: flex;
		align-items: center;
		gap: 0.75rem;
		padding: 0.7rem 0.85rem;
		border-radius: 8px;
		font-size: 0.88rem;
		font-weight: 500;
		color: rgba(255, 255, 255, 0.65);
		text-decoration: none;
		border: 1px solid transparent;
	}

	.drawer-link:hover {
		color: #fff;
		background: rgba(255, 255, 255, 0.07);
	}

	.drawer-link--active {
		color: #fff;
		background: rgba(255, 255, 255, 0.13);
		border-color: rgba(255, 255, 255, 0.14);
		font-weight: 600;
	}

	:global(.drawer-link-icon) {
		width: 1rem;
		height: 1rem;
		flex-shrink: 0;
	}

	.drawer-footer {
		padding: 0.85rem 1.25rem;
		border-top: 1px solid rgba(255, 255, 255, 0.08);
	}
</style>
