# Lab 1 submission

import queue
import random
import time
from flask import Flask, request
import threading
import requests

time_unit = 1

menu = [{
    "id": 1,
    "name": "pizza",
    "preparation-time": 20,
    "complexity": 2,
    "cooking-apparatus": "oven"
}, {
    "id": 2,
    "name": "salad",
    "preparation-time": 10,
    "complexity": 1,
    "cooking-apparatus": None
}, {
    "id": 4,
    "name": "Scallop Sashimi with Meyer Lemon Confit",
    "preparation-time": 32,
    "complexity": 3,
    "cooking-apparatus": None
}, {
    "id": 5,
    "name": "Island Duck with Mulberry Mustard",
    "preparation-time": 35,
    "complexity": 3,
    "cooking-apparatus": "oven"
}, {
    "id": 6,
    "name": "Waffles",
    "preparation-time": 10,
    "complexity": 1,
    "cooking-apparatus": "stove"
}, {
    "id": 7,
    "name": "Aubergine",
    "preparation-time": 20,
    "complexity": 2,
    "cooking-apparatus": None
}, {
    "id": 8,
    "name": "Lasagna",
    "preparation-time": 30,
    "complexity": 2,
    "cooking-apparatus": "oven"
}, {
    "id": 9,
    "name": "Burger",
    "preparation-time": 15,
    "complexity": 1,
    "cooking-apparatus": "oven"
}, {
    "id": 10,
    "name": "Gyros",
    "preparation-time": 15,
    "complexity": 1,
    "cooking-apparatus": None
}]

table_state0 = 'being free'
table_state1 = 'waiting to make a order'
table_state2 = 'waiting for the order to be served'
table_state3 = 'waiting to be free'
tables_list = [{
    "id": 1,
    "state": table_state0,
    "order_id": None
}, {
    "id": 2,
    "state": table_state0,
    "order_id": None
}, {
    "id": 3,
    "state": table_state0,
    "order_id": None
}, {
    "id": 4,
    "state": table_state0,
    "order_id": None
}, {
    "id": 5,
    "state": table_state0,
    "order_id": None
}]

waiters = [{
    'id': 1,
    'name': 'Anna'
}, {
    'id': 2,
    'name': 'Melisa'
}, {
    'id': 3,
    'name': 'Alexandru'
}, {
    'id': 4,
    'name': 'Jeka'
}]

orders = queue.Queue()
orders.join()
orders_bundle = []
orders_done = []
order_rating = []

app = Flask(__name__)
threads = []


@app.route('/distribution', methods=['POST'])
def distribution():
    order = request.get_json()
    print(f'Received order from kitchen. Order ID: {order["order_id"]} items: {order["items"]} ')
    table_id = next((i for i, table in enumerate(tables_list) if table['id'] == order['table_id']), None)
    tables_list[table_id]['state'] = table_state2
    # get the waiter thread and serve order
    waiter_thread: Waiter = next((w for w in threads if type(w) == Waiter and w.id == order['waiter_id']), None)
    waiter_thread.serve_order(order)  #
    return {'isSuccess': True}


class Waiter(threading.Thread):
    def __init__(self, data, *args, **kwargs):
        super(Waiter, self).__init__(*args, **kwargs)
        self.id = data['id']
        self.name = data['name']
        self.daemon = True

    def run(self):
        while True:
            self.search_order()

    def search_order(self):
        try:
            order = orders.get()
            orders.task_done()
            table_id = next((i for i, table in enumerate(tables_list) if table['id'] == order['table_id']), None)
            print(
                f'{threading.current_thread().name} has taken the order with Id: {order["id"]} | priority: {order["priority"]} | items: {order["items"]} ')
            tables_list[table_id]['state'] = table_state2
            payload = dict({
                'order_id': order['id'],
                'table_id': order['table_id'],
                'waiter_id': self.id,
                'items': order['items'],
                'priority': order['priority'],
                'max_wait': order['max_wait'],
                'time_start': time.time()
            })

            time.sleep(random.randint(2, 4) * time_unit)
            # send order to kitchen
            requests.post('http://localhost:3030/order', json=payload, timeout=0.0000000001)

        except (queue.Empty, requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
            pass

    def serve_order(self, desired_order):
        # check if the order is the same order that what was requested
        received_order = next(
            (order for i, order in enumerate(orders_bundle) if order['id'] == desired_order['order_id']), None)
        if received_order is not None and received_order['items'].sort() == desired_order['items'].sort():
            # update table state
            table_id = next((i for i, table in enumerate(tables_list) if table['id'] == desired_order['table_id']),
                            None)
            tables_list[table_id]['state'] = table_state3
            order_serving_timestamp = int(time.time())
            order_pick_up_timestamp = int(desired_order['time_start'])
            # calculate total order time
            Order_total_preparing_time = order_serving_timestamp - order_pick_up_timestamp

            # calculate nr of start
            order_stars = {'order_id': desired_order['order_id']}
            if desired_order['max_wait'] > Order_total_preparing_time:
                order_stars['star'] = 5
            elif desired_order['max_wait'] * 1.1 > Order_total_preparing_time:
                order_stars['star'] = 4
            elif desired_order['max_wait'] * 1.2 > Order_total_preparing_time:
                order_stars['star'] = 3
            elif desired_order['max_wait'] * 1.3 > Order_total_preparing_time:
                order_stars['star'] = 2
            elif desired_order['max_wait'] * 1.4 > Order_total_preparing_time:
                order_stars['star'] = 1
            else:
                order_stars['star'] = 0

            order_rating.append(order_stars)
            sum_stars = sum(feedback['star'] for feedback in order_rating)
            avg = float(sum_stars / len(order_rating))

            served_order = {**desired_order, 'Serving_time': Order_total_preparing_time, 'status': 'DONE',
                            'Stars_feedback': order_stars}
            orders_done.append(served_order)
            # add to see the rating
            print(f'Serving the order Endpoint: /distribution :\n'
                  f'Order Id: {served_order["order_id"]}\n'
                  f'Waiter Id: {served_order["waiter_id"]}\n'
                  f'Table Id: {served_order["table_id"]}\n'
                  f'Items: {served_order["items"]}\n'
                  f'Priority: {served_order["priority"]}\n'
                  f'Max Wait: {served_order["max_wait"]}\n'
                  f'Waiting time: {served_order["Serving_time"]}\n'
                  f'Stars: {served_order["Stars_feedback"]}\n'
                  f'Restaurant rating: {avg}')

        else:
            raise Exception(
                f'Error. Provide the original order to costumer. Original: {received_order}, given: {desired_order}')


class Costumers(threading.Thread):
    def __init__(self, *args, **kwargs):
        super(Costumers, self).__init__(*args, **kwargs)

    def run(self):
        while True:
            time.sleep(1)
            self.create_order()

    @staticmethod
    def create_order():
        (table_id, table) = next(
            ((idx, table) for idx, table in enumerate(tables_list) if table['state'] == table_state0), (None, None))
        if table_id is not None:
            max_wait_time = 0
            food_choices = []
            for i in range(random.randint(1, 5)):
                choice = random.choice(menu)
                if max_wait_time < choice['preparation-time']:
                    max_wait_time = choice['preparation-time']
                food_choices.append(choice['id'])
            max_wait_time = max_wait_time * 1.3
            neworder_id = int(random.randint(1, 10000) * random.randint(1, 10000))
            neworder = {
                'table_id': table['id'],
                'id': neworder_id,
                'items': food_choices,
                'priority': random.randint(1, 5),
                'max_wait': max_wait_time,

            }
            orders.put(neworder)
            # orders_bundle to verify the order after receiving it from kitchen
            orders_bundle.append(neworder)

            tables_list[table_id]['state'] = table_state1
            tables_list[table_id]['order_id'] = neworder_id

        else:
            time.sleep(random.randint(2, 10) * time_unit)
            (table_id, table) = next(
                ((idx, table) for idx, table in enumerate(tables_list) if table['state'] == table_state3), (None, None))
            if table_id is not None:
                tables_list[table_id]['state'] = table_state0



def run_dinninghall_server():
    main_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=3000, debug=False, use_reloader=False),
                                   daemon=True)
    threads.append(main_thread)
    costumer_thread = Costumers()
    threads.append(costumer_thread)
    for _, w in enumerate(waiters):
        waiter_thread = Waiter(w)
        threads.append(waiter_thread)
    for th in threads:
        th.start()
    for th in threads:
        th.join()


if __name__ == '__main__':
    run_dinninghall_server()
