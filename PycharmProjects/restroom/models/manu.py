class MenuItem:
    def __init__(self,name,price,category:str):
        self.name = name
        self.price = price
        self.category = category
        self.status = True
    def get_info(self):
        return f'His name is {self.name}, Its price is {self.price}, The category is {self.category}'
    def  set_available(self):
        if not self.status:
            self.status = True
            return
    def is_available(self):
        return self.status



class Menu:
    def __init__(self):
        self.items = []
    def  add_item(self,menu_item):
        if menu_item in self.items:
            return
        self.items.append(menu_item)
    def remove_item(self,item_name):
        if item_name in self.items:
            self.items.pop(self.items.index(item_name))
    def get_item_by_name(self,name):
        for item in self.items:
            if item.name == name:
               return item
            continue
        print('The product was not found')
        return False
    def get_items_by_category(self,category):
        list_items = []
        for item in self.items:
            if item.category == category:
                list_items.append(item)
        return list_items
    def display_menu(self):
        items = ''
        print('The existing products are')
        for item in self.items:
            if item.status:
                items += item.name
                print(item, end=' ')
        return items
    def get_total_items(self):
        return len(self.items)