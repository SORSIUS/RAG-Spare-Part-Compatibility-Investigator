import re


VEHICLE_QUESTIONS = [
    "Which cars and model years are you comparing?",
    "Is the part at the front or back of the car, and is it one component or the whole suspension assembly?",
    "Which country is the receiving car from, and what is its engine size or version, if known?",
]


def needs_vehicle_details(question):
    component = re.search(r"\b(suspensions?|shocks?|struts?|springs?|brakes?|steering)\b", question, re.IGNORECASE)
    swap = re.search(r"\b(swap|interchange|compatible)\b|\b(can|could)\b.*\b(use|fit|install)\b", question, re.IGNORECASE)
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    return bool(component and swap and len(years) < 2)
