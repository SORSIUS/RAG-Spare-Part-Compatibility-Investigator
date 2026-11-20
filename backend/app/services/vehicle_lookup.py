"""Owner wording -> explicit catalogue filters; no LLM or inferred fitment."""
import re


def matches_engine(record, requested):
    if not requested:
        return True
    text = record.get("application", "")
    number = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:l|cc)?", requested, re.I)
    if number:
        value = float(number[1])
        cc = round(value * 1000) if value < 10 else round(value)
        known = [round(float(v) * 1000) for v in re.findall(r"(?<![\d.])(\d\.\d+)\s*L\b", text, re.I)]
        known.extend(round(float(v)*1000) for v in re.findall(r"\b(\d\.\d+)L?\b", record.get("vehicle_label", ""), re.I))
        if record.get("engine_cc"):
            known.append(record["engine_cc"])
        return cc in known
    normalize = lambda v: re.sub(r"[^A-Z0-9]", "", v.upper())
    if record.get("engine"):
        return normalize(requested) == normalize(record["engine"])
    return bool(re.search(r"(?<![A-Z0-9])" + re.escape(requested.upper()) + r"(?![A-Z0-9])", text.upper()))


def owner_query(question, vehicles):
    if re.search(r"\b(swap|instead|replace.+with)\b", question, re.I):
        return None
    ignition = bool(re.search(r"\b(spark\s*plugs?|plugs?)\b", question, re.I))
    if not ignition and not re.search(r"\b(suspensions?|shocks?|struts?|mounts?|mounting|protection)\b", question, re.I):
        return None
    hits = [v for v in vehicles if re.search(r"\b" + re.escape(v["model"]) + r"\b", question, re.I)
            and (v["model"].lower() != "fit" or re.search(r"\b(?:honda|my|a)\s+fit\b", question, re.I))]
    named = [v for v in hits if re.search(r"\b" + re.escape(v["make"]) + r"\b", question, re.I)]
    specific_models = {v["model"] for v in hits if not any(v["model"].lower() != w["model"].lower() and v["model"].lower() in w["model"].lower() for w in hits)}
    if len(specific_models) > 1:
        return None
    if named:
        hits = named
    hits = [v for v in hits if not any(v["model"].lower() != w["model"].lower() and v["model"].lower() in w["model"].lower() for w in hits)]
    hits = list({(v["make"], v["model"]): v for v in hits}.values())
    if len(hits) != 1:
        return None
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    capacity = re.search(r"\b(\d\.\d+)\s*(?:l(?:itre|iter)?s?)?\b|\b(\d{3,4})\s*cc\b|\b(\d)\s*l(?:itre|iter)?s?\b", question, re.I)
    code = re.search(r"\b(?=[A-Z0-9]{1,4}-)(?=[A-Z0-9]*\d)[A-Z0-9]{1,4}-[A-Z]{1,4}\b", question, re.I)
    chassis = re.search(r"\b[A-Z]{2,4}\d{2,3}[A-Z]?\b", question, re.I)
    engine = code[0] if code else next((value for value in capacity.groups() if value), "") if capacity else ""
    market = next((name for name in ("Taiwan", "Pakistan", "Japan", "India", "Thailand", "Vietnam") if re.search(r"\b"+name+r"\b", question, re.I)), "")
    return {**hits[0], "year": int(years[-1]) if years else None, "engine": engine, "market": market,
            "chassis": chassis[0] if chassis else "",
            "axle": "front" if re.search(r"\bfront\b", question, re.I) and not re.search(r"\b(rear|back)\b", question, re.I) else "rear" if re.search(r"\b(rear|back)\b", question, re.I) and not re.search(r"\bfront\b", question, re.I) else "",
            "category": "ignition" if ignition else "suspension",
            "component": "spark_plug" if ignition else "shock_absorber" if re.search(r"\b(shocks?|struts?)\b", question, re.I) else "mounting_kit" if re.search(r"\b(mounts?|mounting)\b", question, re.I) else "protection_kit" if re.search(r"\bprotection\b", question, re.I) else ""}
