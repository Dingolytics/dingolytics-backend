CREATE TABLE ${db_table} (
  timestamp DateTime64(3) DEFAULT now(),
  message String DEFAULT '',
  host String DEFAULT '',
  pid UInt32 DEFAULT 0,
  metadata JSON DEFAULT '{}',
) ENGINE = MergeTree()
ORDER BY (timestamp, host);
