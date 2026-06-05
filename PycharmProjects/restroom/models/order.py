import customer
import manu

class Order:
    def __init__(self,customer:customer.Customer,order_number,menu:manu.Menu):
        super().__init__()
        self.customer = customer
        self.order_number = order_number
        self.items = []
        self.status = 'pending'
        self.total_price = 0
        self.menu = menu
    def add_item(self,menu_item: manu.MenuItem):
        self.items.append(menu_item)
        self.total_price += menu_item.price
    def remove_item(self,menu_item):
        self.items.pop(self.items.index(menu_item))
        self.total_price -= menu_item.price
    def  get_total(self):
        return self.total_price
    def set_status(self,new_status):
        self.status = new_status
    def display_order(self):
        print(f'{self.order_number}{self.customer}{self.items}{self.total_price}{self.status}')