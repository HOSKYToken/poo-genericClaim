import logging

from flask import Flask, request
from flask_httpauth import HTTPBasicAuth

from daos import DAOFountain, DAOClaimCodes, DAOSendingQueue
from database import StatusesClaimCode
from logger import log

SHELLEY_ADDRESS_START = "addr1"

STATUS_FAUCET_INVALID_MISSING_CLAIM_CODE = "missingclaimcode"
STATUS_FAUCET_INVALID_MISSING_ADDRESS = "missingaddress"
STATUS_FAUCET_INVALID_NOT_A_SHELLEY_ADDRESS = "notshelleyaddress"
STATUS_FAUCET_NOT_ACTIVE = "notactive"
STATUS_FAUCET_TOO_EARLY = "tooearly"
STATUS_FAUCET_EXPIRED = "expired"
STATUS_CLAIM_CODE_NOT_FOUND = "notfound"
STATUS_CLAIM_ACCEPTED = "accepted"
STATUS_CLAIM_QUEUED = "queued"
STATUS_CLAIM_CLAIMED = "claimed"
STATUS_CLAIM_MAX_LIMIT = "maxlimitclaimed"
STATUS_CLAIM_STATE_UNKNOWN = "unknownstate"
STATUS_CLAIM_ALREADY_CLAIMED = "alreadyclaimed"

POST_BODY_KEY_CLAIM_CODE = "claim_code"
POST_BODY_KEY_ADDRESS = "address"

app_claims = Flask(__name__)
app_claims.logger.disabled = True
app_claims.debug = False
app_claims.sessionmaker = None
app_claims.security = None

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.CRITICAL)

auth = HTTPBasicAuth()

# TODO test and check basic auth


@auth.verify_password
def verify_password(username, password):
    if app_claims.security is None:
        return True

    fountain_name = request.view_args.get('fountain_name')

    if "fountain" in app_claims.security:
        if fountain_name in app_claims.security["fountain"]:
            if username in app_claims.security["fountain"][fountain_name]:
                pwd = app_claims.security["fountain"][fountain_name][username]
                return password == pwd or pwd == "*"
            if "*" in app_claims.security["fountain"][fountain_name]:
                pwd = app_claims.security["fountain"][fountain_name]["*"]
                return password == pwd or pwd == "*"
        elif "*" in app_claims.security["fountain"]:
            if username in app_claims.security["fountain"]["*"]:
                pwd = app_claims.security["fountain"]["*"][username]
                return password == pwd or pwd == "*"
            if "*" in app_claims.security["fountain"]["*"]:
                pwd = app_claims.security["fountain"]["*"]["*"]
                return password == pwd or pwd == "*"

    log.error(f"Claims - Could not find rule for fountain/{fountain_name} in {app_claims.security}")
    return False


@app_claims.route("/alive", methods=["OPTIONS", "GET"])
def alive():
    return {"status": "ok"}, 200


@app_claims.route("/status/<fountain_name>", methods=["OPTIONS", "GET"])
def get_fountain_status(fountain_name):
    log.debug(f"Claims - Processing status check for {fountain_name}")
    with app_claims.sessionmaker() as session:
        result = DAOFountain.get_claimed_status(session, fountain_name)
        log.debug(f"Claims - Status for {fountain_name} is {result}")
        return result


def build_response_data(claim_data, code, status, queue_position=None):
    response = {
        "code": code,
        "status": status,
        "lovelaces": str(claim_data.claim_code.lovelaces),
        "tokens": {token.fqn_asset(hex_encoded=True): str(token.amount) for token in claim_data.rewards}
    }

    if queue_position:
        response["queue_position"] = queue_position
    else:
        response["tx_hash"] = claim_data.claim_code.tx_hash

    log.debug(f"Claims - Response {response}")

    return response


def build_response_error(code, status):
    log.error(f"Claims - Error {code} : {status}")
    return {
        "code": code,
        "status": status
    }


def same_claimant(claim_code, claiming_address):
    return claim_code.status == StatusesClaimCode.AVAILABLE or claim_code.address == claiming_address


@app_claims.route("/<fountain_name>", methods=["OPTIONS", "POST"])
@auth.login_required
def process_claim(fountain_name):
    log.debug(f"Claims - Processing claim for {fountain_name}")
    match request.method:
        case "OPTIONS":
            return "", 200
        case "POST":
            data = request.get_json()

            claim_code = data.get(POST_BODY_KEY_CLAIM_CODE, None)
            claiming_address = data.get(POST_BODY_KEY_ADDRESS, None)
            log.info(
                f"Claims - Processing claim code {claim_code} from Fountain {fountain_name} by {claiming_address}")

            if not claim_code:
                return build_response_error(404, STATUS_FAUCET_INVALID_MISSING_CLAIM_CODE), 404

            if claiming_address is None:
                return build_response_error(404, STATUS_FAUCET_INVALID_MISSING_ADDRESS), 404

            if not claiming_address.startswith(SHELLEY_ADDRESS_START):
                return build_response_error(404, STATUS_FAUCET_INVALID_NOT_A_SHELLEY_ADDRESS), 404

            with app_claims.sessionmaker() as session:

                test_claim = True

                if not DAOFountain.is_in_test_mode(session, fountain_name):

                    test_claim = False

                    # Return if not active
                    if not DAOFountain.is_active(session, fountain_name):
                        if DAOFountain.is_tooearly(session, fountain_name):
                            return build_response_error(410, STATUS_FAUCET_TOO_EARLY), 410
                        if DAOFountain.has_expired(session, fountain_name):
                            return build_response_error(425, STATUS_FAUCET_EXPIRED), 425
                        return build_response_error(403, STATUS_FAUCET_NOT_ACTIVE), 403

                # Return if maximum claims by address has been exceeded
                if DAOClaimCodes.exceeded_max_address_claims(session, fountain_name, claim_code, claiming_address):
                    return build_response_error(409, STATUS_CLAIM_MAX_LIMIT), 409

                # Return if not found
                claim = DAOFountain.find_by_name_and_code(session, fountain_name, claim_code)
                if not claim:
                    return build_response_error(404, STATUS_CLAIM_CODE_NOT_FOUND), 404

                # Return if a claim by a different claimant
                if not same_claimant(claim.claim_code, claiming_address):
                    return build_response_error(409, STATUS_CLAIM_ALREADY_CLAIMED), 409

                # Return claim
                match claim.claim_code.status:
                    case StatusesClaimCode.AVAILABLE:
                        queue_position = DAOClaimCodes.queue(session, claim, claiming_address, test_claim, commit=True)
                        return build_response_data(claim, 200, STATUS_CLAIM_ACCEPTED, queue_position), 200
                    case StatusesClaimCode.QUEUED:
                        queue_position = DAOSendingQueue.get_queue_position(session, claim.claim_code.id)
                        return build_response_data(claim, 201, STATUS_CLAIM_QUEUED, queue_position), 201
                    case StatusesClaimCode.CLAIMED:
                        return build_response_data(claim, 202, STATUS_CLAIM_CLAIMED), 202
                    case _:
                        # Should NEVER happen catch all
                        return build_response_error(404, STATUS_CLAIM_STATE_UNKNOWN), 404
