SET allow_experimental_object_type = 1;

CREATE TABLE ${db_table} (
  app String,
  level String,
  path String,
  message String,
  props JSON DEFAULT '{}',

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
