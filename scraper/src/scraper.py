import datetime
import logging

from models import Actor as ActorModel
from models import Fractie as FractieModel
from models import Onderwerp as OnderwerpModel
from models import OnderwerpType
from models import Persoon as PersoonModel
from models import Stemming as StemmingModel
from models import StemmingKeuze
from models import Zaak as ZaakModel
from models import ZaakSoort
from tkapi import TKApi
from tkapi.fractie import Fractie as TkFractie
from tkapi.fractie import FractieFilter
from tkapi.fractie import FractieZetelPersoon as TkFractieZetelPersoon
from tkapi.persoon import Persoon
from tkapi.stemming import Stemming
from tkapi.util import queries
from tkapi.zaak import Zaak
from tkapi.zaak import ZaakSoort


class TkScraper:

    def __init__(self, verbose: bool = True):

        self.api = TKApi(verbose=verbose)

        self.logger = logging.getLogger(f'scraper.{self.__class__.__name__}')

        # self._zaken: dict[str, ZaakModel] = {}
        self._fracties: dict[str, FractieModel] = {}
        self._personen: dict[str, PersoonModel] = {}

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
                nummer=fractie.id,  # TODO: Check what this number is supposed to be
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
                    f'Found {len(leden_actief)} active members in fractie {fractie.naam}',
                )
                # For each active member, create a PersoonModel
                # and add it to the fractie_model
                for lid in leden_actief:
                    persoon = PersoonModel(
                        uuid=lid.persoon.id,
                        nummer=lid.persoon.id,
                        naam=lid.persoon.voornamen + ' ' + lid.persoon.achternaam,
                        geboortedatum=lid.persoon.geboortedatum,
                        geboorteplaats=lid.persoon.geboorteplaats,
                        geslacht=lid.persoon.geslacht,
                        is_lid_van=fractie_model,
                    )

                    fractie_model.leden.append(persoon)

            # Add the fractie_model to self._fracties
            # TODO: Is using uuid the best?
            self._fracties[fractie_model.uuid] = fractie_model

        # ???: Is this return type the best? Or should we
        # just return the dict
        return list(self._fracties.values())


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)
    scraper = TkScraper(verbose=False)
    fracties = scraper.get_all_fracties(populate_members=True)
    for fractie in fracties:
        print(f'Fractie: {fractie.naam} ({fractie.afkorting})')
        print(f'Aantal leden: {len(fractie.leden)}')
        for lid in fractie.leden:
            print(f'  Lid: {lid.naam} ({lid.uuid})')
