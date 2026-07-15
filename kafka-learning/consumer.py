from confluent_kafka import Consumer
import json

consumer = Consumer({
    "bootstrap.servers": "localhost:9092",
    "group.id": "my-group",
    "auto.offset.reset": "earliest"
})

consumer.subscribe(["orders"])

print("Consumer started...")

try:
    while True:
        msg = consumer.poll(1.0)

        if msg is None:
            continue

        if msg.error():
            print(msg.error())
            continue

        order = json.loads(msg.value())

        print(
            f"Partition: {msg.partition()} ",
            f"Customer: {order['customer'] if order['customer'] else None} ",
            f"Product: {order['product'] if order['product'] else None} ",
            f"Order value: {order['quantity'] * order['price'] 
                            if order['quantity'] and order['price'] else 0:.2f}"
        )

except KeyboardInterrupt:
    print("Stopping consumer...")

finally:
    consumer.close()