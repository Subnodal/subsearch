import logging
from urllib.parse import urlsplit
from flask import Flask, Response, request, jsonify
from flask_expects_json import expects_json
from sqlalchemy import select
from sqlalchemy.orm import Session

import node.db
from node.langs import LANGS
from node.models.site import Site
from node.models.document import Document

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
logger = logging.getLogger("subsearch")

@app.route("/")
def index():
    return jsonify({
        "subsearch": "0.1.0"
    })

@app.route("/documents", methods=["POST"])
@expects_json({
    "type": "object",
    "properties": {
        "url": {"type": "string"},
        "title": {"type": "string"},
        "body": {"type": "string"},
        "lang": {"type": "string"},
        "has_consent_or_pay_model": {"type": "boolean"},
        "has_advertisements": {"type": "boolean"},
        "has_paywalls": {"type": "boolean"},
        "has_login_walls": {"type": "boolean"},
        "has_generative_ai_content": {"type": "boolean"}
    },
    "required": ["url", "title", "body"]
})
def ingest_document():
    with Session(node.db.engine) as session:
        data = request.json
        lang_primary = None
        lang_ext = None
        uri = urlsplit(data["url"])

        if isinstance(data.get("lang"), str) and data.get("lang") != "":
            lang_parts = data.get("lang").split("-")
            lang_primary = lang_parts[0]

            if len(lang_parts) > 1:
                lang_ext = "-".join(lang_parts[1:])

        session.begin()

        try:
            site = session.scalars(select(Site).filter_by(host=uri.hostname)).first()

            if site is None:
                site = Site(host=uri.hostname)

            site.has_consent_or_pay_model = site.has_consent_or_pay_model or data.get("has_consent_or_pay_model") or False
            site.has_advertisements = site.has_advertisements or data.get("has_advertisements") or False

            document = Document(
                url=data["url"],
                site=site,
                title=data["title"],
                body=data["body"],
                lang_primary=lang_primary,
                lang_ext=lang_ext,
                lang_regconfig=LANGS.get(lang_primary or "") or "simple",
                has_paywalls=data.get("has_paywalls"),
                has_login_walls=data.get("has_login_walls"),
                has_generative_ai_content=data.get("has_generative_ai_content")
            )

            session.add(site)
            session.add(document)

            session.commit()

            return Response(status=200)
        except Exception as e:
            logger.error(e)

            session.rollback()

            return Response(status=500)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8000)