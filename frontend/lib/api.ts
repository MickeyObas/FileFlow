import type { FileDetailOut, UploadOut } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseError(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    const detail = body.detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) =>
          typeof item === "object" && item && "msg" in item
            ? String((item as { msg: unknown }).msg)
            : JSON.stringify(item),
        )
        .join("; ");
    }
  } catch {
    /* ignore */
  }
  return response.statusText || `Request failed (${response.status})`;
}

async function apiFetch<T>(
  path: string,
  init?: RequestInit & { idempotencyKey?: string },
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.idempotencyKey) {
    headers.set("Idempotency-Key", init.idempotencyKey);
  }
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE}/api/v1${path}`, {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new ApiError(await parseError(response), response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export function createUploadSession(
  file: File,
  contentType: string,
  idempotencyKey: string,
): Promise<UploadOut> {
  return apiFetch<UploadOut>("/uploads/", {
    method: "POST",
    idempotencyKey,
    body: JSON.stringify({
      original_filename: file.name,
      content_type: contentType,
      expected_size: file.size,
    }),
  });
}

export function uploadFileBody(
  uploadId: string,
  file: File,
  onProgress: (loaded: number, total: number) => void,
): Promise<UploadOut> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", `${API_BASE}/api/v1/uploads/${uploadId}`);
    xhr.responseType = "json";

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        onProgress(event.loaded, event.total);
      } else {
        onProgress(event.loaded, file.size);
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(xhr.response as UploadOut);
        return;
      }
      const detail =
        xhr.response &&
        typeof xhr.response === "object" &&
        "detail" in xhr.response
          ? String((xhr.response as { detail: unknown }).detail)
          : xhr.statusText;
      reject(new ApiError(detail || "Upload failed", xhr.status));
    };

    xhr.onerror = () => {
      reject(new ApiError("Network error while uploading file", 0));
    };

    xhr.send(file);
  });
}

export function completeUpload(
  uploadId: string,
  idempotencyKey: string,
): Promise<FileDetailOut> {
  return apiFetch<FileDetailOut>(`/uploads/${uploadId}/complete`, {
    method: "POST",
    idempotencyKey,
  });
}

export function getFile(fileId: string): Promise<FileDetailOut> {
  return apiFetch<FileDetailOut>(`/files/${fileId}`);
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
