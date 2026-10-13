import re

MODEL_NAME = "dslim/bert-base-NER"

# Person, Location, Organizations, Miscellaneous names
ENTITY_TYPES = {"PER", "LOC", "ORG", "MISC"}

# The model is unable to read email addresses. This is created as a way to redact emails.
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

class Redactor:
    """Redacts entities written in English text"""

    def __init__(self, min_score, ner_pipeline=None):
        self.min_score = float(min_score)
        self.model_name = MODEL_NAME

        # Test application without downloading model
        if ner_pipeline == None:
            from transformers import pipeline

            ner_pipeline = pipeline(
                "ner",
                model=MODEL_NAME,
                aggregation_strat="simple"
            )

        self.ner = ner_pipeline

    def redact(self, text, types=None):
        """Returns redacted text, the types of entities redacted, and the model used. Email will always be redacted"""

        if not isinstance(text, str) or not 1 <= len(text) <= 10_000:
            raise ValueError("Text must be between 1 and 10000 characters")

        if types == None:
            types = ENTITY_TYPES.copy()

        # checks whether the input is valid
        if (not isinstance(types, (list, set, tuple))
            or not all(isinstance(t, str) for t in types)
            or not set(types).issubset(ENTITY_TYPES)):

            raise ValueError("types must only be PER, LOC, ORG, or MISC")

        types_used = set(types)

        # Get the entities from the model
        entities = []

        for predictions in self.ner(text):
            entity_type = predictions.get("entity_group")
            start = predictions.get("start")
            end = predictions.get("end")
            score = float(predictions.get("score", 0.0))

            # If the entity type is not used, ignore
            if entity_type not in types_used:
                continue

            # If the score is less than the minimum score, ignore
            if score < self.min_score:
                continue

            # If the start and end are invalid, ignore
            if (not isinstance(start, int)
                or not isinstance(end, int)
                or not 0 <= start < end <= len(text)):
                continue

            # Write the information
            entities.append({
                "type": entity_type,
                "text": text[start:end],
                "start": start,
                "end": end,
                "score": score,
            })

        # Emails will always be redacted
        email_entities = [
            {
                "type": "EMAIL",
                "text": match.group(),
                "start": match.start(),
                "end": match.end(),
                "score": 1.0,
            }
            for match in EMAIL_PATTERN.finditer(text)
        ]

        # If model overlaps email, regex email takes priority
        entities = [
            entity
            for entity in entities
            if not any(
                entity["start"] < email["end"]
                and entity["end"] > email["start"]
                for email in email_entities
            )
        ]

        # Adds the entities from email to the end of the list and sorts them based on the start and end positions
        entities.extend(email_entities)
        entities.sort(key=lambda entity: (entity["start"], entity["end"]))

        # Replace from right to left to preserve validity of character offsets
        redacted_text = text

        for entity in reversed(entities):
            start = entity["start"]
            end = entity["end"]
            placeholder = f"[{entity['type']}]"

            redacted_text = (
                redacted_text[:start]
                + placeholder
                + redacted_text[end:]
            )

        return {
            "redacted_text": redacted_text,
            "entities": entities,
            "model": self.model_name,
        }