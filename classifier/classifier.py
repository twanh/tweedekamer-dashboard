import os
import openai

api_key = "sk-proj-Ztupx3FnepVb4ttjvDgN1p89HxDmRVoQ2yTIAN3BlbkFJ4MbFL_zLsIyjpyBp7jOd7Twangtrxp09sdYx6MzKv6TraP3R1nNnXBeQ7wA"


# Maak de client aan (zorg dat OPENAI_API_KEY in je omgeving is ingesteld)
client = openai.OpenAI(api_key=api_key)

# Mapping van numerieke output naar categorieën
CATEGORY_MAP = {
    1: "BinnenlandseZakenKoninkrijksrelaties",
    2: "BuitenlandseZakenEnDefensie",
    3: "EconomieEnFinancien",
    4: "InfrastructuurEnWaterstaat",
    5: "JustitieEnVeiligheid",
    6: "KlimaatEnEnergie",
    7: "LandbouwEnNatuur",
    8: "OnderwijsCultuurEnWetenschap",
    9: "SocialeZakenEnWerkgelegenheid",
    10: "VolksgezondheidEnZorg"
}


def classify_text(text, model="gpt-4.1-mini"):
    """
    Classificeert één tekst in één van de 10 beleidscategorieën.
    Retourneert de naam van de categorie.
    """
    prompt = (
        "Je bent een tekstclassificatiemodel. "
        "Classificeer de onderstaande tekst in één van de volgende categorieën "
        "en geef alleen het bijbehorende getal (1-10) terug:\n\n"
        "1. BinnenlandseZakenKoninkrijksrelaties\n"
        "2. BuitenlandseZakenEnDefensie\n"
        "3. EconomieEnFinancien\n"
        "4. InfrastructuurEnWaterstaat\n"
        "5. JustitieEnVeiligheid\n"
        "6. KlimaatEnEnergie\n"
        "7. LandbouwEnNatuur\n"
        "8. OnderwijsCultuurEnWetenschap\n"
        "9. SocialeZakenEnWerkgelegenheid\n"
        "10. VolksgezondheidEnZorg\n\n"
        "Geef alleen het getal als antwoord, zonder uitleg of extra tekst.\n\n"
        "Tekst:\n" + text
    )

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt}
                ]
            }
        ],
        max_output_tokens=16,
        temperature=0
    )

    output = response.output_text.strip()

    try:
        category_num = int(output)
        return CATEGORY_MAP.get(category_num, "Onbekend")
    except ValueError:
        return "Onbekend"


def classify_list(texts, model="gpt-4.1-mini"):
    """
    Classificeert een lijst van teksten.
    Retourneert een lijst met categorienamen.
    """
    results = []
    for text in texts:
        category = classify_text(text, model=model)
        results.append(category)
    return results


onderwerpen = [
    "Het kabinet kondigde nieuwe maatregelen aan om de uitstoot van CO2 te verminderen.",
    "De politie heeft extra budget gekregen voor bestrijding van cybercriminaliteit.",
    "Het ministerie investeert in nieuwe spoorlijnen tussen grote steden."
]

resultaten = classify_list(onderwerpen)

for tekst, categorie in zip(onderwerpen, resultaten):
    print(f"→ '{tekst}' → {categorie}")