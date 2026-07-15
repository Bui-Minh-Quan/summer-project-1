from confluent_kafka.admin import AdminClient

admin = AdminClient({"bootstrap.servers": "localhost:9092"})

# Fetch metadata for the entire cluster (timeout in seconds)
cluster_metadata = admin.list_topics(timeout=5.0)

topic_name = "orders"

# Check if the topic exists in the metadata
if topic_name in cluster_metadata.topics:
    topic_info = cluster_metadata.topics[topic_name]
    
    # Access the partitions dictionary
    partitions = topic_info.partitions
    partition_count = len(partitions)
    
    print(f"Topic '{topic_name}' has {partition_count} partitions.")
    print(f"Partition IDs: {list(partitions.keys())}")
else:
    print(f"Topic '{topic_name}' does not exist.")