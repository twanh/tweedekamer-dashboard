import datetime
import logging

from classifier import classify_text
from models import Fractie as FractieModel
from models import Onderwerp
from models import OnderwerpType
from models import Persoon as PersoonModel
from models import Stemming as StemmingModel
from models import StemmingKeuze
from models import Zaak as ZaakModel
from models import ZaakSoort as ZaakSoortEnum
from tkapi import TKApi
from tkapi.fractie import Fractie as TkFractie
from tkapi.fractie import FractieZetelPersoon as TkFractieZetelPersoon
from tkapi.zaak import Zaak


STEMMING_KEUZE_MAP = {
    'Voor': StemmingKeuze.VOOR,
    'Tegen': StemmingKeuze.TEGEN,
    'Niet deelgenomen': StemmingKeuze.NIET_DEELGENOMEN,
}


class TkScraper:

    def __init__(self, verbose: bool = True):

        self.api = TKApi(verbose=verbose)

        self.logger = logging.getLogger(f'scraper.{self.__class__.__name__}')

        self._zaken: dict[str, ZaakModel] = {}
        self._fracties: dict[str, FractieModel] = {}
        self._personen: dict[str, PersoonModel] = {}
        self._onderwerpen: dict[OnderwerpType, Onderwerp] = {}

    def get_all_fracties(
        self,
        populate_members: bool = False,
    ) -> list[FractieModel]:

        self.logger.info(f'Fetching all fracties with {populate_members=}')

        fracties_filter = TkFractie.create_filter()
        fracties_filter.filter_actief()
        fracties_data = self.api.get_fracties(filter=fracties_filter)

        self.logger.info(f'Fetched {len(fracties_data)} active fracties')

        # For every scraped fractie, create a FractieModel
        # and add it to self._fracties
        for fractie in fracties_data:
            self.logger.debug(
                f'Processing fractie: {fractie.naam} ({fractie.afkorting})',
            )

            fractie_model = FractieModel(
                uuid=fractie.id,
                naam=fractie.naam,
                # TODO: Check what this number is supposed to be
                nummer=fractie.id,
                afkorting=fractie.afkorting,
                aantal_zetels=fractie.zetels_aantal or 0,
                datum_actief=fractie.datum_actief,
                datum_inactief=fractie.datum_inactief,
            )

            # Optionally populate members
            if populate_members:
                self.logger.info(
                    f'Populating members for fractie {fractie.naam}',
                )

                # If leden_actief is not provided, fetch it
                leden_actief = fractie.leden_actief

                if not leden_actief:
                    filter = TkFractieZetelPersoon.create_filter()
                    filter.filter_fractie_id(uid=fractie.id)
                    filter.filter_actief()
                    leden_actief = self.api.get_items(
                        TkFractieZetelPersoon, filter=filter,
                    )

                self.logger.info(
                    f'Found {len(leden_actief)} '
                    f'active members in fractie {fractie.naam}',
                )
                # For each active member, create a PersoonModel
                # and add it to the fractie_model
                for lid in leden_actief:
                    persoon = PersoonModel(
                        uuid=lid.persoon.id,
                        nummer=lid.persoon.id,
                        naam=(
                            lid.persoon.voornamen
                            + ' '
                            + lid.persoon.achternaam
                        ),
                        geboortedatum=lid.persoon.geboortedatum,
                        geboorteplaats=lid.persoon.geboorteplaats,
                        geslacht=lid.persoon.geslacht,
                        is_lid_van=fractie_model,
                    )

                    fractie_model.leden.append(persoon)
                    # Add the persoon to self._personen
                    self._personen[persoon.uuid] = persoon

            # Add the fractie_model to self._fracties
            # TODO: Is using uuid the best?
            self._fracties[fractie_model.uuid] = fractie_model

        # ???: Is this return type the best? Or should we
        # just return the dict
        return list(self._fracties.values())

    def get_all_zaken(
        self,
        zaak_type: ZaakSoortEnum | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
    ) -> list[ZaakModel]:

        self.logger.info(
            f'Fetching all zaken with {zaak_type=}, '
            f'{start_date=}, {end_date=}',
        )

        zaken_filter = Zaak.create_filter()
        if start_date and end_date:
            zaken_filter.filter_date_range(
                start_datetime=start_date,
                end_datetime=end_date,
            )

        if zaak_type:
            # TODO: Make sure that the ZaakSoort enum matches the API values
            zaken_filter.filter_soort(zaak_type.value)

        zaken_data = self.api.get_zaken(filter=zaken_filter)

        self.logger.info(f'Fetched {len(zaken_data)} zaken')
        for zaak in zaken_data:
            self.logger.debug(
                'Processing zaak: '
                f'{zaak.nummer} - {zaak.onderwerp} ({zaak.soort})',
            )

            # Classify the zaak onderwerp
            onderwerp_classification = classify_text(zaak.onderwerp)

            if onderwerp_classification is None:
                self.logger.warning(
                    'Could not classify onderwerp for '
                    f'zaak {zaak.nummer}: {zaak.onderwerp}',
                )
                onderwerp_classification = OnderwerpType.Other

            # Create new onderwerp
            if self._onderwerpen.get(onderwerp_classification) is None:
                self.logger.info(
                    'Creating new Onderwerp for '
                    f'{onderwerp_classification}',
                )
                self._onderwerpen[onderwerp_classification] = Onderwerp(
                    onderwerp_type=onderwerp_classification,
                )

            # Create ZaakModel
            zaak_model = ZaakModel(
                uuid=zaak.id,
                nummer=zaak.nummer,
                dossier_nummer=zaak.dossier.nummer if zaak.dossier else None,
                volgnummer=zaak.volgnummer,
                beschrijving=zaak.onderwerp,
                indienings_datum=zaak.gestart_op,
                # FIXME: Get this info another way since API does not
                # give it but OData does have it in their docs
                termijn=None,
                is_afgedaan=zaak.afgedaan,
                # FIXME: Throws error
                # kabinetsappreciatie=
                zaak_soort=zaak_type,
                onderwerp=self._onderwerpen[onderwerp_classification],
            )

            # Add zaak_model to the correct Onderwerp
            self._onderwerpen[onderwerp_classification].zaken.append(
                zaak_model,
            )

            # TODO: Populate besluit and setmming data
            if zaak.besluiten:

                for besluit in zaak.besluiten:
                    zaak_model.besluit_resultaat = besluit.soort
                    zaak_model.besluit_stemming_soort = besluit.stemming_soort

                    stemming_model = StemmingModel(
                        uuid=besluit.id,
                        soort=besluit.stemming_soort,  # e.g., "Hoofdelijk"
                        is_stemming_over=zaak_model,
                        resultaten=[],
                    )

                    for stem in besluit.stemmingen:

                        # Get stemming keuze (voor, tegen, nd)
                        keuze = STEMMING_KEUZE_MAP.get(stem.soort)
                        if not keuze:
                            self.logger.warning(
                                'Unknown stemming keuze: '
                                f'{stem.soort} for stemming {stem.id}',
                            )
                            continue

                        # Create the actor who voted
                        actor_model = None
                        if stem.persoon_id is not None:
                            self.logger.info(
                                'Processing stem by persoon '
                                f'for zaak {zaak_model.nummer}',
                            )
                            # Check if persoon already exists
                            if stem.persoon_id in self._personen:
                                actor_model = self._personen[stem.persoon.id]
                            else:
                                # TODO: Extract this perhaps to a method
                                # that creates or gets a PersoonModel
                                # using the API (with ID)
                                # Note: same then for fracties above
                                actor_model = PersoonModel(
                                    uuid=stem.persoon.id,
                                    nummer=stem.persoon.id,
                                    naam=(
                                        stem.persoon.voornamen
                                        + ' '
                                        + stem.persoon.achternaam
                                    ),
                                    geboortedatum=stem.persoon.geboortedatum,
                                    geboorteplaats=stem.persoon.geboorteplaats,
                                    geslacht=stem.persoon.geslacht,
                                    # TODO: Perhaps fetch fractie?
                                    # is_lid_van=stem.persoon.fracties,
                                )
                                self._personen[actor_model.uuid] = actor_model
                        elif stem.fractie_id is not None:
                            self.logger.info(
                                'Processing stem by fractie '
                                f'for zaak {zaak_model.nummer}',
                            )
                            # Actor is a fractie
                            if stem.fractie_id in self._fracties:
                                actor_model = self._fracties[stem.fractie.id]
                            else:
                                actor_model = FractieModel(
                                    uuid=stem.fractie.id,
                                    naam=stem.fractie.naam,
                                    nummer=stem.fractie.id,
                                    afkorting=stem.fractie.afkorting,
                                    aantal_zetels=(
                                        stem.fractie.zetels_aantal or 0
                                    ),
                                    datum_actief=stem.fractie.datum_actief,
                                    datum_inactief=stem.fractie.datum_inactief,
                                    # TODO: Leden?
                                )
                                self._fracties[actor_model.uuid] = actor_model
                        else:
                            self.logger.warning(
                                f'Stemming {stem.id} '
                                'has no persoon or fractie associated',
                            )
                            continue

                        stemming_model.resultaten.append((actor_model, keuze))

                    zaak_model.stemmingen.append(stemming_model)

            self._zaken[zaak_model.uuid] = zaak_model

        return list(self._zaken.values())
