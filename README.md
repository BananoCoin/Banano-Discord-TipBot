# BANANO Tip Bot

BANANO Tip Bot is an open source, free to use nano tip bot for discord.

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
- BANANO Node v10+
- `setuptools`
- `discord`
- `peewee`
- `asyncio`
- `pycurl`

