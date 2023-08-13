from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship

from database import POODatabase


class TableFountain(POODatabase.base):
    __tablename__ = "FOUNTAINS"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    wallet = Column(String, nullable=False)
    test_mode = Column(Boolean, default=False)
    max_address_claims = Column(Integer, default=1)
    claim_codes = relationship("TableClaimCodes", back_populates="fountain", cascade='all, delete')

    @property
    def current_status(self):
        if len(self.claim_codes) == 0:
            return "No codes loaded"
        elif self.test_mode:
            return "Test Mode"
        elif datetime.now() < self.start_date:
            return "Waiting to start"
        elif datetime.now() > self.end_date:
            return "Expired"
        return "Running"

    def serialize(self):
        return {
            "id": self.id,
            "name": self.name,
            "start_date": self.start_date.strftime("%Y-%m-%d %H:%M:%S"),
            "end_date": self.end_date.strftime("%Y-%m-%d %H:%M:%S"),
            "wallet": self.wallet,
            "status": self.current_status,
            "test_mode": self.test_mode,
            "max_address_claims": self.max_address_claims,
            "claim_codes": [claim_code.serialize() for claim_code in self.claim_codes]
        }
