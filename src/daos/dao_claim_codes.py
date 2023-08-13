from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import TableFountain, TableClaimCodes, StatusesClaimCode


class DAOClaimCodes:

    @staticmethod
    def get_by_id(session: Session, claim_code_id: int) -> Optional[TableFountain]:
        return session.query(TableClaimCodes).filter(TableClaimCodes.id == claim_code_id).first()

    @staticmethod
    def get_by_fountain_id(session: Session, fountain_id: int):
        return session.query(TableClaimCodes).filter(TableClaimCodes.fountain_id == fountain_id).all()

    @staticmethod
    def create(session: Session, fountain: TableFountain, code, lovelaces):
        claim_code = TableClaimCodes(
            code=code,
            status=StatusesClaimCode.AVAILABLE,
            lovelaces=lovelaces
        )
        session.add(claim_code)
        fountain.claim_codes.append(claim_code)
        return claim_code

    @staticmethod
    def queue(session: Session, claim, claiming_address, test_claim, commit=False):
        from . import DAOSendingQueue
        DAOSendingQueue.create(session, claim)
        claim.claim_code.address = claiming_address
        claim.claim_code.status = StatusesClaimCode.QUEUED
        claim.claim_code.test_claim = test_claim
        if commit:
            session.commit()
        return DAOSendingQueue.get_queue_position(session, claim.claim_code.id)

    @staticmethod
    def claimed(session: Session, claim_code, tx_hash="Test", test=False, commit=False):
        claim_code.tx_hash = tx_hash
        claim_code.claimed = datetime.utcnow()
        claim_code.status = StatusesClaimCode.CLAIMED
        claim_code.test_claim = test
        if commit:
            session.commit()

    @staticmethod
    def exceeded_max_address_claims(session: Session, fountain_name: str, claim_code: str, claim_address: str) -> bool:
        fountain = session.query(TableFountain).filter(TableFountain.name == fountain_name).first()
        if not fountain:
            return False

        if fountain.max_address_claims == -1:
            return False

        # noinspection PyTypeChecker
        claimed_count = session.query(func.count(TableClaimCodes.id)).filter(
            TableClaimCodes.fountain_id == fountain.id,
            TableClaimCodes.address == claim_address,
            TableClaimCodes.status != StatusesClaimCode.AVAILABLE
        ).scalar()

        return claimed_count >= fountain.max_address_claims

    """
    # noinspection PyTypeChecker
    @staticmethod
    def already_claimed_on_fountain(session: Session, fountain_name: str, claim_code: str, claim_address: str) -> bool:
        result = session \
            .query(TableClaimCodes) \
            .join(TableFountain) \
            .filter(
                TableFountain.name == fountain_name,
                TableClaimCodes.address == claim_address,
                TableClaimCodes.code != claim_code,
                TableClaimCodes.status != StatusesClaimCode.AVAILABLE
            ) \
            .first()

        return result is not None
    """

    @staticmethod
    def reset_test_claim(session: Session, fountain_id: int, code: str):
        claim_code = session.query(TableClaimCodes).filter_by(fountain_id=fountain_id, code=code).first()
        claim_code.address = None
        claim_code.tx_hash = None
        claim_code.claimed = None
        claim_code.test_claim = False
        claim_code.status = StatusesClaimCode.AVAILABLE
        session.commit()
        return claim_code

    @staticmethod
    def reset_all_test_claims(session: Session, fountain_id: int):
        test_claim_codes = session.query(TableClaimCodes).filter_by(fountain_id=fountain_id, test_claim=True).all()
        reset_claim_codes = []
        for claim_code in test_claim_codes:
            reset_claim_code = DAOClaimCodes.reset_test_claim(session, fountain_id, claim_code.code)
            reset_claim_codes.append(reset_claim_code)

        return [claim_code.serialize() for claim_code in reset_claim_codes]
