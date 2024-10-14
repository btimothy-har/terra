from enum import Enum


class ClaimTypes(Enum):
    FACT = "fact"
    OPINION = "opinion"
    PREDICTION = "prediction"
    HYPOTHESIS = "hypothesis"
    DENIAL = "denial"
    CONFIRMATION = "confirmation"
    ACCUSATION = "accusation"
    PROMISE = "promise"
    WARNING = "warning"
    ANNOUNCEMENT = "announcement"
    OTHER = "other"


class EntityTypes(Enum):
    PERSON = "person"
    ORGANIZATION = "organization"
    INDUSTRY = "industry"
    LOCATION = "location"
    LANGUAGE = "language"
    CURRENCY = "currency"
    GEOPOLITICAL_ENTITY = "geopolitical_entity"
    NORP = "nationality_or_religious_or_political_group"
    POSITION = "position"
    LEGAL = "legal_documents_or_laws_or_treaties"
    ART = "work_of_art"
    PRODUCT_OR_SERVICE = "product_or_service"
    EVENT = "event"
    INFRASTRUCTURE = "infrastructure"
    OTHER = "other"
