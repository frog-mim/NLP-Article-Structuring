def combine_results(title, label, entities, facts):

    return {
        "title": title,
        "predicted_category": label,
        "named_entities": entities,
        "extracted_facts": facts
    }
