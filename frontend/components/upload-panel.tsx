"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import {
  ApiError,
  completeUpload,
  createUploadSession,
  formatBytes,
  getFile,
  uploadFileBody,
} from "@/lib/api";
import type { FileDetailOut } from "@/lib/types";

const ACCEPT =
  ".pdf,.csv,.png,.jpg,.jpeg,application/pdf,text/csv,image/png,image/jpeg";

const EXTENSION_TYPES: Record<string, string> = {
  pdf: "application/pdf",
  csv: "text/csv",
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
};

function resolveContentType(file: File): string | null {
  const allowed = new Set(Object.values(EXTENSION_TYPES));
  if (file.type && allowed.has(file.type)) {
    return file.type;
  }
  const ext = file.name.split(".").pop()?.toLowerCase();
  if (ext && ext in EXTENSION_TYPES) {
    return EXTENSION_TYPES[ext];
  }
  return null;
}

const TERMINAL_FILE_STATUSES = new Set(["completed", "failed", "expired"]);

type ViewState =
  | { phase: "idle" }
  | {
      phase: "uploading";
      fileName: string;
      loaded: number;
      total: number;
    }
  | { phase: "upload_failed"; message: string }
  | { phase: "processing"; file: FileDetailOut }
  | { phase: "done"; file: FileDetailOut }
  | { phase: "processing_failed"; file: FileDetailOut };

function progressPercent(loaded: number, total: number): number {
  if (total <= 0) {
    return 0;
  }
  return Math.min(100, Math.round((loaded / total) * 100));
}

function StatusPill({ label, tone }: { label: string; tone: "neutral" | "ok" | "warn" | "bad" }) {
  const tones = {
    neutral: "bg-zinc-100 text-zinc-700",
    ok: "bg-emerald-100 text-emerald-800",
    warn: "bg-amber-100 text-amber-900",
    bad: "bg-red-100 text-red-800",
  };
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {label}
    </span>
  );
}

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-200">
      <div
        className="h-full rounded-full bg-zinc-900 transition-[width] duration-200"
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

export function UploadPanel() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [view, setView] = useState<ViewState>({ phase: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const reset = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setSelectedFile(null);
    setView({ phase: "idle" });
    if (inputRef.current) {
      inputRef.current.value = "";
    }
  }, []);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const startPolling = useCallback((fileId: string, initial: FileDetailOut) => {
    setView({ phase: "processing", file: initial });

    const poll = async () => {
      try {
        const file = await getFile(fileId);
        if (file.status === "completed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          setView({ phase: "done", file });
          return;
        }
        if (file.status === "failed") {
          if (pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
          const message =
            file.processing_job?.error_message ??
            "Processing failed. You can upload the file again to retry.";
          setView({ phase: "processing_failed", file });
          return;
        }
        setView({ phase: "processing", file });
      } catch (err) {
        if (pollRef.current) {
          clearInterval(pollRef.current);
          pollRef.current = null;
        }
        const message =
          err instanceof ApiError
            ? err.message
            : "Lost connection while checking status.";
        setView({
          phase: "processing_failed",
          file: initial,
        });
        console.error(message);
      }
    };

    pollRef.current = setInterval(() => {
      void poll();
    }, 1500);
    void poll();
  }, []);

  const runUpload = async () => {
    if (!selectedFile) {
      return;
    }

    const file = selectedFile;
    setView({
      phase: "uploading",
      fileName: file.name,
      loaded: 0,
      total: file.size,
    });

    const contentType = resolveContentType(file);
    if (!contentType) {
      setView({
        phase: "upload_failed",
        message:
          "Unsupported file type. Use PDF, CSV, PNG, or JPEG.",
      });
      return;
    }

    try {
      const createKey = crypto.randomUUID();
      const session = await createUploadSession(file, contentType, createKey);

      await uploadFileBody(session.id, file, (loaded, total) => {
        setView({
          phase: "uploading",
          fileName: file.name,
          loaded,
          total,
        });
      });

      const completeKey = crypto.randomUUID();
      const fileDetail = await completeUpload(session.id, completeKey);
      startPolling(fileDetail.id, fileDetail);
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Upload failed";
      setView({ phase: "upload_failed", message });
    }
  };

  const busy =
    view.phase === "uploading" || view.phase === "processing";

  const job = "file" in view ? view.file.processing_job : null;

  return (
    <div className="mx-auto w-full max-w-xl space-y-8">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-900">
          FileFlow
        </h1>
        <p className="text-sm leading-relaxed text-zinc-600">
          Upload a document (PDF, CSV, PNG, or JPEG). Progress covers the
          upload and background processing job.
        </p>
      </header>

      <section className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
        <label className="block text-sm font-medium text-zinc-800">
          Choose file
        </label>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          disabled={busy}
          className="mt-2 block w-full text-sm text-zinc-700 file:mr-4 file:rounded-lg file:border-0 file:bg-zinc-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-zinc-700 disabled:opacity-50"
          onChange={(e) => {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            setView({ phase: "idle" });
            setSelectedFile(e.target.files?.[0] ?? null);
          }}
        />

        <div className="mt-4 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!selectedFile || busy}
            onClick={() => void runUpload()}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            Upload
          </button>
          {(view.phase === "upload_failed" ||
            view.phase === "processing_failed" ||
            view.phase === "done") && (
            <button
              type="button"
              onClick={reset}
              className="rounded-lg border border-zinc-300 px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-50"
            >
              Upload another file
            </button>
          )}
        </div>
      </section>

      {view.phase === "uploading" && (
        <section className="space-y-3 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm font-medium text-zinc-900">
              Uploading {view.fileName}
            </p>
            <StatusPill label="Uploading" tone="warn" />
          </div>
          <ProgressBar
            value={progressPercent(view.loaded, view.total)}
          />
          <p className="text-xs text-zinc-500">
            {formatBytes(view.loaded)} / {formatBytes(view.total)} (
            {progressPercent(view.loaded, view.total)}%)
          </p>
        </section>
      )}

      {view.phase === "upload_failed" && (
        <section className="space-y-2 rounded-2xl border border-red-200 bg-red-50 p-6">
          <div className="flex items-center gap-2">
            <StatusPill label="Upload failed" tone="bad" />
          </div>
          <p className="text-sm text-red-900">{view.message}</p>
          <p className="text-xs text-red-800/80">
            Fix the issue (file type, size, or network) and try again, or pick
            another file.
          </p>
        </section>
      )}

      {(view.phase === "processing" ||
        view.phase === "done" ||
        view.phase === "processing_failed") && (
        <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="text-sm font-semibold text-zinc-900">
              {view.file.original_filename}
            </h2>
            <StatusPill
              label={view.file.status}
              tone={
                view.file.status === "completed"
                  ? "ok"
                  : view.file.status === "failed"
                    ? "bad"
                    : "warn"
              }
            />
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-zinc-500">Size</dt>
            <dd className="text-zinc-900">{formatBytes(view.file.size)}</dd>
            <dt className="text-zinc-500">Type</dt>
            <dd className="text-zinc-900">{view.file.content_type}</dd>
          </dl>

          {job && (
            <div className="space-y-2 border-t border-zinc-100 pt-4">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-zinc-800">
                  Processing
                </span>
                <StatusPill
                  label={job.status}
                  tone={
                    job.status === "completed"
                      ? "ok"
                      : job.status === "failed"
                        ? "bad"
                        : "neutral"
                  }
                />
                {job.stage && (
                  <span className="text-xs text-zinc-500">{job.stage}</span>
                )}
              </div>
              {!TERMINAL_FILE_STATUSES.has(view.file.status) && (
                <>
                  <ProgressBar value={job.progress_percent} />
                  <p className="text-xs text-zinc-500">
                    {job.progress_percent}% — polling every 1.5s
                  </p>
                </>
              )}
              {job.retry_count > 0 && (
                <p className="text-xs text-zinc-500">
                  Worker attempts: {job.retry_count}
                </p>
              )}
            </div>
          )}

          {view.phase === "processing_failed" && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
              <p className="font-medium">Processing error</p>
              <p className="mt-1">
                {job?.error_message ??
                  "Processing failed. Automatic retries may already have run."}
              </p>
              <p className="mt-2 text-xs text-red-800/90">
                Upload the file again to start a new job.
              </p>
            </div>
          )}

          {view.phase === "done" && job?.result_payload && (
            <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4">
              <p className="text-sm font-medium text-emerald-900">Result</p>
              <pre className="mt-2 overflow-x-auto text-xs text-emerald-950">
                {tryFormatJson(job.result_payload)}
              </pre>
            </div>
          )}
        </section>
      )}
    </div>
  );
}

function tryFormatJson(raw: string): string {
  try {
    return JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    return raw;
  }
}
