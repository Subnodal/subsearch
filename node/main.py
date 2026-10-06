import logging
from datetime import datetime
from urllib.parse import urlsplit
from flask import Flask, Response, request, jsonify
from flask_expects_json import expects_json
from jsonschema import ValidationError
from sqlalchemy import select, func
from sqlalchemy.orm import Session

import node.db
from node.langs import LANG_REGCONFIG
from node.models.site import Site
from node.models.document import Document, DatePrecision

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
logger = logging.getLogger("subsearch")

@app.route("/")
def index():
    return jsonify({
        "subsearch": "0.1.0"
    })

@app.errorhandler(400)
def handle_bad_request(error):
    if isinstance(error.description, ValidationError):
        return jsonify({
            "code": "invalid_body",
            "message": "The provided request body is invalid, either because "
            "it contains incorrectly formatted JSON, or is missing a required "
            "value."
        }), 422

    return error

@app.route("/documents", methods=["GET"])
def search_documents():
    query = request.args.get("q")
    query_regconfig = LANG_REGCONFIG["en"]

    if query is None:
        return jsonify({
            "code": "missing_required_parameter",
            "message": "A query is required as URL parameter `q`."
        }), 422

    query = query.strip()

    if query == "":
        return jsonify({
            "code": "invalid_query",
            "message": "The query must not be empty."
        })

    with Session(node.db.engine) as session:
        session.begin()

        ts_query = func.websearch_to_tsquery(query_regconfig, query)
        is_stop_words_only = session.scalar(select(func.numnode(ts_query))) == 0

        if is_stop_words_only:
            ts_query = func.websearch_to_tsquery("simple", query)

        # Text search vector based on combined title and body fields; if query
        # is made entirely of stop words, then use simple regconfig instead of
        # regconfig based on document language so that stop words are not
        # stripped out
        ts_vector = func.to_tsvector(
            "simple" if is_stop_words_only else Document.lang_regconfig,
            Document.title + " " + Document.body
        )

        # Use rank values as keyword scores; higher values more relevant
        keyword_score = func.ts_rank_cd(ts_vector, ts_query).label("keyword_score")

        # Use snippet to show short excerpt of body that is relevant to the
        # query text; keywords that appear in the query are wrapped in double
        # brace brackets
        snippet = func.ts_headline(
            Document.lang_regconfig,
            func.replace(func.replace(Document.body, "{{", ""), "}}", ""),
            ts_query,
            "StartSel={{,StopSel=}}"
        ).label("snippet")

        results = session.execute(
            select(Document, keyword_score, snippet)
                .where(ts_vector.bool_op("@@")(ts_query))
                .order_by(keyword_score.desc())
                .limit(10)
        ).all()

        return jsonify({
            "documents": list(map(lambda result: {
                "id": result.Document.id,
                "url": result.Document.url,
                "title": result.Document.title,
                "description": result.Document.description,
                "keyword_score": result.keyword_score,
                "snippet": result.snippet,
                "ip_region": result.Document.ip_region,
                "crawl_date": result.Document.crawl_date.isoformat(),
                "publication_date": (
                    result.Document.publication_date.isoformat()
                    if result.Document.publication_date is not None
                    else None
                ),
                "publication_date_precision": (
                    DatePrecision.to_str(result.Document.publication_date_precision)
                    if result.Document.publication_date_precision is not None
                    else None
                )
            }, results))
        })

@app.route("/documents", methods=["POST"])
@expects_json({
    "type": "object",
    "properties": {
        "documents": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "body": {"type": "string"},
                    "lang": {"type": "string"},
                    "ip_region": {"type": "string"},
                    "publication_date": {"type": "string"},
                    "publication_date_precision": {"enum": [
                        "day",
                        "second",
                        "millisecond"
                    ]},
                    "has_consent_or_pay_model": {"type": "boolean"},
                    "has_advertisements": {"type": "boolean"},
                    "has_paywall": {"type": "boolean"},
                    "has_login_wall": {"type": "boolean"},
                    "has_generative_ai_content": {"type": "boolean"}
                },
                "required": ["url", "title", "body"]
            }
        }
    },
    "required": ["documents"]
})
def ingest_document():
    with Session(node.db.engine) as session:
        session.begin()

        data = request.json

        try:
            for document_data in data["documents"]:
                lang_primary = None
                lang_ext = None
                uri = urlsplit(document_data["url"])

                if isinstance(document_data.get("lang"), str) and document_data.get("lang") != "":
                    lang_parts = document_data.get("lang").split("-")
                    lang_primary = lang_parts[0]

                    if len(lang_parts) > 1:
                        lang_ext = "-".join(lang_parts[1:])

                publication_date = document_data.get("publication_date")
                publication_date_precision = document_data.get("publication_date_precision")

                if publication_date is not None:
                    try:
                        publication_date = datetime.fromisoformat(publication_date)
                    except ValueError:
                        return {
                            "code": "invalid_body",
                            "message": "The provided publication date is not a valid ISO 8601 timestamp."
                        }, 422

                if publication_date_precision is not None:
                    try:
                        publication_date_precision = DatePrecision.from_str(publication_date_precision)
                    except ValueError:
                        return {
                            "code": "invalid_body",
                            "message": "The provided publication date precision is not a valid enum value."
                        }, 422

                if publication_date is not None and publication_date_precision is None:
                    return {
                        "code": "invalid_body",
                        "message": "A publication date precision must be provided alongside the publication date."
                    }, 422

                if publication_date is None and publication_date_precision is not None:
                    return {
                        "code": "invalid_body",
                        "message": "A publication date precision must not be provided if a publication date is not provided."
                    }, 422

                # Get existing site based on host or create new site entry
                # if nonexistent
                site = session.scalars(select(Site).filter_by(host=uri.hostname)).first()

                if site is None:
                    site = Site(host=uri.hostname)

                # Apply site-specific boolean values if not already set for
                # this site
                site.has_consent_or_pay_model = site.has_consent_or_pay_model or document_data.get("has_consent_or_pay_model") or False
                site.has_advertisements = site.has_advertisements or document_data.get("has_advertisements") or False

                document = Document(
                    url=document_data["url"],
                    site=site,
                    title=document_data["title"],
                    description=document_data.get("description"),
                    body=document_data["body"],
                    lang_primary=lang_primary,
                    lang_ext=lang_ext,
                    lang_regconfig=LANG_REGCONFIG.get(lang_primary or "") or "simple",
                    ip_region=document_data.get("ip_region"),
                    publication_date=publication_date,
                    publication_date_precision=publication_date_precision,
                    has_paywall=document_data.get("has_paywall"),
                    has_login_wall=document_data.get("has_login_wall"),
                    has_generative_ai_content=document_data.get("has_generative_ai_content")
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