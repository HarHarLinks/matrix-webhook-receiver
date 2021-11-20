# Matrix Webhook Receiver [![Matrix](https://img.shields.io/matrix/matrix-webhook-receiver:matrix.org?logo=matrix&label=chat&server_fqdn=matrix.org&style=for-the-badge)](https://matrix.to/#/#matrix-webhook-receiver:matrix.org)

Companion "receiver" to [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) for [\[matrix\]](https://matrix.org).


Do you like to receive notifications from software you deploy in matrix?
Matrix Webhook Receiver (MWR) is an add-on for the [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) bridge. [Webhooks](https://en.wikipedia.org/wiki/Webhook) are essentially web interfaces for applications to "push" data to.
The bridge can receive messages in a certain format, which is nice if the notifying app can be configured. Often it cannot.

This is where MWR comes in:
It can receive any (JSON) content, optionally reformat it nicely (customizable!), and forward it to the webhooks bridge which will post it to a room for you. If you are running any software service, chances are it can notify you via webhooks!

![example screenshot](examples/github_screenshot.jpg)

## Installation

1. `git clone` this repo
2. create a virtual environment
3. `pip install -r requirements.txt`
4. run with `uvicorn main:app`

Alternatively with docker:
```shell
docker build --tag matrix-webhook-receiver:latest .
docker run --name matrix-webhook-receiver --mount "type=bind,src=$PWD/data,dst=/app/data" -p 8000:8000 matrix-webhook-receiver:latest
```

Use a reverse proxy to enable https and/or http basic auth. This is especially relevant for the `/set` and `/delete` endpoints, since otherwise the public can use your receiver. There is an [nginx example](examples/example.nginx.conf) for your convenience.

Set the environment variable `URL_PREFIX` if your reverse proxy is not serving the app at `/`, e.g. in the following case `URL_PREFIX="/webhooks"`.

Since this app is built with [FastAPI](https://fastapi.tiangolo.com), it also hosts its own documentation at `docs`, e.g. https://example.org/webhooks/docs.

## Usage

### Setup

To use this app, you need to create a profile first. I will assume Matrix-Webhook-Receiver is reachable at https://example.org/webhooks/.

I will demonstrate how to interact with the app using `curl` since that makes it obvious what is going on, but you can obviously substitute that for your favorite tool or app. One such possibility is to use the "Try It Out" feature of the docs.

1. get a webhook URL using [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) (`!webhook`). Tip: since matrix-appservice-webhooks does not support encryption (yet), use an unencrypted client like [matrix.sh](https://github.com/fabianonline/matrix.sh) to create webhooks for encrypted rooms.
2. make a POST request like the following: `curl -X POST --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.org/appservice-webhooks/api/v1/matrix/hook/","displayName":"Choose Wisely","avatar":"http://example.org/some-image.jpg","template":"{{ payload  }}","defaultFormat":"plain","defaultEmoji":true,"defaultMsgtype":"text"}' https://example.org/webhooks/set`
3. note the returned `whid`, you need it to POST messages later

`token` is the alphanumeric ID after the last `/` in your webhook URL.

`url` is the rest of the webhook URL, ending in `/`.

`displayName` can be freely chosen and will appear as the account posting your message to [matrix].

`avatar` is supposed to set the avatar of said account, but is currently broken upstream.

`template` (optional) is a [Jinja2](jinja2docs.readthedocs.io) template string. When Matrix-Webhook-Receiver receives a [post request](#post) and a template is installed in the profile, then the request body will be applied to the template and the result posted to matrix. This allows a profile to format a machine readable webhook body into a pretty human readable body. See below for [some examples](#example-templates).

`defaultFormat` (optional) sets the default value for `format` (`plain` or `html`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

`defaultEmoji` (optional) sets the default `emoji` conversion behaviour, see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

`defaultMsgtype` (optional) sets the default value `msgtype` (`plain`, `notice`, `emote`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

To update any info, repeat step 2 but add `"whid":"your-whid"` to the request body: `curl -X POST --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.org/appservice-webhooks/api/v1/matrix/hook/","displayName":"New Name","avatar":"http://example.org/some-image.jpg","whid":"your-whid"}' https://example.org/webhooks/set`.

#### Deleting profiles

To delete a profile, send a DELETE request like this: `curl -X DELETE https://example.org/webhooks/delete/your-whid`.

### Post

1. make a POST like the following, which can usually be done from most apps with a webhook feature: `curl --header 'Content-Type: application/json' --data '{"payload":"hello world"}' https:///example.org/webhooks/whid`. Don't forget to supply credentials if you set up authorization in your reverse proxy.
2. supply optional fields to diverge from your default profile settings: `curl --header 'Content-Type: application/json' --data '{"payload":":beetle:", "emoji":true, "msgtype":"notice"}' https:///example.org/webhooks/whid`

### Example Templates

Look at the Jinja2 templates for an impression of how the final message may look like in [matrix].
The same template is also used in the respective profile template. Fill it in and use with `curl --header 'Content-Type: application/json' --data "@template-name.json" https://example.org/webhooks/set` (add `--user name:password` or similar for your basic auth).

- Ansible Tower/AWX Notifications (Webhook with default messages): [Jinja2 template](examples/ansible-tower.jinja2), [profile template](examples/ansible-tower.json)
- GitLab (webhook):[Jinja2 template](examples/gitlab.jinja2), [profile template](examples/gitlab.json)
- GitHub (webhook): [Jinja2 template](examples/github.jinja2), [profile template](examples/github.json)
- Grafana Alerts (webhook): [Jinja2 template](examples/grafana.jinja2), [profile template](examples/grafana.json)
- submit yours!
