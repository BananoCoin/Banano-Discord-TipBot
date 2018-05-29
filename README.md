# BananoBot++ (a BANANO currency Tip Bot for Discord)

BananoBot++ is an open source, free to use banano bot for discord.

A few of the features included in this bot:

- standard tipping (`ban`,`bansplit`)
- tipping all actively contributing users (`brain`)
- giveaways+raffles from individual sponsors or auto-started by the bot when pool reaches certain amount (`giveaway`,`donate`)
- individual statistics (`tipstats`)
- bot-wide statistics (`ballers`,`toptips`,`winners`)
- individual favorites list (`addfavorite`,`removefavorite`,`banfavorites`,`favorites`)
- Administration commands for specific users or roles (see `adminhelp`)
- Interactive help for user friendly-ness

And much more than listed here probably

## About

BananoBot++ is designed so that every tip is a real transaction on the BANANO network.

Some highlights:

- Transactions are queued and processed synchronously in a worker thread, while bot activity is handled in a main thread.
- User data, transactions, and all other persisted data is stored using the Peewee ORM with Sqlite
- Operates with a single BANANO wallet, with 1 account per user

Recommend using with a GPU/OpenCL configured node (or work peer) on busier discord servers due to POW calculation.

## Getting started

### Requirements

```
sudo apt install python3 python3-dev libcurl4-openssl-dev git
```

(Optional - to run with pm2)

```
sudo apt install npm nodejs
sudo npm install -g pm2
```

Note: python 3.6+ is required. On older distributions you may need to source a third party package.

### Cloning

```
cd ~
git clone https://github.com/BananoCoin/Banano-Discord-TipBot.git bananotipbot
```

### Set up BANANO Node

Reference the [Wiki](https://github.com/BananoCoin/banano/wiki) for directions on running your own node.
You may find additional support in the official [Banano Discord Server](https://chat.banano.co.in)

You need rpc_enable and enable_control set to 'true' in the config.json

### Create wallet for tip bot

```
docker <container_id> exec bananode --wallet_create
```

non-docker nodes:

```
/path/to/bananode --wallet_create
```

This will output your wallet ID (NOT the seed), copy this as you will need it for later

### Discord bot

Create discord bot and get client ID and token (also save both of these for the next step)

Guide written by somebody else https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token

### Configuration

```
cd bananotipbot
cp settings.py.example settings.py
```

Then open settings.py with any text editor and add your bot's client ID, token, and the wallet ID from earlier

### Virtualenv + python requirements

```
virtualenv -p python3.6 venv
source venv/bin/activate
pip install -r requirements.txt
```

### Running with PM2

```
pm2 start bot.py --interpreter=~/bananotipbot/venv/bin/python
pm2 save
```

### Running normally

```
venv/bin/python bot.py
```

or in background:

```
nohup venv/bin/python bot.py &
```

## Database backups

There exists a script in scripts/cron called `bananotipbotbackup`. Highly recommend you use this or something better to backup the tip bot database.

Simply toss the script in cron.hourly, crontab, cron.daily, whatever - and update the backup path and database path.

## Disclaimer

Use Banano TipBot at your own risk. Any losses incurred using tipbot cannot be refunded.
