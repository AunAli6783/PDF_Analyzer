# If you ever see the old error about `langchain.chains`, you are not running this file.
# (Keeping this marker helps confirm the correct module is being executed.)
QA_AGENT_VERSION_MARKER = "qa_agent.py:langchain_community+langchain_groq"

raise RuntimeError("qa_agent.py (LangChain) is disabled on Python 3.14. Use groq_qa_agent.py instead.")