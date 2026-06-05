from models.order import Order


class StaffBase:
    def __init__(self,name, salary):
        self.name = name
        self.salary = salary
        self.energy = 100
    def get_salary(self):
        return self.salary
    def work(self):
        if self.energy > 10:
            self.energy -= 10
            print('The worker works',self.energy)
            return
        print('The employee has no more power.')
    def rest(self):
        self.energy += 20
    def is_tired(self):
        if self.energy < 30:
            return True
        return False
    def get_info(self):
        return f'name: {self.name}salary: {self.salary}energy: {self.energy}'

import time
class Chef(StaffBase):
    def __init__(self,name, salary,specialty: str):
        super().__init__(name, salary)
        self.specialty = specialty
        self.role = 'chef'
    def cook_order(self,order):
        order.status = 'cooking'
        print('cooking..')
        time.sleep(2)
        order.status = 'ready'
        print('ready')
        Chef.work(self)
    def override_work(self):
        if self.energy < 15:
            print('The chef is immediately tired.')
            return
        self.energy -= 15
import random
class Waiter(StaffBase):
    def __init__(self,name,salary):
        super().__init__(name,salary)
        self.tips = 0
        self.role = 'waiter'
    def take_order(self,customer, menu):
        order = Order(customer,random.randint(0,60),menu)
        Waiter.work(self)
        while True:
            customer_pick = input('Enter a product name')
            if customer_pick == 'q':
                return order
            order.add_item(menu.get_item_by_name(customer_pick))
        return
    def serve_order(self,order):
        self.staus = 'delivered'
    def receive_tip(self,amount):
        self.tips += amount
    def get_total_earnings(self):
        return self.salary + self.tips
