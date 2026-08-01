-- Discord Economy Bot PostgreSQL Schema

CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    wallet NUMERIC(20, 2) NOT NULL DEFAULT 0.10,
    bank NUMERIC(20, 2) NOT NULL DEFAULT 0.00,
    xp BIGINT NOT NULL DEFAULT 0,
    level INT NOT NULL DEFAULT 1,
    prestige INT NOT NULL DEFAULT 0,
    title VARCHAR(100) DEFAULT 'Novice',
    daily_streak INT NOT NULL DEFAULT 0,
    weekly_streak INT NOT NULL DEFAULT 0,
    last_daily TIMESTAMPTZ,
    last_weekly TIMESTAMPTZ,
    last_monthly TIMESTAMPTZ,
    last_work TIMESTAMPTZ,
    last_crime TIMESTAMPTZ,
    last_beg TIMESTAMPTZ,
    last_rob TIMESTAMPTZ,
    win_streak INT NOT NULL DEFAULT 0,
    best_win_streak INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_guild_wallet ON users(guild_id, wallet DESC);
CREATE INDEX IF NOT EXISTS idx_users_guild_level ON users(guild_id, level DESC);
CREATE INDEX IF NOT EXISTS idx_users_guild_prestige ON users(guild_id, prestige DESC);

CREATE TABLE IF NOT EXISTS transactions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    guild_id BIGINT NOT NULL,
    amount NUMERIC(20, 2) NOT NULL,
    balance_after NUMERIC(20, 2) NOT NULL,
    tx_type VARCHAR(50) NOT NULL,
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_transactions_guild ON transactions(guild_id, created_at DESC);

CREATE TABLE IF NOT EXISTS inventory (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    item_key VARCHAR(100) NOT NULL,
    item_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}',
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, item_key)
);

CREATE TABLE IF NOT EXISTS shop_items (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    price NUMERIC(20, 2) NOT NULL,
    category VARCHAR(100) DEFAULT 'general',
    stock INT DEFAULT -1,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_guild ON shop_items(guild_id, active);

CREATE TABLE IF NOT EXISTS purchases (
    id BIGSERIAL PRIMARY KEY,
    purchase_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    shop_item_id INT REFERENCES shop_items(id),
    item_name VARCHAR(200) NOT NULL,
    price NUMERIC(20, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    ticket_channel_id BIGINT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tickets (
    id BIGSERIAL PRIMARY KEY,
    channel_id BIGINT NOT NULL UNIQUE,
    purchase_id UUID REFERENCES purchases(purchase_id),
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'open',
    staff_ids BIGINT[] DEFAULT '{}',
    transcript TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS game_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    bet_amount NUMERIC(20, 2) NOT NULL,
    state JSONB NOT NULL DEFAULT '{}',
    active BOOLEAN NOT NULL DEFAULT TRUE,
    seed VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_sessions_user ON game_sessions(user_id, active);

CREATE TABLE IF NOT EXISTS game_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    guild_id BIGINT NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    bet_amount NUMERIC(20, 2) NOT NULL,
    payout NUMERIC(20, 2) NOT NULL DEFAULT 0,
    won BOOLEAN NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_game_history_user ON game_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_game_history_guild_win ON game_history(guild_id, payout DESC);

CREATE TABLE IF NOT EXISTS achievements (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    achievement_key VARCHAR(100) NOT NULL,
    unlocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, achievement_key)
);

CREATE TABLE IF NOT EXISTS user_stats (
    user_id BIGINT PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
    money_earned NUMERIC(20, 2) NOT NULL DEFAULT 0,
    money_lost NUMERIC(20, 2) NOT NULL DEFAULT 0,
    games_played INT NOT NULL DEFAULT 0,
    games_won INT NOT NULL DEFAULT 0,
    biggest_win NUMERIC(20, 2) NOT NULL DEFAULT 0,
    biggest_loss NUMERIC(20, 2) NOT NULL DEFAULT 0,
    commands_used INT NOT NULL DEFAULT 0,
    hours_played NUMERIC(10, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS guild_settings (
    guild_id BIGINT PRIMARY KEY,
    config JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    guild_id BIGINT,
    actor_id BIGINT,
    action VARCHAR(100) NOT NULL,
    target_id BIGINT,
    details JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS active_events (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    multiplier NUMERIC(5, 2) NOT NULL DEFAULT 1.00,
    ends_at TIMESTAMPTZ NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Default shop items seed function
CREATE OR REPLACE FUNCTION seed_default_shop(p_guild_id BIGINT) RETURNS VOID AS $$
BEGIN
    INSERT INTO shop_items (guild_id, name, description, price, category) VALUES
        (p_guild_id, 'Roblox Gift Card', 'Digital Roblox gift card delivery', 10.00, 'gaming'),
        (p_guild_id, 'Netflix 1 Month', 'Netflix subscription code', 15.00, 'streaming'),
        (p_guild_id, 'Disney+ 1 Month', 'Disney+ subscription code', 12.00, 'streaming'),
        (p_guild_id, 'Crunchyroll 1 Month', 'Crunchyroll premium code', 8.00, 'streaming')
    ON CONFLICT DO NOTHING;
END;
$$ LANGUAGE plpgsql;
