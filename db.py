import datetime
import util
from peewee import *

# (Seconds) how long a user must wait in between messaging the bot
LAST_MSG_TIME = 1

db = SqliteDatabase('bananotipbot.db')

logger = util.get_logger("db")

### User Stuff
def get_user_by_id(user_id):
    try:
        user = User.get(user_id=user_id)
        return user
    except User.DoesNotExist:
        # logger.debug('user %s does not exist !', user_id)
        return None


def get_user_by_wallet_address(address):
    try:
        user = User.get(wallet_address=address)
        return user
    except User.DoesNotExist:
        # logger.debug('wallet %s does not exist !', address)
        return None


def get_top_users(count):
    users = User.select().where(User.tipped_amount > 0).order_by(User.tipped_amount.desc()).limit(count)
    return_data = []
    for idx, user in enumerate(users):
        return_data.append({'index': idx + 1, 'name': user.user_name, 'amount': user.tipped_amount})
    return return_data

def update_pending(user_id, send, receive):
    user = get_user_by_id(user_id)
    if user is None:
        return False
    user.pending_send += send
    user.pending_receive += receive
    user.save()
    return True

def create_user(user_id, user_name, wallet_address):
    user = User(user_id=user_id,
                user_name=user_name,
                wallet_address=wallet_address,
                tipped_amount=0.0,
                wallet_balance=0.0,
                pending_receive=0.0,
                pending_send=0.0,
                created=datetime.datetime.now(),
		last_msg=datetime.datetime.now()
                )
    user.save()
    return user

### Transaction Stuff
def create_transaction(uuid, source_addr, to_addr, amt):
    tx = Transaction(uid=uuid,
                     source_address=source_addr,
                     to_address=to_addr,
                     amount=amt,
                     processed=False,
                     created=datetime.datetime.now()
                    )
    tx.save()
    return tx

def get_unprocessed_transactions():
    txs = Transaction.select().where(Transaction.processed == False).order_by(Transaction.created.desc())
    return_data = []
    for idx, tx in enumerate(txs):
        return_data.append({'uid':tx.uid,'source_address':tx.source_address,'to_address':tx.to_address,'amount':tx.amount})
    return return_data

# You may think, this imposes serious double spend risks:
#  ie. if a transaction actually has been processed, but has never been marked processed in the database
#  This shouldn't happen even in that scenario, due to the id (uid here) field in nano node v10
def mark_transaction_processed(uuid):
    with db.atomic() as transaction:
        try:
            tx = Transaction.get(uid=uuid)
            if tx is not None:
                tx.processed=True
                tx.save()
            return
        except Exception as e:
            db.rollback()
            logger.exception(e)
            return

# Return false if last message was < LAST_MSG_TIME
# If > LAST_MSG_TIME, return True and update the user
# Also return true, if user does not have a tip bot acct yet
def last_msg_check(user_id):
    user = get_user_by_id(user_id)
    if user is None:
        return True
    # Get difference in seconds between now and last msg
    since_last_msg_s = (datetime.datetime.now() - user.last_msg).total_seconds()
    if since_last_msg_s < LAST_MSG_TIME:
        return False
    else:
        update_last_msg(user)
    return True

def update_last_msg(user):
    with db.atomic() as transaction:
        try:
            if user is not None:
                user.last_msg=datetime.datetime.now()
                user.save()
            return
        except Exception as e:
            db.rollback()
            logger.exception(e)
            return

# Update tip amount for stats (this value is saved as NANO not xrb)
def update_tipped_amt(user_id, tipped_amt):
    with db.atomic() as transaction:
        try:
            user = get_user_by_id(user_id)
            if user is not None:
                user.tipped_amount += tipped_amt
                user.save()
            return
        except Exception as e:
            db.rollback()
            logger.exception(e)
            return

# User table
class User(Model):
    user_id = CharField()
    user_name = CharField()
    wallet_address = CharField()
    tipped_amount = FloatField()
    wallet_balance = FloatField()
    pending_receive = IntegerField()
    pending_send = IntegerField()
    created = DateTimeField()
    last_msg = DateTimeField()

    class Meta:
        database = db

# Transaction table, keep trac of sends to process
class Transaction(Model):
    uid = CharField()
    source_address = CharField()
    to_address = CharField()
    amount = CharField()
    processed = BooleanField()
    created = DateTimeField()

    class Meta:
        database = db

def create_db():
    db.connect()
    db.create_tables([User, Transaction], safe=True)


create_db()
