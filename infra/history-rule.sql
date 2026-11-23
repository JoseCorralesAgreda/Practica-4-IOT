SELECT state.reported AS reported, topic(3) AS thingName, timestamp() AS receivedAtMs
FROM '$aws/things/+/shadow/update/accepted'
WHERE state.reported.schemaVersion = 4
AND clientToken = state.reported.messageId
