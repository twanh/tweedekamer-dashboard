import enum
from dataclasses import dataclass, field
from datetime import date

class VoteType(enum.Enum):

    # TODO: Check possible types
    VOOR = 'Voor'
    TEGEN = 'Tegen'
    # TODO: Check if this is the correct value, or if its two values
    # https://opendata.tweedekamer.nl/documentatie/stemming
    NIET_DEELGENOMEN = 'Niet deelgenomen'





@dataclass
class TKLid:
    id: str
    first_name: str
    last_name: str
    fractie_id: str
    is_active: bool = True

    @property
    def full_name(self) -> str:
        return f'{self.first_name} {self.last_name}'


@dataclass
class TKFractie:
    id: str
    name: str
    abbreviation: str
    seats: int
    is_active: bool = True
    members: list[TKLid]= field(default_factory=list)


@dataclass
class TKMotie:
    id: str
    # TODO: remove subject/onderwerp
    subject: str
    date_submitted: date|None
    status: str
    onderwerp: str|None = None


@dataclass
class Vote:
    decision_id: str
    member_id: str|None
    party_id: str
    vote_type: VoteType
    is_hoofdelijk: bool = False

