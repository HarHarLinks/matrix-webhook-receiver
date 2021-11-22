# Matrix Webhook Receiver [![Matrix](https://img.shields.io/matrix/matrix-webhook-receiver:matrix.org?logo=matrix&label=chat&server_fqdn=matrix.org&style=for-the-badge)](https://matrix.to/#/#matrix-webhook-receiver:matrix.org)

Companion "receiver" to [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) for [\[matrix\]](https://matrix.org).

Do you like to receive notifications in matrix?

Matrix Webhook Receiver (MWR) is an add-on for the [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) bridge. [Webhooks](https://en.wikipedia.org/wiki/Webhook) are essentially web interfaces for applications to "push" data to.
The bridge can receive messages in a certain format, which is nice if the notifying app can be configured. Often it cannot.

This is where MWR comes in:
It can receive any (JSON) content, optionally reformat it nicely (customizable!), and forward it to the webhooks bridge which will post it to a room for you. If you are running any software service, chances are it can notify you via webhooks!

![example screenshot](examples/github_screenshot.jpg)

# Installation

1. `git clone` this repo
2. create a virtual environment
3. `pip install -r requirements.txt`
4. run with `uvicorn main:app`

Alternatively with docker:
```shell
docker build --tag matrix-webhook-receiver:latest .
docker run --name matrix-webhook-receiver --mount "type=bind,src=$PWD/data,dst=/app/data" -p 8000:8000 matrix-webhook-receiver:latest
```

Use a reverse proxy to enable https and/or http basic auth. This is especially relevant for the profile management endpoints `/set`, `/delete/*`, `/profiles`, `/profile/*`, since otherwise anyone can edit your settings and send spam using your receiver. Any other endpoints should not require authentication since not all apps support it - your `whid` acts as authentication to post messages. There is an [nginx example](examples/example.nginx.conf) for your convenience.

Set the environment variable `URL_PREFIX` if your reverse proxy is serving the app somewhere else than `/`, e.g. in the following case `URL_PREFIX="/webhooks"`.

Since this app is built with [FastAPI](https://fastapi.tiangolo.com), it also hosts its own documentation at `docs`, e.g. https://example.org/webhooks/docs.

# Usage

## Profile Setup

To use this app, you need to create a profile first. An admin GUI is included for easy access: if your Matrix-Webhook-Receiver is reachable at https://example.org/webhooks/ then the admin GUI is at https://example.org/webhooks/profiles.

Choose an existing profile from the list at the top or create a new one. Don't forget to save and test after editing.

- `whid` (WebHookID) is the secret unique identifier for its profile and can be any (URL-encoded) string. If you don't include a `whid`, a new profile with a new `whid` will be created instead. To "edit" the `whid`, create a new profile with the new `whid` and delete the old one. It is possible to choose a custom `whid` upon profile creation, but take care: it also acts as a password for posting with that profile, so choose wisely and **keep it secret**.

- `token` is the alphanumeric ID after the last `/` in your webhook URL.

- `url` is the rest of the webhook URL, starting in `http://` or `https://` and ending in `/`.

- `displayName` can be freely chosen and will appear as the account posting your message to [matrix].

- `avatar` (optional, default: `None`) is supposed to set the avatar of said account (HTTP(S) URL to an image), but is currently [broken upstream](https://github.com/turt2live/matrix-appservice-webhooks/issues/72).

- `defaultFormat` (optional, default: `plain`) sets the default value for `format` (`plain` or `html`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

- `defaultEmoji` (optional, default: `True`) sets the default `emoji` conversion behaviour, see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

- `defaultMsgtype` (optional, default: `plain`) sets the default value `msgtype` (`plain`, `notice`, `emote`), see [upstream README](https://github.com/turt2live/matrix-appservice-webhooks).

- `template` (optional, default: `None`) is a [Jinja2](jinja2docs.readthedocs.io) template string. When Matrix-Webhook-Receiver receives a [post request](#post) and a template is installed in the profile, then the request body will be applied to the template and the result posted to matrix. This allows a profile to format a machine readable JSON webhook body into a pretty human readable message. Continue reading for [some examples](#example-templates).

To update a profile, select it from the list and load it, make your changes, and save. It is possible to copy a profile by loading it and deleting the `whid`.

### Profile Setup Using the JSON API (advanced)

If you want to manage profiles non-interactively, have a look at the automatic documentation (e.g. https://example.org/webhooks/docs) to learn what endpoint exist and accept what data.

I will quickly demonstrate how to interact with the app using `curl` since that makes it obvious what is going on, but you can substitute your favorite tool or app for that as long as it can POST JSON.

1. get a webhook URL using [matrix-appservice-webhooks](https://github.com/turt2live/matrix-appservice-webhooks) (`!webhook`). Tip: since matrix-appservice-webhooks does not support encryption (yet), use an unencrypted client like [matrix.sh](https://github.com/fabianonline/matrix.sh) to create webhooks for encrypted rooms.
2. make a POST request like the following:
```shell
curl -X POST --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.org/appservice-webhooks/api/v1/matrix/hook/","displayName":"Choose Wisely","avatar":"http://example.org/some-image.jpg","defaultFormat":"plain","defaultEmoji":true,"defaultMsgtype":"text"}' https://example.org/webhooks/set
```

3. note the returned `whid`, you need it to POST messages later
4. to delete a profile, send a DELETE request like this: `curl -X DELETE https://example.org/webhooks/delete/your-whid`.
5. to update any info, repeat step 2 but add `"whid":"your-whid"` to the request body:
```shell
curl -X POST --header 'Content-Type: application/json' --data '{"token":"your-webhook-token","url":"https://matrix.example.org/appservice-webhooks/api/v1/matrix/hook/","displayName":"New Name","avatar":"http://example.org/some-image.jpg","whid":"your-whid"}' https://example.org/webhooks/set
```

## Post

Now you are ready to go! Grab your `whid` and enter it into your app's webhook settings as the target/payload URL. Set content type to application/json if needed.

No secret or authorization is required unless your setup exceeds the settings mentioned above.

### Post Manually/Custom

1. make a POST like the following: `curl --header 'Content-Type: application/json' --data '{"payload":"hello world"}' https://example.org/webhooks/whid`. Don't forget to supply credentials if you set up authorization in your reverse proxy.
2. supply optional fields to diverge from your default profile settings: `curl --header 'Content-Type: application/json' --data '{"payload":":beetle:", "emoji":true, "msgtype":"notice"}' https://example.org/webhooks/whid`

## Example Templates

Look at the Jinja2 templates for an impression of how the final message may look like in [matrix].
The same template is also used in the respective profile template. Fill it in and use with `curl --header 'Content-Type: application/json' --data "@template-name.json" https://example.org/webhooks/set` (add `--user name:password` or similar for your basic auth).

- Ansible Tower/AWX Notifications (Webhook with default messages): [Jinja2 template](examples/ansible-tower.jinja2), [profile template](examples/ansible-tower.json)
- GitLab (webhook):[Jinja2 template](examples/gitlab.jinja2), [profile template](examples/gitlab.json)
- GitHub (webhook): [Jinja2 template](examples/github.jinja2), [profile template](examples/github.json)
- Grafana Alerts (webhook): [Jinja2 template](examples/grafana.jinja2), [profile template](examples/grafana.json)
- submit yours!
