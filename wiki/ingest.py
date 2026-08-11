    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        text = re.sub(r",\s*([}\]])", r"\1", text)
        data = json.loads(text)
    return data if isinstance(data, dict) else {}
