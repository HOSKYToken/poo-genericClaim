from sqlalchemy import Column, BigInteger, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from database import POODatabase, TableClaimCodes


class TableRewards(POODatabase.base):
    __tablename__ = "REWARDS"

    id = Column(Integer, primary_key=True)
    code_id = Column(Integer, ForeignKey("CLAIM_CODES.id"))
    claim_code = relationship(TableClaimCodes, back_populates="rewards")
    policy = Column(String, nullable=False)
    asset_name = Column(String, nullable=False)
    asset_hex = Column(String, nullable=False)
    amount = Column(BigInteger, nullable=False)

    def serialize(self):
        return {
            "id": self.id,
            "code_id": self.code_id,
            "policy": self.policy,
            "asset_name": self.asset_name,
            "asset_hex": self.asset_hex,
            "amount": self.amount,
        }

    def fqn_asset(self, hex_encoded=False):
        return f"{self.policy}.{self.asset_hex}" if hex_encoded else f"{self.policy}.{self.asset_name}"
