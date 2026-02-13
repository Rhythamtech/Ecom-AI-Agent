import os
import logging
import json
import uuid
from .config import settings
from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from langchain_cohere import CohereEmbeddings


class RAGPipeline:
    def __init__(self):
        self.embedder = CohereEmbeddings(model="embed-v4.0")
        self.qdrant_url = settings.QDRANT_URL

    def create_chunks_index(self, chunks: list[dict], collection_name: str):
        logging.info("Creating chunks index.")
        chunk_docs = []        
            
        try:
            for chunk in chunks:
                metadata = chunk["metadata"]

                data = {key: value for key, value in chunk.items() if key != "metadata"}
                doc = Document(
                    page_content=f"{data}",
                    metadata={"id": str(uuid.uuid4()), **metadata}
                )
                chunk_docs.append(doc)
          
        except json.JSONDecodeError as e:
            logging.error(f"Failed to decode JSON: {e}")
            logging.error(f"Invalid JSON string: {response.choices[0].message.content}")


        QdrantVectorStore.from_documents(
            documents=chunk_docs,
            embedding=self.embedder,
            collection_name=collection_name,
            url=self.qdrant_url
        )
        logging.info("Ecom Context vector store created successfully.")

    def query_qna_index(self, user_query, collection_name: str):
        logging.info(f"Querying QnA index with: {user_query}")
        vector_store = QdrantVectorStore.from_existing_collection(
            embedding=self.embedder,
            collection_name=collection_name,
            url=self.qdrant_url
        )
        results = vector_store.similarity_search(query=user_query, k=3)
        return results


# if __name__ == "__main__":
#     rag = RAGPipeline()

#     folder = "app/json_chunks"

#     files_path = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith(".json")]

#     for file_path in files_path:
#         with open(file_path, "r") as f:
#             collection_name = file_path.split("/")[-1].split(".")[0]
#             if collection_name == "qna":
#                 print( "Collection Name: ", collection_name)
#                 rag.create_chunks_index(json.load(f), collection_name)