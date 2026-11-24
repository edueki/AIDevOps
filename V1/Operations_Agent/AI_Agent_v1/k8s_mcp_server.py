
import os
from kubernetes import client, config

from mcp.server.mcpserver import MCPServer

config.load_kube_config()
core = client.CoreV1Api()
apps = client.AppsV1Api()

mcp = MCPServer("eks-mcp-server")

@mcp.tool()
def list_namespaces():
    """List the namespaces in the cluster."""
    namespaces = core.list_namespace().items
    return {"namespaces": [ns.metadata.name for ns in namespaces]}

@mcp.tool()
def list_deployments(namespace: str = "default") -> dict:
    """List the deployments in a namespace, with ready and desired replicas."""
    deployments = apps.list_namespaced_deployment(namespace).items
    return {"deployments": [
        {"name": d.metadata.name, "ready": d.status.ready_replicas or 0, "desired": d.spec.replicas}
        for d in deployments
    ]}


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host=os.getenv("MCP_HOST", "127.0.0.1"), port=8002)    # MCP_HOST=0.0.0.0 inside a container