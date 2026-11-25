export type Language = 'ar' | 'fr';

export type ViewState = 'home' | 'results' | 'knowledge_base' | 'history' | 'system_health';

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

export interface RawSearchRequest {
	query: string;
	domain?: string;
	top_k?: number;
	strategy?: 'dense' | 'bm25' | 'rrf';
}

export interface RawSearchResult {
	id: number;
	article_number: string;
	text: string;
	law_name: string;
	domain: string;
	chapter_title: string;
	section_title: string;
	source_file: string;
	similarity: number;
	dense_rank: number;
	bm25_rank: number;
	rrf_score: number;
}

export interface RawSearchResponse {
	query: string;
	strategy: string;
	total_results: number;
	search_time_ms: number;
	results: RawSearchResult[];
}

export interface Law {
	law_name: string;
	domain: string;
	article_count: number;
	ingested_at: string;
}

export interface LawsResponse {
	total_laws: number;
	laws: Law[];
}

export interface AskRequest {
	query: string;
	domain?: string;
	top_k?: number;
}

export interface AskSource {
	article_number: string;
	law_name: string;
	domain: string;
	chapter_title: string | null;
	section_title: string | null;
	text_preview: string;
	text_full?: string;
	relevance_score: number;
}

export interface AskResponse {
	query: string;
	short_answer: string;
	long_answer: string;
	example: string;
	disclaimer: string;
	sources: AskSource[];
	knowledge_base: string[];
	session_id: string;
	search_time_ms: number;
	generation_time_ms: number;
	total_time_ms: number;
	model_name: string;
}

// --- Upload types ---

/** Matches backend UploadedFileInfo schema */
export interface UploadedFile {
	file_id: string;
	original_filename: string;
	size_bytes: number;
	uploaded_at: string;
	processed: boolean;
	processing: boolean;
	article_count: number;
	json_path?: string | null;
	error?: string | null;
}

/** Immediate response from POST /upload */
export interface UploadResponse {
	file_id: string;
	original_filename: string;
	size_bytes: number;
	status: 'processing' | 'done' | 'uploaded';
	message: string;
}

/** Response from GET /uploads/{file_id}/status */
export interface UploadStatus {
	file_id: string;
	status: 'processing' | 'done' | 'error' | 'unknown';
	article_count: number;
	error?: string | null;
	processing_time_ms?: number | null;
}

/** Matches backend UploadListResponse */
export interface UploadListResponse {
	total: number;
	files: UploadedFile[];
}

export interface ArticleContext {
	book?: string | null;
	section?: string | null;
	subsection?: string | null;
	chapter?: string | null;
	branch?: string | null;
}

export interface UploadArticle {
	article_number?: string;
	text: string;
	footnotes?: string[];
	context?: ArticleContext;
	law_name?: string;
	domain?: string;
	[key: string]: unknown;
}

/** Matches backend /uploads/{file_id}/articles response */
export interface UploadArticlesResponse {
	file_id: string;
	articles: UploadArticle[];
	article_count: number;
}

/** A single node in the hierarchy tree from /uploads/{file_id}/hierarchy */
export interface HierarchyNode {
	level: 'book' | 'section' | 'subsection' | 'chapter' | 'branch' | 'article';
	title: string | null;
	article_number: string | null;
	text_preview?: string;
	children: HierarchyNode[];
}

/** Response from GET /uploads/{file_id}/hierarchy */
export interface HierarchyResponse {
	file_id: string;
	article_count: number;
	node_count: number;
	hierarchy: HierarchyNode[];
}

/** Response from POST /uploads/{file_id}/embed */
export interface EmbedResponse {
	file_id: string;
	source_file: string;
	domain: string;
	ingested: number;
	clear_existing: boolean;
	message: string;
}

// --- Conversation History types ---

export interface ConversationSource {
	article_number: string;
	law_name: string;
	domain: string;
}

export interface ConversationTurn {
	id: number;
	session_id: string;
	role: 'user' | 'assistant' | 'system';
	content: string;
	sources: ConversationSource[] | null;
	metadata: Record<string, unknown>;
	created_at: string;
}

export interface SessionSummary {
	session_id: string;
	first_query: string;
	turn_count: number;
	last_active: string; // ISO timestamp
}

export interface SessionsResponse {
	total: number;
	sessions: SessionSummary[];
}

export interface SessionDetailResponse {
	session_id: string;
	turns: ConversationTurn[];
}
