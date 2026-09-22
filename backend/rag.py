"""Repository RAG pipeline for semantic code and documentation understanding.

Pipeline:
  GitHub Repository
         │ (via MCP tree discovery & file reader)
         ▼
  Selective File Filtering (docs, configs, key source code; skips noise/binary/lockfiles)
         │
         ▼
  Chunking (RecursiveCharacterTextSplitter)
         │
         ▼
  Embeddings (Google Gemini / OpenAI Embeddings)
         │
         ▼
  Vector Store (Chroma)
         │
         ▼
  Retriever -> Relevant Context -> Agent / LLM
"""

import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from mcp_server.github_tools import fetch_repository_tree, read_repository_file

load_dotenv()

# File extensions prioritized for repository RAG understanding
IMPORTANT_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx",
    ".go", ".rs", ".java", ".cpp", ".c", ".h",
    ".md", ".rst", ".txt",
    ".toml", ".yaml", ".yml", ".json",
    ".sh", ".sql",
}

# Files that should be excluded from semantic chunking (generated, lockfiles, minified)
EXCLUDED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
}


def is_important_file(path: str) -> bool:
    """Determine if a file is an important source or documentation file for RAG ingestion."""
    base_name = os.path.basename(path).lower()

    if base_name in EXCLUDED_FILENAMES:
        return False
    if base_name.endswith(".min.js") or base_name.endswith(".min.css"):
        return False

    # Always include top-level configs and documentation
    if base_name.startswith("readme") or base_name in {
        "dockerfile", "docker-compose.yml", "pyproject.toml",
        "requirements.txt", "setup.py", "package.json", "go.mod", "cargo.toml"
    }:
        return True

    _, ext = os.path.splitext(base_name)
    return ext in IMPORTANT_EXTENSIONS


def get_embeddings() -> Embeddings:
    """Return the configured embedding model."""
    google_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if google_key and google_key.strip():
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        return GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    if openai_key and openai_key.strip():
        from langchain_openai import OpenAIEmbeddings
        return OpenAIEmbeddings(model="text-embedding-3-small")

    raise ValueError(
        "No supported embedding key found. Set GOOGLE_API_KEY or OPENAI_API_KEY in .env"
    )


class RepositoryRAG:
    """Manages semantic ingestion and retrieval for a GitHub repository."""

    def __init__(self, repo_url: str, vectorstore: Chroma):
        self.repo_url = repo_url
        self.vectorstore = vectorstore
        self.retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    @classmethod
    def index_repository(
        cls,
        repo_url: str,
        max_files: int = 15,
        chunk_size: int = 800,
        chunk_overlap: int = 100,
    ) -> "RepositoryRAG":
        """Fetch important files from the repository via GitHub API and index into Chroma.

        Args:
            repo_url: GitHub repository URL or shorthand.
            max_files: Maximum number of files to selectively index.
            chunk_size: Text splitter chunk size in characters.
            chunk_overlap: Text splitter chunk overlap.

        Returns:
            An instantiated RepositoryRAG object ready for retrieval.
        """
        # Step 1: Fetch filtered repository tree
        tree_res = fetch_repository_tree(repo_url)
        if tree_res.get("error"):
            raise ValueError(f"Cannot index repository: {tree_res.get('message')}")

        all_files = tree_res.get("files", [])
        candidates = [f for f in all_files if is_important_file(f.get("path", ""))]

        # Sort priority: READMEs and configs first, then source files by size
        def priority_score(item: Dict[str, Any]) -> int:
            p = item.get("path", "").lower()
            if "readme" in p:
                return 0
            if any(cfg in p for cfg in ["pyproject", "setup.py", "package.json", "dockerfile", "requirements"]):
                return 1
            return 2

        candidates.sort(key=priority_score)
        selected_files = candidates[:max_files]

        # Step 2: Read contents and create documents
        documents: List[Document] = []
        for file_info in selected_files:
            file_path = file_info.get("path")
            content_res = read_repository_file(repo_url=repo_url, file_path=file_path)
            if content_res.get("error"):
                continue

            raw_text = content_res.get("content", "")
            if raw_text and raw_text.strip():
                documents.append(
                    Document(
                        page_content=raw_text,
                        metadata={
                            "source": file_path,
                            "repo": repo_url,
                            "size_bytes": content_res.get("size_bytes", 0),
                        },
                    )
                )

        if not documents:
            raise ValueError(f"No indexable textual documents found in {repo_url}")

        # Step 3: Chunking
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunked_docs = splitter.split_documents(documents)

        # Step 4 & 5: Embeddings & Vector Store
        embeddings = get_embeddings()
        vectorstore = Chroma.from_documents(documents=chunked_docs, embedding=embeddings)

        return cls(repo_url=repo_url, vectorstore=vectorstore)

    def retrieve_context(self, query: str, top_k: int = 4) -> str:
        """Search the indexed repository and format matching chunks as structured markdown."""
        docs = self.vectorstore.similarity_search(query, k=top_k)
        if not docs:
            return "(No relevant repository context found)"

        formatted = []
        for idx, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "unknown")
            formatted.append(f"### [Chunk {idx} from `{source}`]\n```\n{doc.page_content.strip()}\n```")

        return "\n\n".join(formatted)
