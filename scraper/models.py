import enum
import uuid
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Optional

from rdflib import Graph
from rdflib import Literal
from rdflib import Namespace
from rdflib import RDF
from rdflib import URIRef
from rdflib import XSD


class ZaakSoort(enum.Enum):
    MOTIE = 'Motie'
    WETSVOORSTEL = 'Wetsvoorstel'
    AMENDEMENT = 'Amendement'
    INITIATIEF_WETGEVING = 'Initiatief Wetgeving'


class StemmingKeuze(enum.Enum):
    VOOR = 'Voor'
    TEGEN = 'Tegen'
    NIET_DEELGENOMEN = 'Niet Deelgenomen'


class OnderwerpType(enum.Enum):
    BinnenlandseZakenKoninkrijksrelaties = 'Binnenlandse Zaken en Koninkrijksrelaties'  # noqa: E501
    BuitenlandseZakenEnDefensie = 'Buitenlandse Zaken en Defensie'
    EconomieEnFinancien = 'Economie en Financien'
    InfrastructuurEnWaterstaat = 'Infrastructuur en Waterstaat'
    JustitieEnVeiligheid = 'Justitie en Veiligheid'
    KlimaatEnEnergie = 'Klimaat en Energie'
    LandbouwEnNatuur = 'Landbouw en Natuur'
    OnderwijsCultuurEnWetenschap = 'Onderwijs Cultuur en Wetenschap'
    SocialeZakenEnWerkgelegenheid = 'Sociale Zaken en Werkgelegenheid'
    VolksgezondheidEnZorg = 'Volksgezondheid en Zorg'

    def __str__(self):
        return self.value


TK = Namespace('http://www.semanticweb.org/twanh/ontologies/2025/9/tk/')


@dataclass
class RdfModel:
    """
    A base dataclass which the other models will inherit
    to provde common URI generation.
    """

    # Generate a new UUID for each instance if not provided
    # Note: most TK models have their own ID's so this may not be used
    uuid: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_uri(self) -> URIRef:
        """
        Generate a URI for the instance based on its class name and UUID.
        """
        # TODO: Test that the __name__ is correct here, otherwise:
        # pass class_name as parameter to get_uri
        return TK[f'{self.__class__.__name__.lower()}/{self.uuid}']

    def to_rdf(self, g: Graph) -> None:
        """
        Convert the instance to RDF and add it to the provided graph.

        Note that `g` is passed by reference, so modifications to `g` will
        be reflected outside this method.
        """
        raise NotImplementedError('Should be implemented by subclass')


@dataclass
class Actor(RdfModel):
    """:Actor"""

    naam: Optional[str] = None
    # TODO: This is defined in the ontology,
    # but what does it reference to in the API?
    nummer: Optional[str] = None

    # TODO: Add heeftGestemdOp?

    def to_rdf(self, g: Graph) -> None:

        actor_uri = self.get_uri()
        g.add((actor_uri, RDF.type, TK.Actor))
        if self.naam:
            g.add(
                (
                    actor_uri,
                    TK.naam,
                    Literal(self.naam, datatype=XSD.string),
                ),
            )
        if self.nummer:
            g.add((
                actor_uri, TK.nummer, Literal(
                    self.nummer, datatype=XSD.string,
                ),
            ))


@dataclass
class Persoon(Actor):
    """:Persoon"""

    geboortedatum: Optional[datetime] = None
    geboorteplaats: Optional[str] = None
    geboorteland: Optional[str] = None
    geslacht: Optional[str] = None
    woonplaats: Optional[str] = None

    is_lid_van: Optional['Fractie'] = None  # :isLidVan (Range is Fractie)

    def to_rdf(self, g: Graph) -> None:
        persoon_uri = self.get_uri()
        g.add((persoon_uri, RDF.type, TK.Persoon))
        # Add properties from Actor
        super().to_rdf(g)

        if self.geboortedatum:
            g.add((
                persoon_uri, TK.geboortedatum, Literal(
                    self.geboortedatum.date(), datatype=XSD.date,
                ),
            ))
        if self.geboorteplaats:
            g.add((
                persoon_uri, TK.geboorteplaats, Literal(
                    self.geboorteplaats, datatype=XSD.string,
                ),
            ))
        if self.geboorteland:
            g.add((
                persoon_uri, TK.geboorteland, Literal(
                    self.geboorteland, datatype=XSD.string,
                ),
            ))
        if self.geslacht:
            g.add((
                persoon_uri, TK.geslacht, Literal(
                    self.geslacht, datatype=XSD.string,
                ),
            ))
        if self.woonplaats:
            g.add((
                persoon_uri, TK.woonplaats, Literal(
                    self.woonplaats, datatype=XSD.string,
                ),
            ))
        if self.is_lid_van:
            fractie_uri = self.is_lid_van.get_uri()
            g.add((persoon_uri, TK.isLidVan, fractie_uri))
            # Also add the inverse relationship
            g.add((fractie_uri, TK.heeftLid, persoon_uri))


@dataclass
class Fractie(Actor):
    """:Fractie"""

    afkorting: Optional[str] = None
    aantal_zetels: Optional[int] = None
    datum_actief: Optional[datetime] = None
    datum_inactief: Optional[datetime] = None

    # :heeftLid (Inverse of :isLidVan)
    # :heeftLid does not map to a single Persoon, but to multiple
    # so we use a list in the to_rdf method this is covnerted to
    # the proper relation.
    leden: list['Persoon'] = field(default_factory=list)

    def to_rdf(self, g: Graph) -> None:
        fractie_uri = self.get_uri()
        g.add((fractie_uri, RDF.type, TK.Fractie))

        # Add properties from Actor
        super().to_rdf(g)

        if self.afkorting:
            g.add((
                fractie_uri, TK.afkorting, Literal(
                    self.afkorting, datatype=XSD.string,
                ),
            ))
        # Explicitly check for None to allow 0 zetels
        if self.aantal_zetels is not None:
            g.add((
                fractie_uri, TK.aantalZetels, Literal(
                    self.aantal_zetels, datatype=XSD.integer,
                ),
            ))
        if self.datum_actief:
            g.add((
                fractie_uri, TK.datumActief, Literal(
                    self.datum_actief.date(), datatype=XSD.date,
                ),
            ))
        if self.datum_inactief:
            g.add((
                fractie_uri, TK.datumInactief, Literal(
                    self.datum_inactief.date(), datatype=XSD.date,
                ),
            ))

        # Add for each lid the relationship :heeftLid
        for lid in self.leden:
            lid_uri = lid.get_uri()
            g.add((fractie_uri, TK.heeftLid, lid_uri))
            # Also add the inverse relationship
            g.add((lid_uri, TK.isLidVan, fractie_uri))
            lid.to_rdf(g)


@dataclass
class Zaak(RdfModel):
    """:Zaak, also maps its subclasses"""

    titel: Optional[str] = None
    # TODO: Check that all these numbers are needed
    # and add propper documentation on what they represent
    nummer: Optional[str] = None
    dossier_nummer: Optional[str] = None
    volgnummer: Optional[str] = None
    beschrijving: Optional[str] = None
    indienings_datum: Optional[datetime] = None
    termijn: Optional[datetime] = None
    is_afgedaan: Optional[bool] = None
    kabinetsappreciatie: Optional[str] = None

    besluit_resultaat: Optional[str] = None
    besluit_stemming_soort: Optional[str] = None  # TODO: Enum?

    zaak_soort: Optional[ZaakSoort] = None

    # Object properties
    onderwerp: Optional['Onderwerp'] = None
    stemmingen: list['Stemming'] = field(default_factory=list)

    def to_rdf(self, g: Graph):

        zaak_uri = self.get_uri()
        g.add((zaak_uri, RDF.type, TK.Zaak))

        if self.zaak_soort:
            subclass_name = self.zaak_soort.name.replace('_', '')
            if hasattr(TK, subclass_name):
                g.add((zaak_uri, RDF.type, getattr(TK, subclass_name)))

            # Use the enum's value for the data property literal
            g.add(
                (
                    zaak_uri,
                    TK.zaakSoort,
                    Literal(
                        self.zaak_soort.value,
                        datatype=XSD.string,
                    ),
                ),
            )

        if self.titel:
            g.add(
                (zaak_uri, TK.titel, Literal(self.titel, datatype=XSD.string)),
            )
        if self.nummer:
            g.add(
                (
                    zaak_uri,
                    TK.nummer,
                    Literal(self.nummer, datatype=XSD.string),
                ),
            )
        if self.dossier_nummer:
            g.add((
                zaak_uri, TK.dossierNummer, Literal(
                    self.dossier_nummer, datatype=XSD.string,
                ),
            ))
        if self.volgnummer:
            g.add((
                zaak_uri, TK.volgnummer, Literal(
                    self.volgnummer, datatype=XSD.string,
                ),
            ))
        if self.beschrijving:
            g.add((
                zaak_uri, TK.beschrijving, Literal(
                    self.beschrijving, datatype=XSD.string,
                ),
            ))
        if self.indienings_datum:
            g.add((
                zaak_uri, TK.indieningsDatum, Literal(
                    self.indienings_datum.date(), datatype=XSD.date,
                ),
            ))
        if self.termijn:
            g.add((
                zaak_uri, TK.termijn, Literal(
                    self.termijn.date(), datatype=XSD.date,
                ),
            ))
        if self.is_afgedaan is not None:
            g.add((
                zaak_uri, TK.isAfgedaan, Literal(
                    self.is_afgedaan, datatype=XSD.boolean,
                ),
            ))
        if self.kabinetsappreciatie:
            g.add((
                zaak_uri, TK.kabinetsappreciatie, Literal(
                    self.kabinetsappreciatie, datatype=XSD.string,
                ),
            ))
        if self.besluit_resultaat:
            g.add((
                zaak_uri, TK.besluitResultaat, Literal(
                    self.besluit_resultaat, datatype=XSD.string,
                ),
            ))
        if self.besluit_stemming_soort:
            g.add((
                zaak_uri, TK.besluitStemmingSoort, Literal(
                    self.besluit_stemming_soort, datatype=XSD.string,
                ),
            ))

        if self.onderwerp:
            onderwerp_uri = self.onderwerp.get_uri()
            g.add((zaak_uri, TK.heeftOnderwerp, onderwerp_uri))
            # Also add the inverse relationship
            g.add((onderwerp_uri, TK.heeftZaak, zaak_uri))
            # Add the Onderwerp itself to the graph
            self.onderwerp.to_rdf(g)

        for stemming in self.stemmingen:
            stemming_uri = stemming.get_uri()
            g.add((zaak_uri, TK.heeftStemming, stemming_uri))
            # Also add the inverse relationship
            g.add((stemming_uri, TK.isStemmingOver, zaak_uri))
            # Add the Stemming itself to the graph
            stemming.to_rdf(g)


@dataclass
class Stemming(RdfModel):

    soort: Optional[str] = None  # Maps to :stemmingSoort
    fractie_grootte_op_moment_van_stemming: Optional[int] = None

    # Should this be optional?
    is_stemming_over: Optional['Zaak'] = None

    # This field will hold the raw scraped voting data.
    resultaten: list[
        tuple['Actor', 'StemmingKeuze']
    ] = field(default_factory=list)

    def to_rdf(self, g: Graph):
        """Adds RDF triples for this stemming instance to the graph."""

        stemming_uri = self.get_uri()
        if not self.is_stemming_over:
            raise ValueError(
                'Stemming must be associated with a Zaak via is_stemming_over.',  # noqa: E501
            )

        zaak_uri = self.is_stemming_over.get_uri()

        g.add((stemming_uri, RDF.type, TK.Stemming))
        # Add inverse link from Zaak to Stemming
        g.add((zaak_uri, TK.heeftStemming, stemming_uri))
        g.add((stemming_uri, TK.isStemmingOver, zaak_uri))

        if self.soort:
            g.add((
                stemming_uri, TK.stemmingSoort, Literal(
                    self.soort, datatype=XSD.string,
                ),
            ))

        if self.fractie_grootte_op_moment_van_stemming is not None:
            g.add((
                stemming_uri,
                TK.fractieGrooteOpMomentVanStemming,
                Literal(
                    self.fractie_grootte_op_moment_van_stemming,
                    datatype=XSD.integer,
                ),
            ))

        # Process the individual vote results
        # The ontology links the Actor directly to the Zaak with a
        # specific property (e.g., :heeftVoorGestemd),
        # so we create those triples here.
        for actor, keuze in self.resultaten:
            actor_uri = actor.get_uri()
            vote_property = None

            if keuze == StemmingKeuze.VOOR:
                vote_property = TK.heeftVoorGestemd
            elif keuze == StemmingKeuze.TEGEN:
                vote_property = TK.heeftTegenGestemd
            elif keuze == StemmingKeuze.NIET_DEELGENOMEN:
                vote_property = TK.heeftNietDeelgenomen

            if vote_property:
                # Link the Actor directly to the Zaak with the vote type
                g.add((actor_uri, vote_property, zaak_uri))

            # Ensure the Actor's own data is also added to the graph
            actor.to_rdf(g)


@dataclass
class Onderwerp(RdfModel):
    """:Onderwerp"""

    onderwerp_type: Optional[OnderwerpType] = None
    zaken: list['Zaak'] = field(default_factory=list)

    def to_rdf(self, g: Graph):
        onderwerp_uri = self.get_uri()

        g.add((onderwerp_uri, RDF.type, TK.Onderwerp))
        if self.onderwerp_type:
            g.add(
                (
                    onderwerp_uri,
                    RDF.type,
                    getattr(TK, self.onderwerp_type.name),
                ),
            )
            g.add((
                onderwerp_uri, TK.onderwerpType, Literal(
                    self.onderwerp_type.value, datatype=XSD.string,
                ),
            ))

        for zaak in self.zaken:
            zaak_uri = zaak.get_uri()
            g.add((onderwerp_uri, TK.heeftZaak, zaak_uri))
            # Also add the inverse property from Zaak to Onderwerp
            g.add((zaak_uri, TK.heeftOnderwerp, onderwerp_uri))
            # Ensure the linked zaak's data is also added to the graph
            zaak.to_rdf(g)
