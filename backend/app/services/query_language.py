import re


def expand_owner_question(question):
    additions = []
    if re.search(r"\b(bounc\w*|bumps?|potholes?)\b", question, re.IGNORECASE):
        additions.append("vehicle suspension shock absorbers struts damping")
    if re.search(r"\b(smells?|odou?rs?|stink\w*)\b", question, re.IGNORECASE):
        additions.append("cabin air filter activated carbon filtration")
    if re.search(r"\b(pollen|sneez\w*|allerg\w*)\b", question, re.IGNORECASE):
        additions.append("cabin air filter particles filtration")
    return question + (" " + " ".join(additions) if additions else "")
