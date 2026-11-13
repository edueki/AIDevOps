import os
import chromadb
from langchain_text_splitters import RecursiveCharacterTextSplitter

HERE = os.path.dirname(os.path.abspath(__file__))
WIKI_FOLDER = os.path.join(HERE, "..", "wiki_pages")     # the pages we load
DB_FOLDER = os.path.join(HERE, "chroma_db")              # ChromaDB saves its data here
COLLECTION_NAME = "runbookdata"

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
client = chromadb.PersistentClient(path=DB_FOLDER)
collection = client.create_collection(name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"})

ids = []
documents = []
metadatas = []

for file in sorted(os.listdir(WIKI_FOLDER)):
    if not file.endswith(".md"):
        continue

    text = open(os.path.join(WIKI_FOLDER, file), encoding="utf-8").read()
    title = text.splitlines()[0].lstrip("# ")            # the first line of the page is its title
    chunks = splitter.split_text(text)
    print(f"{file}: {len(chunks)} chunks")

    for number, chunk in enumerate(chunks):
        ids.append(f"{file}-{number + 1}")
        documents.append(title + "\n" + chunk)           # the title in front of every chunk
        metadatas.append({"file": file, "title": title})
collection.add(ids=ids, documents=documents, metadatas=metadatas)
print("Collection ready. Items inside:", collection.count())
