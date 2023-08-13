from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from database import POODatabase, TableClaimCodes


class TableSendingQueue(POODatabase.base):
    __tablename__ = "SENDING_QUEUE"

    id = Column(Integer, primary_key=True)
    claim_code_id = Column(Integer, ForeignKey("CLAIM_CODES.id"))
    fountain_id = Column(Integer, ForeignKey("FOUNTAINS.id"))

    claim_code = relationship("TableClaimCodes", backref="sending_queue")
    fountain = relationship("TableFountain", backref="sending_queue")

    def serialize(self):
        return {
            "id": self.id,
            "claim_code_id": self.claim_code_id,
            "fountain_id": self.fountain_id
        }
