
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

llm = ChatAnthropic(model="claude-opus-5-5", api_key=os.getenv("ANTHROPIC_API_KEY"), max_tokens=1024)

prompt = ChatPromptTemplate.from_template("Can you explain this topic? {topic}")

chain = prompt | llm

response = chain.invoke({"topic": "kubernetes pod status CrashLoopBackOff"}).text

print (response)



