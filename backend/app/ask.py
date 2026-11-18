import argparse
import json

from app.core.settings import Settings
from app.integrations.groq_client import ProviderError
from app.models.chat import ChatRequest
from app.repositories.catalogue import CatalogueRepository
from app.repositories.conversations import ConversationRepository
from app.services.answer_service import AnswerService


def main():
    parser = argparse.ArgumentParser(description="Ask the local DENSO RAG pipeline from the terminal.")
    parser.add_argument("question")
    parser.add_argument("--evidence-only", action="store_true")
    arguments = parser.parse_args()
    settings = Settings.load()
    service = AnswerService(CatalogueRepository(settings), ConversationRepository(settings.runtime_dir / "conversations.sqlite3"))
    try:
        response = service.ask(ChatRequest(question=arguments.question, mode="evidence" if arguments.evidence_only else "answer"), settings)
    except (ProviderError, ValueError, OSError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
