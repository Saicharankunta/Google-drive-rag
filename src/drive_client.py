from __future__ import annotations

import io
from dataclasses import dataclass
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pypdf import PdfReader

from src.config import Settings

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
PDF_MIME = "application/pdf"
TEXT_MIMES = {
    "text/plain",
    "text/markdown",
    "text/csv",
}

SUPPORTED_MIMES = TEXT_MIMES | {GOOGLE_DOC_MIME, PDF_MIME}


@dataclass
class DriveDocument:
    file_id: str
    name: str
    mime_type: str
    text: str


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return "\n".join(parts)


def extract_text(name: str, mime_type: str, content: bytes) -> str | None:
    if mime_type == PDF_MIME:
        return _extract_pdf_text(content)

    if mime_type in TEXT_MIMES or name.endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8", errors="replace")

    return None


class DriveClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._service = build("drive", "v3", credentials=self._get_credentials())

    def _get_credentials(self) -> Credentials:
        creds: Credentials | None = None
        token_path = self._settings.google_token_path
        credentials_path = self._settings.google_credentials_path

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not credentials_path.exists():
                    raise FileNotFoundError(
                        f"Missing {credentials_path}. Download OAuth credentials from Google Cloud Console."
                    )
                flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
                creds = flow.run_local_server(port=0)

            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json())

        return creds

    def list_files(self) -> list[dict]:
        query_parts = [
            "trashed = false",
            "("
            + " or ".join(f"mimeType = '{mime}'" for mime in sorted(SUPPORTED_MIMES))
            + ")",
        ]
        if self._settings.drive_folder_id:
            query_parts.append(f"'{self._settings.drive_folder_id}' in parents")

        query = " and ".join(query_parts)
        files: list[dict] = []
        page_token: str | None = None

        while True:
            response = (
                self._service.files()
                .list(
                    q=query,
                    spaces="drive",
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                    pageSize=100,
                )
                .execute()
            )
            files.extend(response.get("files", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return files

    def download_document(self, file_meta: dict) -> DriveDocument | None:
        file_id = file_meta["id"]
        name = file_meta["name"]
        mime_type = file_meta["mimeType"]

        if mime_type == GOOGLE_DOC_MIME:
            content = (
                self._service.files()
                .export(fileId=file_id, mimeType="text/plain")
                .execute()
            )
            if isinstance(content, bytes):
                text = content.decode("utf-8", errors="replace")
            else:
                text = str(content)
            return DriveDocument(file_id=file_id, name=name, mime_type=mime_type, text=text)

        buffer = io.BytesIO()
        request = self._service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        text = extract_text(name, mime_type, buffer.getvalue())
        if not text or not text.strip():
            return None

        return DriveDocument(file_id=file_id, name=name, mime_type=mime_type, text=text)

    def fetch_all_documents(self) -> list[DriveDocument]:
        documents: list[DriveDocument] = []
        for file_meta in self.list_files():
            doc = self.download_document(file_meta)
            if doc and doc.text.strip():
                documents.append(doc)
        return documents
