from confluent_kafka import Producer
import random
import uuid
import json

producer = Producer({
    "bootstrap.servers": "localhost:9092"
})

customers = ["Alice", "Bob", "Charlie", "John", "Anne", "Michael"]
products = ["Laptop", "TV", "Book", "Lamp", "Cup", "Toilet paper", "Cookies", "Table"]


for i in range(20):
    order = {
        "order_id": str(uuid.uuid4()),
        "customer": random.choice(customers),
        "product": random.choice(products),
        "quantity": random.randint(1, 100),
        "price": random.random() * 1000
    }

    producer.produce(
        topic="orders",
        key=order["customer"],
        value=json.dumps(order)
    )

producer.flush()
