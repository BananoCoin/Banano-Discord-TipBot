import discord
from discord.ext import commands
from discord.ext.commands import Bot
from aiohttp import ClientError
from asyncio import TimeoutError
import random
import secrets
import collections
import random
import re
import errno
import asyncio
import uuid
import datetime
import time

import wallet
import util
import settings
import db
import paginator

logger = util.get_logger("main")

BOT_VERSION = "2.5"

# How many users to display in the top users count
TOP_TIPPERS_COUNT=15
# How many previous giveaway winners to display
WINNERS_COUNT=10
# Minimum Amount for !rain
RAIN_MINIMUM = settings.rain_minimum
# Minimum Amount for !rolesoak
ROLESOAK_MINIMUM = settings.rolesoak_minimum
# Minimum amount for !startgiveaway
GIVEAWAY_MINIMUM = settings.giveaway_minimum
# Giveaway duration
GIVEAWAY_MIN_DURATION = 5
GIVEAWAY_MAX_DURATION = settings.giveaway_max_duration
GIVEAWAY_AUTO_DURATION = settings.giveaway_auto_duration
# Rain Delta (Minutes) - How long to look back for active users for !rain
RAIN_DELTA=30
# Spam Threshold (Seconds) - how long to output certain commands (e.g. bigtippers)
SPAM_THRESHOLD=60
# Send Job (seconds) - process send transactions at this interval
SEND_JOB=10
# Receive check job (seconds) - checks for pending transactions and pockets them
RECEIVE_CHECK_JOB=300
# MAX TX_Retries - If wallet does not indicate a successful send for whatever reason, retry this many times
MAX_TX_RETRIES=3
# Change command prefix to whatever you want to begin commands with
COMMAND_PREFIX=settings.command_prefix
# Withdraw cooldown - how long must wait until wirhdraws
WITHDRAW_COOLDOWN=300
# Pool giveaway auto amount (1%)
TIPGIVEAWAY_AUTO_ENTRY=int(.01 * GIVEAWAY_MINIMUM)

# HELP menu header
AUTHOR_HEADER="BananoBot++ v{0} (BANANO Tip Bot)".format(BOT_VERSION)

# Command DOC (TRIGGER, CMD, Overview, Info)
'''
TRIGGER: Users can get information about this command specifically via help $TRIGGER
CMD: Command overview for help doc
OVERVIEW: General overview of command for overview of command listings
INFO: Detailed command usage/examples/information/etc.
'''

def get_aliases(dict, exclude=''):
	'''Returns list of command triggers excluding `exclude`'''
	cmds = dict["TRIGGER"]
	ret_cmds = []
	for cmd in cmds:
		if cmd != exclude:
			ret_cmds.append(cmd)
	return ret_cmds

### All commands

BALANCE = {
		"TRIGGER"  : ["balance", "bal", "$"],
		"CMD"      : "{0}balance".format(COMMAND_PREFIX),
		"OVERVIEW" : "Display balance of your account",
		"INFO"     : ("Displays the balance of your tip account (in BANANO) as described:" +
				"\nActual Balance: The actual balance in your tip account" +
				"\nAvailable Balance: The balance you are able to tip with (Actual - Pending Send)" +
				"\nPending Send: Tips you have sent, but have not yet been broadcasted to network" +
				"\nPending Receipt: Tips that have been sent to you, but have not yet been pocketed by the node. " +
				"\nPending funds will be available for tip/withdraw after they have been pocketed by the node")
}

DEPOSIT ={
		"TRIGGER"  : ["deposit", "register", "wallet", "address"],
		"CMD"      : "{0}deposit or {0}register or {0}wallet or {0}address".format(COMMAND_PREFIX),
		"OVERVIEW" : "Shows your account address",
		"INFO"     : ("Displays your tip bot account address along with a Link to the blockchain explorer" +
				"\n- Send BANANO to this address to increase your tip bot balance" +
				"\n- If you do not have a tip bot account yet, this command will create one for you (receiving a tip automatically creates an account too)")
}

WITHDRAW = {
		"TRIGGER"  : ["withdraw"],
		"CMD"      : "{0}withdraw, takes: address (optional amount)".format(COMMAND_PREFIX),
		"OVERVIEW" : "Allows you to withdraw from your tip account",
		"INFO"     : ("Withdraws specified amount to specified address, " +
				"if amount isn't specified your entire tip account balance will be withdrawn" +
				"\nExample: `{0}withdraw ban_133711111111111111111111111111111111111111111111111hifc8npp 1000` - Withdraws 1000 BANANO").format(COMMAND_PREFIX)
}

TIP = {
		"TRIGGER"  : ["ban", "b"],
		"CMD"      : "{0}ban, takes: amount <*users>".format(COMMAND_PREFIX),
		"OVERVIEW" : "Send a tip to mentioned users",
		"INFO"     : ("Tip specified amount to mentioned user(s) (minimum tip is 1 BANANO)" +
		"\nThe recipient(s) will be notified of your tip via private message" +
		"\nSuccessful tips will be deducted from your available balance immediately" +
		"\nExample: `{0}ban 2 @user1 @user2` would send 2 to user1 and 2 to user2").format(COMMAND_PREFIX)
}

TIPSPLIT = {
		"TRIGGER"  : ["bansplit", "bsplit", "bs"],
		"CMD"      : "{0}bansplit, takes: amount, <*users>".format(COMMAND_PREFIX),
		"OVERVIEW" : "Split a tip among mentioned uses",
		"INFO"     : "Distributes a tip evenly to all mentioned users.\nExample: `{0}bansplit 2 @user1 @user2` would send 1 to user1 and 1 to user2".format(COMMAND_PREFIX)
}

TIPRANDOM = {
		"TRIGGER"  : ["banrandom", "br"],
		"CMD"      : "{0}banrandom, takes: amount".format(COMMAND_PREFIX),
		"OVERVIEW" : "Tips a random active user",
		"INFO"     : ("Tips amount to a random active user. Active user list picked using same logic as brain" +
				"\n**Minimum banrandom amount: {0} BANANO**").format(settings.tiprandom_minimum)
}

RAIN = {
		"TRIGGER"  : ["brain"],
		"CMD"      : "{0}brain, takes: amount".format(COMMAND_PREFIX),
		"OVERVIEW" : "Split tip among all active* users",
		"INFO"     : ("Distribute <amount> evenly to users who are eligible.\n" +
				"Eligibility is determined based on your *recent* activity **and** contributions to public channels. " +
				"Several factors are considered in picking who receives brain. If you aren't receiving it, you aren't contributing enough or your contributions are low-quality/spammy.\n" +
				"Note: Users who have a status of 'offline' or 'do not disturb' do not receive brain.\n" +
				"Example: `{0}brain 1000` - distributes 1000 evenly to eligible users (similar to `bansplit`)" +
				"\n**Minimum brain amount: {1} BANANO**").format(COMMAND_PREFIX, RAIN_MINIMUM)
}

ROLESOAK = {	"TRIGGER"  : ["bancitizens", "tc"],
		"CMD"      : "{0}bancitizens, takes: amount".format(COMMAND_PREFIX),
		"OVERVIEW" : "Rain across to all citizens",
		"INFO"     : ("Distribute amount evenly to users who are citizens and have been active relatively recently.\n" +
				"Example: `{0}bancitizens 1000` - distributes 1000 evenly to users in Citizens role (similar to `brain`)" +
				"\n**Minimum bancitizens amount: {1} BANANO**").format(COMMAND_PREFIX, ROLESOAK_MINIMUM)
}

START_GIVEAWAY = {
		"TRIGGER"  : ["giveaway", "sponsorgiveaway"],
		"CMD"      : "{0}giveaway, takes: amount, fee=(amount), duration=(minutes)".format(COMMAND_PREFIX),
		"OVERVIEW" : "Sponsor a giveaway",
		"INFO"     : ("Start a giveaway with given amount, entry fee, and duration." +
				"\nEntry fees are added to the total prize pool" +
				"\nGiveaway will end and choose random winner after (duration)" +
				"\nExample: `{0}giveaway 1000 fee=5 duration=30` - Starts a giveaway of 1000, with fee of 5, duration of 30 minutes" +
				"\n**Minimum required to sponsor a giveaway: {1} BANANO**" +
				"\n**Minimum giveaway duration: {2} minutes**" +
				"\n**Maximum giveaway duration: {3} minutes**").format(COMMAND_PREFIX, GIVEAWAY_MINIMUM, GIVEAWAY_MIN_DURATION, GIVEAWAY_MAX_DURATION)
}

ENTER = {
		"TRIGGER"  : ["ticket", "enter", "e"],
		"CMD"      : "{0}ticket, takes: fee (conditional)".format(COMMAND_PREFIX),
		"OVERVIEW" : "Enter the current giveaway",
		"INFO"     : ("Enter the current giveaway, if there is one. Takes (fee) as argument only if there's an entry fee." +
				"\n Fee will go towards the prize pool and be deducted from your available balance immediately" +
				"\nExample: `{0}ticket` (to enter a giveaway without a fee), `{0}ticket 10` (to enter a giveaway with a fee of 10)").format(COMMAND_PREFIX)
}

TIPGIVEAWAY = {
		"TRIGGER"  : ["donate", "tipgiveaway", "d"],
		"CMD"      : "{0}donate, takes: amount".format(COMMAND_PREFIX),
		"OVERVIEW" : "Add to present or future giveaway prize pool",
		"INFO"     : ("Add <amount> to the current giveaway pool\n"+
				"If there is no giveaway, one will be started when minimum is reached." +
				"\nTips >= {0} BANANO automatically enter you for giveaways sponsored by the community." +
				"\nDonations count towards the next giveaways entry fee" +
				"\nExample: `{1}donate 1000` - Adds 1000 to giveaway pool").format(TIPGIVEAWAY_AUTO_ENTRY, COMMAND_PREFIX)
}

TICKETSTATUS = {
		"TRIGGER"  : ["ticketstatus", "ts"],
		"CMD"      : "{0}ticketstatus".format(COMMAND_PREFIX),
		"OVERVIEW" : "Check if you are entered into the current giveaway",
		"INFO"     : "Check if you are entered into the current giveaway"
}

GIVEAWAY_STATS= {
		"TRIGGER"  : ["gstats", "giveawaystats", "gs", "giveawaystatus", "gstatus"],
		"CMD"      : "{0}giveawaystats or {0}goldenticket".format(COMMAND_PREFIX),
		"OVERVIEW" : "Display statistics relevant to the current giveaway",
		"INFO"     : "Display statistics relevant to the current giveaway"
}

WINNERS = {
		"TRIGGER"  : ["winners"],
		"CMD"      : "{0}winners".format(COMMAND_PREFIX),
		"INFO"     : "Display previous giveaway winners",
		"OVERVIEW" : "Display previous giveaway winners"
}

LEADERBOARD = {
		"TRIGGER"  : ["leaderboard", "ballers", "bigtippers"],
		"CMD"      : "{0}leaderboard or {0}ballers".format(COMMAND_PREFIX),
		"INFO"     : "Display the all-time tip leaderboard",
		"OVERVIEW" : "Display the all-time tip leaderboard"
}

TOPTIPS = {
		"TRIGGER"  : ["toptips"],
		"CMD"      : "{0}toptips".format(COMMAND_PREFIX),
		"OVERVIEW" : "Display largest individual tips",
		"INFO"     : "Display the single largest tips for the past 24 hours, current month, and all time"
}

STATS = {
		"TRIGGER"  : ["tipstats"],
		"CMD"      : "{0}tipstats".format(COMMAND_PREFIX),
		"OVERVIEW" : "Display your personal tipping stats",
		"INFO"     : "Display your personal tipping stats (rank, total tipped, and average tip)"
}

ADD_FAVORITE = {
		"TRIGGER"  : ["addfav", "addfavorite", "addfavourite"],
		"CMD"      : "{0}addfavorite, takes: *users".format(COMMAND_PREFIX),
		"OVERVIEW" : "Add users to your favorites list",
		"INFO"     : "Adds mentioned users to your favorites list.\nExample: `{0}addfavorite @user1 @user2 @user3` - Adds user1,user2,user3 to your favorites".format(COMMAND_PREFIX)
}

DEL_FAVORITE = {
		"TRIGGER"  : ["removefavorite", "removefavourite", "removefav"],
		"CMD"      : "{0}removefavorite, takes: *users or favorite ID".format(COMMAND_PREFIX),
		"OVERVIEW" : "Removes users from your favorites list",
		"INFO"     : ("Removes users from your favorites list. " +
				"You can either @mention the user in a public channel or use the ID in your `favorites` list" +
				"\nExample 1: `{0}removefavorite @user1 @user2` - Removes user1 and user2 from your favorites" +
				"\nExample 2: `{0}removefavorite 1 6 3` - Removes favorites with ID : 1, 6, and 3").format(COMMAND_PREFIX)
}

FAVORITES = {
		"TRIGGER"  : ["favorites", "favs", "favourites"],
		"CMD"      : "{0}favorites".format(COMMAND_PREFIX),
		"OVERVIEW" : "View your favorites list",
		"INFO"     : "View your favorites list. Use `{0}addfavorite` to add favorites to your list and `{0}removefavorite` to remove favories".format(COMMAND_PREFIX)
}

TIP_FAVORITES = {
		"TRIGGER"  : ["tipfavs", "tipfavorites", "tipfavourites", "tf"],
		"CMD"      : "{0}tipfavorites, takes: amount".format(COMMAND_PREFIX),
		"OVERVIEW" : "Tip your entire favorites list",
		"INFO"     : ("Tip everybody in your favorites list specified amount" +
				"\nExample: `{0}tipfavorites 1000` Distributes 1000 to your entire favorites list (similar to `tipsplit`)").format(COMMAND_PREFIX)
}

MUTE = {
		"TRIGGER"  : ["mute"],
		"CMD"      : "{0}mute, takes: user id".format(COMMAND_PREFIX),
		"OVERVIEW" : "Block tip notifications when sent by this user",
		"INFO"     : "When someone is spamming you with tips and you can't take it anymore"
}

UNMUTE = {
		"TRIGGER"  : ["unmute"],
		"CMD"      : "{0}unmute, takes: user id".format(COMMAND_PREFIX),
		"OVERVIEW" : "Unblock tip notificaitons sent by this user",
		"INFO"     : "When the spam is over and you want to know they still love you"
}

MUTED = {
		"TRIGGER"  : ["muted"],
		"CMD"      : "{0}muted".format(COMMAND_PREFIX),
		"OVERVIEW" : "View list of users you have muted",
		"INFO"     : "Are you really gonna drunk dial?"
}

### ADMIN-only commands
FREEZE = {
		"CMD"      : "{0}freeze, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Suspends every action from user, including withdraw"
}

UNFREEZE = {
		"CMD"      : "{0}unfreeze, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Unfreezes mentioned user"
}

FROZEN = {
		"CMD"	   : "{0}frozen".format(COMMAND_PREFIX),
		"INFO"     : "List frozen users"
}

WALLET_FOR = {
		"CMD"      : "{0}walletfor, takes: user".format(COMMAND_PREFIX),
		"INFO"     : "Returns wallet address for mentioned user"
}

USER_FOR_WALLET = {
		"CMD"      : "{0}userforwallet, takes: address".format(COMMAND_PREFIX),
		"INFO"     : "Returns user owning wallet address"
}

PAUSE = {
		"CMD"      : "{0}pause".format(COMMAND_PREFIX),
		"INFO"     : "Pause all transaction-related activity"
}

UNPAUSE = {
		"CMD"      : "{0}unpause".format(COMMAND_PREFIX),
		"INFO"     : "Resume all transaction-related activity"
}

TIPBAN = {
		"CMD"      : "{0}tipban, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Makes it so mentioned users can no longer receive tips"
}

TIPUNBAN = {
		"CMD"      : "{0}tipunban, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Makes it so mentioned users can receive tips again"
}

BANNED = {
		"CMD"      : "{0}banned".format(COMMAND_PREFIX),
		"INFO"     : "View list of users currently tip banned"
}

STATSBAN = {
		"CMD"      : "{0}statsban, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Bans mentioned users from all stats consideration"
}

STATSUNBAN = {
		"CMD"      : "{0}statsunban, takes: users".format(COMMAND_PREFIX),
		"INFO"     : "Unbans mentioned users from stats considerations"
}

STATSBANNED = {
		"CMD"      : "{0}statsbanned".format(COMMAND_PREFIX),
		"INFO"     : "View list of stats banned users"
}

INCREASETIPTOTAL = {
		"CMD"      : "{0}increasetips (amount) (user)".format(COMMAND_PREFIX),
		"INFO"     : "Increases users tip total by (amount), for stats purposes"
}

DECREASETIPTOTAL = {
		"CMD"      : "{0}decreasetips (amount) (user)".format(COMMAND_PREFIX),
		"INFO"     : "Decreases users tip total by (amount), for stats purposes"
}

SETTOPTIP = {
		"CMD"      : "{0}settoptip".format(COMMAND_PREFIX),
		"INFO"     : ("Allows you to set a users top tips. You can set 1 or all of monthly, 24h, and all-time " +
				"toptips.\n Example: \n `settoptip @user alltime=2.38 month=1.23 day=0.5` " +
				"sets @user's biggest alltime tip to 2.38 BANANO, month to 1.23 BANANO, and day to 0.5 BANANO")
}

INCREASETIPCOUNT = {
		"CMD"      : "{0}increasetipcount (amount) (user)".format(COMMAND_PREFIX),
		"INFO"     : "Increases the number of tips a user has made (used for average TIP)"
}

DECREASETIPCOUNT = {
		"CMD"      : "{0}decreasetipcount (amount) (user)".format(COMMAND_PREFIX),
		"INFO"     : "Decreases the number of tips a user has made (used for average TIP)"
}

COMMANDS = {
		"ACCOUNT_COMMANDS"      : [BALANCE, DEPOSIT, WITHDRAW],
		"TIPPING_COMMANDS"      : [TIP, TIPSPLIT, TIPRANDOM, RAIN, ROLESOAK],
		"GIVEAWAY_COMMANDS"     : [START_GIVEAWAY, ENTER, TIPGIVEAWAY, TICKETSTATUS],
		"STATISTICS_COMMANDS"   : [GIVEAWAY_STATS, WINNERS, LEADERBOARD, TOPTIPS,STATS],
		"FAVORITES_COMMANDS"    : [ADD_FAVORITE, DEL_FAVORITE, FAVORITES, TIP_FAVORITES],
		"NOTIFICATION_COMMANDS" : [MUTE, UNMUTE, MUTED],
		"ADMIN_COMMANDS"	: [FREEZE, UNFREEZE, FROZEN, USER_FOR_WALLET, WALLET_FOR, PAUSE, UNPAUSE, TIPBAN, TIPUNBAN, BANNED, STATSBAN, STATSUNBAN, STATSBANNED, INCREASETIPTOTAL, DECREASETIPTOTAL, SETTOPTIP, INCREASETIPCOUNT, DECREASETIPCOUNT]
}

### Response Templates###

# balance
BALANCE_TEXT=(	"```Actual Balance   : {0:,.2f} BANANO\n" +
		"Available Balance: {1:,.2f} BANANO\n" +
		"Pending Send     : {2:,.2f} BANANO\n" +
		"Pending Receipt  : {3:,.2f} BANANO```")

# deposit (split into 3 for easy copypasting address on mobile)
DEPOSIT_TEXT="Your wallet address is:"
DEPOSIT_TEXT_2="{0}"
DEPOSIT_TEXT_3=":Account history and QR code: https://creeper.banano.cc/explorer/account/{0}"

# generic tip replies (apply to numerous tip commands)
INSUFFICIENT_FUNDS_TEXT="You don't have enough BANANO in your available balance!"
TIP_RECEIVED_TEXT="You were tipped {0} BANANO by {1}. You can mute tip notifications from this person using `" + COMMAND_PREFIX + "mute {2}`"
TIP_SELF="No valid recipients found in your tip.\n(You cannot tip yourself and certain other users are exempt from receiving tips)"

# withdraw
WITHDRAW_SUCCESS_TEXT="Withdraw has been queued for processing, I'll send you a link to the transaction after I've broadcasted it to the network!"
WITHDRAW_PROCESSED_TEXT="Withdraw processed:\nTransaction: https://creeper.banano.cc/explorer/block/{0}\nIf you have an issue with a withdraw please wait **24 hours** before contacting my master."
WITHDRAW_NO_BALANCE_TEXT="You have no BANANO to withdraw"
WITHDRAW_INVALID_ADDRESS_TEXT="Withdraw address is not valid"
WITHDRAW_COOLDOWN_TEXT="You need to wait {0} seconds before making another withdraw"
WITHDRAW_INSUFFICIENT_BALANCE="Your balance isn't high enough to withdraw that much"

# leaderboard
TOP_HEADER_TEXT="Here are the top {0} tippers :clap:"
TOP_HEADER_EMPTY_TEXT="The leaderboard is empty!"
TOP_SPAM="No more big tippers for {0} seconds"

# tipstats (individual)
STATS_ACCT_NOT_FOUND_TEXT="I could not find an account for you, try private messaging me `{0}register`".format(COMMAND_PREFIX)
STATS_TEXT="You are rank #{0}, you've tipped a total of {1:.2f} BANANO, your average tip is {2:.2f} BANANO, and your biggest tip of all time is {3:.2f} BANANO"

# tipsplit
TIPSPLIT_SMALL="Tip amount is too small to be distributed to that many users"

# rain
RAIN_NOBODY="I couldn't find anybody eligible to receive rain"

# giveaway (all giveaway related commands)
GIVEAWAY_EXISTS="There's already an active giveaway"
GIVEAWAY_STARTED="{0} has sponsored a giveaway of {1:.2f} BANANO! Use:\n - `" + COMMAND_PREFIX + "ticket` to enter\n - `" + COMMAND_PREFIX + "donate` to increase the pot\n - `" + COMMAND_PREFIX + "ticketstatus` to check the status of your entry"
GIVEAWAY_STARTED_FEE="{0} has sponsored a giveaway of {1:.2f} BANANO! The entry fee is {2} BANANO. Use:\n - `" + COMMAND_PREFIX + "ticket {2}` to buy your ticket\n - `" + COMMAND_PREFIX + "donate` to increase the pot\n - `" + COMMAND_PREFIX + "ticketstatus` to check the status of your entry"
GIVEAWAY_FEE_TOO_HIGH="A giveaway has started where the entry fee is higher than your donations! Use `{0}ticketstatus` to see how much you need to enter!".format(COMMAND_PREFIX)
GIVEAWAY_MAX_FEE="Giveaway entry fee cannot be more than 5% of the prize pool"
GIVEAWAY_ENDED="Congratulations! <@{0}> was the winner of the giveaway! They have been sent {1:.2f} BANANO!"
GIVEAWAY_STATS_NF="There are {0} entries to win {1:.2f} BANANO ending in {2} - sponsored by {3}.\nUse:\n - `" + COMMAND_PREFIX + "ticket` to enter\n - `" + COMMAND_PREFIX + "donate` to add to the pot\n - `" + COMMAND_PREFIX + "ticketstatus` to check status of your entry"
GIVEAWAY_STATS_FEE="There are {0} entries to win {1:.2f} BANANO ending in {2} - sponsored by {3}.\nEntry fee: {4} BANANO. Use:\n - `" + COMMAND_PREFIX + "ticket {4}` to enter\n - `" + COMMAND_PREFIX + "donate` to add to the pot\n - `" + COMMAND_PREFIX + "ticketstatus` to check the status of your entry"
GIVEAWAY_STATS_INACTIVE="There are no active giveaways\n{0} BANANO required to to automatically start one! Use\n - `" + COMMAND_PREFIX + "donate` to donate to the next giveaway.\n - `" + COMMAND_PREFIX + "giveaway` to sponsor your own giveaway\n - `" + COMMAND_PREFIX + "ticketstatus` to see how much you've already donated to the next giveaway"
ENTER_ADDED="You've been successfully entered into the giveaway"
ENTER_DUP="You've already entered the giveaway"
TIPGIVEAWAY_NO_ACTIVE="There are no active giveaways. Check giveaway status using `{0}giveawaystats`, or donate to the next one using `{0}tipgiveaway`".format(COMMAND_PREFIX)
TIPGIVEAWAY_ENTERED_FUTURE="With your bantastic donation I have reserved your ticket for the next community sponsored giveaway!"

# toptips
TOPTIP_SPAM="No more top tips for {0} seconds"

# admin command responses
PAUSE_MSG="All transaction activity is currently suspended. Check back later."
BAN_SUCCESS="User {0} can no longer receive tips"
BAN_DUP="User {0} is already banned"
UNBAN_SUCCESS="User {0} has been unbanned"
UNBAN_DUP="User {0} is not banned"
STATSBAN_SUCCESS="User {0} is no longer considered in tip statistics"
STATSBAN_DUP="User {0} is already stats banned"
STATSUNBAN_SUCCESS="User {0} is now considered in tip statistics"
STATSUNBAN_DUP="User {0} is not stats banned"

# past giveaway winners
WINNERS_HEADER="Here are the previous {0} giveaway winners! :trophy:".format(WINNERS_COUNT)
WINNERS_EMPTY="There are no previous giveaway winners"
WINNERS_SPAM="No more winners for {0} seconds"

# Banano-discord
RIGHTS="```You have been arrested by the BRPD for crimes against the Banano Republic. You have the right to remain unripe. Anything you say can and will be used against you in a banano court. You have the right to have an orangutan. If you cannot afford one, one will be appointed to you by the court. Until your orangutan arrives, you will spend your time in #jail, bail is set at 10 BANANO.```"
RELEASE="```You have been released from Jail!```"
CITIZENSHIP="```I hereby declare you a Citizen of the Banano Republic, may the Banano gods grant you all things which your heart desires.```"
DEPORT="```I hereby withdraw your Citizenship to the Banano Republic, we don’t want to talk to you no more, you empty-headed animal-food-trough wiper. We fart in your general direction. Your mother was a hamster, and your father smelt of elderberries.```"
TROLL="```You have been marked as a TROLL and are no longer a Citizen in the Banano Republic```"
UNTROLL="```You are no longer known as a TROLL in the Banano Republic, please reapply for Citizenship.```"
FROZEN_MSG="Your account is frozen. Contact an admin for help"
### END Response Templates ###

# Paused flag, indicates whether or not bot is paused
paused = False

# Create discord client
client = Bot(command_prefix=COMMAND_PREFIX)
client.remove_command('help')

# Receive check job to pocket transactions
async def receive_check_job():
	try:
		logger.info("Running receive job...")
		accts = []
		cursor = db.User.select(db.User.wallet_address)
		for a in cursor:
			accts.append(a.wallet_address)
		accts_pending_action = {
			"action":"accounts_pending",
			"accounts":accts,
			"threshold":100000000000000000000000000000
		}
		response = await wallet.communicate_wallet_async(accts_pending_action)
		if response is None:
			response = 'None'
		if 'blocks' not in response:
			logger.error('invalid response %s. Rescheduling job', str(response))
			await schedule_receive_job()
			return
		for account, blocks in response['blocks'].items():
			for b in blocks:
				logger.info('Receiving block %s for account %s', b, account)
				receive_action = {
					"action":"receive",
					"wallet":settings.wallet,
					"account":account,
					"block":b
				}
				rcv_response = await wallet.communicate_wallet_async(receive_action)
				if rcv_response is None:
					rcv_response='None'
				if 'block' not in rcv_response:
					logger.info("Couldn't receive %s - response: %s", b, str(rcv_response))
				else:
					logger.info("pocketed block %s", b)
		logger.info("receive job complete")
		await schedule_receive_job()
	except (ClientError, TimeoutError):
		logger.info("aiohttp error, rescheduling receive_job")
		await schedule_receive_job()
	except Exception as e:
		logger.exception(e)

async def schedule_receive_job():
	await asyncio.sleep(RECEIVE_CHECK_JOB)
	asyncio.get_event_loop().create_task(receive_check_job())

# TODO
# Would be nice to spawn multiple threads of this at one time.
# Mainly the work_generate process would be nice to multithread

# This isn't as un-optimized as it seems
# Yes a send is a long-running task due to work_generate
# Yes we are not achieving "true" multithreading/multiprocessing with asyncio
# But, the long-running job (work_generate) is executed outside of this program

async def send_job():
	try:
		logger.info("send_job started")
		txs = db.get_unprocessed_transactions()
		for tx in txs:
			source_address = tx['source_address']
			to_address = tx['to_address']
			amount = tx['amount']
			uid = tx['uid']
			attempts = tx['attempts']
			raw_withdraw_amt = str(amount) + '00000000000000000000000000000'
			wallet_command = {
				'action': 'send',
				'wallet': settings.wallet,
				'source': source_address,
				'destination': to_address,
				'amount': int(raw_withdraw_amt),
				'id': uid
			}
			src_usr = db.get_user_by_wallet_address(source_address)
			trg_usr = db.get_user_by_wallet_address(to_address)
			source_id=None
			target_id=None
			pending_delta = int(amount) * -1
			if src_usr is not None:
				source_id=src_usr.user_id
			if trg_usr is not None:
				target_id=trg_usr.user_id
			db.mark_transaction_sent(uid, pending_delta, source_id, target_id)
			logger.debug("RPC Send")
			wallet_output = await wallet.communicate_wallet_async(wallet_command)
			logger.debug("RPC Response")
			if 'block' in wallet_output:
				txid = wallet_output['block']
				db.mark_transaction_processed(uid, txid)
				logger.info('TX processed. UID: %s, TXID: %s', uid, txid)
				if target_id is None:
					# Don't wait for the result of this, doesn't matter
					asyncio.get_event_loop().create_task(notify_of_withdraw(source_id, txid))
			else:
				# Not sure what happen but we'll retry a few times
				if attempts >= MAX_TX_RETRIES:
					logger.info("Max Retires Exceeded for TX UID: %s", uid)
					db.mark_transaction_processed(uid, 'invalid')
				else:
					db.inc_tx_attempts(uid)
		logger.info("send_job complete, rescheduling")
		await schedule_send_job()
	except (ClientError, TimeoutError):
		logger.info("aiohttp error, rescheduling send_job")
		await schedule_send_job()
	except Exception as e:
		logger.exception(e)

async def schedule_send_job():
	await asyncio.sleep(SEND_JOB)
	asyncio.get_event_loop().create_task(send_job())

# Don't make them wait when bot first launches
initial_ts=datetime.datetime.now() - datetime.timedelta(seconds=SPAM_THRESHOLD)
last_big_tippers = {}
last_top_tips = {}
last_winners = {}
last_gs = {}
last_blocks = {}
def create_spam_dicts():
	"""map every channel the client can see to datetime objects
	   this way we can have channel-specific spam prevention"""
	global last_big_tippers
	global last_top_tips
	global last_winners
	for c in client.get_all_channels():
		if not is_private(c):
			last_big_tippers[c.id] = initial_ts
			last_top_tips[c.id] = initial_ts
			last_winners[c.id] = initial_ts
			last_gs[c.id] = initial_ts
			last_blocks[c.id] = initial_ts

@client.event
async def on_ready():
	logger.info("BananoBot++ v%s started", BOT_VERSION)
	logger.info("Discord.py API version %s", discord.__version__)
	logger.info("Name: %s", client.user.name)
	logger.info("ID: %s", client.user.id)
	create_spam_dicts()
	await client.change_presence(activity=discord.Game(settings.playing_status))
	logger.info("Starting send_job")
	asyncio.get_event_loop().create_task(send_job())
	logger.info("Continuing outstanding giveaway")
	asyncio.get_event_loop().create_task(start_giveaway_timer())
	logger.info("Running unsilence job")
	asyncio.get_event_loop().create_task(unsilence_users())
	logger.info("Starting receive check job")
	asyncio.get_event_loop().create_task(receive_check_job())

@client.event
async def on_member_join(member):
	if db.silenced(member.id):
		muzzled = discord.utils.get(message.guild.roles,name='muzzled')
		await member.add_roles(muzzled)

# Periodic check job to unsilence users
async def unsilence_users():
	try:
		await asyncio.sleep(10)
		asyncio.get_event_loop().create_task(unsilence_users())
		for s in db.get_silenced():
			if s.expiration is None:
				continue
			elif datetime.datetime.now() >= s.expiration:
				for guild in client.guilds:
					if guild.id == s.server_id:
						muzzled = discord.utils.get(guild.roles,name='muzzled')
						for member in guild.members:
							if member.id == int(s.user_id):
								await member.remove_roles(muzzled)
								break
				db.unsilence(s.user_id)
	except Exception as ex:
		logger.exception(ex)

async def notify_of_withdraw(user_id, txid):
	"""Notify user of withdraw with a block explorer link"""
	user = await client.get_user_info(int(user_id))
	await post_dm(user, WITHDRAW_PROCESSED_TEXT, txid)

def is_private(channel):
	"""Check if a discord channel is private"""
	return isinstance(channel, discord.abc.PrivateChannel)

@client.event
async def on_message(message):
	# disregard messages sent by our own bot
	if message.author.id == client.user.id:
		return

	citizen = False
	if not is_private(message.channel):
		for r in message.author.roles:
			if r.name == 'Citizens':
				citizen=True
	if db.last_msg_check(message.author.id, message.content, is_private(message.channel), citizen) == False:
		return
	await client.process_commands(message)


def has_admin_role(roles):
	"""Check if user has an admin role defined in our settings"""

	for r in roles:
		if r.name in settings.admin_roles:
			return True
	return False

async def pause_msg(message):
	if paused:
		await post_dm(message.author, PAUSE_MSG)

def is_admin(user):
	if str(user.id) in settings.admin_ids:
		return True
	for m in client.get_all_members():
		if m.id == user.id:
			if has_admin_role(m.roles):
				return True
	return False

### Commands
def build_page(group_name,commands_dictionary):
	entries = []
	for cmd in commands_dictionary[group_name]:
			entries.append(paginator.Entry(cmd["CMD"],cmd["INFO"]))
	return entries

def build_help():
	"""Returns an array of paginator.Page objects for help  menu"""
	pages = []
	# Overview
	author=AUTHOR_HEADER
	title="Command Overview"
	description=("Use `{0}help command` for more information about a specific command " +
		     " or go to the next page").format(COMMAND_PREFIX)
	entries = []
	tmp_command_list = [
		"ACCOUNT_COMMANDS",
		"TIPPING_COMMANDS",
		"GIVEAWAY_COMMANDS",
		"STATISTICS_COMMANDS",
		"FAVORITES_COMMANDS",
		"NOTIFICATION_COMMANDS"
	]
	for command_group in tmp_command_list:
		for cmd in COMMANDS[command_group]:
			entries.append(paginator.Entry(cmd["CMD"],cmd["OVERVIEW"]))
	pages.append(paginator.Page(entries=entries, title=title,author=author, description=description))
	# Account
	author="Account Commands"
	description="Check account balance, withdraw, or deposit"
	entries = build_page("ACCOUNT_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author,description=description))
	# Tipping
	author="Tipping Commands"
	description="The different ways you are able to tip with this bot"
	entries = build_page("TIPPING_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author,description=description))
	# Giveaway
	author="Giveaway Commands"
	description="The different ways to interact with the bot's giveaway functionality"
	entries = build_page("GIVEAWAY_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author, description=description))
	# Stats
	author="Statistics Commands"
	description="Individual, bot-wide, and giveaway stats"
	entries = build_page("STATISTICS_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author,description=description))
	# Favorites
	author="Favorites Commands"
	description="How to interact with your favorites list"
	entries = build_page("FAVORITES_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author,description=description))
	# notifications
	author="Notification Settings"
	description="Handle how tip bot gives you notifications"
	entries = build_page("NOTIFICATION_COMMANDS",COMMANDS)
	pages.append(paginator.Page(entries=entries, author=author, description=description))
	# Info
	entries = []
	author=AUTHOR_HEADER + " - by bbedward"
	description=("**Reviews**:\n" + "'10/10 True Masterpiece' - BANANO Core Team" +
			"\n'0/10 Didn't get brain' - Almost everybody else\n\n" +
			"BANANO Tip Bot is completely free to use and open source." +
			" Developed by bbedward (reddit: /u/bbedward, discord: bbedward#9246)" +
			"\nFeel free to send tips, suggestions, and feedback.\n\n" +
			"github: https://github.com/BananoCoin/Banano-Discord-TipBot/")
	pages.append(paginator.Page(entries=entries, author=author,description=description))
	return pages

@client.command()
async def help(ctx):
	message = ctx.message
	# If they spplied an argument post usage for a specific command if applicable
	content = message.content.split(' ')
	if len(content) > 1:
		arg = content[1].strip().lower()
		for key, value in COMMANDS.items():
			if key == 'ADMIN_COMMANDS':
				continue
			for v in value:
				if arg in v["TRIGGER"]:
					await post_usage(message, v)
					return
	try:
		pages = paginator.Paginator(client, message=message, page_list=build_help(),as_dm=True)
		await pages.paginate(start_page=1)
	except paginator.CannotPaginate as e:
		logger.exception(str(e))

@client.command()
async def adminhelp(ctx):
	message = ctx.message
	if not is_admin(ctx.message.author):
		return
	embed = discord.Embed(colour=discord.Colour.magenta())
	embed.title = "Admin Commands"
	for cmd in COMMANDS["ADMIN_COMMANDS"]:
		embed.add_field(name=cmd['CMD'], value=cmd['INFO'], inline=False)
	await message.author.send(embed=embed)

@client.command(aliases=get_aliases(BALANCE, exclude='balance'))
async def balance(ctx):
	message = ctx.message
	if is_private(message.channel):
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		balances = await wallet.get_balance(user)
		actual = balances['actual']
		available = balances['available']
		send = balances['pending_send']
		receive = balances['pending']
		await post_response(message, BALANCE_TEXT, actual, available, send, receive)

@client.command(aliases=get_aliases(DEPOSIT, exclude='deposit'))
async def deposit(ctx):
	message = ctx.message
	if is_private(message.channel):
		user = await wallet.create_or_fetch_user(message.author.id, message.author.name)
		user_deposit_address = user.wallet_address
		await post_response(message, DEPOSIT_TEXT)
		await post_response(message, DEPOSIT_TEXT_2, user_deposit_address)
		await post_response(message, DEPOSIT_TEXT_3, get_qr_url(user_deposit_address))

@client.command()
async def withdraw(ctx):
	message = ctx.message
	if paused:
		await pause_msg(message)
		return
	elif db.is_frozen(message.author.id):
		await post_dm(message.author, FROZEN_MSG)
	elif is_private(message.channel):
		try:
			withdraw_amount = find_amount(message.content)
		except util.TipBotException as e:
			withdraw_amount = 0
		try:
			withdraw_address = find_address(message.content)
			user = db.get_user_by_id(message.author.id, user_name=message.author.name)
			if user is None:
				return
			last_withdraw_delta = db.get_last_withdraw_delta(user.user_id)
			if WITHDRAW_COOLDOWN > last_withdraw_delta:
				raise util.TipBotException("cooldown_error")
			source_id = user.user_id
			source_address = user.wallet_address
			balance = await wallet.get_balance(user)
			amount = balance['available']
			if withdraw_amount == 0:
				withdraw_amount = amount
			else:
				withdraw_amount = abs(withdraw_amount)
			if amount == 0:
				await post_response(message, WITHDRAW_NO_BALANCE_TEXT)
			elif withdraw_amount > amount:
				await post_response(message, WITHDRAW_INSUFFICIENT_BALANCE)
			else:
				uid = str(uuid.uuid4())
				await wallet.make_transaction_to_address(user, withdraw_amount, withdraw_address, uid,verify_address = True)
				await post_response(message, WITHDRAW_SUCCESS_TEXT)
				db.update_last_withdraw(user.user_id)
		except util.TipBotException as e:
			if e.error_type == "address_not_found":
				await post_usage(message, WITHDRAW)
			elif e.error_type == "invalid_address":
				await post_response(message, WITHDRAW_INVALID_ADDRESS_TEXT)
			elif e.error_type == "balance_error":
				await post_response(message, INSUFFICIENT_FUNDS_TEXT)
			elif e.error_type == "error":
				await post_response(message, WITHDRAW_ERROR_TEXT)
			elif e.error_type == "cooldown_error":
				await post_response(message, WITHDRAW_COOLDOWN_TEXT, (WITHDRAW_COOLDOWN - last_withdraw_delta))

@client.command(aliases=get_aliases(TIP, exclude='ban'))
async def ban(ctx):
	await do_tip(ctx.message)

@client.command(aliases=get_aliases(TIPRANDOM,exclude='banrandom'))
async def banrandom(ctx):
	await do_tip(ctx.message, rand=True)

async def do_tip(message, rand=False):
	if is_private(message.channel):
		return
	elif paused:
		await pause_msg(message)
		return
	elif db.is_frozen(message.author.id):
		await post_dm(message.author, FROZEN_MSG)
		return
	try:
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		amount = find_amount(message.content)
		if rand and amount < settings.tiprandom_minimum:
			raise util.TipBotException("usage_error")
		# Make sure amount is valid and at least 1 user is mentioned
		if amount < 1 or (len(message.mentions) < 1 and not rand):
			raise util.TipBotException("usage_error")
		# Create tip list
		users_to_tip = []
		if not rand:
			for member in message.mentions:
				# Disregard mentions of exempt users and self
				if member.id not in settings.exempt_users and member.id != message.author.id and not db.is_banned(member.id) and not member.bot:
					users_to_tip.append(member)
			if len(users_to_tip) < 1:
				raise util.TipBotException("no_valid_recipient")
		else:
			# Spam Check
			spam = db.tiprandom_check(user)
			if spam > 0:
				await post_dm(message.author, "You need to wait {0} seconds before you can banrandom again", spam)
				await add_x_reaction(message)
				return
			# Pick a random active user
			active = db.get_active_users(RAIN_DELTA)
			if len(active) == 0:
				await post_dm(message.author, "I couldn't find any active user to tip")
				return
			if str(message.author.id) in active:
				active.remove(str(message.author.id))
			# Remove bots from consideration
			for a in active:
				dmember = message.guild.get_member(int(a))
				if dmember is None or dmember.bot:
					active.remove(a)
			sysrand = random.SystemRandom()
			sysrand.shuffle(active)
			offset = secrets.randbelow(len(active))
			users_to_tip.append(message.guild.get_member(int(active[offset])))
		# Cut out duplicate mentions
		users_to_tip = list(set(users_to_tip))
		# Make sure this user has enough in their balance to complete this tip
		required_amt = amount * len(users_to_tip)
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if user_balance < required_amt:
			await add_x_reaction(message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		# Distribute tips
		for member in users_to_tip:
			uid = str(uuid.uuid4())
			actual_amt = await wallet.make_transaction_to_user(user, amount, member.id, member.name, uid)
			# Something went wrong, tip didn't go through
			if actual_amt == 0:
				required_amt -= amount
			else:
				msg = TIP_RECEIVED_TEXT
				if rand:
					msg += ". You were randomly chosen by {0}'s `banrandom`".format(message.author.name)
					await post_dm(message.author, "{0} was the recipient of your random {1} BANANO tip", member.name, actual_amt, skip_dnd=True)
				if not db.muted(member.id, message.author.id):
					await post_dm(member, msg, actual_amt, message.author.name, message.author.id, skip_dnd=True)
		# Post message reactions
		await react_to_message(message, required_amt)
		# Update tip stats
		if message.channel.id not in (416306340848336896, 443985110371401748) and not user.stats_ban:
			db.update_tip_stats(user, required_amt)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			if rand:
				await post_usage(message, TIPRANDOM)
			else:
				await post_usage(message, TIP)
		elif e.error_type == "no_valid_recipient":
			await post_dm(message.author, TIP_SELF)

@client.command(aliases=get_aliases(TIPSPLIT, exclude='bansplit'))
async def bansplit(ctx):
	await do_tipsplit(ctx.message)

async def do_tipsplit(message, user_list=None):
	if is_private(message.channel):
		return
	elif paused:
		await pause_msg(message)
		return
	elif db.is_frozen(message.author.id):
		await post_dm(message.author, FROZEN_MSG)
		return
	try:
		amount = find_amount(message.content)
		# Make sure amount is valid and at least 1 user is mentioned
		if amount < 1 or (len(message.mentions) < 1 and user_list is None):
			raise util.TipBotException("usage_error")
		# Create tip list
		users_to_tip = []
		if user_list is not None:
			for m in message.mentions:
				user_list.append(m)
		else:
			user_list = message.mentions
		if int(amount / len(user_list)) < 1:
			raise util.TipBotException("invalid_tipsplit")
		for member in user_list:
			# Disregard mentions of self and exempt users
			if member.id not in settings.exempt_users and member.id != message.author.id and not db.is_banned(member.id) and not member.bot:
				users_to_tip.append(member)
		if len(users_to_tip) < 1:
			raise util.TipBotException("no_valid_recipient")
		# Remove duplicates
		users_to_tip = list(set(users_to_tip))
		# Make sure user has enough in their balance
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if user_balance < amount:
			await add_x_reaction(ctx.message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		# Distribute tips
		tip_amount = int(amount / len(users_to_tip))
		# Recalculate amount as it may be different since truncating decimal
		real_amount = tip_amount * len(users_to_tip)
		for member in users_to_tip:
			uid = str(uuid.uuid4())
			actual_amt = await wallet.make_transaction_to_user(user, tip_amount, member.id, member.name, uid)
			# Tip didn't go through
			if actual_amt == 0:
				amount -= tip_amount
			else:
				if not db.muted(member.id, message.author.id):
					await post_dm(member, TIP_RECEIVED_TEXT, tip_amount, message.author.name, message.author.id, skip_dnd=True)
		await react_to_message(message, amount)
		if message.channel.id not in (416306340848336896, 443985110371401748) and not user.stats_ban:
			db.update_tip_stats(user, real_amount)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			if user_list is None:
				await post_usage(message, TIPSPLIT)
			else:
				await post_usage(message, TIP_FAVORITES)
		elif e.error_type == "invalid_tipsplit":
			await post_dm(message.author, TIPSPLIT_SMALL)
		elif e.error_type == "no_valid_recipient":
			await post_dm(message.author, TIP_SELF)

@client.command(aliases=get_aliases(TIP_FAVORITES,exclude='banfavorites'))
async def banfavorites(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id, user_name=message.author.name)
	if user is None:
		return
	# Spam Check
	spam = db.tipfavorites_check(user)
	if spam > 0:
		await post_dm(message.author, "You need to wait {0} seconds before you can banfavorites again", spam)
		await add_x_reaction(message)
		return
	favorites = db.get_favorites_list(message.author.id)
	if len(favorites) == 0:
		await post_dm(message.author, "There's nobody in your favorites list. Add some people by using `{0}addfavorite`", COMMAND_PREFIX)
		return
	user_list = []
	for fav in favorites:
		discord_user = message.guild.get_member(int(fav['user_id']))
		if discord_user is not None:
			user_list.append(discord_user)
	await do_tipsplit(message, user_list=user_list)

@client.command()
async def brain(ctx):
	message = ctx.message
	if is_private(message.channel):
		return
	elif paused:
		await pause_msg(message)
		return
	try:
		amount = find_amount(message.content)
		if amount < RAIN_MINIMUM:
			raise util.TipBotException("usage_error")
		# Create tip list
		users_to_tip = []
		active_user_ids = db.get_active_users(RAIN_DELTA)
		if len(active_user_ids) < 1:
			raise util.TipBotException("no_valid_recipient")
		for auid in active_user_ids:
			dmember = message.guild.get_member(int(auid))
			if dmember is not None and (dmember.status == discord.Status.online or dmember.status == discord.Status.idle):
				if str(dmember.id) not in settings.exempt_users and dmember.id != message.author.id and not db.is_banned(dmember.id) and not dmember.bot:
					users_to_tip.append(dmember)
		users_to_tip = list(set(users_to_tip))
		if len(users_to_tip) < 1:
			raise util.TipBotException("no_valid_recipient")
		if int(amount / len(users_to_tip)) < 1:
			raise util.TipBotException("invalid_tipsplit")
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if user_balance < amount:
			await add_x_reaction(message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		# Distribute Tips
		tip_amount = int(amount / len(users_to_tip))
		# Recalculate actual tip amount as it may be smaller now
		real_amount = tip_amount * len(users_to_tip)
		# 1) Make all transactions first
		for member in users_to_tip:
			uid = str(uuid.uuid4())
			actual_amt = await wallet.make_transaction_to_user(user, tip_amount, member.id, member.name, uid)
		# 2) Add reaction
		await react_to_message(message, amount)
		await message.add_reaction('\:bananorain:430826677543895050')
		# 3) Update tip stats
		db.update_tip_stats(user, real_amount,rain=True)
		db.mark_user_active(user)
		# 4) Send DMs (do this last because this takes the longest)
		for member in users_to_tip:
			if not db.muted(member.id, message.author.id):
				await post_dm(member, TIP_RECEIVED_TEXT, actual_amt, message.author.name, message.author.id)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			await post_usage(message, RAIN)
		elif e.error_type == "no_valid_recipient":
			await post_dm(message.author, RAIN_NOBODY)
		elif e.error_type == "invalid_tipsplit":
			await post_dm(message.author, TIPSPLIT_SMALL)

@client.command(aliases=get_aliases(ROLESOAK, exclude='bancitizens'))
async def bancitizens(ctx):
	message = ctx.message
	if is_private(message.channel):
		return
	try:
		amount = find_amount(message.content)
		if ROLESOAK_MINIMUM > amount:
			raise util.TipBotException("usage_error")
		users_to_tip = []
		active = db.get_active_users(90)
		for m in message.guild.members:
			if str(m.id) not in active or m.id == message.author.id:
				continue
			for r in m.roles:
				if r.name == 'Citizens':
					u = db.get_user_by_id(m.id)
					if u is None:
						break
					delta = datetime.datetime.now() - u.last_msg
					if delta.total_seconds() > 10800:
						break
					users_to_tip.append(m)
					break
		if len(users_to_tip) == 0:
			raise util.TipBotException("no_recipient")
		if 1 > int(amount / len(users_to_tip)):
			raise util.TipBotException("invalid_tipsplit")
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if amount > user_balance:
			await add_x_reaction(message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		# Distribute Tips
		tip_amount = int(amount / len(users_to_tip))
		real_amount = tip_amount * len(users_to_tip)
		# 1) Make all transactions first
		for member in users_to_tip:
			uid = str(uuid.uuid4())
			actual_amt = await wallet.make_transaction_to_user(user, tip_amount, member.id, member.name, uid)
		# 2) Add reaction
		await react_to_message(message, amount)
		await message.add_reaction('\U0001F4A6') # Sweat Drops
		# 3) Update tip stats
		db.update_tip_stats(user, real_amount,rain=True)
		db.mark_user_active(user)
		# 4) Send DMs (do this last because this takes the longest)
		for member in users_to_tip:
			if not db.muted(member.id, message.author.id):
				await post_dm(member, TIP_RECEIVED_TEXT, actual_amt, message.author.name, message.author.id)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			await post_usage(message, ROLESOAK)
		elif e.error_type == "no_recipient":
			await post_dm(message.author, "Could not find any users on the server in mentioned role(s)")
		elif e.error_type == "invalid_tipsplit":
			await post_dm(message.author, TIPSPLIT_SMALL)

@client.command(aliases=get_aliases(ENTER, exclude='ticket'))
async def ticket(ctx):
	message = ctx.message
	if not db.is_active_giveaway():
		await post_dm(message.author, TIPGIVEAWAY_NO_ACTIVE)
		await remove_message(message)
		return
	giveaway = db.get_giveaway()
	if db.is_banned(message.author.id):
		await post_dm(message.author, "You may not enter giveaways at this time")
	elif giveaway.entry_fee == 0:
		entered = db.add_contestant(message.author.id)
		if entered:
			await wallet.create_or_fetch_user(message.author.id, message.author.name)
			await post_dm(message.author, ENTER_ADDED)
		else:
			await post_dm(message.author, ENTER_DUP)
	else:
		if db.contestant_exists(message.author.id):
			await post_dm(message.author, ENTER_DUP)
		else:
			await tip_giveaway(message,ticket=True)
	await remove_message(message)

@client.command(aliases=get_aliases(START_GIVEAWAY,exclude='giveaway'))
async def giveaway(ctx):
	message = ctx.message
	if is_private(message.channel):
		return
	elif paused:
		await pause_msg(message)
		return
	try:
		# One giveaway at a time
		if db.is_active_giveaway():
			await post_dm(message.author, GIVEAWAY_EXISTS)
			return
		amount = find_amount(message.content)
		# Find fee and duration in message
		fee = -1
		duration = -1
		split_content = message.content.split(' ')
		for split in split_content:
			if split.startswith('fee='):
				split = split.replace('fee=','').strip()
				if not split:
					continue
				try:
					fee = int(split)
				except ValueError as e:
					fee = -1
			elif split.startswith('duration='):
				split=split.replace('duration=','').strip()
				if not split:
					continue
				try:
					duration = int(split)
				except ValueError as e:
					duration = -1

		# Sanity checks
		max_fee = int(0.05 * amount)
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if fee == -1 or duration == -1:
			raise util.TipBotException("usage_error")
		elif amount < GIVEAWAY_MINIMUM:
			raise util.TipBotException("usage_error")
		elif fee > max_fee:
			await post_dm(message.author, GIVEAWAY_MAX_FEE)
			return
		elif duration > GIVEAWAY_MAX_DURATION or GIVEAWAY_MIN_DURATION > duration:
			raise util.TipBotException("usage_error")
		elif 0 > fee:
			raise util.TipBotException("usage_error")
		elif user is None:
			return
		# If balance is sufficient fire up the giveaway
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if user_balance < amount:
			await add_x_reaction(message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		end_time = datetime.datetime.now() + datetime.timedelta(minutes=duration)
		nano_amt = amount
		giveaway,deleted = db.start_giveaway(message.author.id, message.author.name, nano_amt, end_time, message.channel.id, entry_fee=fee)
		uid = str(uuid.uuid4())
		await wallet.make_transaction_to_address(user, amount, None, uid, giveaway_id=giveaway.id)
		if fee > 0:
			await post_response(message, GIVEAWAY_STARTED_FEE, message.author.name, nano_amt, fee)
		else:
			await post_response(message, GIVEAWAY_STARTED, message.author.name, nano_amt)
		asyncio.get_event_loop().create_task(start_giveaway_timer())
		db.update_tip_stats(user, amount, giveaway=True)
		db.add_contestant(message.author.id)
		for d in deleted:
			await post_dm(await client.get_user_info(int(d)), GIVEAWAY_FEE_TOO_HIGH)
		db.mark_user_active(user)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			await post_usage(message, START_GIVEAWAY)

@client.command(aliases=get_aliases(TIPGIVEAWAY, exclude='donate'))
async def donate(ctx):
	await tip_giveaway(ctx.message)

async def tip_giveaway(message, ticket=False):
	if is_private(message.channel) and not ticket:
		return
	elif paused:
		await pause_msg(message)
		return
	try:
		giveaway = db.get_giveaway()
		amount = find_amount(message.content)
		user = db.get_user_by_id(message.author.id, user_name=message.author.name)
		if user is None:
			return
		balance = await wallet.get_balance(user)
		user_balance = balance['available']
		if user_balance < amount:
			await add_x_reaction(message)
			await post_dm(message.author, INSUFFICIENT_FUNDS_TEXT)
			return
		nano_amt = amount
		if giveaway is not None:
			db.add_tip_to_giveaway(nano_amt)
			giveawayid = giveaway.id
			fee = giveaway.entry_fee
		else:
			giveawayid = -1
			fee = TIPGIVEAWAY_AUTO_ENTRY
		contributions = db.get_tipgiveaway_contributions(message.author.id, giveawayid)
		if ticket:
			if fee > (amount + contributions):
				owed = fee - contributions
				await post_dm(message.author,
					"You were NOT entered into the giveaway!\n" +
					"This giveaway has a fee of **{0} BANANO**\n" +
					"You've donated **{1} BANANO** so far\n" +
					"You need **{2} BANANO** to enter\n" +
					"You may enter using `{3}ticket {2}`"
					, fee, contributions, owed, COMMAND_PREFIX)
				return
		uid = str(uuid.uuid4())
		await wallet.make_transaction_to_address(user, amount, None, uid, giveaway_id=giveawayid)
		if not ticket:
			await react_to_message(message, amount)
		# If eligible, add them to giveaway
		if (amount + contributions) >= fee and not db.is_banned(message.author.id):
			if (amount + contributions) >= (TIPGIVEAWAY_AUTO_ENTRY * 4):
				db.mark_user_active(user)
			entered = db.add_contestant(message.author.id)
			if entered:
				if giveaway is None:
					if message.channel.id not in settings.no_spam_channels:
						await post_response(message, TIPGIVEAWAY_ENTERED_FUTURE)
					else:
						await post_dm(message.author, TIPGIVEAWAY_ENTERED_FUTURE)
				else:
					await post_dm(message.author, ENTER_ADDED)
			elif ticket:
				await post_dm(message.author, ENTER_DUP)
		# If tip sum is >= GIVEAWAY MINIMUM then start giveaway
		if giveaway is None:
			tipgiveaway_sum = db.get_tipgiveaway_sum()
			nano_amt = float(tipgiveaway_sum)
			if tipgiveaway_sum >= GIVEAWAY_MINIMUM:
				end_time = datetime.datetime.now() + datetime.timedelta(minutes=GIVEAWAY_AUTO_DURATION)
				db.start_giveaway(client.user.id, client.user.name, 0, end_time, message.channel.id,entry_fee=fee)
				await post_response(message, GIVEAWAY_STARTED_FEE, client.user.name, nano_amt, fee)
				asyncio.get_event_loop().create_task(start_giveaway_timer())
		# Update top tipY
		if not user.stats_ban:
			db.update_tip_stats(user, amount, giveaway=True)
	except util.TipBotException as e:
		if e.error_type == "amount_not_found" or e.error_type == "usage_error":
			if ticket:
				await post_usage(message, ENTER)
			else:
				await post_usage(message, TIPGIVEAWAY)

@client.command(aliases=get_aliases(TICKETSTATUS,exclude='ticketstatus'))
async def ticketstatus(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id)
	if user is not None:
		await post_dm(message.author, db.get_ticket_status(message.author.id))
	await remove_message(message)

@client.command(aliases=get_aliases(GIVEAWAY_STATS, exclude='giveawaystats'))
async def giveawaystats(ctx):
	message = ctx.message
	global last_gs
	if message.channel.id in settings.no_spam_channels:
		return
	if not is_private(message.channel):
		if message.channel.id not in last_gs:
			last_gs[message.channel.id] = datetime.datetime.now()
		if 5 > (datetime.datetime.now() - last_gs[message.channel.id]).total_seconds():
			return
		last_gs[message.channel.id] = datetime.datetime.now()
	stats = db.get_giveaway_stats()
	if stats is None:
		for_next = GIVEAWAY_MINIMUM - db.get_tipgiveaway_sum()
		await post_response(message, GIVEAWAY_STATS_INACTIVE, for_next)
	else:
		end = stats['end'] - datetime.datetime.now()
		end_s = int(end.total_seconds())
		str_delta = time.strftime("%M Minutes and %S Seconds", time.gmtime(end_s))
		fee = stats['fee']
		if fee == 0:
			await post_response(message, GIVEAWAY_STATS_NF, stats['entries'], stats['amount'], str_delta, stats['started_by'])
		else:
			await post_response(message, GIVEAWAY_STATS_FEE, stats['entries'], stats['amount'], str_delta, stats['started_by'], fee)

async def start_giveaway_timer():
	giveaway = db.get_giveaway()
	if giveaway is None:
		return
	delta = (giveaway.end_time - datetime.datetime.now()).total_seconds()
	if delta <= 0:
		await finish_giveaway(0)
		return

	await finish_giveaway(delta)

async def finish_giveaway(delay):
	await asyncio.sleep(delay)
	giveaway = db.finish_giveaway()
	if giveaway is not None:
		channel = client.get_channel(int(giveaway.channel_id))
		response = GIVEAWAY_ENDED.format(giveaway.winner_id, giveaway.amount + giveaway.tip_amount)
		await channel.send(response)
		await post_dm(await client.get_user_info(int(giveaway.winner_id)), response)

@client.command()
async def winners(ctx):
	message = ctx.message
	if message.channel.id in settings.no_spam_channels:
		return
	# Check spam
	global last_winners
	if not is_private(message.channel):
		if message.channel.id not in last_winners:
			last_winners[message.channel.id] = datetime.datetime.now()
		tdelta = datetime.datetime.now() - last_winners[message.channel.id]
		if SPAM_THRESHOLD > tdelta.seconds:
			await post_response(message, WINNERS_SPAM, (SPAM_THRESHOLD - tdelta.seconds))
			return
		last_winners[message.channel.id] = datetime.datetime.now()
	winners = db.get_giveaway_winners(WINNERS_COUNT)
	if len(winners) == 0:
		await post_response(message, WINNERS_EMPTY)
	else:
		response = WINNERS_HEADER
		response += "```"
		max_l = 0
		winner_nms = []
		for winner in winners:
			if winner['index'] >= 10:
				winner_nm = '{0}: {1} '.format(winner['index'], winner['name'])
			else:
				winner_nm = '{0}:  {1} '.format(winner['index'], winner['name'])
			if len(winner_nm) > max_l:
				max_l = len(winner_nm)
			winner_nms.append(winner_nm)

		for winner in winners:
			winner_nm = winner_nms[winner['index'] - 1]
			padding = " " * ((max_l - len(winner_nm)) + 1)
			response += winner_nm
			response += padding
			response += 'won {0:.2f} BANANO'.format(winner['amount'])
			response += '\n'
		response += "```"
		await post_response(message, response)

@client.command(aliases=get_aliases(LEADERBOARD, exclude='leaderboard'))
async def leaderboard(ctx):
	message = ctx.message
	if message.channel.id in settings.no_spam_channels:
		return
	# Check spam
	global last_big_tippers
	if not is_private(message.channel):
		if message.channel.id not in last_big_tippers:
			last_big_tippers[message.channel.id] = datetime.datetime.now()
		tdelta = datetime.datetime.now() - last_big_tippers[message.channel.id]
		if SPAM_THRESHOLD > tdelta.seconds:
			await post_response(message, TOP_SPAM, (SPAM_THRESHOLD - tdelta.seconds))
			return
		last_big_tippers[message.channel.id] = datetime.datetime.now()
	top_users = db.get_top_users(TOP_TIPPERS_COUNT)
	if len(top_users) == 0:
		await post_response(message, TOP_HEADER_EMPTY_TEXT)
	else:
		# Probably a very clunky and sloppy way to format this output, I'm sure there's something better
		response = TOP_HEADER_TEXT.format(TOP_TIPPERS_COUNT)
		response += "```"
		max_l = 0
		top_user_nms = []
		for top_user in top_users:
			if top_user['index'] >= 10:
				top_user_nm = '{0}: {1} '.format(top_user['index'], top_user['name'])
			else:
				top_user_nm = '{0}:  {1} '.format(top_user['index'], top_user['name'])
			if len(top_user_nm) > max_l:
				max_l = len(top_user_nm)
			top_user_nms.append(top_user_nm)

		for top_user in top_users:
			top_user_nm = top_user_nms[top_user['index'] - 1]
			padding = " " * ((max_l - len(top_user_nm)) + 1)
			response += top_user_nm
			response += padding
			response += '- {0:.2f} BANANO'.format(top_user['amount'])
			response += '\n'
		response += "```"
		await post_response(message, response)

@client.command()
async def toptips(ctx):
	message = ctx.message
	if message.channel.id in settings.no_spam_channels:
		return
	# Check spam
	global last_top_tips
	if not is_private(message.channel):
		if not message.channel.id in last_top_tips:
			last_top_tips[message.channel.id] = datetime.datetime.now()
		tdelta = datetime.datetime.now() - last_top_tips[message.channel.id]
		if SPAM_THRESHOLD > tdelta.seconds:
			await post_response(message, TOPTIP_SPAM, (SPAM_THRESHOLD - tdelta.seconds))
			return
		last_top_tips[message.channel.id] = datetime.datetime.now()
	top_tips_msg = db.get_top_tips()
	await post_response(message, top_tips_msg)

@client.command(aliases=['banstats'])
async def tipstats(ctx):
	message = ctx.message
	if message.channel.id in settings.no_spam_channels:
		return
	tip_stats = db.get_tip_stats(message.author.id)
	if tip_stats is None or len(tip_stats) == 0:
		await post_response(message, STATS_ACCT_NOT_FOUND_TEXT)
		return
	if tip_stats['rank'] == -1:
		tip_stats['rank'] = 'N/A'
	await post_response(message, STATS_TEXT, str(tip_stats['rank']), tip_stats['total'], tip_stats['average'],tip_stats['top'])

@client.command(aliases=get_aliases(ADD_FAVORITE, exclude='addfavorite'))
async def addfavorite(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	added_count = 0
	for mention in message.mentions:
		if mention.id != message.author.id and not mention.bot:
			if db.add_favorite(user.user_id,mention.id):
				added_count += 1
	if added_count > 0:
		await post_dm(message.author, "{0} users added to your favorites!", added_count)
	else:
		await post_dm(message.author, "I couldn't find any users to add as favorites in your message! They may already be in your favorites or they may not have accounts with me")

@client.command(aliases=get_aliases(DEL_FAVORITE, exclude='removefavorite'))
async def removefavorite(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	remove_count = 0
	# Remove method #1: Mentions
	if len(message.mentions) > 0:
		for mention in message.mentions:
			if db.remove_favorite(user.user_id,favorite_id=mention.id):
				remove_count += 1

	# Remove method #2: identifiers
	remove_ids = []
	for c in message.content.split(' '):
		try:
			id=int(c.strip())
			remove_ids.append(id)
		except ValueError as e:
			pass
	for id in remove_ids:
		if db.remove_favorite(user.user_id,identifier=id):
			remove_count += 1
	if remove_count > 0:
		await post_dm(message.author, "{0} users removed from your favorites!", remove_count)
	else:
		await post_dm(message.author, "I couldn't find anybody in your message to remove from your favorites!")

@client.command(aliases=get_aliases(FAVORITES, exclude='favorites'))
async def favorites(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	favorites = db.get_favorites_list(message.author.id)
	if len(favorites) == 0:
		embed = discord.Embed(colour=discord.Colour.red())
		embed.title="No Favorites"
		embed.description="Your favorites list is empty. Add to it with `{0}addfavorite`".format(COMMAND_PREFIX)
		await message.author.send(embed=embed)
		return
	title="Favorites List"
	description=("Here are your favorites! " +
			   "You can tip everyone in this list at the same time using `{0}banfavorites amount`").format(COMMAND_PREFIX)
	entries = []
	for fav in favorites:
		fav_user = db.get_user_by_id(fav['user_id'])
		name = str(fav['id']) + ": " + fav_user.user_name
		value = "You can remove this favorite with `{0}removefavorite {1}`".format(COMMAND_PREFIX, fav['id'])
		entries.append(paginator.Entry(name,value))

	# Do paginator for favorites > 10
	if len(entries) > 10:
		pages = paginator.Paginator.format_pages(entries=entries,title=title,description=description)
		p = paginator.Paginator(client,message=message,page_list=pages,as_dm=True)
		await p.paginate(start_page=1)
	else:
		embed = discord.Embed(colour=discord.Colour.teal())
		embed.title = title
		embed.description = description
		for e in entries:
			embed.add_field(name=e.name,value=e.value,inline=False)
		await message.author.send(embed=embed)

@client.command()
async def muted(ctx):
	message = ctx.message
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	muted = db.get_muted(message.author.id)
	if len(muted) == 0:
		embed = discord.Embed(colour=discord.Colour.red())
		embed.title="Nobody Muted"
		embed.description="Nobody is muted. You can mute people with `{0}mute discord_id`".format(COMMAND_PREFIX)
		await message.author.send(embed=embed)
		return
	title="Muted List"
	description=("This is your muted list. You can still receive tips from these people, but the bot will not PM you " +
			   "when you receive a tip from them.")
	entries = []
	idx = 1
	for m in muted:
		name = str(idx) + ": " + m['name']
		value = "You can unmute with person with `{0}unmute {1}`".format(COMMAND_PREFIX, m['id'])
		entries.append(paginator.Entry(name,value))
		idx += 1

	# Do paginator for favorites > 10
	if len(entries) > 10:
		pages = paginator.Paginator.format_pages(entries=entries,title=title,description=description)
		p = paginator.Paginator(client,message=message,page_list=pages,as_dm=True)
		await p.paginate(start_page=1)
	else:
		embed = discord.Embed(colour=discord.Colour.teal())
		embed.title = title
		embed.description = description
		for e in entries:
			embed.add_field(name=e.name,value=e.value,inline=False)
		await message.author.send(embed=embed)

@client.command()
async def mute(ctx):
	message = ctx.message
	if not is_private(message.channel):
		return
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	muted_count = 0
	mute_ids = []
	for c in message.content.split(' '):
		try:
			id=int(c.strip())
			mute_ids.append(id)
		except ValueError as e:
			pass
	for id in mute_ids:
		target = db.get_user_by_id(id)
		if target is not None and db.mute(user.user_id, target.user_id, target.user_name):
			muted_count += 1
	if muted_count > 0:
		await post_dm(message.author, "{0} users have been muted!", muted_count)
	else:
		await post_dm(message.author, "I couldn't find any users to mute in your message. They probably are already muted or they aren't registered with me")

@client.command()
async def unmute(ctx):
	message = ctx.message
	if not is_private(message.channel):
		return
	user = db.get_user_by_id(message.author.id)
	if user is None:
		return
	unmute_count = 0
	unmute_ids = []
	for c in message.content.split(' '):
		try:
			id=int(c.strip())
			unmute_ids.append(id)
		except ValueError as e:
			pass
	for id in unmute_ids:
		if db.unmute(user.user_id,id) > 0:
			unmute_count += 1
	if unmute_count > 0:
		await post_dm(message.author, "{0} users have been unmuted!", unmute_count)
	else:
		await post_dm(message.author, "I couldn't find anybody in your message to unmute!")

@client.command()
async def blocks(ctx):
	message = ctx.message
	global last_blocks
	if not is_private(message.channel):
		if message.channel.id not in last_blocks:
			last_blocks[message.channel.id] = datetime.datetime.now()
		tdelta = datetime.datetime.now() - last_blocks[message.channel.id]
		if SPAM_THRESHOLD > tdelta.seconds:
			await post_response(message, "No more blocks for {0} seconds", (SPAM_THRESHOLD - tdelta.seconds))
			return
		last_blocks[message.channel.id] = datetime.datetime.now()
	count,unchecked = await wallet.get_blocks()
	await post_response(message, "```Count: {0:,}\nUnchecked: {1:,}```", int(count), int(unchecked))

@client.command()
async def frozen(ctx):
	message = ctx.message
	if is_admin(message.author):
		await post_dm(message.author, db.frozen())
	
@client.command()
async def banned(ctx):
	message = ctx.message
	if is_admin(message.author):
		await post_dm(message.author, db.get_banned())

@client.command()
async def statsbanned(ctx):
	message = ctx.message
	if is_admin(message.author):
		await post_dm(message.author, db.get_statsbanned())		
		
@client.command()
async def pause(ctx):
	message = ctx.message
	if is_admin(message.author):
		global paused
		paused = True
		await post_response(message, "Transaction-related activity is now suspended")

@client.command()
async def unpause(ctx):
	message = ctx.message
	if is_admin(message.author):
		global paused
		paused = False
		await post_response(message, "Transaction-related activity is no longer suspended")

@client.command()
async def freeze(ctx):
	message = ctx.message
	if is_admin(message.author):
		for member in message.mentions:
			if db.freeze(member):
				await post_dm(message.author, "User {0} is frozen", member.name)
			else:
				await post_dm(message.author, "Couldn't freeze user they may already be frozen")

@client.command()
async def tipban(ctx):
	await do_tipban(ctx.message)

async def do_tipban(message):
	if is_admin(message.author):
		for member in message.mentions:
			if member.id not in settings.admin_ids and not has_admin_role(member.roles):
				if db.ban_user(member.id):
					await post_dm(message.author, BAN_SUCCESS, member.name)
				else:
					await post_dm(message.author, BAN_DUP, member.name)

@client.command()
async def statsban(ctx):
	message = ctx.message
	if is_admin(message.author):
		for member in message.mentions:
			if db.statsban_user(member.id):
				await post_dm(message.author, STATSBAN_SUCCESS, member.name)
			else:
				await post_dm(message.author, STATSBAN_DUP, member.name)

@client.command()
async def unfreeze(ctx):
	message = ctx.message
	if is_admin(message.author):
		for member in message.mentions:
			if db.unfreeze(member.id):
				await post_dm(message.author, "{0} has been unfrozen", member.name)
			else:
				await post_dm(message.author, "Couldn't unfreeze, {0} may not be frozen", member.name)

@client.command()
async def tipunban(ctx):
	await do_tipunban(ctx.message)

async def do_tipunban(message):
	if is_admin(message.author):
		for member in message.mentions:
			if db.unban_user(member.id):
				await post_dm(message.author, UNBAN_SUCCESS, member.name)
			else:
				await post_dm(message.author, UNBAN_DUP, member.name)

@client.command()
async def statsunban(ctx):
	message = ctx.message
	if is_admin(message.author):
		for member in message.mentions:
			if db.statsunban_user(member.id):
				await post_dm(message.author, STATSUNBAN_SUCCESS, member.name)
			else:
				await post_dm(message.author, STATSUNBAN_DUP, member.name)

@client.command(aliases=['wfu'])
async def walletfor(ctx, user: discord.Member = None, user_id: str = None):
	if user is None and user_id is None:
		await post_usage(ctx.message, WALLET_FOR)
		return
	wa = None;
	if user is not None:
		wa = db.get_address(user.id)
	else:
		wa = db.get_address(user_id)
		user = db.get_user_by_id(user_id)
	if wa is not None:
		await post_dm(ctx.message.author, "Address for user '{0}' with Discord id {1}: {2} https://creeper.banano.cc/explorer/account/{2}", user.user_name, user.user_id, wa)
	else:
		await post_dm(ctx.message.author, "Could not find address for user")

@client.command(aliases=['ufw'])
async def userforwallet(ctx, address: str):
	u = db.get_user_by_wallet_address(address)
	if u is None:
		await post_dm(ctx.message.author, "No user with that wallet address")
	else:
		await post_dm(ctx.message.author, "Address https://creeper.banano.cc/explorer/account/{0} belongs to user '{1}', discordid: {2}", address, u.user_name, u.user_id)

@client.command(aliases=['addtips', 'incrementtips'])
async def increasetips(ctx, amount: float = -1.0, user: discord.Member = None):
	if not is_admin(ctx.message.author):
		return
	u = db.get_user_by_id(user.id)
	if u is None or 0 > amount:
		await post_usage(ctx.message, INCREASETIPS)
		return
	new_total = u.tipped_amount + amount
	db.update_tip_total(user.id, new_total)
	await post_dm(ctx.message.author, "New tip total for {0} is {1:.6f}", user.name, new_total)

@client.command(aliases=['decrementtips', 'decreasetips', 'removetips'])
async def reducetips(ctx, amount: float = -1.0, user: discord.Member = None):
	if not is_admin(ctx.message.author):
		return
	u = db.get_user_by_id(user.id)
	if u is None or amount < 0:
		await post_usage(ctx.message, DECREASETIPS)
		return
	new_total = u.tipped_amount - amount
	db.update_tip_total(user.id, new_total)
	await post_dm(ctx.message.author, "New tip total for {0} is {1:.6f}", user.name, new_total)

@client.command(aliases=['incrementtipcount'])
async def increasetipcount(ctx, cnt: int = -1, user: discord.Member = None):
	if is_admin(ctx.message.author):
		u = db.get_user_by_id(user.id)
		if u is None or cnt < 0:
			await post_usage(ctx.message, INCREASETIPCOUNT)
			return
		new_cnt = u.tip_count + new_cnt
		db.update_tip_count(user.id, new_cnt)
		await post_dm(ctx.message.author, "New tip count for {0} is {1}", user.name, new_cnt)

@client.command(aliases=['decrementtipcount', 'reducetipcount'])
async def decreasetipcount(ctx, cnt: int = -1, user: discord.Member = None):
	if is_admin(ctx.message.author):
		u = db.get_user_by_id(user.id)
		if u is None or 0 > cnt:
			await post_usage(ctx.message, DECREASETIPCOUNT)
			return
		new_cnt = u.tip_count - cnt
		db.update_tip_count(user.id, new_cnt)
		await post_dm(ctx.message.author, "New tip count for {0} is {1}", user.name, new_cnt)

@client.command(aliases=['settoptips'])
async def settoptip(ctx):
	if not is_admin(ctx.message.author):
		return
	month = -1.0
	alltime = -1.0
	day = -1.0
	for split in ctx.message.content.split(' '):
		if split.startswith('month='):
			split = split.replace('month=', '').strip()
			if not split:
				continue
			try:
				month = float(split)
			except ValueError:
				pass
		elif split.startswith('alltime='):
			split = split.replace('alltime=', '').strip()
			if not split:
				continue
			try:
				alltime = float(split)
			except ValueError:
				pass
		elif split.startswith('day='):
			split = split.replace('day=', '').strip()
			if not split:
				continue
			try:
				day = float(split)
			except ValueError:
				pass
	if month == -1 and alltime == -1 and day == -1:
		await post_usage(ctx.message, SETTOPTIP)
		return
	for m in ctx.message.mentions:
		u = db.get_user_by_id(m.id)
		if u is None:
			continue
		# We use increments in db.update_top_tips so compute those
		if month == -1:
			mdelta = 0
		elif month >  u.top_tip_month:
			mdelta = month - u.top_tip_month
		elif u.top_tip_month > month:
			mdelta = -1 * (u.top_tip_month - month)
		if alltime == -1:
			adelta = 0
		elif alltime > u.top_tip:
			adelta = alltime - u.top_tip
		elif u.top_tip > alltime:
			adelta = -1 * (u.top_tip - alltime)
		if day == -1:
			ddelta = 0
		elif day > u.top_tip_day:
			ddelta = day - u.top_tip_day
		elif u.top_tip_day > day:
			ddelta = -1 * (u.top_tip_day - day)
		upd = db.update_top_tips(u.user_id, month=mdelta, alltime=adelta, day=ddelta)
		if upd > 0:
			await post_dm(ctx.message.author, "top tips for {0} adjusted successfully", u.user_name)
		else:
			await post_dm(ctx.message.author, "Could not adjust top tip for {0}", u.user_name)

@client.command()
async def arrest(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			# Tip ban too
			await do_tipban(message)
			jail = discord.utils.get(message.guild.roles,name='BANANO JAIL')
			for member in message.mentions:
				await member.add_roles(jail)
				await post_response(message, RIGHTS, mention_id=member.id)
			await message.add_reaction('\U0001f694')

@client.command()
async def release(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			# Tip unban too
			await do_tipunban(message)
			jail = discord.utils.get(message.guild.roles,name='BANANO JAIL')
			for member in message.mentions:
				await member.remove_roles(jail)
				await post_response(message, RELEASE, mention_id=member.id)

@client.command(aliases=['muzzle'])
async def silence(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			muzzled = discord.utils.get(message.guild.roles,name='muzzled')
			duration = None
			try:
				duration = find_amount(message.content)
			except util.TipBotException:
				pass
			expiration = None
			if duration is not None:
				expiration = datetime.datetime.now() + datetime.timedelta(minutes=int(duration))
			for member in message.mentions:
				if not db.silence(member.id, message.guild.id, expiration=expiration):
					await post_response(message, '<@{0}> is already muzzled', member.id)
					continue
				await member.add_roles(muzzled)
				if duration is not None:
					await post_response(message, '<@{0}> has been muzzled for {1} minutes', member.id, duration)
				else:
					await post_response(message, '<@{0}> has been muzzled indefinitely', member.id)
			await message.add_reaction('\U0001f694')

@client.command(aliases=['unmuzzle'])
async def unsilence(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			muzzled = discord.utils.get(message.guild.roles,name='muzzled')
			for member in message.mentions:
				await member.remove_roles(muzzled)
				if not db.unsilence(member.id):
					await post_response(message, '<@{0}> is not muzzled', member.id)
					continue
				await post_response(message, '<@{0}> has been unmuzzled', member.id)

@client.command()
async def citizenship(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			citizenship = discord.utils.get(message.guild.roles,name='Citizens')
			for member in message.mentions:
				await member.add_roles(citizenship)
				await post_response(message, CITIZENSHIP, mention_id=member.id)
			await message.add_reaction('\:bananorepublic:429691019538202624')

@client.command()
async def deport(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			citizenship = discord.utils.get(message.guild.roles,name='Citizens')
			for member in message.mentions:
				await member.remove_roles(citizenship)
				await post_response(message, DEPORT, mention_id=member.id)
			await message.add_reaction('\U0001F6F3')

@client.command()
async def troll(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			troll = discord.utils.get(message.guild.roles,name='Troll')
			citizenship = discord.utils.get(message.guild.roles,name='Citizens')
			for member in message.mentions:
				await member.add_roles(troll)
				await member.remove_roles(citizenship)
				await post_response(message, TROLL, mention_id=member.id)

@client.command()
async def untroll(ctx):
	message = ctx.message
	if is_admin(message.author):
		if len(message.mentions) > 0:
			troll = discord.utils.get(message.guild.roles,name='Troll')
			for member in message.mentions:
				await member.remove_roles(troll)
				await post_response(message, UNTROLL, mention_id=member.id)


### Utility Functions
def get_qr_url(text):
	return 'https://chart.googleapis.com/chart?cht=qr&chl={0}&chs=180x180&choe=UTF-8&chld=L|2'.format(text)

def find_address(input_text):
	address = input_text.split(' ')
	if len(address) == 1:
		raise util.TipBotException("address_not_found")
	elif address[1] is None:
		raise util.TipBotException("address_not_found")
	return address[1]

def find_amount(input_text):
	regex = r'(?:^|\s)(\d*\.?\d+)(?=$|\s)'
	matches = re.findall(regex, input_text, re.IGNORECASE)
	if len(matches) >= 1:
		return float(matches[0].strip())
	else:
		raise util.TipBotException("amount_not_found")

### Re-Used Discord Functions
async def post_response(message, template, *args, incl_mention=True, mention_id=None):
	if mention_id is None:
		mention_id = message.author.id
	response = template.format(*args)
	if not is_private(message.channel) and incl_mention:
		response = "<@" + str(mention_id) + "> \n" + response
	logger.info("sending response: '%s' for message: '%s' to userid: '%s' name: '%s'", response, message.content, message.author.id, message.author.name)
	asyncio.sleep(0.05) # Slight delay to avoid discord bot responding above commands
	return await message.channel.send(response)

async def post_usage(message, command):
	embed = discord.Embed(colour=discord.Colour.purple())
	embed.title = "Usage:"
	embed.add_field(name=command['CMD'], value=command['INFO'],inline=False)
	await message.author.send(embed=embed)

async def post_dm(member, template, *args, skip_dnd=False):
	response = template.format(*args)
	logger.info("sending dm: '%s' to user: %s", response, member.id)
	try:
		asyncio.sleep(0.05)
		if skip_dnd and member.status == discord.Status.dnd:
			return None
		return await member.send(response)
	except:
		return None

async def post_edit(message, template, *args):
	response = template.format(*args)
	return await message.edit(content=response)

async def remove_message(message):
	if is_private(message.channel):
		return
	client_member = message.guild.get_member(client.user.id)
	if client_member.permissions_in(message.channel).manage_messages:
		await message.delete()

async def add_x_reaction(message):
	await message.add_reaction('\U0000274C') # X
	return

async def react_to_message(message, amount):
	if amount > 0:
		await message.add_reaction('\:tip:425878628119871488') # TIP mark
		await message.add_reaction('\:tick:425880814266351626') # check mark
	if amount > 0 and amount < 50:
		await message.add_reaction('\U0001F987') # S
	elif amount >= 50 and amount < 250:
		await message.add_reaction('\U0001F412') # C
	elif amount >= 250:
		await message.add_reaction('\U0001F98D') # W

# Start the bot
client.run(settings.discord_bot_token)
