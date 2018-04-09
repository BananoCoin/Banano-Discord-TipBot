#!/bin/bash

sqlite3 discord.db < sql/reset_pending.sql
