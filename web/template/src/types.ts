export type Language = 'ar' | 'fr';

export type ViewState = 'home' | 'results' | 'knowledge_base' | 'history';

export interface SourceArticle {
  id: string;
  title: string;
  law: string;
  content: string;
  relevance: number;
  snippet: string;
}

export interface QueryResult {
  query: string;
  domain: string;
  answerLegal: string;
  answerSimple: string;
  sources: SourceArticle[];
}

export interface HistoryItem {
  id: string;
  timestamp: string;
  query: string;
  domain: string;
  sourcesCount: number;
}

export interface KBItem {
  id: string;
  title: string;
  status: 'active' | 'processing' | 'error';
  lastUpdated: string;
  articleCount: number;
}
