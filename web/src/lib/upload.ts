import { PUBLIC_API_ENDPOIT } from '$env/static/public';
import type {
	UploadedFile,
	UploadResponse,
	UploadStatus,
	UploadListResponse,
	UploadArticlesResponse,
	HierarchyResponse,
	EmbedResponse
} from './types';

/** List all uploaded files */
export async function listUploads(): Promise<UploadListResponse> {
	const res = await fetch(`${PUBLIC_API_ENDPOIT}/uploads`);
	if (!res.ok) throw new Error(`Failed to fetch uploads: ${res.status}`);
	return res.json();
}

/** Poll processing status for a specific file */
export async function getUploadStatus(fileId: string): Promise<UploadStatus> {
	const res = await fetch(`${PUBLIC_API_ENDPOIT}/uploads/${encodeURIComponent(fileId)}/status`);
	if (!res.ok) throw new Error(`Failed to fetch status: ${res.status}`);
	return res.json();
}

/** Get articles for a specific upload */
export async function getUploadArticles(fileId: string): Promise<UploadArticlesResponse> {
	const res = await fetch(
		`${PUBLIC_API_ENDPOIT}/uploads/${encodeURIComponent(fileId)}/articles`
	);
	if (!res.ok) throw new Error(`Failed to fetch articles: ${res.status}`);
	return res.json();
}

/** Delete an upload and its processed data */
export async function deleteUpload(fileId: string): Promise<void> {
	const res = await fetch(`${PUBLIC_API_ENDPOIT}/uploads/${encodeURIComponent(fileId)}`, {
		method: 'DELETE'
	});
	if (!res.ok) throw new Error(`Failed to delete upload: ${res.status}`);
}

/** Get the hierarchical document tree for a specific upload */
export async function getUploadHierarchy(fileId: string): Promise<HierarchyResponse> {
	const res = await fetch(
		`${PUBLIC_API_ENDPOIT}/uploads/${encodeURIComponent(fileId)}/hierarchy`
	);
	if (!res.ok) throw new Error(`Failed to fetch hierarchy: ${res.status}`);
	return res.json();
}

/**
 * Upload a PDF file. Returns immediately with status="processing".
 * Poll getUploadStatus() every 2-3 s until status=="done" or "error".
 */
export async function uploadPdf(file: File): Promise<UploadResponse> {
	const formData = new FormData();
	formData.append('file', file);
	const res = await fetch(`${PUBLIC_API_ENDPOIT}/upload`, {
		method: 'POST',
		body: formData
	});
	if (!res.ok) {
		const body = await res.text();
		throw new Error(`Upload failed (${res.status}): ${body}`);
	}
	return res.json();
}
/**
 * Embed a processed upload into the vector database.
 * Synchronous — may take 10-60s for large files.
 */
export async function embedUpload(
	fileId: string,
	domain = 'uploaded',
	clearExisting = true
): Promise<EmbedResponse> {
	const params = new URLSearchParams({
		domain,
		clear_existing: String(clearExisting)
	});
	const res = await fetch(
		`${PUBLIC_API_ENDPOIT}/uploads/${encodeURIComponent(fileId)}/embed?${params}`,
		{ method: 'POST' }
	);
	if (!res.ok) {
		const body = await res.text();
		throw new Error(`Embedding failed (${res.status}): ${body}`);
	}
	return res.json();
}
