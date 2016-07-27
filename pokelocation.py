class PokeLocation:
    
    def __init__(self, api):
        self.api = api
        self.position = api.get_position()
        self.speed = 3

    def set_position(self, position):
        self.position = position
        api.set_position(*self.position)

    def get_position(self):
        return self.position

