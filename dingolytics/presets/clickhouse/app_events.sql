CREATE TABLE {db_table} (
  timestamp DateTime64(3),
  level String,
  message String,
  platform String,
  application String,
  path String
) ENGINE = MergeTree() ORDER BY (timestamp);
