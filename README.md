# Discord Economy & Casino Bot

Production-ready Discord economy and casino bot built with **Python 3.13+**, **discord.py 2.x**, and **PostgreSQL**.

## Features

- **Economy**: balance, daily/weekly/monthly rewards, work, crime, beg, rob, deposit, withdraw, pay, profile, stats, inventory
- **Casino**: coinflip, dice, slots, roulette, blackjack, limbo, crash, plinko, mines (interactive 5×4 grid)
- **Shop & Tickets**: browse, buy, admin management, automatic ticket channels with staff ping
- **Leaderboards**: paginated richest, level, prestige, biggest win, net profit, and more
- **Events**: rain, jackpot, flash giveaway, double XP/money (automatic + admin-triggered)
- **Admin Panel**: add/remove/set balance, reset user, economy stats, events, cog reload
- **Progression**: XP, levels, streaks, achievements tracking, win streaks
- **Security**: atomic transactions, connection pooling, rate limiting, ownership validation
- **Dynamic House Edge**: wealth-tier adjustments (internal, never exposed to users)

## Requirements

- Python 3.13+
- PostgreSQL 14+
- Discord Bot Token ([Discord Developer Portal](https://discord.com/developers/applications))

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/YOUR_USERNAME/discord-economy-bot.git
cd discord-economy-bot
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy .env.example .env
```

Edit `.env`:

```env
DISCORD_TOKEN=your_bot_token
DATABASE_URL=postgresql://postgres:password@localhost:5432/discord_economy
BOT_OWNER_IDS=your_discord_user_id
DISCORD_GUILD_ID=your_guild_id   # optional, speeds up slash command sync in dev
STAFF_ROLE_ID=staff_role_id      # optional, for shop tickets
TICKET_CATEGORY_ID=category_id   # optional
```

### 3. Create Database

```sql
CREATE DATABASE discord_economy;
```

The bot automatically applies `schema.sql` on startup.

### 4. Run

```bash
python bot.py
```

## Project Structure

```
discord-economy-bot/
├── bot.py                 # Entry point
├── config.py              # Environment configuration
├── schema.sql             # PostgreSQL schema
├── cogs/                  # Slash command modules
│   ├── economy.py
│   ├── gambling.py
│   ├── shop.py
│   ├── admin.py
│   ├── leaderboards.py
│   ├── help.py
│   └── tasks.py
├── services/              # Business logic
├── repositories/          # Database access
├── views/                 # Interactive Discord UI
├── utils/                 # Embeds, currency, cooldowns
├── database/              # Connection pool
└── tests/                 # Pytest suite
```

## Commands

| Category | Commands |
|----------|----------|
| Economy | `/balance` `/daily` `/weekly` `/monthly` `/work` `/crime` `/beg` `/rob` `/deposit` `/withdraw` `/pay` `/profile` `/stats` `/inventory` |
| Gambling | `/gamble coinflip` `/gamble dice` `/gamble slots` `/gamble roulette` `/gamble blackjack` `/gamble limbo` `/gamble crash` `/gamble plinko` `/gamble mines` |
| Shop | `/shop browse` `/buy` `/shop add` `/shop remove` `/shop edit` |
| Leaderboards | `/leaderboard` |
| Admin | `/admin addmoney` `/admin removemoney` `/admin setbalance` `/admin resetuser` `/admin stats` `/admin event` `/admin reload` |
| Help | `/help` |

## Development

```bash
# Lint
ruff check .
black .

# Test
pytest -v
```

## Economy Constants

| Setting | Value |
|---------|-------|
| Starting Balance | $0.10 |
| Daily Reward | $0.10 |
| Weekly Reward | $1.00 |
| Monthly Reward | $5.00 |
| Pay Tax | 2% |

## Scaling Notes

- asyncpg connection pool (5–50 connections)
- Prepared statements via parameterized queries
- Indexed leaderboard and transaction queries
- Interaction deferral for long-running commands
- Rate limiting per user
- Background event/cleanup tasks

## License

MIT
