# lexrpc
Python implementation of [AT Protocol](https://atproto.com/)'s [XRPC](https://atproto.com/specs/xrpc) + [Lexicon](https://atproto.com/guides/lexicon).

TODO:
* CI
* docs


API:

SCHEMA = {
  ...
}
feed = lexrpc.Client([SCHEMAS])
feed.call(''app.bsky.feed.getAuthorFeed', author='@example.com', limit=5)

server = lexrpc.Server([SCHEMAS])
server.method(
    'com.atproto.repo.createRecord'
    # did='did:plc:123',
    record={
        'text': 'I hereby post',
        'createdAt', '2022-11-05T20:33:00Z',
    })
