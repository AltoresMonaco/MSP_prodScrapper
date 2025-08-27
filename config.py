# config.py

# Dictionnaire définissant les catégories et leurs patterns associés.
PRIMARY_PATTERNS = {
    "Transport et Mobilité": [
        "https://monservicepublic.gouv.mc/thematiques/transports-et-mobilite",
        "https://monservicepublic.gouv.mc/en/themes/transport-and-mobility"
    ],

    "Nationalité et residence": [
        "https://monservicepublic.gouv.mc/thematiques/nationalite-et-residence",
        "https://monservicepublic.gouv.mc/en/themes/nationality-and-residency"
    ],

    "Logement": [
        "https://monservicepublic.gouv.mc/thematiques/logement",
        "https://monservicepublic.gouv.mc/en/themes/housing"
    ],

    "Emploie": [
        "https://monservicepublic.gouv.mc/thematiques/emploi",
        "https://monservicepublic.gouv.mc/en/themes/employment"
    ],

    "Securite et prevention": [
        "https://monservicepublic.gouv.mc/thematiques/securite-et-prevention",
        "https://monservicepublic.gouv.mc/en/themes/security-and-prevention"
    ],

    "Justice": [
        "https://monservicepublic.gouv.mc/thematiques/justice",
        "https://monservicepublic.gouv.mc/en/themes/justice"
    ],

    "Social-sante-et-famille": [
        "https://monservicepublic.gouv.mc/thematiques/social-sante-et-famille",
        "https://monservicepublic.gouv.mc/en/themes/social-health-and-families"
    ],

    "Education": [
        "https://monservicepublic.gouv.mc/thematiques/education",
        "https://monservicepublic.gouv.mc/en/themes/education"
    ],

    "Fiscalite": [
        "https://monservicepublic.gouv.mc/thematiques/fiscalite",
        "https://monservicepublic.gouv.mc/en/themes/tax"
  
    ],

    "Temps libre": [
         "https://monservicepublic.gouv.mc/thematiques/temps-libre",
         "https://monservicepublic.gouv.mc/en/themes/free-time"
    ],

    "Relations avec l'administration": [
       "https://monservicepublic.gouv.mc/thematiques/relations-avec-l-administration",
       "https://monservicepublic.gouv.mc/en/themes/you-and-the-government-services"
    ],

    "Associations et fondations": [
        "https://monservicepublic.gouv.mc/thematiques/associations-et-fondations",
        "https://monservicepublic.gouv.mc/en/themes/associations-and-foundations"
    ],

    "EdV je m installe a monaco": [
        "https://monservicepublic.gouv.mc/evenements-de-vie/je-m-installe-a-monaco",
        "https://monservicepublic.gouv.mc/en/events-in-your-life/settling-in-monaco"
    ],

    "EdV je demenage": [
        "https://monservicepublic.gouv.mc/evenements-de-vie/je-demenage",
        "https://monservicepublic.gouv.mc/en/events-in-your-life/moving-house"
    ],

    "EdV j attends un enfant": [
        "https://monservicepublic.gouv.mc/evenements-de-vie/j-attends-un-enfant",
        "https://monservicepublic.gouv.mc/en/events-in-your-life/expecting-a-baby"
    ],

    "EdV je deviens ecoresponsable": [
        "https://monservicepublic.gouv.mc/evenements-de-vie/je-deviens-ecoresponsable",
        "https://monservicepublic.gouv.mc/en/events-in-your-life/becoming-environmentally-responsible"
    ]

}

# 2. Liste d'URLs « fixes » qui ne doivent pas être traitées comme des patterns primaires.
#    Elles ne sont pas exclues du scraping, mais seront rangées en "general" si rencontrées.
FIXED_URLS = [
    {"url": "https://monservicepublic.gouv.mc/thematiques/transports-et-mobilite", "thematique": "Transport et Mobilité"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/transport-and-mobility", "thematique": "Transport et Mobilité"},

    {"url": "https://monservicepublic.gouv.mc/thematiques", "thematique": "Toutes les Thematique"},
    {"url": "https://monservicepublic.gouv.mc/en/themes", "thematique": "Toutes les Thematique"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/nationalite-et-residence", "thematique": "Nationalité et residence"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/nationality-and-residency", "thematique": "Nationalité et residence"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/logement", "thematique": "Logement"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/housing", "thematique": "Logement"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/emploi", "thematique": "Emploie"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/employment", "thematique": "Emploie"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/securite-et-prevention", "thematique": "Securite et prevention"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/security-and-prevention", "thematique": "Securite et prevention"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/justice", "thematique": "Justice"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/justice", "thematique": "Justice"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/social-sante-et-famille", "thematique": "Social-sante-et-famille"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/social-health-and-families", "thematique": "Social-sante-et-famille"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/education", "thematique": "Education"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/education", "thematique": "Education"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/fiscalite", "thematique": "Fiscalite"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/tax", "thematique": "Fiscalite"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/temps-libre", "thematique": "Temps libre"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/free-time", "thematique": "Temps libre"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/relations-avec-l-administration", "thematique": "Relations avec l'administration"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/you-and-the-government-services", "thematique": "Relations avec l'administration"},

    {"url": "https://monservicepublic.gouv.mc/thematiques/associations-et-fondations", "thematique": "Associations et fondations"},
    {"url": "https://monservicepublic.gouv.mc/en/themes/associations-and-foundations", "thematique": "Associations et fondations"},

    {"url": "https://monservicepublic.gouv.mc/evenements-de-vie", "thematique": "All Evenement de vie"},
    {"url": "https://monservicepublic.gouv.mc/en/events-in-your-life", "thematique": "All Evenement de vie"},

    {"url": "https://monservicepublic.gouv.mc/evenements-de-vie/je-m-installe-a-monaco", "thematique": "EdV je m installe a monaco"},
    {"url": "https://monservicepublic.gouv.mc/en/events-in-your-life/settling-in-monaco", "thematique": "EdV je m installe a monaco"},

    {"url": "https://monservicepublic.gouv.mc/evenements-de-vie/je-demenage", "thematique": "EdV je demenage"},
    {"url": "https://monservicepublic.gouv.mc/en/events-in-your-life/moving-house", "thematique": "EdV je demenage"},

    {"url": "https://monservicepublic.gouv.mc/evenements-de-vie/j-attends-un-enfant", "thematique": "EdV j attends un enfant"},
    {"url": "https://monservicepublic.gouv.mc/en/events-in-your-life/expecting-a-baby", "thematique": "EdV j attends un enfant"},

    {"url": "https://monservicepublic.gouv.mc/evenements-de-vie/je-deviens-ecoresponsable", "thematique": "EdV je deviens ecoresponsable"},
    {"url": "https://monservicepublic.gouv.mc/en/events-in-your-life/becoming-environmentally-responsible", "thematique": "EdV je deviens ecoresponsable"},

    {"url": "https://monservicepublic.gouv.mc/annuaire-des-services-administratifs", "thematique": "Annuaire administratif & site lie"},
    {"url": "https://monservicepublic.gouv.mc/sites-lies", "thematique": "Annuaire administratif & site lie"},

    {"url": "https://monservicepublic.gouv.mc/actualites?query=&limit=60&sort_by=date_desc", "thematique": "Actualités & Agenda"},
    {"url": "https://monservicepublic.gouv.mc/agenda?query=&limit=60&sort_by=date_asc", "thematique": "Actualités & Agenda"},

    {"url": "https://monservicepublic.gouv.mc/", "thematique": "Accueil & A propos"},
    {"url": "https://monservicepublic.gouv.mc/a-propos", "thematique": "Accueil & A propos"},
    {"url": "https://monservicepublic.gouv.mc/en", "thematique": "Accueil & A propos"},
    {"url": "https://monservicepublic.gouv.mc/en/about", "thematique": "Accueil & A propos"},

    {"url": "https://monservicepublic.gouv.mc/dernieres-mises-a-jour", "thematique": "Derniere mises à jour"},
    {"url": "https://monservicepublic.gouv.mc/en/latest-updates", "thematique": "Derniere mises à jour"}
]

ANNUAIRE_URL_PATTERNS = [
    "annuaire-des-services-administratifs",
    "directory-of-government-services"
]
ANNUAIRE_NAMESPACE = "child"


# Domaine de base (pour la conversion des URLs relatives).
BASE_DOMAIN = "https://monservicepublic.gouv.mc"

# Namespace utilisé pour les URLs fixes.
PARENT_NAMESPACE = "general"
