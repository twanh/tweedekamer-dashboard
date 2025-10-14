from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

# --- Forward Declarations for Inter-Class Relationships ---
# We use forward references (strings) for type hinting classes that are defined later.

@dataclass
class Actor:
    """
    De basis entiteit voor entiteiten die kunnen stemmen of initiëren,
    zoals een Persoon of een Fractie.
    Corresponds to the :Actor class.
    """
    naam: str = field()
    nummer: Optional[str] = field(default=None)
    uuid: Optional[str] = field(default=None)


@dataclass
class Onderwerp:
    """
    Een verzameling van thematische onderwerpen waaronder Zaken vallen.
    Corresponds to the :Onderwerp class.
    """
    # Datatype Properties
    onderwerp_type: Optional[str] = field(default=None) # :onderwerpType

    # Object Properties (Relationships)
    zaken: List['Zaak'] = field(default_factory=list) # Inverse of :heeftOnderwerp


@dataclass
class Zaak:
    """
    Een Kamerstuk of een ander proces, zoals een Motie of Wetsvoorstel.
    Corresponds to the :Zaak class.
    """
    # Datatype Properties
    titel: str = field()                                   # :titel
    zaak_soort: str = field()                              # :zaakSoort
    dossier_nummer: str = field()                          # :dossierNummer
    uuid: Optional[str] = field(default=None)              # :uuid
    nummer: Optional[str] = field(default=None)            # :nummer
    volgnummer: Optional[str] = field(default=None)        # :volgnummer
    beschrijving: Optional[str] = field(default=None)      # :beschrijving (OData "Onderwerp")
    indienings_datum: Optional[datetime] = field(default=None) # :indieningsDatum (OData "GestartOp")
    termijn: Optional[datetime] = field(default=None)      # :termijn (End date)
    besluit_resultaat: Optional[str] = field(default=None) # :besluitResultaat
    besluit_stemming_soort: Optional[str] = field(default=None) # :besluitStemmingSoort
    is_afgedaan: bool = field(default=False)               # :isAfgedaan
    kabinets_appreciatie: Optional[str] = field(default=None) # :kabinetsappreciatie

    # Object Properties (Relationships)
    onderwerpen: List[Onderwerp] = field(default_factory=list) # :heeftOnderwerp
    stemmingen: List['Stemming'] = field(default_factory=list) # :heeftStemming


@dataclass
class Stemming:
    """
    Een specifieke stemming over een Zaak.
    Corresponds to the :Stemming class.
    """
    # Datatype Properties
    stemming_soort: Optional[str] = field(default=None)              # :stemmingSoort
    fractie_groote_op_moment_van_stemming: Optional[int] = field(default=None) # :fractieGrooteOpMomentVanStemming

    # Object Properties (Relationships)
    is_stemming_over: Zaak = field()                  # :isStemmingOver
    uitgebracht_door: Actor = field()                # :isUitgebrachtDoor (Inverse of :heeftGestemdOp)

    # Note: The object properties like :heeftVoorGestemd, :heeftTegenGestemd, etc.
    # are subproperties of :heeftGestemdOp and describe the *result* of the
    # stemming event relative to the Zaak, but are defined on the Actor.
    # In a data model, this result is best captured by the overall collection
    # of Stemming objects linked to the Zaak.


# --- Subclasses of Actor ---

@dataclass
class Persoon(Actor):
    """
    Een individueel lid van de Tweede Kamer.
    Corresponds to the :Persoon class, subclass of :Actor.
    """
    # Datatype Properties
    geboortedatum: Optional[datetime] = field(default=None)   # :geboortedatum
    geboorteland: Optional[str] = field(default=None)        # :geboorteland
    geboorteplaats: Optional[str] = field(default=None)      # :geboorteplaats
    geslacht: Optional[str] = field(default=None)            # :geslacht
    woonplaats: Optional[str] = field(default=None)          # :woonplaats

    # Object Properties (Relationships)
    is_lid_van: Optional['Fractie'] = field(default=None)     # :isLidVan (Range is Fractie)


@dataclass
class Fractie(Actor):
    """
    Een politieke partij of fractie.
    Corresponds to the :Fractie class, subclass of :Actor.
    """
    # Datatype Properties
    afkorting: Optional[str] = field(default=None)      # :afkorting
    aantal_zetels: Optional[int] = field(default=None)  # :aantalZetels
    aantal_stemmen: Optional[int] = field(default=None) # :aantalStemmen
    datum_actief: Optional[datetime] = field(default=None) # :datumActief
    datum_inactief: Optional[datetime] = field(default=None) # :datumInactief

    # Object Properties (Relationships)
    leden: List[Persoon] = field(default_factory=list) # :heeftLid (Inverse of :isLidVan)


# --- Subclasses of Zaak ---

@dataclass
class Amendement(Zaak):
    """
    Een Amendement, een subclass van Zaak met vaste zaakSoort="Amendement".
    """
    zaak_soort: str = field(default="Amendement", init=False)


@dataclass
class Motie(Zaak):
    """
    Een Motie, een subclass van Zaak met vaste zaakSoort="Motie".
    """
    zaak_soort: str = field(default="Motie", init=False)


@dataclass
class Wetsvoorstel(Zaak):
    """
    Een Wetsvoorstel, een subclass van Zaak met vaste zaakSoort="Wetsvoorstel".
    """
    zaak_soort: str = field(default="Wetsvoorstel", init=False)


@dataclass
class InitiatiefWetgeving(Zaak):
    """
    Initiatief Wetgeving, een subclass van Zaak met vaste zaakSoort="Initiatief Wetgeving".
    """
    zaak_soort: str = field(default="Initiatief Wetgeving", init=False)


# --- Example Usage (Optional) ---

def main():
    # 1. Create a Fractie and a Persoon
    pvda_fractie = Fractie(
        naam="Partij van de Arbeid (PvdA)",
        afkorting="PvdA",
        aantal_zetels=9,
        nummer="25",
    )

    lid_diederik = Persoon(
        naam="Diederik Samsom",
        geboortedatum=datetime(1971, 7, 31),
        geslacht="M",
        is_lid_van=pvda_fractie,
        nummer="250",
    )
    pvda_fractie.leden.append(lid_diederik)

    # 2. Create an Onderwerp
    economie_onderwerp = Onderwerp(onderwerp_type="EconomieEnFinancien")

    # 3. Create a Zaak (Motie)
    motie_titel = "Motie over het verlagen van de belasting op arbeid"
    motie = Motie(
        titel=motie_titel,
        dossier_nummer="34550",
        indienings_datum=datetime(2025, 10, 10),
        is_afgedaan=False,
    )
    motie.onderwerpen.append(economie_onderwerp)

    # 4. Create a Stemming on the Zaak
    stemming_voor = Stemming(
        is_stemming_over=motie,
        uitgebracht_door=lid_diederik,
        stemming_soort="Voor",
        fractie_groote_op_moment_van_stemming=9,
    )
    motie.stemmingen.append(stemming_voor)

    print(f"Fractie: {pvda_fractie.naam} ({pvda_fractie.afkorting})")
    print(f"Lid: {lid_diederik.naam}, Lid van: {lid_diederik.is_lid_van.afkorting}")
    print(f"Zaak (Motie): {motie.titel}")
    print(f"Stemming 1: Door {stemming_voor.uitgebracht_door.naam} ({stemming_voor.stemming_soort})")


if __name__ == "__main__":
    main()
