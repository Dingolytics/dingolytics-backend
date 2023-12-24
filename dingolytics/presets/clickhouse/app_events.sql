SET allow_experimental_object_type = 1;

CREATE TABLE {db_table} (
  app String,
  name String,
  path String,
  props JSON DEFAULT '{}',
  user_id Nullable(String),
  user_props JSON DEFAULT '{}',

  browser_agent Nullable(String),
  browser_name Nullable(String),
  browser_version Nullable(String),
  is_mobile Nullable(UInt8),
  os_name Nullable(String),
  os_version Nullable(String),
  referrer Nullable(String),

  timestamp DateTime64(3) DEFAULT now(),
  month UInt32 DEFAULT toYYYYMM(timestamp)
) ENGINE = MergeTree()
PARTITION BY month
ORDER BY (timestamp, app, path);
