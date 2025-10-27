import os

import dotenv
import openai
from models import OnderwerpType

dotenv.load_dotenv()

api_key = os.getenv('OPENAI_API_KEY')

client = openai.OpenAI(api_key=api_key)

CATEGORY_MAP = {
    1: OnderwerpType.BinnenlandseZakenKoninkrijksrelaties,
    2: OnderwerpType.BuitenlandseZakenEnDefensie,
    3: OnderwerpType.EconomieEnFinancien,
    4: OnderwerpType.InfrastructuurEnWaterstaat,
    5: OnderwerpType.JustitieEnVeiligheid,
    6: OnderwerpType.KlimaatEnEnergie,
    7: OnderwerpType.LandbouwEnNatuur,
    8: OnderwerpType.OnderwijsCultuurEnWetenschap,
    9: OnderwerpType.SocialeZakenEnWerkgelegenheid,
    10: OnderwerpType.VolksgezondheidEnZorg,
}


def classify_text(text, model='gpt-4o-mini-2024-07-18'):
    prompt = (
        'Je bent een tekstclassificatiemodel. '
        'Classificeer de onderstaande tekst in één van de volgende categorieën '
        'en geef alleen het bijbehorende getal (1-10) terug:\n\n'
        '1. BinnenlandseZakenKoninkrijksrelaties\n'
        '2. BuitenlandseZakenEnDefensie\n'
        '3. EconomieEnFinancien\n'
        '4. InfrastructuurEnWaterstaat\n'
        '5. JustitieEnVeiligheid\n'
        '6. KlimaatEnEnergie\n'
        '7. LandbouwEnNatuur\n'
        '8. OnderwijsCultuurEnWetenschap\n'
        '9. SocialeZakenEnWerkgelegenheid\n'
        '10. VolksgezondheidEnZorg\n\n'
        'Geef alleen het getal als antwoord, zonder uitleg of extra tekst.\n\n'
        'Tekst:\n' + text
    )

    response = client.responses.create(
        model=model,
        input=[
            {
                'role': 'user',
                'content': [
                    {'type': 'input_text', 'text': prompt},
                ],
            },
        ],
        max_output_tokens=16,
        temperature=0,
    )

    output = response.output_text.strip()

    try:
        category_num = int(output)
        return CATEGORY_MAP.get(category_num, None)
    except ValueError:
        return None


def classify_list(texts, model='gpt-4o-mini-2024-07-18'):
    results = []
    for text in texts:
        category = classify_text(text, model=model)
        results.append(category)
    return results
