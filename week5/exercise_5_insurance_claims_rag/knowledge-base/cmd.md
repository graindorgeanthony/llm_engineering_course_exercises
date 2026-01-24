uv run knowledge-base/knowledge_generator.py --use-cases "Claim management RAG that will be use for other claims to be processed efficiently and help agents make better decisions" --num-files 150

uv run knowledge-base/consistency_audit.py --overwrite

uv run implementation/ingest.py

uv run knowledge-base/test_cases_generator.py --use-cases "Generate claims context & claims approval/refusal case answer + reasons. Question formulated as if an internal agent asks to get advice on if he/she should accept or refuse a claim request." --num-cases 150 --overwrite --use-chunks
