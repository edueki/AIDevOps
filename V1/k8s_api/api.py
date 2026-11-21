import uvicorn
from fastapi import FastAPI

from kubernetes import client, config

config.load_kube_config()
core = client.CoreV1Api()
apps = client.AppsV1Api()

app = FastAPI()

@app.get("/namespaces")
def list_namespaces():
    namespaces = core.list_namespace().items
    return {"namespaces": [ns.metadata.name for ns in namespaces]}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)

