
import subprocess

CONFIG = """
port = "8080"
read_only = false
"""

subprocess.run(["npx", "-y", "kubernetes-mcp-server@latest", "--config", "-"], input=CONFIG, text=True)    # "--config -" = read the settings from here