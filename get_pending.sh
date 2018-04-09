#!/bin/bash
echo "Normal: $(sqlite3 discord.db < sql/get_pending.sql)"
echo "Giveaway: $(sqlite3 discord.db < sql/get_pending_giveaway.sql)"
