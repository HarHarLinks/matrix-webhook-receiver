#!/usr/bin/env python

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import sessionmaker
import requests
from typing import Optional
from fastapi import FastAPI, Response
from pydantic import BaseModel


engine = create_engine('sqlite:///data/db.sqlite3')
Base = declarative_base()

class Webhook(Base):
    __tablename__ = 'webhooks'

    token = Column(String, primary_key=True)
    url = Column(String)
    displayName = Column(String)
    avatar = Column(String)
    defaultFormat = Column(String)
    emoji = Column(Boolean)
    msgtype = Column(String)

class CreateWebhook(BaseModel):
    token: str
    url: str
    displayName: str
    avatar: str
    defaultFormat: Optional[str] = 'plain' # or html
    emoji: Optional[bool] = True
    msgtype: Optional[str] = 'text' # or notice or emote

class Post(BaseModel):
    payload: str
    format: Optional[str] = None
    emoji: Optional[bool] = None
    msgtype: Optional[str] = None

Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

app = FastAPI()

@app.put("/new", status_code=201)
def add(new_hook: CreateWebhook):
    webhook = session.query(Webhook).filter_by(token=new_hook.token).one_or_none()
    if webhook is None:
        session.add(Webhook(token=new_hook.token, url=new_hook.url, displayName=new_hook.displayName, avatar=new_hook.avatar, defaultFormat=new_hook.defaultFormat, emoji=new_hook.emoji, msgtype=new_hook.msgtype))
    else:
        webhook.url = new_hook.url
        webhook.displayName = new_hook.displayName
        webhook.avatar = new_hook.avatar
        webhook.defaultFormat = new_hook.defaultFormat
        webhook.emoji = new_hook.emoji
        webhook.msgtype = new_hook.msgtype
    session.commit()
    return Response(status_code=201)

@app.post("/{token}")
def receive(token: str, post: Post):
    # get data frame from db
    webhook = session.query(Webhook).filter_by(token=token).one_or_none()
    if webhook is None:
        return Response(status_code=404)
    data = {
        "text": post.payload,
        "format": webhook.defaultFormat if post.format is None else post.format,
        "displayName": webhook.displayName,
        "avatar_url": webhook.avatar,
        "emoji": webhook.emoji if post.emoji is None else post.emoji
    }
    if webhook.msgtype != 'plain':
        data['msgtype'] = webhook.msgtype if post.msgtype is None else post.msgtype
    response = requests.post(webhook.url + webhook.token, json=data)
    return response.json()
