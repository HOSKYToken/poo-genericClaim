import logging
import os
import io
from datetime import datetime

from flask import Flask, request, send_from_directory, jsonify, send_file, Response
from flask_cors import CORS

from daos import DAOFountain, DAOClaimCodes, DAORewards
from helpers import file_exists, load_json, generate_qr_image, is_valid_qr_png, fetch_file_content
from logger import log

app_admin = Flask(__name__, )
app_admin.logger.disabled = True
app_admin.debug = False
app_admin.claims_url = None
app_admin.wallet_path = None
app_admin.cardano_cli = None
app_admin.sessionmaker = None

CORS(app_admin)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.CRITICAL)

# TODO Change CSV to take multiple rows of data


@app_admin.route("/")
def index():
    return serve_static("fountains.html")


@app_admin.route('/claims_url', methods=["GET"])
def claims_url():
    return {"url": app_admin.claims_url}, 200


@app_admin.route("/<path:filename>", methods=["GET"])
def serve_static(filename):
    return send_from_directory(app_admin.static_folder, filename)


@app_admin.route("/db/fountains")
def fountain_list():
    with app_admin.sessionmaker() as session:
        return DAOFountain.list_all(session)


@app_admin.route("/db/fountain/<int:fountain_id>", methods=["GET"])
def fountain_get(fountain_id):
    with app_admin.sessionmaker() as session:
        fountain = DAOFountain.get_by_id(session, fountain_id)
        if fountain:
            return fountain.serialize()
        else:
            return {"error": "fountain not found"}, 404


@app_admin.route("/db/fountain", methods=["POST"])
def fountain_create():
    data = request.get_json()
    with app_admin.sessionmaker() as session:
        fountain = DAOFountain.create(
            session,
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            wallet=data["wallet"],
            max_address_claims=data["max_address_claims"],
            commit=True
        )
        return fountain.serialize(), 201


@app_admin.route("/db/fountain/<int:fountain_id>", methods=["PUT"])
def fountain_update(fountain_id):
    data = request.get_json()
    with app_admin.sessionmaker() as session:
        fountain = DAOFountain.update(
            session,
            fountain_id=fountain_id,
            name=data["name"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            wallet=data["wallet"],
            max_address_claims=data["max_address_claims"],
            commit=True
        )
        return fountain.serialize(), 201


@app_admin.route("/db/fountain/<int:fountain_id>/toggle-test-mode", methods=["POST"])
def toggle_test_mode(fountain_id):
    with app_admin.sessionmaker() as session:
        fountain = DAOFountain.toggle_test_mode(
            session,
            fountain_id=fountain_id,
            commit=True
        )
        return fountain.serialize(), 201


@app_admin.route("/db/fountain/<int:fountain_id>", methods=["DELETE"])
def fountain_delete(fountain_id):
    with app_admin.sessionmaker() as session:
        DAOFountain.delete(session, fountain_id, cascade=True, commit=True)
    return {}, 204


@app_admin.route('/db/claimcodes/<int:fountain_id>', methods=['GET'])
def get_claim_codes(fountain_id):
    with app_admin.sessionmaker() as session:
        claim_codes = DAOClaimCodes.get_by_fountain_id(
            session,
            fountain_id
        )
        return {
            "test_mode": DAOFountain.is_in_test_mode(session, fountain_id=fountain_id),
            "claim_codes": [code.serialize() for code in claim_codes]
        }


@app_admin.route("/db/fountain/<int:fountain_id>/upload_claim_codes", methods=["POST"])
def fountain_upload_claim_codes(fountain_id):
    data = request.get_json()

    with app_admin.sessionmaker() as session:
        fountain = DAOFountain.get_by_id(session, fountain_id)
        for code in data:
            lovelaces = code["assets"]["lovelaces"]
            claim_code = DAOClaimCodes.create(session, fountain, code["code"], lovelaces)
            log.debug(f"Adding Claim Code: {claim_code.code} with {claim_code.lovelaces} lovelaces")
            for asset in code["assets"]:
                if asset != "lovelaces":
                    policy = asset.split('.')[0]
                    asset_name = asset.split('.')[1]
                    amount = code["assets"][asset]
                    reward = DAORewards.create(session, claim_code, policy, asset_name, amount)
                    log.debug(f"With a reward of: {reward.policy}.{reward.asset_name} with {reward.amount}")
        session.commit()
        return fountain.serialize(), 201


@app_admin.route('/db/wallets')
def list_wallets():
    path = app_admin.wallet_path
    directories = [name for name in os.listdir(path) if os.path.isdir(os.path.join(path, name))]
    wallets = [
        {
            'name': name,
            'path': os.path.join(path, name),
            'address': 'tbc',
            'lovelaces': 'loading..'
        } for name in directories
    ]
    return jsonify(wallets)


@app_admin.route('/db/wallet/<wallet_name>', methods=['GET'])
def get_wallet(wallet_name):
    wallet_path = f"{app_admin.wallet_path}{wallet_name}/balance.json"
    if file_exists(wallet_path):
        balance = load_json(wallet_path)
        file_dts = os.path.getmtime(wallet_path)
        dt = datetime.fromtimestamp(file_dts)
        balance["date"] = dt.strftime("%Y-%m-%d")
        balance["time"] = dt.strftime("%H:%M:%S")
        return balance
    else:
        return {"address": "Loading...", "date": "", "time": "", "lovelaces": "Loading...", "assets": None}


@app_admin.route('/db/wallet/<wallet_name>/qr', methods=['GET'])
def get_wallet_qr(wallet_name):
    qr_path = f"{app_admin.wallet_path}{wallet_name}/qr.png"
    if not file_exists(qr_path):
        address = fetch_file_content(f"{app_admin.wallet_path}{wallet_name}/payment.addr")
        while True:
            qr_img = generate_qr_image(address)
            qr_img.save(qr_path)
            if is_valid_qr_png(qr_path):
                break
    return send_file(qr_path, mimetype='image/png')


@app_admin.route('/db/qr/generate/<data>', methods=['GET'])
@app_admin.route('/db/qr/generate/<data>/<hex_encoded>', methods=['GET'])
def generate_qr(data, hex_encoded=None):
    if hex_encoded is not None:
        data = bytes.fromhex(data)

    print(data)

    qr_img = generate_qr_image(data)

    # Convert the image to bytes
    img_bytes = io.BytesIO()
    qr_img.save(img_bytes, format='PNG')
    img_bytes.seek(0)

    return Response(img_bytes.getvalue(), content_type='image/png')


@app_admin.route('/db/fountain/<int:fountain_id>/clear-test-claim/<code>', methods=['POST'])
def clear_test_clam(fountain_id, code):
    with app_admin.sessionmaker() as session:
        claim_code = DAOClaimCodes.reset_test_claim(
            session,
            fountain_id,
            code
        )
        return claim_code.serialize(), 201


@app_admin.route('/db/fountain/<int:fountain_id>/clear-all-test-claims', methods=['POST'])
def clear_all_test_clams(fountain_id):
    with app_admin.sessionmaker() as session:
        reset_claim_codes = DAOClaimCodes.reset_all_test_claims(session, fountain_id)
        return jsonify(reset_claim_codes), 201
