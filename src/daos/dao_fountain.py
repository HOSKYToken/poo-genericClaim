import json
from datetime import datetime

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from database import TableFountain, TableClaimCodes, StatusesClaimCode, TableRewards


class DataClaim:
    def __init__(self, fountain, claim_code, rewards):
        self.fountain = fountain
        self.claim_code = claim_code
        self.rewards = rewards


class DAOFountain:

    @staticmethod
    def list_all(session: Session):
        # noinspection PyTypeChecker
        subquery = session.query(
            TableClaimCodes.fountain_id,
            func.count().label('total_claim_codes'),
            func.sum(case((TableClaimCodes.status == StatusesClaimCode.CLAIMED, 1), else_=0)).label('total_claimed')
        ).group_by(TableClaimCodes.fountain_id).subquery()

        # noinspection PyTypeChecker
        query = session.query(
            TableFountain,
            subquery.c.total_claim_codes,
            subquery.c.total_claimed
        ).outerjoin(subquery, TableFountain.id == subquery.c.fountain_id).all()

        fountains = []
        for result in query:
            fountain = result[0]
            fountain_dict = {c.name: getattr(fountain, c.name) for c in fountain.__table__.columns}
            fountain_dict['status'] = fountain.current_status
            fountain_dict['total_claim_codes'] = result[1] if result[1] else '-'
            fountain_dict['total_claimed'] = result[2] if result[2] else 0 if result[1] else '-'
            fountains.append(fountain_dict)

        return fountains

    @staticmethod
    def get_claimed_status(session: Session, name: str) -> str:
        # noinspection PyTypeChecker
        query = session.query(func.count(TableClaimCodes.id)).join(TableFountain).filter(
            TableFountain.name == name,
            TableClaimCodes.status != StatusesClaimCode.AVAILABLE
        ).scalar()

        if query is None:
            return json.dumps({})

        return json.dumps({"total_claimed": query})

    @staticmethod
    def get_by_id(session: Session, fountain_id: int):
        return session.query(TableFountain).filter(TableFountain.id == fountain_id).first()

    @staticmethod
    def is_active(session: Session, name: str):
        result = session.query(TableFountain).filter(TableFountain.name == name).first()
        return result and result.start_date <= datetime.now() <= result.end_date

    @staticmethod
    def is_in_test_mode(session: Session, fountain_name: str = "", fountain_id: int = -1):
        query = session.query(TableFountain.test_mode)

        if id is not None and fountain_id >= 0:
            query = query.filter(TableFountain.id == fountain_id)
        elif fountain_name:
            query = query.filter(TableFountain.name == fountain_name)

        result = query.first()
        return result and result[0]

    @staticmethod
    def is_tooearly(session: Session, name: str):
        result = session.query(TableFountain).filter(TableFountain.name == name).first()
        return result and datetime.now() < result.start_date

    @staticmethod
    def has_expired(session: Session, name: str):
        result = session.query(TableFountain).filter(TableFountain.name == name).first()
        return result and datetime.now() > result.end_date

    @staticmethod
    def find_by_name_and_code(session: Session, fountain_name: str, claim_code: str):
        result = session \
            .query(TableFountain, TableClaimCodes, TableRewards) \
            .select_from(TableFountain) \
            .join(TableClaimCodes) \
            .outerjoin(TableRewards).filter(
                TableFountain.name == fountain_name,
                TableClaimCodes.code == claim_code
            ) \
            .first()

        return DataClaim(result[0], result[1], [reward for reward in result[1].rewards]) if result else None

    @staticmethod
    def create(session: Session, name, start_date, end_date, wallet, max_address_claims, commit=False):
        fountain = TableFountain(
            name=name,
            start_date=datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S"),
            end_date=datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S"),
            wallet=wallet,
            max_address_claims=max_address_claims
        )
        session.add(fountain)
        if commit:
            session.commit()
        return fountain

    @staticmethod
    def update(session: Session, fountain_id, name, start_date, end_date, wallet, max_address_claims, commit=False):
        fountain = DAOFountain.get_by_id(session, fountain_id)
        if not fountain:
            return None
        fountain.name = name
        fountain.start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
        fountain.end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
        fountain.wallet = wallet
        fountain.max_address_claims = max_address_claims
        if commit:
            session.commit()
        return fountain

    @staticmethod
    def toggle_test_mode(session: Session, fountain_id, commit=False):
        fountain = DAOFountain.get_by_id(session, fountain_id)
        if not fountain:
            return None
        fountain.test_mode = not fountain.test_mode
        if commit:
            session.commit()
        return fountain

    @staticmethod
    def delete(session: Session, fountain_id: int, cascade=False, commit=False):
        if cascade:
            claim_codes = session.query(TableClaimCodes).filter(TableClaimCodes.fountain_id == fountain_id).all()
            for claim_code in claim_codes:
                # noinspection PyTypeChecker
                session.query(TableRewards).filter(TableRewards.code_id == claim_code.id).delete()
            session.query(TableClaimCodes).filter(TableClaimCodes.fountain_id == fountain_id).delete()

        session.query(TableFountain).filter(TableFountain.id == fountain_id).delete()

        if commit:
            session.commit()
