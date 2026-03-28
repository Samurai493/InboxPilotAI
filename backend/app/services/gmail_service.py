"""Gmail service for reading emails and creating drafts."""
from __future__ import annotations

import base64
import time
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Partial response masks (smaller JSON; faster over the wire and to parse).
GMAIL_LIST_MESSAGES_FIELDS = "messages/id,nextPageToken"
GMAIL_MESSAGE_METADATA_FIELDS = "id,snippet,payload(headers)"

# Sub-requests per batch HTTP call. With sequential batches only (no parallel execute),
# ~50 is usually one round trip for a default inbox page; lower if you see 429s.
GMAIL_METADATA_BATCH_SIZE = 50
# Pause only between the 2nd+ batch in the same page (burst guard).
GMAIL_METADATA_BATCH_PAUSE_SEC = 0.05
# Hard cap per list page to keep latency predictable.
GMAIL_LIST_PAGE_MAX = 100


def _message_summary_from_resource(message_id: str, resource: Dict[str, Any]) -> Dict[str, Any]:
    headers_list = resource.get("payload", {}).get("headers", [])
    headers = {h["name"]: h["value"] for h in headers_list}
    return {
        "id": message_id,
        "subject": headers.get("Subject", ""),
        "from_email": headers.get("From", ""),
        "date": headers.get("Date", ""),
        "body": "",
        "snippet": resource.get("snippet", ""),
    }


def _is_gmail_429(exc: BaseException) -> bool:
    if isinstance(exc, HttpError) and exc.resp is not None and exc.resp.status == 429:
        return True
    msg = str(exc).lower()
    return "429" in msg and ("ratelimit" in msg or "too many concurrent" in msg)


def _gmail_service_for_batch(
    credentials: Credentials,
    service: Any | None,
) -> Any:
    """Prefer the long-lived client from ``GmailService`` (avoids repeated discovery per chunk)."""
    if service is not None:
        return service
    return build("gmail", "v1", credentials=credentials, cache_discovery=False)


def _batch_get_message_metadata_once(
    credentials: Credentials,
    message_ids: List[str],
    *,
    service: Any | None = None,
) -> Dict[str, Dict[str, Any]]:
    """One HTTP batch request: many messages.get(metadata) in a single round trip."""
    svc = _gmail_service_for_batch(credentials, service)
    results: Dict[str, Dict[str, Any]] = {}
    errors: Dict[str, BaseException] = {}

    def callback(request_id: str, response: Any, exception: BaseException | None) -> None:
        rid = str(request_id)
        if exception is not None:
            errors[rid] = exception
        elif response is not None:
            results[rid] = _message_summary_from_resource(rid, response)

    batch = svc.new_batch_http_request(callback=callback)
    for mid in message_ids:
        batch.add(
            svc.users().messages().get(
                userId="me",
                id=mid,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"],
                fields=GMAIL_MESSAGE_METADATA_FIELDS,
            ),
            request_id=mid,
        )
    batch.execute()
    if not errors:
        return results
    non_429 = [e for e in errors.values() if not _is_gmail_429(e)]
    if non_429:
        raise Exception(f"Gmail batch metadata failed: {non_429[0]}") from non_429[0]
    missing = [mid for mid in message_ids if mid not in results]
    if not missing:
        return results
    if len(missing) == len(message_ids):
        raise next(iter(errors.values()))
    time.sleep(GMAIL_METADATA_BATCH_PAUSE_SEC)
    more = _batch_get_message_metadata(credentials, missing, service=svc)
    results.update(more)
    still_missing = [mid for mid in message_ids if mid not in results]
    if still_missing:
        raise Exception(
            f"Gmail metadata incomplete after rate-limit retry ({len(still_missing)} message(s))"
        )
    return results


def _batch_get_message_metadata(
    credentials: Credentials,
    message_ids: List[str],
    *,
    service: Any | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Batch metadata with backoff when Gmail returns 429 (per-user concurrency / quota)."""
    if not message_ids:
        return {}
    backoff_sec = (0.0, 0.75, 1.75, 3.5)
    last: BaseException | None = None
    for wait in backoff_sec:
        if wait > 0:
            time.sleep(wait)
        try:
            return _batch_get_message_metadata_once(
                credentials, message_ids, service=service
            )
        except HttpError as e:
            last = e
            if _is_gmail_429(e):
                continue
            raise Exception(f"Gmail batch metadata failed: {e}") from e
        except Exception as e:
            last = e
            if _is_gmail_429(e):
                continue
            raise
    raise Exception(f"Gmail batch metadata failed after retries: {last}") from last


def _fetch_message_metadata_batched(
    credentials: Credentials,
    message_ids: List[str],
    *,
    batch_size: int = GMAIL_METADATA_BATCH_SIZE,
    service: Any | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Split ids into batches; run each batch HTTP request sequentially (no parallel batch.execute)."""
    if not message_ids:
        return {}
    merged: Dict[str, Dict[str, Any]] = {}
    for i in range(0, len(message_ids), batch_size):
        if i > 0 and GMAIL_METADATA_BATCH_PAUSE_SEC > 0:
            time.sleep(GMAIL_METADATA_BATCH_PAUSE_SEC)
        chunk = message_ids[i : i + batch_size]
        merged.update(_batch_get_message_metadata(credentials, chunk, service=service))
    return merged


class GmailService:
    """Service for Gmail API operations."""

    def __init__(self, credentials: Optional[Credentials] = None):
        """Initialize Gmail service with credentials."""
        self.credentials = credentials
        self.service = None
        if credentials:
            self.service = build("gmail", "v1", credentials=credentials)

    def list_messages(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        List messages from inbox.

        Args:
            max_results: Maximum number of messages to return

        Returns:
            List of message metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")

        try:
            results = self.service.users().messages().list(
                userId="me",
                maxResults=max_results,
            ).execute()

            messages = results.get("messages", [])
            return messages
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get a specific message.

        Args:
            message_id: Gmail message ID

        Returns:
            Message content and metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")

        try:
            message = self.service.users().messages().get(
                userId="me",
                id=message_id,
                format="full",
            ).execute()

            # Extract message data
            payload = message.get("payload", {})
            headers = payload.get("headers", [])

            # Extract headers
            subject = next((h["value"] for h in headers if h["name"] == "Subject"), "")
            from_header = next((h["value"] for h in headers if h["name"] == "From"), "")
            date = next((h["value"] for h in headers if h["name"] == "Date"), "")

            # Extract body
            body = self._extract_body(payload)

            return {
                "id": message_id,
                "subject": subject,
                "from": from_header,
                "date": date,
                "body": body,
                "snippet": message.get("snippet", ""),
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def list_message_summaries_page(
        self,
        max_results: int = 10,
        page_token: str | None = None,
    ) -> Dict[str, Any]:
        """List one inbox page with summaries and pagination token."""
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")
        if not self.credentials:
            raise ValueError("Gmail service not initialized. Credentials required.")

        max_results = min(max(max_results, 1), GMAIL_LIST_PAGE_MAX)
        try:
            kwargs: Dict[str, Any] = {"userId": "me", "maxResults": max_results}
            if page_token:
                kwargs["pageToken"] = page_token
            kwargs["fields"] = GMAIL_LIST_MESSAGES_FIELDS
            results = self.service.users().messages().list(**kwargs).execute()
            messages = results.get("messages", [])
            ids = [m["id"] for m in messages]
            by_id = _fetch_message_metadata_batched(
                self.credentials, ids, service=self.service
            )
            out = [by_id[mid] for mid in ids if mid in by_id]
            if len(out) != len(ids):
                missing = set(ids) - set(by_id)
                raise Exception(f"Gmail metadata incomplete for message(s): {sorted(missing)[:5]}")
            return {
                "messages": out,
                "next_page_token": results.get("nextPageToken"),
            }
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")

    def list_message_summaries(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """List inbox messages with subject, from, date, snippet (no body text)."""
        return self.list_message_summaries_page(max_results=max_results).get("messages", [])

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract message body from payload."""
        body = ""

        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    body += base64.urlsafe_b64decode(data).decode("utf-8")
        elif payload.get("mimeType") == "text/plain":
            data = payload["body"].get("data", "")
            body += base64.urlsafe_b64decode(data).decode("utf-8")

        return body

    def create_draft(self, to: str, subject: str, body: str) -> Dict[str, Any]:
        """
        Create a draft email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body

        Returns:
            Draft metadata
        """
        if not self.service:
            raise ValueError("Gmail service not initialized. Credentials required.")

        try:
            message = MIMEText(body)
            message["to"] = to
            message["subject"] = subject

            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

            draft = self.service.users().drafts().create(
                userId="me",
                body={
                    "message": {
                        "raw": raw_message,
                    },
                },
            ).execute()

            return draft
        except HttpError as error:
            raise Exception(f"An error occurred: {error}")
