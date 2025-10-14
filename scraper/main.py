import datetime

from tkapi import TKApi
from tkapi.persoon import Persoon
from tkapi.fractie import FractieFilter
from tkapi.stemming import Stemming
from tkapi.fractie import FractieZetelPersoon
from tkapi.fractie import Fractie
from tkapi.zaak import Zaak
from tkapi.zaak import ZaakSoort
from tkapi.util import queries
import logging

from models import TKLid, VoteType
from models import TKFractie
from models import TKMotie
from models import Vote

class Scraper:

    def __init__(self, api: TKApi|None) -> None:

        # Initialize the TKApi instance
        # If an instance is provided, use it; otherwise, create a new one
        self.api = TKApi or TKApi()
        self.logger = logging.getLogger(f'scraper.{self.__class__.__name__}')


class FractieScraper(Scraper):

    def get_all_fracties(self, populate_members: bool = False) -> list[TKFractie]:

        self.logger.info('Fetching all parties (fracties)')
        fracties_filter = Fractie.create_filter()
        fracties_filter.filter_actief()
        fracties_data = self.api.get_fracties(filter=fracties_filter)
        self.logger.info(f'Fetched {len(fracties_data)} active parties')

        fracties: list[TKFractie] = []

        for fractie in fracties_data:
            self.logger.debug(f'Processing party: {fractie.naam} ({fractie.afkorting})')

            tk_fractie = TKFractie(
                id=fractie.id,
                name=fractie.naam,
                abbreviation=fractie.afkorting,
                seats=fractie.zetels_aantal or 0,
                is_active=True
            )

            if populate_members:
                self._populate_members(tk_fractie, fractie.leden_actief)
            fracties.append(tk_fractie)

        return fracties

    def _populate_members(self, fractie: TKFractie, leden_actief: list[FractieZetelPersoon]|None=None) -> None:
        # Note: fractie is passed by reference, so we modify it directly

        if not leden_actief:
            filter = FractieZetelPersoon.create_filter()
            filter.filter_fractie_id(uid=fractie.id)
            filter.filter_actief()
            leden_actief = self.api.get_items(
                FractieZetelPersoon, filter=filter
            )


        for lid in leden_actief:
            tk_lid = TKLid(
                id=lid.persoon.id,
                first_name=lid.persoon.roepnaam,
                last_name=lid.persoon.achternaam,
                fractie_id=fractie.id,
                is_active=True
            )
            fractie.members.append(tk_lid)

    def get_fractie_by_id(self, fractie_id: str) -> TKFractie | None:

        self.logger.info(f'Fetching party (fractie) by ID: {fractie_id}')

        fracties_filter = Fractie.create_filter()
        fracties_filter.filter_fractie_id(fractie_id)
        fracties_data = self.api.get_fracties(filter=fracties_filter)

        if not fracties_data:
            self.logger.warning(f'No party found with ID: {fractie_id}')
            return None

        fractie = fracties_data[0]

        tk_fractie = TKFractie(
            id=fractie.id,
            name=fractie.naam,
            abbreviation=fractie.afkorting,
            seats=fractie.zetels_aantal or 0,
            is_active=True
        )

        return tk_fractie




class MemberScraper(Scraper):

    def get_all_active_members(self) -> list[TKLid]:

        self.logger.info('Fetching all active members')
        members_data = queries.get_kamerleden_active()
        self.logger.info(f'Fetched {len(members_data)} active members')

        members: list[TKLid] = []

        for member in members_data:
            self.logger.debug(f'Processing member: {member.roepnaam} {member.achternaam}')

            fractie_id = None
            if hasattr(member, 'fracties'):
                if len(member.fracties) > 0:
                    # Default pick the first party
                    fractie_id = member.fracties[0].id

            # Create an ID for "Onafhankelijk" members
            if not fractie_id:
                fractie_id = "Onafhankelijk"

            tk_member = TKLid(
                id=member.id,
                first_name=member.roepnaam,
                last_name=member.achternaam,
                fractie_id=fractie_id,
                is_active=True
            )
            members.append(tk_member)


        return members


class MotieScraper(Scraper):

    def get_all_moties_by_year(self, year:int) -> list[TKMotie]:

        self.logger.info('Fetching all motions (moties)')

        begin_datetime = datetime.datetime(year=year, month=1, day=1)
        end_datetime = datetime.datetime(year=year, month=12, day=30)

        moties_filter = Zaak.create_filter()
        moties_filter.filter_date_range(
            start_datetime=begin_datetime,
            end_datetime=end_datetime,
        )

        moties_filter.filter_soort(ZaakSoort.MOTIE)
        moties_data = self.api.get_zaken(filter=moties_filter)

        moties: list[TKMotie] = []
        for motie in moties_data:
            self.logger.debug(f'Processing motion: {motie.onderwerp}')

            tk_motie = TKMotie(
                id=motie.id,
                subject=motie.onderwerp or 'No Subject',
                date_submitted=motie.gestart_op,
                status=motie.afgedaan and 'Afgedaan' or 'Open',
                onderwerp=motie.onderwerp
            )
            moties.append(tk_motie)

        return moties


class VoteScraper(Scraper):

    def get_votes_for_zaak_id(self, zaak_id: str) -> list[Vote]:

        zaak_filter = Zaak.create_filter()
        zaak_filter.filter_property('id', zaak_id)
        zaak = self.api.get_zaken(filter=zaak_filter)
        breakpoint()


    def get_votes_for_zaak(self, zaak_id: str) -> list[Vote]:

        # TODO: Differantiate between hoofdelijk and non-hoofdelijke votes

        self.logger.info(f'Fetching votes for zaak: {zaak_id}')

        stemming_filter = Stemming.create_filter()
        stemming_filter.filter_zaak(zaak_id)
        stemmingen = self.api.get_stemmingen(filter=stemming_filter)
        breakpoint()

        votes = []
        for stemming in stemmingen:
            # Get individual votes
            vote = Vote(
                decision_id=stemming.id,
                member_id=stemming.persoon.id if stemming.persoon else None,
                party_id=stemming.fractie.id if stemming.fractie else 'Unknown',
                vote_type=VoteType[stemming.soort],
                is_hoofdelijk=stemming.is_hoofdelijk,
            )
            votes.append(vote)

        self.logger.info(f'Fetched {len(votes)} votes for zaak {zaak_id}')
        return votes

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    # scraper = FractieScraper(api=None)
    # fracties = scraper.get_all_fracties(populate_members=True)

    # for fractie in fracties:
    #     print(f'{fractie.name} ({fractie.abbreviation}) - Seats: {fractie.seats} - Active: {fractie.is_active}')
    #     for member in fractie.members:
    #         print(f'  - {member.full_name} - Active: {member.is_active}')


    scraper = MotieScraper(api=None)
    moties = scraper.get_all_moties_by_year(2025)
    for motie in moties[:10]:
        print(f'{motie.date_submitted} - {motie.subject} - Status: {motie.status}')
        print(f'  Subject: {motie.onderwerp}')

        # vote_scraper = VoteScraper(api=None)
        # votes = vote_scraper.get_votes_for_zaak_id(motie.id)
        # Get votes
        # vote_scraper = VoteScraper(api=None)
        # votes = vote_scraper.get_votes_for_zaak(motie.id)
        # print(f'  Votes: {len(votes)}')
        # for vote in votes:
        #     print(f'    - Member ID: {vote.member_id}, Party ID: {vote.party_id}, Vote: {vote.vote_type.name}, Hoofdelijke: {vote.is_hoofdelijk}')

    print(f'Total motions in 2025: {len(moties)}')
