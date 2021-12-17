#!/usr/bin/env python

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
import requests
from typing import Optional
from fastapi import FastAPI, Response, Body, Request, Header
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, HttpUrl, stricturl
from urllib.parse import urlparse
import hashlib
import uuid
import os
import json
from jinja2 import Environment, DebugUndefined


engine = create_engine('sqlite:///data/db.sqlite3', connect_args={"check_same_thread": False})
Base = declarative_base()

class Webhook(Base):
    __tablename__ = 'webhooks'

    whid = Column(String, primary_key=True)
    token = Column(String)
    url = Column(String)
    displayName = Column(String)
    avatar = Column(String)
    template = Column(String)
    defaultFormat = Column(String)
    defaultEmoji = Column(Boolean)
    defaultMsgtype = Column(String)

class CreateWebhook(BaseModel):
    whid: Optional[str] = None
    token: str
    url: HttpUrl
    displayName: str
    template: Optional[str] = None
    avatar: Optional[stricturl(allowed_schemes={'http', 'https', 'mxc'})] = ''
    defaultFormat: Optional[str] = 'plain' # or html
    defaultEmoji: Optional[bool] = True
    defaultMsgtype: Optional[str] = 'plain' # or notice or emote

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

app = FastAPI(
    title="matrix-webhook-receiver",
    description="Companion receiver to matrix-appservice-webhooks for matrix.",
    version="1.1.0-rc.1",
    contact={
        "name": "HarHarLinks",
        "url": "https://github.com/HarHarLinks/matrix-webhook-receiver"
    },
    redoc_url=None,
    root_path=os.environ.get('URL_PREFIX', '')
)

jinja2_extensions=['jinja2.ext.loopcontrols']

@app.post('/set', status_code=201)
def add(new_hook: CreateWebhook, response: Response):
    # verify template is valid jinja2
    if new_hook.template is not None:
        env = Environment(extensions=jinja2_extensions)
        try:
            env.parse(new_hook.template)
        except SyntaxError:
            response.status_code = 400
            return "invalid Jinja2 syntax"

    # create new token/primary key if not passed
    whid = new_hook.whid
    if whid is None or whid == '':
        whid = hashlib.sha256()
        whid.update(str(uuid.uuid4()).encode('utf-8'))
        whid = whid.hexdigest()

    # if the token exists update the db, else insert
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()

    if webhook is None:
        session.add(Webhook(whid=whid,
                            token=new_hook.token,
                            url=str(new_hook.url),
                            displayName=new_hook.displayName,
                            avatar=str(new_hook.avatar),
                            template=new_hook.template,
                            defaultFormat=new_hook.defaultFormat,
                            defaultEmoji=new_hook.defaultEmoji,
                            defaultMsgtype=new_hook.defaultMsgtype))
    else:
        webhook.token = new_hook.token
        webhook.url = str(new_hook.url)
        webhook.displayName = new_hook.displayName
        webhook.avatar = str(new_hook.avatar)
        webhook.template = new_hook.template
        webhook.defaultFormat = new_hook.defaultFormat
        webhook.defaultEmoji = new_hook.defaultEmoji
        webhook.defaultMsgtype = new_hook.defaultMsgtype

    session.commit()
    return {"whid": whid}

@app.get('/profiles')
def get_profiles(accept: Optional[str] = Header(None)):
    print(accept)
    if accept is not None and 'application/json' in accept:
        webhooks = session.query(Webhook)
        for webhook in webhooks:
            if urlparse(url=webhook.avatar).scheme not in ['http', 'https', 'mxc']:
                print(f"not a url: {webhook.avatar}")
                webhook.avatar = ''
        return list(webhooks)
    else:
        with open('profiles.html', 'r') as htmlpage:
            return HTMLResponse(content=htmlpage.read())

@app.get('/profile/{whid}')
def get_profiles(whid: str):
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()
    if urlparse(url=webhook.avatar).scheme not in ['http', 'https', 'mxc']:
        print(f"not a url: {webhook.avatar}")
        webhook.avatar = ''
    return webhook

@app.delete('/delete/{whid}', status_code=204)
def delete(whid: str):
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()
    if webhook is not None:
        session.delete(webhook)
        session.commit()
    return Response(status_code=204)

@app.post('/{whid}')
def receive(whid: str, post: dict = Body(...)):
    # get data frame from db
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()
    if webhook is None:
        return Response(status_code=404)

    env = Environment(undefined=DebugUndefined, extensions=jinja2_extensions)

    if webhook.template is None or webhook.template == '':
        # sadly the bridge converts the first newline char
        # right after the first opening curly brace
        # into a <br> for some reason, which isn't great.
        # when we prefix the message as we do here, instead
        # the newline char before the code block is converted,
        # working around the upstream bug
        payload = f"raw message:\n<pre><code>{json.dumps(post, sort_keys=False, indent=4)}\n</code></pre>\n"
        post['format'] = 'html'
    else:
        template = env.from_string(webhook.template)
        payload = template.render(post)

    if len(payload) == 0:
        return Response(status_code=400)

    format = post.get('format') or webhook.defaultFormat
    if format not in ('plain', 'html'):
        template = env.from_string(format)
        format = template.render(post)

    avatar = None if urlparse(url=webhook.avatar).scheme not in ['http', 'https', 'mxc'] else webhook.avatar

    if webhook.defaultMsgtype != 'plain':
        msgtype = webhook.defaultMsgtype
    if post.get('msgtype') is not None:
        msgtype = post.get('msgtype')
    if msgtype is not None and msgtype not in ('text', 'notice', 'emote'):
        template = env.from_string(msgtype)
        msgtype = template.render(post)

    data = {
        "text": payload,
        "format": format,
        "displayName": webhook.displayName,
        "emoji": webhook.defaultEmoji if post.get('emoji') is None else post.get('emoji')
    }
    if avatar is not None:
        data['avatar_url'] = avatar
        data['avatarUrl'] = avatar
    if msgtype is not None:
        data['msgtype'] = msgtype

    response = requests.post(webhook.url + webhook.token, json=data)
    return response.json()
