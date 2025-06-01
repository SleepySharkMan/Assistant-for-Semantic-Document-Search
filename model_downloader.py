import re
import sys
import getpass
from pathlib import Path
from typing import Optional

from huggingface_hub import snapshot_download, login, HfHubHTTPError


class ModelDownloader:
    """Скачивает публичные и приватные репозитории Hugging Face в папку ./models."""

    _URL_RE = re.compile(r"^https?://huggingface\.co/([\w\-/]+)/?$", re.I)

    def __init__(self, cache_dir: str | Path | None = None, revision: str | None = None) -> None:
        self.cache_dir = Path(cache_dir or "models").expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.revision = revision

    def download(
        self,
        link_or_repo: str,
        *,
        token: Optional[str] = None,
        force: bool = False,
    ) -> Path:
        repo_id = self._normalize(link_or_repo)
        if token is None and sys.stdin.isatty():
            token = self._prompt_token()
        if token:
            login(token=token, add_to_git_credential=True)

        try:
            dst = snapshot_download(
                repo_id=repo_id,
                cache_dir=self.cache_dir,
                revision=self.revision,
                resume_download=not force,
                token=token,
            )
            return Path(dst)
        except HfHubHTTPError as e:
            if getattr(e.response, "status_code", None) in {401, 403}:
                raise RuntimeError("Требуется действительный Hugging Face token") from e
            raise

    def _normalize(self, text: str) -> str:
        m = self._URL_RE.match(text.strip())
        if m:
            return m.group(1)
        if "/" in text:
            return text.strip()
        raise ValueError("Неверный URL или repo_id")

    @staticmethod
    def _prompt_token() -> Optional[str]:
        token = getpass.getpass("HF_TOKEN (Enter — если модель публичная): ").strip()
        return token or None