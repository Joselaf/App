import tinytuya

cloud = tinytuya.Cloud(apiRegion='eu', apiKey='c8uhx3vs89grhea8mg7p', apiSecret='7221603a3b754d8b89b30c8dc9114b0d')
print('devices count', len(cloud.getdevices()))
print('mqtt config', cloud.getmqttconfig())
