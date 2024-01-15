CREATE TABLE ${db_table} (
  app String,
  level String,
  path String,
  message String,
  attrs_raw Nullable(String),

  ip_addr_v4 Nullable(IPv4),
  ip_addr_v6 Nullable(IPv6),
  client_id Nullable(String),
  client_name Nullable(String),
  client_user_agent Nullable(String),
  client_version Nullable(String),
  is_mobile Nullable(UInt8),
  os_name Nullable(String),
  os_version Nullable(String),
  referrer Nullable(String),

  timestamp DateTime64(3) DEFAULT now(),
) ENGINE = MergeTree()
ORDER BY (timestamp, app, path);
