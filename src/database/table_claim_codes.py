from sqlalchemy import Column, ForeignKey, Enum, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from database import POODatabase


class StatusesClaimCode:
    AVAILABLE = "AVAILABLE"
    QUEUED = "QUEUED"
    CLAIMED = "CLAIMED"


class TableClaimCodes(POODatabase.base):
    __tablename__ = "CLAIM_CODES"

    id = Column(Integer, primary_key=True)
    fountain_id = Column(Integer, ForeignKey("FOUNTAINS.id"))
    code = Column(String, nullable=False)
    status = Column(
        Enum(StatusesClaimCode.AVAILABLE, StatusesClaimCode.CLAIMED, StatusesClaimCode.QUEUED),
        nullable=False,
        default=StatusesClaimCode.AVAILABLE
    )
    lovelaces = Column(Integer)
    rewards = relationship("TableRewards", back_populates="claim_code", cascade='all, delete')
    address = Column(String)
    tx_hash = Column(String)
    claimed = Column(DateTime)
    test_claim = Column(Boolean, default=False)

    fountain = relationship("TableFountain", back_populates="claim_codes")

    def serialize(self):
        if self.test_claim and not self.status == StatusesClaimCode.AVAILABLE:
            status = f"TEST {self.status}"
        else:
            status = self.status

        return {
            "id": self.id,
            "fountain_id": self.fountain_id,
            "code": self.code,
            "lovelaces": self.lovelaces,
            "status": status,
            "rewards": [reward.serialize() for reward in self.rewards],
            "address": self.address,
            "tx_hash": self.tx_hash,
            "claimed": self.claimed.strftime("%Y-%m-%d %H:%M:%S") if self.claimed else None,
            "test_claim": self.test_claim,
            "assets": [{"name": reward.asset_name, "amount": reward.amount} for reward in self.rewards]
        }
