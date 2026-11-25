import type { Language, SourceArticle } from './types';

export const appState = $state({
	language: 'ar' as Language,
	selectedArticle: null as SourceArticle | null
});
