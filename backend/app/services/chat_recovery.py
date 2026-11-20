"""Honest, source-preserving chat responses when generation is unavailable."""
from app.services.fitment_answer import fitment_answer


def provider_recovery(base, error, validate):
    fallback = fitment_answer(base['sources'])
    if fallback:
        validate(fallback, base['sources'])
        return {**base, **fallback.model_dump(exclude={'insufficient_evidence'}), 'status': 'answered',
                'answer_method': 'linked_catalogue', 'generation_note': 'I could not generate an explanation right now, so I am showing the checked catalogue details.',
                'provider_issue': error.code}
    messages = {
        'configuration_missing': 'I found the source passages, but explained answers are not configured yet. You can read the references below or complete answer setup and try again.',
        'provider_auth': 'I found the references, but the answer service could not authenticate. Check answer setup, then try again. Your sources are still available below.',
        'provider_rate_limit': 'The answer service is busy with its usage limit. You can check the references below now, or try the explanation again later.',
        'provider_timeout': 'The explanation took too long this time. Your references are below. Try a shorter question, or retry in a moment.',
    }
    return {**base, 'status': 'provider_unavailable', 'assistant_text': messages.get(error.code, 'I could not generate the explanation just now. I have kept the relevant references below so you can still check the evidence.'),
            'provider_issue': error.code, 'summary': 'Your references are still here', 'follow_up_questions': []}
