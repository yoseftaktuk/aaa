import manu
import order
import random
import staf
class Restaurant:
    def __init__(self,name):
        self.name = name
        self.manu = manu.Menu()
        self.staff = []
        self.ordes = []
        self.money = 1000
        self.order = None
    def hire_staff(self,staff_member):
        self.staff.append(staff_member)
    def fire_staff(self,staff_name):
        self.staff.pop(self.staff.index(staff_name))
    def create_order(self,customer):
        self.order = order.Order(customer,random.randint(1,60),self.manu)
        self.ordes.append(self)
    def process_order(self):
        for staff in self.staff:
            if staff.role == 'chef' and not staff.is_tired():
               staff.cook_order(self.order)
        for staff in self.staff:
            if staff.role == 'waiter' and not staff.is_tired():
                staff.work()
    def complete_order(self):
        self.money += self.order.get_total()
        self.ordes.pop(self.ordes.index(self.order))
    def pay_salaries(self):
        for staff in self.staff:
            self.money -= staff.get_salary()
    def get_statistics(self):
        return {
            'total_ordes': self.ordes,
            'money': self.money,
            'staff_count': len(self.staff),
            'manu': self.manu.get_total_items()
        }
    def display_status(self):
        print(f'name: {self.name}, money: {self.money} ordes: {self.ordes} staff: {self.staff}')


a = Restaurant('piza')
b = staf.Waiter('a',100)
c = staf.Chef('yosef',200,'s')
a.hire_staff(b)
a.hire_staff(c)
print(a.staff)
a.display_status()






