# NANO Tip Bot

NANO Tip Bot is an open source, free to use nano tip bot for discord.

Intended to operate in a similar manner to the old tip bot on nano's discord server, with some enhancements.

## Usage

To run the bot, update `settings.py` with nano wallet ID and discord bot ID+Token, then simply use:

```
python3 bot.py
```

or to run in background

```
nohup python3 bot.py &
```

## Dependencies (install using pip)

- Python 3.5+
- NANO Node v10+
- `setuptools`
- `discord`
- `peewee`
- `asyncio`
- `pycurl`

## Disclaimer

Banano TipBot for Reddit.
TipBot is still in beta testing and should be used for fun, at your own risk. Bugs may arise and we will fix them asap but we cannot refund any losses or invalid TX's. TipBot NEVER loses funds, funds are always returned to the sending accounts.
