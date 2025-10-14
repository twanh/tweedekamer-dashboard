from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, list
from __future__ import annotations

# --- Base Classes ---

@dataclass
class Actor:
    """
    Base class for any entity that performs an action (Persoon or Fractie).
    Corresponds to the :Actor class in the ontology.
    """
    uuid: str
    naam: str
    nummer: str
    # Object properties from the ontology:
    # :heeftGestemdOp is handled via the Stemming class's 'uitgebracht_door' field.
    # We omit it here to simplify the base class.


@dataclass
class Onderwerp:
    """
    Represents a specific topic or subject area.
    Corresponds to the :Onderwerp class, which has many specific subclasses.
    """
    # The 'onderwerpType' is the only core data property defined on this class.
    onderwerp_type: Optional[str] = field(default=None)


@dataclass
class Stemming:
    """
    Represents a vote or voting result (StemVoor, StemTegen, etc.).
    Corresponds to the :Stemming class.
    """
    stemming_soort: Optional[str] = field(default=None)
    fractie_groote_op_moment_van_stemming: Optional[int] = field(default=None)

    # Object properties (Relationships):
    zaak: Optional[Zaak] = field(default=None)
    uitgebracht_door: Optional[Actor] = field(default=None)


@dataclass
class Zaak:
    """
    Represents a matter, item, or proposal (Wetsvoorstel, Motie, etc.).
    Corresponds to the :Zaak class.
    """
    uuid: str
    nummer: str
    titel: Optional[str] = field(default=None)
    beschrijving: Optional[str] = field(default=None)  # Maps to "Ondwerp" in OData
    dossier_nummer: Optional[str] = field(default=None)
    volgnummer: Optional[str] = field(default=None)
    zaak_soort: Optional[str] = field(default=None) # Defined implicitly by subclasses
    indienings_datum: Optional[datetime] = field(default=None)  # Called "GestartOp" in OData
    termijn: Optional[datetime] = field(default=None)
    is_afgedaan: Optional[bool] = field(default=None)
    kabinets_appreciatie: Optional[str] = field(default=None)
    besluit_resultaat: Optional[str] = field(default=None)
    besluit_stemming_soort: Optional[str] = field(default=None)

    # Object properties (Relationships):
    onderwerpen: list[Onderwerp] = field(default_factory=list)
    stemmingen: list[Stemming] = field(default_factory=list)


# --- Subclasses of Actor ---

@dataclass
class Fractie(Actor):
    """
    Represents a political faction/party.
    Corresponds to the :Fractie class, subclass of :Actor.
    """
    aantal_stemmen: Optional[int] = field(default=None)
    aantal_zetels: Optional[int] = field(default=None)
    afkorting: Optional[str] = field(default=None)
    datum_actief: Optional[datetime] = field(default=None)
    datum_inactief: Optional[datetime] = field(default=None)

    # Object properties (Relationship: :heeftLid)
    leden: list[Persoon] = field(default_factory=list)


@dataclass
class Persoon(Actor):
    """
    Represents an individual person, typically an MP.
    Corresponds to the :Persoon class, subclass of :Actor.
    """
    geboortedatum: Optional[datetime] = field(default=None)
    geboorteland: Optional[str] = field(default=None)
    geboorteplaats: Optional[str] = field(default=None)
    geslacht: Optional[str] = field(default=None)
    woonplaats: Optional[str] = field(default=None)

    # Object properties (Relationship: :isLidVan)
    fractie: Optional[Fractie] = field(default=None)


# --- Subclasses of Zaak (Matter Types) ---
# These mainly inherit properties from Zaak but define a specific zaak_soort.

@dataclass
class Amendement(Zaak):
    """Corresponds to :Amendement, where zaakSoort="Amendement"."""
    pass

@dataclass
class Motie(Zaak):
    """Corresponds to :Motie, where zaakSoort="Motie"."""
    pass

@dataclass
class Wetsvoorstel(Zaak):
    """Corresponds to :Wetsvoorstel, where zaakSoort="Wetsvoorstel"."""
    pass

@dataclass
class IntiatiefWetgeving(Zaak):
    """Corresponds to :InitiatiefWetgeving, where zaakSoort="Initiatief Wetgeving"."""
    pass


# --- Subclasses of Stemming (Vote Types) ---
# These inherit properties from Stemming but define a specific stemmingSoort.

@dataclass
class StemVoor(Stemming):
    """Corresponds to :StemVoor, where stemmingSoort="Voor"."""
    pass

@dataclass
class StemTegen(Stemming):
    """Corresponds to :StemTegen, where stemmingSoort="Tegen"."""
    pass

@dataclass
class StemNietDeelgenomen(Stemming):
    """Corresponds to :StemNietDeelgenomen, where stemmingSoort="Niet deelgenomen"."""
    pass


# --- Specific Onderwerp Subclasses (Included for completeness/hierarchy) ---
# These can inherit from the base Onderwerp class if needed, but for most purposes,
# the base Onderwerp class with the 'onderwerp_type' field is sufficient.

@dataclass
class BinnenlandseZakenKoninkrijksrelaties(Onderwerp):
    pass

@dataclass
class BuitenlandseZakenEnDefensie(Onderwerp):
    pass

@dataclass
class EconomieEnFinancien(Onderwerp):
    pass

@dataclass
class InfrastructuurEnWaterstaat(Onderwerp):
    pass

@dataclass
class JustitieEnVeiligheid(Onderwerp):
    pass

@dataclass
class KlimaatEnEnergie(Onderwerp):
    pass

@dataclass
class LandbouwEnNatuur(Onderwerp):
    pass

@dataclass
class OnderwijsCultuurEnWetenschap(Onderwerp):
    pass

@dataclass
class SocialeZakenEnWerkgelegenheid(Onderwerp):
    pass

@dataclass
class VolksgezondheidEnZorg(Onderwerp):
    pass

# Example usage (uncomment to test):
# if __name__ == '__main__':
#     # 1. Create a Zaak (matter)
#     zaak = Motie(
#         uuid="uuid-12345",
#         nummer="35925-10",
#         titel="Motie over het verbeteren van de ICT-veiligheid",
#         zaak_soort="Motie",
#         indienings_datum=datetime(2025, 10, 14),
#         is_afgedaan=False,
#     )
#
#     # 2. Create a Fractie (faction)
#     fractie_pvd = Fractie(
#         uuid="f-001",
#         naam="Partij van de Vrijheid",
#         nummer="1",
#         afkorting="PvdV",
#         aantal_zetels=15
#     )
#
#     # 3. Create a Persoon (person)
#     persoon_jansen = Persoon(
#         uuid="p-001",
#         naam="M. Jansen",
#         nummer="999",
#         geslacht="M",
#         fractie=fractie_pvd,
#     )
#
#     # 4. Link the Persoon to the Fractie
#     fractie_pvd.leden.append(persoon_jansen)
#
#     # 5. Create a Stemming (vote)
#     stemming = StemVoor(
#         stemming_soort="Voor",
#         zaak=zaak,
#         uitgebracht_door=persoon_jansen,
#     )
#
#     # 6. Link the Stemming to the Zaak
#     zaak.stemmingen.append(stemming)
#
#     print(f"Zaak Titel: {zaak.titel}")
#     print(f"Stemming door: {stemming.uitgebracht_door.naam}")
#     print(f"Lid van fractie: {persoon_jansen.fractie.afkorting}")
