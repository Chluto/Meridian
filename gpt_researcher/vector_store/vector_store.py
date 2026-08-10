"""
Wrapper for langchain vector store
"""
import os
from typing import List, Dict

from langchain_core.documents import Document
from langchain_community.vectorstores import VectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

class VectorStoreWrapper:
    """
    A Wrapper for LangchainVectorStore to handle GPT-Researcher Document Type
    """
    def __init__(self, vector_store : VectorStore):
        self.vector_store = vector_store

    def load(self, documents):
        """
        Load the documents into vector_store
        Translate to langchain doc type, split to chunks then load
        """
        langchain_documents = self._create_langchain_documents(documents)
        splitted_documents = self._split_documents(langchain_documents)
        self.vector_store.add_documents(splitted_documents)
    
    def _create_langchain_documents(self, data: List[Dict[str, str]]) -> List[Document]:
        """Convert GPT Researcher Document to Langchain Document"""
        return [Document(page_content=item["raw_content"], metadata={"source": item["url"]}) for item in data]

    def _split_documents(self, documents: List[Document], chunk_size: int | None = None, chunk_overlap: int | None = None) -> List[Document]:
        """
        Split documents into smaller chunks

        切分参数支持配置驱动（环境变量 CHUNK_SIZE / CHUNK_OVERLAP），
        便于针对中文长文档调整切分粒度。
        """
        if chunk_size is None:
            chunk_size = int(os.getenv("CHUNK_SIZE", "1000"))
        if chunk_overlap is None:
            chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "200"))
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        return text_splitter.split_documents(documents)

    async def asimilarity_search(self, query, k, filter):
        """Return query by vector store"""
        results = await self.vector_store.asimilarity_search(query=query, k=k, filter=filter)
        return results
