import sys
import os
import json
from db_setup.helper import setup
from src.rag import RAGPipeline


if __name__ == "__main__":
    setup()
    rag = RAGPipeline()
    folder = "json_chunks"

    files_path = [os.path.join(folder, file) for file in os.listdir(folder) if file.endswith(".json")]

    for file_path in files_path:
        with open(file_path, "r") as f:
            collection_name = file_path.split("/")[-1].split(".")[0]
            print( "Collection Name: ", collection_name)
            rag.create_chunks_index(json.load(f), collection_name)


