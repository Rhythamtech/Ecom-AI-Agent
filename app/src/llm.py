from langchain_openai import ChatOpenAI
from .config import settings
from .prompts import sql_system_prompt, data_analyst_prompt
from schema import SqlResponse
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from typing import Optional
load_dotenv()



llm = ChatOpenAI(
    model=settings.OPENAI_MODEL,
    base_url=settings.OPENAI_BASE_URL,
    api_key=settings.OPENAI_API_KEY
)


class BaseAgent:
    def __init__(self, system_prompt: str):
        self.system_prompt = system_prompt
    
    def base_agent(self, question: str, data: Optional[str] = None, schema: Optional[object] = None):
        prompt = ChatPromptTemplate.from_messages([
        ("system", self.system_prompt),
        ("user", "{question} \n {data}"),])

        chain = prompt | llm

        if schema:
            chain = prompt | llm.with_structured_output(schema)
            return chain.invoke({"question": question, "data": data})
        return chain.invoke({"question": question, "data": data})



class SQLAgent(BaseAgent):
    def __init__(self):
        super().__init__(sql_system_prompt)
    
    def sql_agent(self, question: str):
        schema = SqlResponse
        return self.base_agent(question=question, schema=schema)

class DataAnalystAgent(BaseAgent):
    def __init__(self):
        super().__init__(data_analyst_prompt)
    
    def data_analyst(self, question: str, data: str):
        schema = None
        return self.base_agent(question=question, data=data)

    
