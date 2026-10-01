def upload_progress(
    *,
    bytes_received: int,
    expected_size: int | None,
) -> tuple[int | None, float | None]:
    if expected_size is None or expected_size <= 0:
        return None, None
    percent = min(100.0, round(bytes_received / expected_size * 100, 2))
    return expected_size, percent


def job_progress_for_status(
    *,
    status: str,
    stage: str | None,
    stored_percent: int,
) -> tuple[str | None, int]:
    if status == "completed":
        return "done", 100
    if status == "failed":
        return stage, stored_percent
    if status == "pending":
        return stage or "queued", stored_percent
    return stage, stored_percent
