from sqlalchemy.orm import Session

from database import TableClaimCodes, TableRewards
from helpers import convert_asset_to_hrf_and_hex_form


class DAORewards:

    @staticmethod
    def list_all(session: Session):
        return session.query(TableRewards).all()

    @staticmethod
    def create(session: Session, claim_code: TableClaimCodes, policy, asset_name, amount):
        asset_name, asset_hex = convert_asset_to_hrf_and_hex_form(asset_name)

        reward = TableRewards(
            claim_code=claim_code,
            policy=policy,
            asset_name=asset_name,
            asset_hex=asset_hex,
            amount=amount
        )
        session.add(reward)
        claim_code.rewards.append(reward)
        return reward
