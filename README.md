# Matrix-Webhook-Receiver

Companion "receiver" to [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks).

The purpose of this app is to listen for generic webhook messages POSTed to a URI like https://example.com/mysecrettoken, repackage the content appropriately for matrix-appservice-webhooks, and POST it to there.

## Installation

`git clone` this repo, create a virtual environment, `pip install -r requirements.txt`. Run with `uvicorn main:app`.

Alternatively, `docker build --tag matrix-webhook-receiver:latest .` and `docker run --name matrix-webhook-receiver --mount "type=bind,src=$PWD/data,dst=/app/data" -p 8000:8000 matrix-webhook-receiver:latest`.

Use a reverse proxy to enable https and/or http basic auth. This is especially relevant for the `/set` and `/delete` endpoints, since otherwise the public can use your receiver.

## Usage

### Setup

To use this app, first create a profile. I will assume Matrix-Webhook-Receiver is reachable at https://example.com/webhooks/.

1. get a webhook URI using [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) (`!webhook`)
2. make a POST request like the following: `curl -X PUT --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.com/appservice-webhooks/api/v1/matrix/hook/","displayName":"Choose Wisely","avatar":"http://example.com/some-image.jpg","defaultFormat":"plain","defaultEmoji":true,"defaultMsgtype":"text"}' https://example.com/webhooks/set`
3. note the returned `whid`, you need it to POST messages later

`your-webhook-token` is the alphanumeric ID after the last `/` in your webhook URL. The value for `url` is the rest of that URL, ending in `/`.

`displayName` can be freely chosen and will appear as the account posting your message to matrix.

`avatar` is supposed to set the avatar of said account, but is currently broken upstream.

`defaultFormat` (optional) sets the default value for `format` (`plain` or `html`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

`defaultEmoji` (optional) sets the default `emoji` conversion behaviour, see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

`defaultMsgtype` (optional) sets the default value `msgtype` (`plain`, `notice`, `emote`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

The profile is identified by the `whid`. To update any info besides the token, repeat step 2 but add `"whid":"your-whid"` to the request body: `curl -X PUT --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.com/appservice-webhooks/api/v1/matrix/hook/","displayName":"New Name","avatar":"http://example.com/some-image.jpg","whid":"your-whid"}' https://example.com/webhooks/set`.

#### Deleting profiles

To delete a profile, send a DELETE request like this: `curl -X DELETE https://example.com/webhooks/delete/your-whid`.

### Post

1. make a POST like the following, which can usually be done from most apps with a webhook feature: `curl -v --header 'Content-Type: application/json' --data '{"payload":"hello world"}' https:///example.com/webhooks/whid`. Don't forget to supply credentials if you set up authorization in your reverse proxy.
2. supply optional fields to diverge from your default profile settings: `curl -v --header 'Content-Type: application/json' --data '{"payload":":beetle:", "emoji":true, "msgtype":"notice"}' https:///example.com/webhooks/whid`
