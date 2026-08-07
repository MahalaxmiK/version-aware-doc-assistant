\# Version-Aware Documentation Assistant



A technical-documentation question-answering service that retrieves

information from the user-selected product version and generates answers

with source citations.



\## Project objective



The project demonstrates retrieval-augmented generation, metadata-filtered

retrieval, grounded answer generation, citation handling and systematic

evaluation. Its primary requirement is version isolation: a question about

version 1 must never be answered using version 2 documentation.



\## Current status



The initial project structure, synthetic versioned documentation and

FastAPI health endpoint are implemented. Document ingestion, embeddings,

retrieval and LLM answer generation will be added incrementally.



\## Example behavior



Question:



> What is the API request limit?



Expected answers:



\- Version 1: 100 requests per minute

\- Version 2: 250 requests per minute



\## Technology



\- Python

\- FastAPI

\- Pytest

\- Vector database and LLM provider to be selected



\## Run locally



Create and activate a virtual environment, then install dependencies:



```powershell

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt

