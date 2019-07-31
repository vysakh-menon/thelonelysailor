DROP TABLE IF EXISTS DeviceMessage;

CREATE TABLE DeviceMessage (
  id INTEGER PRIMARY KEY,
  messengerId TEXT NOT NULL,
  messengerName TEXT NOT NULL,
  unixTime INTEGER NOT NULL,
  messageType TEXT NOT NULL,
  latitude DECIMAL(10,6) NOT NULL,
  longitude DECIMAL(10,6) NOT NULL,
  modelId TEXT NOT NULL,
  showCustomMsg TEXT NOT NULL,
  [dateTime] TEXT NOT NULL,
  batteryState TEXT NOT NULL,
  [hidden] TEXT NOT NULL,
  altitude TEXT NOT NULL,
  kph TEXT NULL,
  comments TEXT NULL
);