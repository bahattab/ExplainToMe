
from __future__ import print_function

import json
import os
import sys

import requests
from flask import (Blueprint, flash, jsonify, make_response, redirect,
                   render_template, request, session, url_for)
from sumy.nlp.tokenizers import Tokenizer

from wtforms.validators import URL

from ..forms import LinkForm
from ..textrank import get_parser, run_summarizer

site = Blueprint('site', __name__)


def respond(recipient_id, message_text, response="Thanks"):
    log(message_text)
    data = {
        "recipient": {
            "id": recipient_id
        },
        "message": {
            "text": response
        }
    }
    resp = requests.post(
        "https://graph.facebook.com/v2.6/me/messages",
        params={"access_token": os.environ["PAGE_ACCESS_TOKEN"]},
        headers={"Content-Type": 'application/json'},
        data=json.dumps(data),
    )
    return resp


def log(message):
    print(str(message), file=sys.stderr)
    sys.stderr.flush()


def valid_url(raw_url):
    validator = URL()
    match = validator.regex.match(raw_url)
    if not match:
        return False
    return validator.validate_hostname(match.group('host'))


def recieve():
    data = json.loads(request.data)
    log(data)
    if data["object"] != "page":
        return 'ok', 200
    for entry in data["entry"]:
        for message in entry['messaging']:
            # someone sent us a message
            if message.get("message", ''):
                log(respond(message["sender"]["id"], message["message"]["text"]))
            # delivery confirmation
            if message.get("delivery", ''):
                pass
            # optin confirmation
            if message.get("optin", ''):
                pass
            # user clicked/tapped "postback" button in earlier message
            if message.get("postback", ''):
                pass
    return 'ok', 200


@site.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method.upper() == 'POST':
        return recieve()
    if request.method.upper() == 'GET':
        if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.challenge"):
            if request.args.get("hub.verify_token") == os.environ["VERIFY_TOKEN"]:
                return request.args['hub.challenge'], 200
            else:
                return "Verification token mismatch", 403

        return redirect(url_for('site.index'))


@site.route('/summary', methods=['POST'])
def summary():
    language = 'english'
    url = request.form.get('url', '')
    max_sent = int(request.form.get('max_sent', 10))
    tokenizer = Tokenizer(language)
    parser, meta = get_parser(url, tokenizer)
    summary = run_summarizer(parser, max_sent, language)
    session_data = dict(
        summary=summary,
        url=url,
        meta=meta,
        max_sent=max_sent
    )
    session.update(session_data)
    return redirect(url_for('site.index', _anchor='summary'))


@site.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           url=session.get('url'),
                           meta=session.get('meta'),
                           summary=session.get('summary'),
                           max_sent=session.get('max_sent'),
                           form=LinkForm())
