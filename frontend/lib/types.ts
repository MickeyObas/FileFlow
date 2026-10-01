export type FileStatus =
  | "pending"
  | "uploading"
  | "uploaded"
  | "processing"
  | "completed"
  | "failed"
  | "expired";

export type JobStatus = "pending" | "processing" | "completed" | "failed";

export interface JobOut {
  id: string;
  file_id: string;
  status: JobStatus;
  stage: string | null;
  progress_percent: number;
  error_message: string | null;
  result_payload: string | null;
  result_storage_key: string | null;
  retry_count: number;
  created_at: string;
  updated_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface FileDetailOut {
  id: string;
  original_filename: string;
  content_type: string;
  size: number;
  status: FileStatus;
  created_at: string;
  processing_job: JobOut | null;
}

export interface UploadOut {
  id: string;
  original_filename: string;
  content_type: string;
  expected_size: number | null;
  status: FileStatus;
  bytes_received: number;
  bytes_total: number | null;
  progress_percent: number | null;
  file_id: string | null;
  created_at: string;
}
