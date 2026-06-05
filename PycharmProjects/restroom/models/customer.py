class Customer:
    def __init__(self,name):
        self.name = name
        self.satisfaction = 50
    def increase_satisfaction(self,amount: int):
        if self.satisfaction + amount > 100:
            print('The number is too large')
            return
        self.satisfaction += amount
        return
    def decrease_satisfaction(self,amount):
        if self.satisfaction - amount < 0:
            print('The number is too large')
            return
        self.satisfaction -= amount
        return
    def is_happy(self):
        if self.satisfaction > 70:
            return  True
        return False
    def get_info(self):
        print(f'customer name: {self.name} Satisfaction level: {self.satisfaction}')
