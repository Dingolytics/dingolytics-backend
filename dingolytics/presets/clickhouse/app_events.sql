CREATE TABLE ${db_table} (
  app String,
  name String,
  path String,
  attrs JSON DEFAULT '{}',
  user_id Nullable(String),
  client_agent Nullable(String),
  client_name Nullable(String),
  client_version Nullable(String),
  is_mobile Nullable(UInt8),
  os_name Nullable(String),
  os_version Nullable(String),
  referrer Nullable(String),
  timestamp DateTime64(3) DEFAULT now(),
  month UInt32 DEFAULT toYYYYMM(timestamp)
) ENGINE = MergeTree()
PARTITION BY month
ORDER BY (timestamp, app, path);
