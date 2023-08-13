from sqlalchemy import func
from sqlalchemy.orm import Session

from database import TableSendingQueue


class DAOSendingQueue:

    @staticmethod
    def get_by_claim_id(session: Session, claim_code_id: int):
        return session.query(TableSendingQueue).filter(TableSendingQueue.claim_code_id == claim_code_id).first()

    @staticmethod
    def get_queue_position(session: Session, claim_code_id: int):
        position = DAOSendingQueue.get_by_claim_id(session, claim_code_id)
        if position:
            # noinspection PyTypeChecker
            return 1 + session.query(func.count(TableSendingQueue.id)).filter(
                TableSendingQueue.id < position.id
            ).scalar()
        return 1

    """
    @staticmethod
    def get_next_batch(session: Session, max_limit: int):
        # TODO make this find the first entry then up to limit of the same fountain!
        query = session.query(TableSendingQueue.id).order_by(TableSendingQueue.id).limit(max_limit).all()
        return [item[0] for item in query]
    """

    @staticmethod
    def get_next_batch(session: Session, max_limit: int):
        topmost_item = session.query(TableSendingQueue).order_by(TableSendingQueue.id).first()

        if topmost_item:
            query = session.query(TableSendingQueue.id) \
                .filter(TableSendingQueue.fountain_id == topmost_item.fountain_id) \
                .order_by(TableSendingQueue.id).limit(max_limit).all()

            return [item[0] for item in query]
        else:
            return []

    @staticmethod
    def get_claim_code(session: Session, queue_id: int):
        sending_queue = session.query(TableSendingQueue).get(queue_id)
        if sending_queue:
            return sending_queue.claim_code
        return None

    @staticmethod
    def create(session: Session, claim):
        sending_queue = TableSendingQueue(claim_code=claim.claim_code, fountain=claim.fountain)
        session.add(sending_queue)

    @staticmethod
    def delete(session: Session, claim_code, commit=False):
        item = session.query(TableSendingQueue).filter_by(claim_code=claim_code).first()
        if item:
            session.delete(item)
            if commit:
                session.commit()
            return True
        return False
