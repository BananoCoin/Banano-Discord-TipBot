# BananoBot++ (a BANANO currency Tip Bot for Discord)

BananoBot++ is an open source, free to use banano tip bot for discord.

Based on Graham (https://github.com/bbedward/Graham_Nano_Tip_Bot)

A few of the features included in this bot:

- standard tipping (`ban`,`bansplit`)
- tipping all actively contributing users (`rain`)
- giveaways+raffles from individual sponsors or auto-started by the bot when pool reaches certain amount (`giveaway`,`tipgiveaway`)
- individual statistics (`tipstats`)
- bot-wide statistics (`ballers`,`toptips`,`winners`)
- individual favorites list (`addfavorite`,`removefavorite`,`tipfavorites`)
- Administration commands for specific users or roles (`tipban`/`tipunban`, `statsban/statsunban`, `settiptotal/settipcount`, `pause/unpause`)

## About

BananoBot++ is designed so that every tip is a real transaction on the BANANO network.

Some highlights:

- Transactions are queued and processed synchronously in a worker thread, while bot activity is handled in a main thread.
- User data, transactions, and all other persisted data is stored using the Peewee ORM with Sqlite
- Operates with a single BANANO wallet, with 1 account per user

Recommend using with a GPU/OpenCL configured node (or work peer) on busier discord servers due to POW calculation.

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

- Python 3.6+
- NANO Node v10+
- `discord.py` 1.0.0a (rewrite)
- `peewee`
- `asyncio`
- `pycurl`

## Disclaimer

TipBot is still in beta testing and should be used for fun, at your own risk. Bugs may arise and we will fix them asap but we cannot refund any losses or invalid TX's. TipBot NEVER loses funds, funds are always returned to the sending accounts.
