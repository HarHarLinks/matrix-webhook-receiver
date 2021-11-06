#!/usr/bin/env python

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
import requests
from typing import Optional
from fastapi import FastAPI, Response
from pydantic import BaseModel
import hashlib


engine = create_engine('sqlite:///data/db.sqlite3')
Base = declarative_base()

class Webhook(Base):
    __tablename__ = 'webhooks'

    whid = Column(String, primary_key=True)
    token = Column(String)
    url = Column(String)
    displayName = Column(String)
    avatar = Column(String)
    defaultFormat = Column(String)
    defaultEmoji = Column(Boolean)
    defaultMsgtype = Column(String)

class CreateWebhook(BaseModel):
    whid: Optional[str] = None
    token: str
    url: str
    displayName: str
    avatar: str
    defaultFormat: Optional[str] = 'plain' # or html
    defaultEmoji: Optional[bool] = True
    defaultMsgtype: Optional[str] = 'text' # or notice or emote

class Post(BaseModel):
    payload: str
    format: Optional[str] = None
    emoji: Optional[bool] = None
    msgtype: Optional[str] = None

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

app = FastAPI()

@app.post("/set", status_code=201)
def add(new_hook: CreateWebhook):
    whid = new_hook.whid
    if whid is None:
        whid = hashlib.sha256()
        whid.update(new_hook.token.encode('utf-8'))
        whid.update(new_hook.url.encode('utf-8'))
        whid.update(new_hook.displayName.encode('utf-8'))
        whid = whid.hexdigest()

    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()

    if webhook is None:
        session.add(Webhook(whid=whid, token=new_hook.token, url=new_hook.url, displayName=new_hook.displayName, avatar=new_hook.avatar, defaultFormat=new_hook.defaultFormat, defaultEmoji=new_hook.defaultEmoji, defaultMsgtype=new_hook.defaultMsgtype))
    else:
        webhook.token = new_hook.token
        webhook.url = new_hook.url
        webhook.displayName = new_hook.displayName
        webhook.avatar = new_hook.avatar
        webhook.defaultFormat = new_hook.defaultFormat
        webhook.defaultEmoji = new_hook.defaultEmoji
        webhook.defaultMsgtype = new_hook.defaultMsgtype

    session.commit()
    return {"whid": whid}

@app.delete("/delete/{whid}", status_code=204)
def delete(whid: str):
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()
    if webhook is not None:
        session.delete(webhook)
        session.commit()
    return Response(status_code=204)

@app.post("/{whid}")
def receive(whid: str, post: Post):
    # get data frame from db
    webhook = session.query(Webhook).filter_by(whid=whid).one_or_none()
    if webhook is None:
        return Response(status_code=404)

    data = {
        "text": post.payload,
        "format": webhook.defaultFormat if post.format is None else post.format,
        "displayName": webhook.displayName,
        "avatar_url": webhook.avatar,
        "emoji": webhook.defaultEmoji if post.emoji is None else post.emoji
    }
    if webhook.defaultMsgtype != 'plain':
        data['msgtype'] = webhook.defaultMsgtype
    if post.msgtype is not None:
        data['msgtype'] = post.msgtype

    response = requests.post(webhook.url + webhook.token, json=data)
    return response.json()
